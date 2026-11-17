"""Propriete des ressources ; les decisions demeurent dans les blocs geles."""
from dataclasses import replace
from hashlib import sha1,sha256
from pathlib import Path
import importlib,os
from xpbots.infra.c0a_types import ErreurInfra,champ_natif,entier_natif
from xpbots.infra.c0b_horloge import HorlogeSysteme
from xpbots.infra.c0c_sqlite import DepotSQLite
from xpbots.infra.c0d_journal import JournalFichiers,lire_json,ecrire_json,alerter
from xpbots.infra.c0e_snapshot import LecteurSnapshot
from xpbots.infra.c0g_controles import SourcesControles
from xpbots.infra.c0h_verrou import VerrouProcessus
from xpbots.infra.c1_session import SessionMT5
from xpbots.infra.c3_courtier import CourtierMT5
from xpbots.noyau.c0c_configuration import ParametresCommuns
from ._fichiers import ouvrir_ticks


def _hex(v,longueurs):
    return type(v) is str and len(v) in longueurs and all(c in '0123456789abcdef' for c in v)


def _meta(meta):
    if type(meta) is not dict or set(meta)!={'deploiement','mode','empreintes','commit'}:raise ErreurInfra('META_DEPLOIEMENT_INVALIDE')
    if type(meta['mode']) is not str or type(meta['empreintes']) is not dict or set(meta['empreintes'])!={'technique','ia'}:
        raise ErreurInfra('META_DEPLOIEMENT_INVALIDE')
    tailles=(len(sha1().hexdigest()),len(sha256().hexdigest()))
    if not _hex(meta['commit'],tailles) or any(not _hex(v,(len(sha256().hexdigest()),)) for v in meta['empreintes'].values()):
        raise ErreurInfra('EMPREINTES_DEPLOIEMENT_INVALIDES')
    return dict(deploiement=meta['deploiement'],mode=meta['mode'],empreintes=dict(meta['empreintes']),commit=meta['commit'])


class InfrastructurePhysique:
    def __init__(self,commun,meta,liaisons,*,racine,max_octets_echange,snapshot_max_octets,
            sdk=None,chemin_terminal=None,common_files_attendu=None):
        if not isinstance(commun,ParametresCommuns):raise ErreurInfra('PARAMETRES_COMMUNS_REELS_REQUIS')
        self._meta=_meta(meta);self._commun=commun;self._courtier=None;self._session=None
        self._depot=None;self._verrou=None;self._fermee=False;self.horloge=HorlogeSysteme()
        try:
            self._racine=Path(racine).resolve()
            if not self._racine.is_dir():raise ErreurInfra('RACINE_PHYSIQUE_INVALIDE')
            self._journal=JournalFichiers(self._racine,self._meta['deploiement'])
            self._chemin_etat=self._racine/'runtime'/self._meta['deploiement']/'etat.sqlite'
            if sdk is None:
                try:sdk=importlib.import_module('MetaTrader5')
                except Exception:raise ErreurInfra('SDK_MT5_INDISPONIBLE') from None
            attendu=common_files_attendu if common_files_attendu is not None else os.environ.get('XPBOTS_COMMON_FILES_DIR')
            self._session=SessionMT5(sdk,self._meta['mode'],chemin_terminal=chemin_terminal,common_files_attendu=attendu)
            statut=self._session.attacher();commun_files=Path(statut.common_files)
            self._controles=SourcesControles(commun_files,liaisons,max_octets_echange)
            self._snapshot=LecteurSnapshot(commun_files/'XPBots/ai/v1/context_latest.json',snapshot_max_octets)
            self._liaisons=dict(self._controles.liaisons)
            execution=commun_files/'XPBots/execution/v1'
            self._verrou=VerrouProcessus(execution/'coordinateur.lock');self._verrou.acquerir()
            compte=self._session.appeler('account_info')
            serveur=champ_natif(compte,'server');numero=entier_natif(champ_natif(compte,'login'))
            if type(serveur) is not str or not serveur or numero<=0:raise ErreurInfra('IDENTITE_COMPTE_INCOMPLETE')
            self.empreinte_compte_sha256=sha256((serveur+'\0'+str(numero)).encode('utf-8')).hexdigest()
            attendu=dict(schema='xp-proprietaire-compte-v1',empreinte_compte_sha256=self.empreinte_compte_sha256,
                deploiement=self._meta['deploiement'],chemin_etat_sha256=sha256(os.path.normcase(str(self._chemin_etat.resolve())).encode('utf-8')).hexdigest())
            liaison=execution/('proprietaire_'+self.empreinte_compte_sha256+'.json')
            natif=self._meta['mode'] in ('DEMO','REEL')
            existe=liaison.exists() if natif else False
            if existe:
                if lire_json(liaison,max_octets_echange)!=attendu:raise ErreurInfra('PROPRIETE_COMPTE_INCOMPATIBLE')
                if not self._chemin_etat.is_file():raise ErreurInfra('ETAT_COMPTE_PERSISTANT_ABSENT')
            self._depot=DepotSQLite(self._chemin_etat,dict(self._meta,empreinte_compte_sha256=self.empreinte_compte_sha256))
            self._journal.publier(self._depot.evenements())
            if natif and not existe:ecrire_json(liaison,attendu)
            for code in statut.alertes:alerter(code,'DOSSIER_COMMUN_NATIF_CONSERVE')
        except BaseException as erreur:
            try:self.fermer(0)
            except Exception:pass
            if isinstance(erreur,(KeyboardInterrupt,SystemExit)):raise
            if isinstance(erreur,ErreurInfra):raise
            raise ErreurInfra('INITIALISATION_PHYSIQUE_REFUSEE') from None

    @property
    def meta(self):return dict(self._meta,empreintes=dict(self._meta['empreintes']))
    @property
    def session(self):return self._session
    @property
    def depot(self):return self._depot
    @property
    def journal(self):return self._journal
    @property
    def courtier(self):
        if self._courtier is None:raise ErreurInfra('COURTIER_NON_INITIALISE')
        return self._courtier

    def _ouverte(self):
        if self._fermee:raise ErreurInfra('INFRASTRUCTURE_FERMEE')

    def initialiser_courtier(self,table,qualification,parametres,*,etat=None):
        self._ouverte()
        if self._courtier is not None:raise ErreurInfra('COURTIER_DEJA_INITIALISE')
        if type(parametres) is not dict:raise ErreurInfra('PARAMETRES_COURTIER_INCOMPLETS')
        requis={'departs_ticks_utc_ms','depuis_historique_compte_utc_ms','seances_max_age_ms','fermetures_max_age_ms',
            'max_jours_horaires','ecart_horloges_max_ms','taille_lot','max_ticks_lot','longueur_empreinte','max_taches_natives'}
        if set(parametres)!=requis:raise ErreurInfra('PARAMETRES_COURTIER_INCOMPLETS')
        c=CourtierMT5(self._session,self._commun,table,self._liaisons,self.horloge,self.horloge.utc_ms(),
            qualification=qualification,etat=etat,**parametres)
        if (c.execution.exporter_etat()['empreinte_compte_sha256']!=self.empreinte_compte_sha256
                or qualification['compte']['empreinte_compte_sha256']!=self.empreinte_compte_sha256):
            c.fermer(0);raise ErreurInfra('COMPTE_COURTIER_INCOMPATIBLE')
        self._courtier=c
        return c

    def lire_controles(self):
        self._ouverte();r=self._controles.lire(self.horloge.utc_ms());connu=self.horloge.utc_ms()
        return tuple(replace(v,instant_ms=connu) for v in r)

    def lire_snapshot(self):
        self._ouverte();b,_,erreur=self._snapshot.lire(self.horloge.utc_ms())
        return b,self.horloge.utc_ms(),erreur

    def lecture_ticks(self,chemin):self._ouverte();return ouvrir_ticks(chemin)

    def fermer(self,attente_ms):
        if type(attente_ms) is not int or attente_ms<0:raise ErreurInfra('ATTENTE_ARRET_INVALIDE')
        if self._fermee:return True
        if self._courtier is not None and not self._courtier.fermer(attente_ms):return False
        self._fermee=True;erreur=False
        for ressource in (self._session,self._depot):
            if ressource is not None:
                try:ressource.fermer()
                except Exception:erreur=True
        if self._verrou is not None:
            try:self._verrou.liberer()
            except Exception:erreur=True
        if erreur:raise ErreurInfra('FERMETURE_PHYSIQUE_INCOMPLETE')
        return True

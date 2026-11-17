"""Cablage public et datation des retours ; aucun calcul de trading nouveau."""
from dataclasses import dataclass,replace
from xpbots.infra.c0a_types import ErreurInfra,TableHeureServeur
from xpbots.infra.c0b_horloge import HorlogeSysteme
from xpbots.infra.c1_session import SessionMT5
from xpbots.infra.c2a_specifications import SpecificationsMT5
from xpbots.infra.c2b_flux import FluxMT5
from xpbots.infra.c2c_calculs import CalculsMT5
from xpbots.infra.c2d_execution_mt5 import ExecutionMT5
from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1b_instrument import Intervalle


@dataclass(frozen=True)
class LotMarcheMT5:
    instant_ms:int
    ticks:tuple=()
    couvertures:tuple=()
    erreurs:tuple=()
    a_jour:tuple=()
    def __post_init__(self):
        verifier_instant(self.instant_ms)
        for nom in ('ticks','couvertures','erreurs','a_jour'):object.__setattr__(self,nom,tuple(getattr(self,nom)))
        if any(not isinstance(q,Tick) or q.instant_reception_ms!=self.instant_ms or q.instant_fournisseur_ms>self.instant_ms for q in self.ticks):
            raise ErreurInfra('ticks non causaux dans reception native')
        for nom in ('couvertures','erreurs','a_jour'):
            valeurs=getattr(self,nom)
            if any(type(v) is not tuple or len(v)!=len(('symbole','valeur')) or type(v[0]) is not str or not v[0] for v in valeurs):
                raise ErreurInfra('paires natives explicites requises')
            if len({v[0] for v in valeurs})!=len(valeurs):raise ErreurInfra('symbole de lot duplique')
        if any(type(b) is not bool for s,b in self.a_jour) or any(type(e) is not str or not e for s,e in self.erreurs):
            raise ErreurInfra('statut de lot natif invalide')
        if any(not isinstance(v,(tuple,list)) or any(not isinstance(i,Intervalle) or i.fin_ms>self.instant_ms for i in v) for s,v in self.couvertures):
            raise ErreurInfra('couverture native future ou mal typee')


class CourtierMT5:
    def __init__(self,session,commun,table,liaisons,horloge,instant_ms,*,qualification,
            departs_ticks_utc_ms,depuis_historique_compte_utc_ms,seances_max_age_ms,fermetures_max_age_ms,
            max_jours_horaires,ecart_horloges_max_ms,taille_lot,max_ticks_lot,longueur_empreinte,max_taches_natives,etat=None):
        if (not isinstance(session,SessionMT5) or not isinstance(commun,ParametresCommuns)
                or not isinstance(table,TableHeureServeur) or not isinstance(horloge,HorlogeSysteme)):
            raise ErreurInfra('parents physiques reels requis')
        verifier_instant(instant_ms)
        if type(liaisons) is not dict or type(departs_ticks_utc_ms) is not dict or set(liaisons)!=set(departs_ticks_utc_ms):
            raise ErreurInfra('liaisons et departs explicites requis')
        if not liaisons or not set(liaisons)<=set(commun.universe_priority):raise ErreurInfra('univers natif invalide')
        liaisons={s:liaisons[s] for s in commun.universe_priority if s in liaisons}
        departs={s:departs_ticks_utc_ms[s] for s in liaisons}
        sauvegarde=dict(specifications=None,flux=None,execution=None)
        if etat is not None:
            if type(etat) is not dict or set(etat)!={'schema','dernier_ms','specifications','flux','execution'} or etat['schema']!='xp-courtier-mt5-v1':
                raise ErreurInfra('etat courtier incompatible')
            verifier_instant(etat['dernier_ms'])
            if etat['dernier_ms']>instant_ms:raise ErreurInfra('reprise du courtier future')
            for nom in sauvegarde:
                if type(etat[nom]) is not dict:raise ErreurInfra('etat enfant absent')
                verifier_instant(etat[nom].get('dernier_ms'))
                if etat[nom]['dernier_ms']>etat['dernier_ms']:raise ErreurInfra('etat enfant futur')
                sauvegarde[nom]=etat[nom]
        self._horloge,self._dernier,self._liaisons=horloge,instant_ms,liaisons
        self._specifications=SpecificationsMT5(session,commun,table,qualification,liaisons,
            seances_max_age_ms=seances_max_age_ms,fermetures_max_age_ms=fermetures_max_age_ms,
            max_jours_horaires=max_jours_horaires,ecart_horloges_max_ms=ecart_horloges_max_ms,etat=sauvegarde['specifications'])
        historique=qualification['known_at_utc_ms']
        convention=self._specifications.convention_ticks(historique)
        preuves={s:self._specifications.preuve(s,historique)['historique_ticks_complet'] for s in liaisons}
        compte=self._specifications.preuve_compte(historique)
        self._flux=FluxMT5(session,table,liaisons,departs,taille_lot=taille_lot,max_ticks_lot=max_ticks_lot,
            historique_complet=preuves,etat=sauvegarde['flux'],convention_ticks=convention)
        self._execution=ExecutionMT5(session,commun,table,liaisons,horloge,
            profil=self._specifications.instrument,preuve=self._specifications.preuve,
            qualification_compte=self._specifications.compte,preuve_compte=self._specifications.preuve_compte,
            longueur_empreinte=longueur_empreinte,max_taches_natives=max_taches_natives,
            depuis_utc_ms=depuis_historique_compte_utc_ms,etat=sauvegarde['execution'],convention_ticks=convention)
        self._calculs=CalculsMT5(session,commun,liaisons,instant_ms,profil=self._specifications.instrument,
            qualification_compte=self._specifications.compte,proprietaire=self._execution.proprietaire,
            flux_externe=self._execution.flux_externe,assiette_stop_out=compte['assiette_stop_out'])

    @property
    def specifications(self):return self._specifications
    @property
    def calculs(self):return self._calculs
    @property
    def execution(self):return self._execution

    def actualiser_instant(self,t):
        verifier_instant(t)
        if t<self._dernier:raise ErreurInfra('horloge du courtier en recul')
        self._calculs.actualiser_instant(t);self._dernier=t

    def profil_compte(self,t):return self._specifications.compte(t)
    def convertir_serveur(self,texte):return self._specifications.convertir_serveur(texte)

    def recevoir_exports(self,t,*,seances,fermetures):
        self.actualiser_instant(t)
        return self._specifications.recevoir_exports(t,seances=seances,fermetures=fermetures)

    def lire_marche(self):
        debut=self._horloge.utc_ms();self.actualiser_instant(debut)
        try:
            if not all(self._specifications.preuve(s,debut)['historique_ticks_complet'] for s in self._liaisons):
                raise ErreurInfra('S08 courante absente')
        except (ValueError,KeyError,TypeError):
            fin=self._horloge.utc_ms();self.actualiser_instant(fin)
            return LotMarcheMT5(fin,erreurs=tuple((s,'HISTORIQUE_NON_QUALIFIE') for s in self._liaisons),
                a_jour=tuple((s,False) for s in self._liaisons))
        lot=self._flux.lire(debut)
        fin=self._horloge.utc_ms();self.actualiser_instant(fin)
        return LotMarcheMT5(fin,tuple(replace(q,instant_reception_ms=fin) for q in lot.ticks),
            lot.couvertures,lot.erreurs,lot.a_jour)

    def collecter(self):
        r=self._execution.collecter();self.actualiser_instant(r.instant_ms);return r

    def observer(self,*,depuis_flux_ms=None):
        r=self._execution.observer(depuis_flux_ms=depuis_flux_ms);self.actualiser_instant(r.instant_ms);return r

    def preparer_entrees(self,commandes,t):
        self.actualiser_instant(t);return self._execution.preparer_entrees(commandes,t)
    def autoriser_entrees(self,preuve):return self._execution.autoriser_entrees(preuve)
    def soumettre_defenses(self,commandes,t):
        self.actualiser_instant(t);return self._execution.soumettre_defenses(commandes,t)

    def exporter_etat(self):
        return dict(schema='xp-courtier-mt5-v1',dernier_ms=self._dernier,
            specifications=self._specifications.exporter_etat(),flux=self._flux.exporter_etat(),execution=self._execution.exporter_etat())

    def fermer(self,attente_ms):return self._execution.fermer(attente_ms)

"""Composition du transport et de l'observation sur le registre durable unique."""
from hashlib import sha256
import json
from xpbots.infra.c0a_types import ErreurInfra,TableHeureServeur,champ_natif,entier_natif
from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.noyau.c1b_instrument import ProfilInstrument
from xpbots.execution.c0a_types import PositionCompte
from xpbots.execution.c4_cycle import CommandeExecution,NatureCommande
from ._transport import TransportMT5
from ._observation import ObservationMT5
from xpbots.execution.c4_cycle import ReponseCourtier
from xpbots.execution.c1b_gardes import MouvementCompte
from xpbots.infra.c0a_types import nombre_decimal
from decimal import Decimal

_STATUTS=frozenset(('PREPAREE','EN_COURS','INCONNUE','REFUS_PRIX','REFUS_DEFINITIF','ACCEPTEE','TERMINEE'))


class ExecutionMT5(TransportMT5,ObservationMT5):
    def __init__(self,session,commun,table,liaisons,horloge,*,profil,preuve,qualification_compte,preuve_compte,
                 longueur_empreinte,max_taches_natives,depuis_utc_ms,etat=None,convention_ticks='SERVEUR_S01'):
        if not isinstance(table,TableHeureServeur):raise ErreurInfra('table S01 reelle requise')
        self._initialiser_transport(session,commun,table,liaisons,horloge,profil,preuve,qualification_compte,preuve_compte,
            longueur_empreinte,max_taches_natives,depuis_utc_ms,convention_ticks)
        self._empreinte_compte,self._mode_compte=self._identite_compte()
        configuration=dict(compte=self._empreinte_compte,mode=session.mode,liaisons=liaisons,
            mode_marge=self._mode_compte,convention_ticks=convention_ticks,
            longueur=longueur_empreinte,maximum=max_taches_natives,depuis=depuis_utc_ms,
            quote_max_age=commun.quote_max_age_seconds,univers=commun.universe_priority,
            table=dict(serveur=table.serveur,version=table.version,date_releve=table.date_releve,mesures=table.mesures,
                segments=[(s.debut_utc_ms,s.fin_utc_ms,s.decalage_secondes) for s in table.segments]))
        self._signature=sha256(json.dumps(configuration,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        self._solde_rapproche=None;self._flux_non_neutralise=True
        self._faits={};self._transactions={};self._transactions_lues={};self._tickets_positions={};self._mouvements=();self._dernier_rapport_ms=None
        if etat is not None:self._restaurer(etat)

    def _identite_compte(self,compte=None):
        if compte is None:compte=self._session.appeler('account_info')
        sdk=self._session.sdk
        serveur=champ_natif(compte,'server');numero=entier_natif(champ_natif(compte,'login'))
        if type(serveur) is not str or serveur!=self._table.serveur or numero<=0:raise ErreurInfra('compte natif incompatible')
        mode=entier_natif(champ_natif(compte,'margin_mode'))
        if mode==sdk.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING:marge='HEDGING'
        elif mode in (sdk.ACCOUNT_MARGIN_MODE_RETAIL_NETTING,sdk.ACCOUNT_MARGIN_MODE_EXCHANGE):marge='NETTING'
        else:raise ErreurInfra('mode marge non qualifie')
        return sha256((serveur+'\0'+str(numero)).encode('utf-8')).hexdigest(),marge

    def _verifier_compte(self,compte=None):
        empreinte,mode=self._identite_compte(compte)
        if (empreinte,mode)!=(self._empreinte_compte,self._mode_compte):raise ErreurInfra('compte natif change')

    def proprietaire(self,ticket):
        with self._verrou:return self._proprietaires.get(ticket)

    def flux_externe(self,instant_ms,solde):
        verifier_instant(instant_ms)
        if self._dernier_rapport_ms is None or instant_ms<self._dernier_rapport_ms:raise ErreurInfra('rapprochement monetaire absent ou futur')
        return self._flux_non_neutralise or solde!=self._solde_rapproche

    def exporter_etat(self):
        with self._verrou:
            return dict(schema='xp-execution-mt5-v1',configuration_sha256=self._signature,
                empreinte_compte_sha256=self._empreinte_compte,revision=self._revision,numero=self._numero,
                dernier_ms=self._dernier,registre=tuple(dict(r) for r in sorted(self._registre.values(),key=lambda r:r['numero'])),
                autorisees=tuple(sorted(self._autorisees)),proprietaires=tuple(self._proprietaires.values()),
                solde_rapproche=self._solde_rapproche,flux_non_neutralise=self._flux_non_neutralise,
                faits=dict(self._faits),transactions=dict(self._transactions),transactions_lues=dict(self._transactions_lues),tickets_positions=dict(self._tickets_positions),mouvements=tuple(self._mouvements),
                dernier_rapport_ms=self._dernier_rapport_ms)

    def _restaurer(self,d):
        cles={'schema','configuration_sha256','empreinte_compte_sha256','revision','numero','dernier_ms','registre',
            'autorisees','proprietaires','solde_rapproche','flux_non_neutralise','faits','transactions','transactions_lues','tickets_positions','mouvements','dernier_rapport_ms'}
        if (type(d) is not dict or set(d)!=cles or d['schema']!='xp-execution-mt5-v1'
                or d['configuration_sha256']!=self._signature or d['empreinte_compte_sha256']!=self._empreinte_compte):
            raise ErreurInfra('registre natif incompatible')
        verifier_instant(d['dernier_ms'])
        if type(d['revision']) is not int or d['revision']<0 or type(d['numero']) is not int or d['numero']<0:
            raise ErreurInfra('compteurs natifs invalides')
        if not isinstance(d['registre'],(tuple,list)) or not isinstance(d['autorisees'],(tuple,list)) or not isinstance(d['proprietaires'],(tuple,list)):
            raise ErreurInfra('collections natives explicites requises')
        numeros=set()
        for r in d['registre']:
            if type(r) is not dict or set(r)!={'numero','commande','profil','statut','appel_termine','envoi_termine','ordre','code'}:raise ErreurInfra('enregistrement natif invalide')
            c=r['commande']
            if (not isinstance(c,CommandeExecution) or c.nature not in (NatureCommande.ENTREE,NatureCommande.TP,NatureCommande.CLOTURE,NatureCommande.ANNULATION)
                    or c.reference in self._registre or c.instant_ms>d['dernier_ms'] or c.cle.symbole not in self._liaisons
                    or type(r['numero']) is not int or not 0<r['numero']<=d['numero'] or r['numero'] in numeros
                    or r['statut'] not in _STATUTS or r['profil'] is not None and not isinstance(r['profil'],ProfilInstrument)
                    or type(r['appel_termine']) is not bool or type(r['envoi_termine']) is not bool):raise ErreurInfra('enregistrement natif contradictoire')
            numeros.add(r['numero'])
            sauvegarde=dict(r)
            if r['statut'] in ('PREPAREE','EN_COURS','ACCEPTEE'):sauvegarde['statut']='INCONNUE'
            self._registre[c.reference]=sauvegarde
        if len(numeros)!=d['numero'] or sum(r['commande'].nature is NatureCommande.ENTREE for r in self._registre.values())!=d['revision']:
            raise ErreurInfra('compteurs natifs non concordants')
        if len(set(d['autorisees']))!=len(d['autorisees']) or any(r not in self._registre for r in d['autorisees']):raise ErreurInfra('autorisation inconnue')
        self._autorisees=set(d['autorisees']);self._revision=d['revision'];self._numero=d['numero'];self._dernier=d['dernier_ms']
        for p in d['proprietaires']:
            if not isinstance(p,PositionCompte) or p.cle is None or p.identifiant in self._proprietaires:raise ErreurInfra('propriete native invalide')
            if not self._entree_connue(p.cle):raise ErreurInfra('propriete sans intention native')
            self._proprietaires[p.identifiant]=p
        if (type(d['flux_non_neutralise']) is not bool or type(d['faits']) is not dict or type(d['transactions']) is not dict
                or type(d['transactions_lues']) is not dict or type(d['tickets_positions']) is not dict
                or not isinstance(d['mouvements'],(tuple,list))):
            raise ErreurInfra('historique natif invalide')
        for ref,r in d['faits'].items():
            if not isinstance(r,ReponseCourtier) or ref!=r.reference or r.instant_ms>d['dernier_ms'] or not self._entree_connue(r.cle):
                raise ErreurInfra('fait persiste invalide')
        if any(not isinstance(m,MouvementCompte) or m.instant_ms>d['dernier_ms'] for m in d['mouvements']):
            raise ErreurInfra('mouvements persistants invalides')
        if len({m.reference for m in d['mouvements']})!=len(d['mouvements']):raise ErreurInfra('mouvement persiste duplique')
        for identifiant,ticket in d['tickets_positions'].items():
            from ._valeurs import ticket_natif
            if ticket_natif(identifiant)!=identifiant or ticket_natif(ticket)!=ticket:raise ErreurInfra('liaison ticket invalide')
        if d['solde_rapproche'] is not None and (type(d['solde_rapproche']) is not Decimal or not d['solde_rapproche'].is_finite()):
            raise ErreurInfra('solde persiste invalide')
        if (d['dernier_rapport_ms'] is None)!=(d['solde_rapproche'] is None):raise ErreurInfra('preuve monetaire persistante incomplete')
        self._solde_rapproche=d['solde_rapproche'];self._flux_non_neutralise=d['flux_non_neutralise']
        self._faits=dict(d['faits']);self._transactions=dict(d['transactions']);self._mouvements=tuple(d['mouvements'])
        self._tickets_positions=dict(d['tickets_positions'])
        self._transactions_lues=dict(d['transactions_lues'])
        self._dernier_rapport_ms=d['dernier_rapport_ms']
        if self._dernier_rapport_ms is not None:
            verifier_instant(self._dernier_rapport_ms)
            if self._dernier_rapport_ms>self._dernier:raise ErreurInfra('observation native future')
        # Les proprietes passees restent une piste ; la monnaie et le netting
        # doivent etre rapproches dans le processus courant avant une entree.
        self._flux_non_neutralise=True

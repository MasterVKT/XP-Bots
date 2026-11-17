"""Assembler les blocs réels ; aucun calcul, transport ou décision supplémentaire."""
from collections.abc import Mapping
from datetime import datetime,timezone

from xpbots.app.c0_configuration import ErreurApplication
from xpbots.contexte_ia.c0_types import charger_parametres,PolitiqueVeto
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.execution.c0a_types import RefusExecution
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.execution.c1a_calcul import CalculCourtier
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.london.c2_moteur import fabriquer_strategie
from xpbots.noyau.c0a_temps import instant_depuis_datetime,verifier_instant
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1b_instrument import ProfilCompte,ProfilInstrument
from xpbots.noyau.c1c_domaine import Motif
from xpbots.orchestration.c0_contrats import Deploiement,FabriqueStrategie,REFERENCE,IA
from xpbots.orchestration.c1_bras import construire_bras
from xpbots.orchestration.c2_moteur import MoteurDecision,CheckpointMoteur,CheckpointJournalMoteur


class PortCompte:
    def __init__(self,backend,profil_compte):
        if not isinstance(backend,CalculCourtier) or not isinstance(profil_compte,ProfilCompte):
            raise ErreurApplication('PORT_CALCUL_ET_COMPTE_CANONIQUES_REQUIS')
        self._backend=backend;self.profil_compte=profil_compte;self._disponibles=frozenset()

    def fixer_disponibilite(self,symboles):
        if not isinstance(symboles,(tuple,list,set,frozenset)) or any(type(s) is not str or not s for s in symboles):
            raise ErreurApplication('SYMBOLES_DISPONIBLES_INVALIDES')
        self._disponibles=frozenset(symboles)

    def profit(self,*a,**k):return self._backend.profit(*a,**k)
    def marge(self,*a,**k):return self._backend.marge(*a,**k)
    def frais_aller_retour(self,*a,**k):return self._backend.frais_aller_retour(*a,**k)
    def frais_sortie(self,*a,**k):return self._backend.frais_sortie(*a,**k)
    def specifications(self,*a,**k):return self._backend.specifications(*a,**k)
    def etat_compte(self,*a,**k):return self._backend.etat_compte(*a,**k)
    def controler(self,ordre,compte,remplacement=False):
        if not remplacement and ordre.cle.symbole not in self._disponibles:
            return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'rattrapage_flux')
        return self._backend.controler(ordre,compte,remplacement=remplacement)


class _SansBackend:
    def __init__(self,profil_compte):self.profil_compte=profil_compte
    def _interdit(self,*a,**k):raise AssertionError('BACKEND_INTERDIT_REJEU_INCIDENT')
    profit=marge=frais_aller_retour=frais_sortie=controler=specifications=etat_compte=_interdit


def _valider(c,i):
    cles={'schema','configuration','deploiement','mode','longueur_empreinte','profils','horaires',
          'periodes_couvertes','initiales','scenario_fondamental','table_heure','politique_ia'}
    if (not isinstance(c,ConfigurationFigee) or not isinstance(i,Mapping) or set(i)!=cles
            or i['schema']!='xp-composition-direct-v1' or i['configuration']!=c):
        raise ErreurApplication('INITIALISATION_MOTEUR_ETRANGERE')
    if i['mode'] not in ('PAPER','PAPER_AB','DEMO','REEL'):
        raise ErreurApplication('MODE_DIRECT_INVALIDE')
    p=i['politique_ia']
    if not isinstance(p,Mapping) or set(p)!={'bras_ia','execution_reelle','validation_financiere'}:
        raise ErreurApplication('POLITIQUE_IA_INVALIDE')
    politique=PolitiqueVeto(**p)
    natif=i['mode'] in ('DEMO','REEL')
    if politique.execution_reelle!=natif:
        raise ErreurApplication('POLITIQUE_IA_INCOMPATIBLE_AVEC_MODE')
    if i['mode']=='PAPER_AB':noms=(REFERENCE,IA)
    else:noms=(IA if natif and politique.bras_ia else REFERENCE,)
    if (i['mode']=='PAPER_AB' and not politique.bras_ia
            or i['mode']=='PAPER' and politique.bras_ia):
        raise ErreurApplication('POLITIQUE_IA_INCOMPATIBLE_AVEC_BRAS')
    if (i['scenario_fondamental'] not in (None,'TECHNICAL_CONTROL_NEUTRAL')
            or natif and i['scenario_fondamental'] is not None):
        raise ErreurApplication('SCENARIO_FONDAMENTAL_INTERDIT')
    if not isinstance(i['initiales'],Mapping) or set(i['initiales'])!=set(noms):
        raise ErreurApplication('COMPTES_INITIAUX_INCOMPATIBLES')
    for v in i['initiales'].values():
        if not isinstance(v,Mapping) or set(v)!={'profil_compte','instant_ms','observation','base_utc'}:
            raise ErreurApplication('COMPTE_INITIAL_INVALIDE')
        verifier_instant(v['instant_ms'])
        if not isinstance(v['profil_compte'],ProfilCompte):raise ErreurApplication('PROFIL_COMPTE_INITIAL_INVALIDE')
    if len({v['instant_ms'] for v in i['initiales'].values()})!=1:
        raise ErreurApplication('HORLOGES_INITIALES_DIFFERENTES')
    if (not isinstance(i['profils'],Mapping) or not i['profils']
            or any(not isinstance(p,ProfilInstrument) or s!=p.symbole for s,p in i['profils'].items())
            or set(i['profils'])!=set(i['horaires']) or set(i['profils'])!=set(i['periodes_couvertes'])):
        raise ErreurApplication('PROFILS_INITIAUX_INCOHERENTS')
    return noms,politique


def composer_moteur(configuration,initialisation,ports,*,checkpoint=None,entrees=(),appels_initialisation=None):
    i=initialisation;noms,politique=_valider(configuration,i)
    if not isinstance(ports,Mapping) or set(ports)!=set(noms):raise ErreurApplication('PORTS_DES_BRAS_INCOHERENTS')
    if checkpoint is not None and not isinstance(checkpoint,CheckpointMoteur):
        raise ErreurApplication('CHECKPOINT_COMPLET_REQUIS_POUR_REPRISE_C08')
    if appels_initialisation is not None and (not isinstance(appels_initialisation,Mapping)
            or set(appels_initialisation)!=set(noms)):
        raise ErreurApplication('APPELS_INITIAUX_INCOHERENTS')
    if i['scenario_fondamental'] is None:
        table=TableHeureServeur.depuis_document(i['table_heure'])
        def convertir(texte):
            format_='%Y.%m.%d %H:%M:%S';dt=datetime.strptime(texte,format_)
            if dt.strftime(format_)!=texte:raise ErreurApplication('HEURE_SERVEUR_INVALIDE')
            return table.utc_de_serveur(instant_depuis_datetime(dt.replace(tzinfo=timezone.utc)))
        fond=PermissionsFondamentales(configuration.technique.commun,convertir,
                                      None if checkpoint is None else checkpoint.fondamental)
    else:fond=None
    controle=fond if fond is not None else ControleTechniqueNeutre()
    lecteur=LecteurContexte(charger_parametres(configuration),politique,
                           None if checkpoint is None else checkpoint.ia) if IA in noms else None
    d=Deploiement(i['deploiement'],i['mode'],(FabriqueStrategie(configuration.technique.london['strategy_id'],
        fabriquer_strategie),),{s:p.tick_size for s,p in i['profils'].items()},i['longueur_empreinte'])
    etats={} if checkpoint is None else {b.nom:b for b in checkpoint.bras}
    if checkpoint is not None and set(etats)!=set(noms):raise ErreurApplication('CHECKPOINT_BRAS_ETRANGERS')
    bras=[]
    for nom in noms:
        v=i['initiales'][nom];port=ports[nom]
        if not isinstance(port,CalculCourtier) or port.profil_compte!=v['profil_compte']:
            raise ErreurApplication('PORT_COMPTE_INITIAL_ETRANGER')
        appels=None if appels_initialisation is None else appels_initialisation[nom]
        if checkpoint is not None:appels=()
        bras.append(construire_bras(configuration,d,nom,i['profils'],port,controle,
            v['instant_ms'] if checkpoint is None else checkpoint.instant_ms,
            observation=v['observation'] if checkpoint is None else None,
            base_utc=v['base_utc'] if checkpoint is None else None,
            lecteur_ia=lecteur if nom==IA else None,etat=etats.get(nom),appels_initialisation=appels))
    return MoteurDecision(configuration,bras,i['horaires'],i['periodes_couvertes'],
        controle_fondamental=fond,lecteur_ia=lecteur,scenario_fondamental=i['scenario_fondamental'],
        checkpoint=checkpoint,entrees=entrees)


def rejouer_incident(configuration,initialisation,appels_initialisation,entrees,checkpoint,*,reprises=()):
    if not isinstance(checkpoint,CheckpointJournalMoteur):raise ErreurApplication('CHECKPOINT_JOURNAL_REQUIS')
    checkpoint.verifier();noms,_=_valider(configuration,initialisation)
    if not isinstance(appels_initialisation,Mapping) or set(appels_initialisation)!=set(noms):
        raise ErreurApplication('APPELS_INITIAUX_INCOHERENTS')
    ports={n:_SansBackend(initialisation['initiales'][n]['profil_compte']) for n in noms}
    moteur=composer_moteur(configuration,initialisation,ports,appels_initialisation=appels_initialisation)
    reprises=tuple(reprises);entrees=tuple(entrees);precedent=0
    for marqueur in reprises:
        if not isinstance(marqueur,CheckpointJournalMoteur):raise ErreurApplication('MARQUEUR_REPRISE_INVALIDE')
        marqueur.verifier()
        if not precedent<=marqueur.numero_entrees<=len(entrees):raise ErreurApplication('MARQUEUR_REPRISE_HORS_PREFIXE')
        precedent=marqueur.numero_entrees
    index=0;sorties=[]
    def appliquer_reprises(prefixe):
        nonlocal moteur,index
        while index<len(reprises) and reprises[index].numero_entrees==prefixe:
            moteur=composer_moteur(configuration,initialisation,ports,
                checkpoint=moteur.exporter_checkpoint(),entrees=moteur.entrees)
            if moteur.exporter_checkpoint_journal()!=reprises[index]:
                raise ErreurApplication('REPRISE_INCIDENT_DIVERGENTE')
            index+=1
    for prefixe,j in enumerate(entrees):
        appliquer_reprises(prefixe);sorties.append(moteur.rejouer(j))
    appliquer_reprises(len(entrees))
    if moteur.exporter_checkpoint_journal()!=checkpoint:
        raise ErreurApplication('REJEU_INCIDENT_DIVERGENT')
    return moteur,tuple(sorties)

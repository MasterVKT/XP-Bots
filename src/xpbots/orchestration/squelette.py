"""Façade S4 de compatibilité ; la décision appartient uniquement au moteur MCL."""
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.orchestration.c0_contrats import (Strategie,SortieMoteur,FabriqueStrategie,Deploiement,MiseAJourBras)
from xpbots.orchestration.c1_bras import Bras,CoordinateurTrace
from xpbots.orchestration.c2_moteur import MoteurDecision

BRAS_UNIQUE='REFERENCE'
LONGUEUR_EMPREINTE_SQUELETTE=16  # Qualification réelle par la sonde S-05, phase 13.
SCENARIO_TECHNIQUE=ControleTechniqueNeutre.scenario


def composer_coordinateur(configuration,deploiement,profils,port,instant_ms,*,observation,base_utc,
                          controle_fondamental=None,scenario=None,lecteur_ia=None):
    if scenario==SCENARIO_TECHNIQUE and controle_fondamental is None:f=ControleTechniqueNeutre()
    elif scenario is None and isinstance(controle_fondamental,PermissionsFondamentales):f=controle_fondamental
    else:raise ValueError('port C05 réel ou scénario technique explicite requis, choix exclusifs')
    return CoordinateurTrace(configuration.technique,deploiement,profils,port.profil_compte,port,f,
        instant_ms,longueur_empreinte=LONGUEUR_EMPREINTE_SQUELETTE,mode='REJEU',
        observation=observation,base_utc=base_utc,contexte=lecteur_ia)


def composer_coordinateur_neutre(configuration,deploiement,profils,port,instant_ms,*,observation,base_utc,lecteur_ia=None):
    return composer_coordinateur(configuration,deploiement,profils,port,instant_ms,
        observation=observation,base_utc=base_utc,scenario=SCENARIO_TECHNIQUE,lecteur_ia=lecteur_ia)


class MoteurMinimal:
    def __init__(self,strategie,configuration,mode,deploiement,horaires,periodes_couvertes,
                 coordinateur,profils,profil_compte=None,scenario_fondamental=None,
                 controle_fondamental=None,source_fondamentale=None,lecteur_ia=None,source_ia=None,*,fabriques=None):
        if fabriques is None:
            if not isinstance(strategie,Strategie):raise ValueError('stratégie structurelle requise')
            fabriques=(FabriqueStrategie(strategie.identifiant,lambda c,t:strategie),)
        d=Deploiement(deploiement,mode,tuple(fabriques),{s:p.tick_size for s,p in profils.items()},LONGUEUR_EMPREINTE_SQUELETTE)
        self.bras='IA' if lecteur_ia is not None and lecteur_ia.politique.bras_ia else BRAS_UNIQUE
        self._bras=Bras(configuration,d,self.bras,coordinateur,profils,profil_compte,
            fondamental=controle_fondamental if controle_fondamental is not None else ControleTechniqueNeutre(),lecteur_ia=lecteur_ia)
        self.moteur=MoteurDecision(configuration,(self._bras,),horaires,periodes_couvertes,
            controle_fondamental=controle_fondamental,lecteur_ia=lecteur_ia,source_fondamentale=source_fondamentale,
            source_ia=source_ia,scenario_fondamental=scenario_fondamental)

    @property
    def prochaine_echeance_ms(self):return self.moteur.prochaine_echeance_ms

    def alerte(self,code,instant_ms):return self._bras.alerte(code,instant_ms)

    def traiter_evenement(self,instant_ms,*,reponses=(),observation=None,base_utc=None):
        return self.moteur.traiter_evenement(instant_ms,mises_a_jour={self.bras:MiseAJourBras(reponses,observation,base_utc)}).par_bras[self.bras]

    def traiter_tick(self,tick,**kwargs):return self.traiter_ticks((tick,),**kwargs)

    def traiter_ticks(self,ticks,*,reponses=(),observation=None,base_utc=None):
        return self.moteur.traiter_ticks(ticks,mises_a_jour={self.bras:MiseAJourBras(reponses,observation,base_utc)}).par_bras[self.bras]

    def confirmer_persistance(self,preuve,instant_ms):
        return self.moteur.confirmer_persistance({self.bras:preuve},instant_ms).par_bras[self.bras]


def fabriquer_moteur_minimal(strategie,configuration,mode,deploiement='squelette',**kwargs):
    return MoteurMinimal(strategie,configuration,mode,deploiement,**kwargs)

"""Pilote externe de test de la jonction 0→1→2, sans façade S4/S7."""
from itertools import groupby
from robot.outils.orchestration import C,composer_bras
from robot.outils.contexte_ia import parametres
from xpbots.orchestration.c0_contrats import MiseAJourBras,ReceptionExterne
from xpbots.orchestration.c1_bras import construire_bras
from xpbots.orchestration.c2_moteur import MoteurDecision
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.execution.c4_cycle import ReponseCourtier
from xpbots.execution.c5b_reprise import ObservationNative
from xpbots.contexte_ia.c0_types import PolitiqueVeto
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.rejeu.squelette import ExecutionPapierMinimale,StockageMemoirePapier


class ReceptionsScenario:
    def __init__(self,lecteur,paquets):self.lecteur=lecteur;self.paquets=list(paquets)
    @property
    def prochaine_reception_ms(self):return self.paquets[0].instant_ms if self.paquets else None
    def extraire(self,t):
        r=[]
        if self.prochaine_reception_ms is not None and self.prochaine_reception_ms<t:raise ValueError('réception sautée')
        while self.prochaine_reception_ms==t:r.append(ReceptionExterne('SNAPSHOT',self.paquets.pop(0).octets))
        return tuple(r)


def duo(ticks,*,fondamental=None,source=None,fabriques=None,paquets_ia=()):
    ia=LecteurContexte(parametres(),PolitiqueVeto(True))
    premier=ticks[0].instant_reception_ms
    modele,p,h,c=composer_bras(ticks=ticks,mode=C.ia.parametres['default_evaluation_mode'],fabriques=fabriques)
    f=fondamental if fondamental is not None else modele.fondamental
    ports={};bras=[]
    for n in ('REFERENCE','IA'):
        p=ExecutionPapierMinimale(C,modele.profils,premier//86400000*86400000);p.avancer_au(premier);ports[n]=p
        bras.append(construire_bras(C,modele.deploiement,n,p.profils,p,f,premier,
            observation=p.observation(),base_utc=p.base_utc(),lecteur_ia=ia if n=='IA' else None))
    m=MoteurDecision(C,bras,h,c,controle_fondamental=fondamental,lecteur_ia=ia,
        scenario_fondamental=ControleTechniqueNeutre.scenario if fondamental is None else None,
        source_fondamentale=source,source_ia=ReceptionsScenario(ia,paquets_ia))
    return m,ports,ia,h,c


def piloter(ticks,m,ports,stockages=None):
    stockages=stockages or {n:StockageMemoirePapier() for n in ports}
    sorties=[];reponses={n:[] for n in ports}
    def transmettre(s,t):
        file=[s]
        while file:
            s=file.pop(0);sorties.append(s);maj={};preuves={}
            for n,v in s.sorties:
                p=ports[n]
                # La preuve est renouvelée après toute réponse qui change la révision.
                ev=p.soumettre(v.commandes)
                if ev:
                    r=tuple(x for x in ev if isinstance(x,ReponseCourtier));reponses[n].extend(r)
                    obs=next((x for x in reversed(ev) if isinstance(x,ObservationNative)),None)
                    maj[n]=MiseAJourBras(r,obs,p.base_utc())
                elif v.lot is not None and v.lot.preparations:
                    preuves[n]=stockages[n].persister(v.lot)
            if maj:file.append(m.traiter_evenement(t,mises_a_jour=maj))
            elif preuves:file.append(m.confirmer_persistance(preuves,t))
    for t,g in groupby(ticks,key=lambda x:x.instant_reception_ms):
        g=tuple(g)
        while m.prochaine_echeance_ms is not None and m.prochaine_echeance_ms<t:
            e=m.prochaine_echeance_ms
            for p in ports.values():p.avancer_au(e)
            transmettre(m.traiter_evenement(e,mises_a_jour={n:MiseAJourBras(base_utc=p.base_utc()) for n,p in ports.items()}),e)
        maj={}
        for n,p in ports.items():
            r=tuple(v for x in g for v in p.sur_tick(x));reponses[n].extend(r);maj[n]=MiseAJourBras(r,base_utc=p.base_utc())
        transmettre(m.traiter_ticks(g,mises_a_jour=maj),t)
    return sorties,reponses

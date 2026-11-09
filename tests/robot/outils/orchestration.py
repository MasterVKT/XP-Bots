"""Compositions de test : fabriques et couches réelles, seul le courtier est papier."""
from decimal import Decimal as D
from robot.outils.configuration import configuration_figee
from robot.outils.fabrique_ticks import lignes_csv
from xpbots.london.c2_moteur import fabriquer_strategie
from xpbots.noyau.c1a_marche import Tick,Cotation
from xpbots.noyau.c1c_domaine import SignalTechnique
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.orchestration.c0_contrats import FabriqueStrategie,Deploiement
from xpbots.orchestration.c1_bras import construire_bras
from xpbots.donnees.c1c_couverture import RegistreCouverture
from xpbots.donnees.c3_flux import FluxBougies
from xpbots.rejeu.squelette import (ContratPapier,ExecutionPapierMinimale,StockageMemoirePapier,
    hypotheses_marche_squelette,profils_papier,analyser_lignes_ticks)

C=configuration_figee();T=1_794_211_200_000


def ticks_courts(symboles=('EURUSD',)):
    pas=C.technique.commun.timeframe_seconds*1000
    return [Tick(s,s,T+n*pas,T+n*pas,i,1.1,1.1001)
        for i,(n,s) in enumerate((n,s) for n in range(5) for s in symboles)]


def composer_bras(nom='REFERENCE',*,ticks=None,mode='REJEU',fabriques=None,etat=None,lecteur=None):
    ticks=ticks_courts() if ticks is None else ticks
    tailles={s:D('.00001') for s in {t.symbole for t in ticks}}
    d=Deploiement('essai_orchestration',mode,
        tuple(fabriques) if fabriques is not None else (FabriqueStrategie(C.technique.london['strategy_id'],fabriquer_strategie),),tailles,16)
    h,p=hypotheses_marche_squelette(ticks,C)
    profils=profils_papier(ticks,tailles,{s:ContratPapier(D('1000'),D('.1'),D('1'),D('.1')) for s in tailles},h,C)
    debut=ticks[0].instant_reception_ms
    port=ExecutionPapierMinimale(C,profils,debut//86400000*86400000);port.avancer_au(debut)
    fond=ControleTechniqueNeutre()
    b=construire_bras(C,d,nom,profils,port,fond,debut,observation=port.observation(),base_utc=port.base_utc(),
        lecteur_ia=lecteur,etat=etat)
    return b,port,h,p


def flux(h,p):
    return {s:FluxBougies(s,C.technique,h[s],RegistreCouverture(p[s])) for s in h}


def executer_bras(b,port,ticks,h,p):
    """Jonction 0→1 : pilote externe de test, sans utiliser la couche 2 future."""
    f=flux(h,p);stockage=StockageMemoirePapier();lignes=[];signaux=[];reponses=[]
    def consommer(lot,t):
        file=[lot]
        while file:
            lot=file.pop(0);s=b.consommer(lot,t);lignes.extend(s.enregistrements)
            evenements=port.soumettre(s.commandes)
            if evenements:
                from xpbots.execution.c4_cycle import ReponseCourtier
                from xpbots.execution.c5b_reprise import ObservationNative
                r=tuple(e for e in evenements if isinstance(e,ReponseCourtier));reponses.extend(r)
                o=next((e for e in reversed(evenements) if isinstance(e,ObservationNative)),None)
                file.append(b.coordinateur.traiter(t,reponses=r,observation=o,base_utc=port.base_utc()))
            elif lot.preparations:
                file.append(b.coordinateur.confirmer_persistance(stockage.persister(lot),t))
    for tick in ticks:
        t=tick.instant_reception_ms;r=port.sur_tick(tick);reponses.extend(r)
        q=Cotation(tick.symbole,D(str(tick.bid)),D(str(tick.ask)),tick.instant_fournisseur_ms,t)
        consommer(b.coordinateur.traiter(t,cotations=(q,),reponses=r,base_utc=port.base_utc()),t)
        from xpbots.donnees.c0a_types import BougieEnrichie
        for bougie in f[tick.symbole].sur_tick(tick):
            if isinstance(bougie,BougieEnrichie):
                for resultat in b.sur_bougie(bougie):
                    if isinstance(resultat,SignalTechnique):signaux.append(resultat);consommer(b.coordinateur.traiter(t,signaux=(resultat,)),t)
    return lignes,signaux,reponses

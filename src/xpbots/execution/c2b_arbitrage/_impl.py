"""Implémentation de la couche 2b (arbitrage). Révisable à comportement constant sous harnais complet."""
from dataclasses import dataclass
from xpbots.execution.c0a_types import EtatReservations,ErreurExecution
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1c_domaine import SignalTechnique

@dataclass(frozen=True)
class CandidatArbitrage:
    signal: SignalTechnique
    etat_reservations: EtatReservations
    def __post_init__(self):
        if not isinstance(self.signal,SignalTechnique) or not isinstance(self.etat_reservations,EtatReservations):
            raise ErreurExecution('signal et instantané de réservations attendus')

def ordonner_signaux(signaux,commun):
    if not isinstance(commun,ParametresCommuns): raise ErreurExecution('paramètres attendus')
    try: suite=tuple(signaux)
    except TypeError as e: raise ErreurExecution('séquence de signaux attendue') from e
    if any(not isinstance(s,SignalTechnique) for s in suite): raise ErreurExecution('signal canonique attendu')
    if len({s.cloture_ms for s in suite})>1: raise ErreurExecution('une seule clôture par arbitrage')
    cles=[(s.strategie,s.symbole,s.cloture_ms,s.sens) for s in suite]
    if len(set(cles))!=len(cles): raise ErreurExecution('signal dupliqué')
    methodes={s:i for i,s in enumerate(commun.simultaneous_strategy_priority)}
    symboles={s:i for i,s in enumerate(commun.universe_priority)}
    if any(s.strategie not in methodes or s.symbole not in symboles for s in suite): raise ErreurExecution('signal non configuré')
    return tuple(sorted(suite,key=lambda s:(methodes[s.strategie],symboles[s.symbole])))

def candidats_admission(signaux,commun,registre):
    if not isinstance(registre,RegistreReservations): raise ErreurExecution('registre réel attendu')
    for signal in ordonner_signaux(signaux,commun):
        yield CandidatArbitrage(signal,registre.etat)

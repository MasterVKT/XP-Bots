"""Implémentation de la couche 0b (ports_controles). Révisable à comportement constant sous harnais complet."""
from typing import Protocol,runtime_checkable
from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.noyau.c1c_domaine import Sens,DecisionFondamentale,DecisionContexteIA,ContexteIA

@runtime_checkable
class ControleFondamental(Protocol):
    def evaluer(self,symbole:str,sens:Sens,instant_ms:int)->DecisionFondamentale: ...
    def clotures_obligatoires(self,instant_ms:int)->tuple[str,...]: ...

@runtime_checkable
class LecteurContexteIA(Protocol):
    def evaluer(self,symbole:str,instant_ms:int)->DecisionContexteIA: ...

def _verifier(symbole,instant_ms):
    if type(symbole) is not str or not symbole: raise ValueError('symbole attendu')
    verifier_instant(instant_ms)

class ControleTechniqueNeutre:
    scenario='TECHNICAL_CONTROL_NEUTRAL'
    def evaluer(self,symbole,sens,instant_ms):
        _verifier(symbole,instant_ms)
        if not isinstance(sens,Sens): raise ValueError('sens attendu')
        return DecisionFondamentale(True)
    def clotures_obligatoires(self,instant_ms):
        verifier_instant(instant_ms)
        return ()

class ComplementAbsent:
    def evaluer(self,symbole,instant_ms):
        _verifier(symbole,instant_ms)
        return DecisionContexteIA(ContexteIA.NEUTRAL)

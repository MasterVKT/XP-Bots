"""Implémentation de la couche 1a (port_calcul). Révisable à comportement constant sous harnais complet."""
from decimal import Decimal
from typing import Protocol,runtime_checkable
from xpbots.execution.c0a_types import EtatCompte,ControleNatif,OrdreCalcule,RefusExecution
from xpbots.noyau.c1b_instrument import ProfilInstrument
from xpbots.noyau.c1c_domaine import Motif,Sens

@runtime_checkable
class CalculCourtier(Protocol):
    def profit(self,profil:ProfilInstrument,sens:Sens,volume:Decimal,entree:Decimal,sortie:Decimal)->Decimal: ...
    def frais_aller_retour(self,profil:ProfilInstrument,sens:Sens,volume:Decimal)->Decimal: ...
    def frais_sortie(self,profil:ProfilInstrument,sens:Sens,volume:Decimal)->Decimal: ...
    def marge(self,profil:ProfilInstrument,sens:Sens,volume:Decimal,entree:Decimal)->Decimal: ...
    def controler(self,ordre:OrdreCalcule,compte:EtatCompte,remplacement:bool=False)->ControleNatif: ...
    def specifications(self,symbole:str)->ProfilInstrument: ...
    def etat_compte(self)->EtatCompte: ...

def appeler_calcul(port,fonction,*args,**kwargs):
    if fonction not in ('profit','frais_aller_retour','frais_sortie','marge','controler','specifications','etat_compte'):
        raise ValueError('fonction de calcul inconnue')
    try:
        resultat=getattr(port,fonction)(*args,**kwargs)
        attendu={'controler':ControleNatif,'specifications':ProfilInstrument,'etat_compte':EtatCompte}.get(fonction,Decimal)
        if not isinstance(resultat,attendu): raise ValueError('résultat absent ou mal typé')
        if attendu is Decimal and (not resultat.is_finite() or fonction!='profit' and resultat<0):
            raise ValueError('montant invalide')
        return resultat
    except Exception:
        return RefusExecution(Motif.ENVIRONMENT_NOT_READY,fonction)

"""Implémentation de la couche 2a (risque_all_in). Révisable à comportement constant sous harnais complet."""
from dataclasses import dataclass,fields
from decimal import Context,Decimal,localcontext
from xpbots.execution.c0a_types import RefusExecution,ErreurExecution,decimal_fini
from xpbots.execution.c0d_prix import NiveauxExecutables
from xpbots.execution.c1a_calcul import appeler_calcul
from xpbots.noyau.c0b_nombres import decimal_depuis
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1b_instrument import ProfilInstrument,construire_profil_instrument
from xpbots.noyau.c1c_domaine import SignalTechnique,Motif

@dataclass(frozen=True)
class MesureRisque:
    total: Decimal
    perte_prix: Decimal
    frais: Decimal
    glissement: Decimal
    entree_pessimiste: Decimal
    sortie_pessimiste: Decimal
    def __post_init__(self):
        for n in ('total','perte_prix','frais','glissement','entree_pessimiste','sortie_pessimiste'):
            decimal_fini(getattr(self,n),n,Decimal(0),n not in ('total','perte_prix','frais'))
        with localcontext(Context(prec=48)):
            if self.total!=self.perte_prix+self.frais: raise ErreurExecution('total de risque incohérent')

def verifier_profil(profil,commun):
    if not isinstance(commun,ParametresCommuns): raise ErreurExecution('paramètres communs attendus')
    if not isinstance(profil,ProfilInstrument): return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'profil')
    donnees={f.name:getattr(profil,f.name) for f in fields(ProfilInstrument)}
    try:
        resultat=construire_profil_instrument(donnees,commun)
    except ValueError:
        return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'profil')
    if resultat.non_prets: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,resultat.non_prets[0])
    with localcontext(Context(prec=48)):
        if profil.volume_min%profil.volume_pas: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'volume_min')
    if not profil.protections_a_l_entree: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'protections_a_l_entree')
    if not profil.convention_declenchement_verifiee: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'convention_declenchement_verifiee')
    return None

def calculer_risque(signal,niveaux,volume,profil,commun,port,*,apres_remplissage=False,frais_entree_reels=None):
    if not isinstance(signal,SignalTechnique) or not isinstance(niveaux,NiveauxExecutables) or type(apres_remplissage) is not bool:
        raise ErreurExecution('signal, niveaux et mode de risque attendus')
    decimal_fini(volume,'volume',Decimal(0),True)
    refus=verifier_profil(profil,commun)
    if refus is not None: return refus
    if signal.symbole!=profil.symbole or signal.sens is not niveaux.sens: raise ErreurExecution('signal et niveaux incohérents')
    with localcontext(Context(prec=48)):
        if volume<profil.volume_min or volume>profil.volume_max or volume%profil.volume_pas:
            raise ErreurExecution('volume hors grille native')
        if apres_remplissage:
            if frais_entree_reels is None: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'frais_entree_reels')
            decimal_fini(frais_entree_reels,'frais_entree_reels',Decimal(0))
        elif frais_entree_reels is not None:
            raise ErreurExecution('frais réalisés fournis avant remplissage')
        g=max(profil.tick_size,decimal_depuis(commun.slippage_budget_atr_per_leg)*decimal_depuis(signal.atr_reference))
        s=signal.sens.signe
        entree=niveaux.entree if apres_remplissage else niveaux.entree+s*g
        sortie=niveaux.stop-s*g
        if entree<=0 or sortie<=0: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'prix_pessimiste')
        profit=appeler_calcul(port,'profit',profil,signal.sens,volume,entree,sortie)
        if isinstance(profit,RefusExecution): return profit
        frais=appeler_calcul(port,'frais_sortie' if apres_remplissage else 'frais_aller_retour',profil,signal.sens,volume)
        if isinstance(frais,RefusExecution): return frais
        if apres_remplissage: frais+=frais_entree_reels
        perte=max(Decimal(0),-profit)
        return MesureRisque(perte+frais,perte,frais,g,entree,sortie)

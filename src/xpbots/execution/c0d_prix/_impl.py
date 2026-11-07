"""Implémentation de la couche 0d (prix_executables). Révisable à comportement constant sous harnais complet."""
from dataclasses import dataclass,replace
from decimal import Context,Decimal,localcontext
from xpbots.noyau.c0b_nombres import Arrondi,arrondir_sur_grille,decimal_depuis,est_sur_grille
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1a_marche import Cotation
from xpbots.noyau.c1b_instrument import ProfilInstrument
from xpbots.noyau.c1c_domaine import Motif,Sens,SignalTechnique,verifier_motif

@dataclass(frozen=True)
class RefusPrix:
    motif: Motif
    detail: str | None = None
    def __post_init__(self):
        verifier_motif(self.motif,self.detail)

@dataclass(frozen=True)
class NiveauxExecutables:
    sens: Sens
    entree: Decimal
    stop: Decimal
    objectif: Decimal
    distance: Decimal
    multiple: Decimal
    tick_size: Decimal
    objectif_depasse: bool = False
    def __post_init__(self):
        if not isinstance(self.sens,Sens) or type(self.objectif_depasse) is not bool: raise ValueError('sens ou état invalide')
        for n in ('entree','stop','objectif','distance','multiple','tick_size'):
            v=getattr(self,n)
            if type(v) is not Decimal or not v.is_finite() or v<=0: raise ValueError('niveau décimal positif attendu')
        if self.distance!=self.sens.signe*(self.entree-self.stop): raise ValueError('distance incohérente')
        if self.sens.signe*(self.objectif-self.entree)<=0: raise ValueError('objectif du mauvais côté')
        if not est_sur_grille(self.stop,self.tick_size) or not est_sur_grille(self.objectif,self.tick_size): raise ValueError('protections hors grille')

def _objectif(entree,stop,sens,multiple,tick):
    distance=sens.signe*(entree-stop)
    cible=arrondir_sur_grille(entree+sens.signe*multiple*distance,tick,Arrondi.HAUT if sens is Sens.ACHAT else Arrondi.BAS)
    return NiveauxExecutables(sens,entree,stop,cible,distance,multiple,tick)

def construire_niveaux(signal,cotation,profil,commun):
    if not isinstance(signal,SignalTechnique) or not isinstance(cotation,Cotation) or not isinstance(commun,ParametresCommuns): raise ValueError('signal, cotation et paramètres attendus')
    if not isinstance(profil,ProfilInstrument): return RefusPrix(Motif.ENVIRONMENT_NOT_READY,'profil')
    if signal.symbole!=cotation.symbole or profil.symbole!=signal.symbole: raise ValueError('symboles incohérents')
    if not profil.protections_a_l_entree: return RefusPrix(Motif.ENVIRONMENT_NOT_READY,'protections_a_l_entree')
    if not profil.convention_declenchement_verifiee: return RefusPrix(Motif.ENVIRONMENT_NOT_READY,'convention_declenchement_verifiee')
    with localcontext(Context(prec=48)):
        tick=profil.tick_size
        if cotation.spread<0 or not all(est_sur_grille(v,tick) for v in (cotation.bid,cotation.ask)):
            return RefusPrix(Motif.ENVIRONMENT_NOT_READY,'cotation')
        brut=decimal_depuis(signal.stop_technique); a=decimal_depuis(signal.atr_reference)
        d=signal.sens.signe*(decimal_depuis(signal.cloture_prix)-brut)
        if not 0<d<=decimal_depuis(commun.maximum_chart_stop_atr)*a: return RefusPrix(Motif.STOP_TOO_WIDE)
        achat=signal.sens is Sens.ACHAT
        stop=arrondir_sur_grille(brut if achat else brut+cotation.spread,tick,Arrondi.BAS if achat else Arrondi.HAUT)
        entree=cotation.ask if achat else cotation.bid
        if signal.sens.signe*(entree-stop)<=0: return RefusPrix(Motif.PROTECTION_ERROR,'CONTRAINTE_NATIVE_AVANT_ORDRE')
        n=_objectif(entree,stop,signal.sens,decimal_depuis(signal.multiple_objectif),tick)
        declencheur=cotation.bid if achat else cotation.ask
        distances=(signal.sens.signe*(declencheur-stop),signal.sens.signe*(n.objectif-declencheur))
        minimum=profil.point*profil.distance_stops_min_points
        gel=profil.point*profil.niveau_gel_points
        if any(d<=0 or d<minimum or gel>0 and d<=gel for d in distances):
            return RefusPrix(Motif.PROTECTION_ERROR,'CONTRAINTE_NATIVE_AVANT_ORDRE')
        return n

def recalculer_objectif(niveaux,prix_reel,cotation=None):
    if not isinstance(niveaux,NiveauxExecutables) or type(prix_reel) is not Decimal or not prix_reel.is_finite() or prix_reel<=0: raise ValueError('niveaux et prix réel décimal attendus')
    with localcontext(Context(prec=48)):
        if niveaux.sens.signe*(prix_reel-niveaux.stop)<=0: return RefusPrix(Motif.PROTECTION_ERROR,'SL_ABSENT')
        n=_objectif(prix_reel,niveaux.stop,niveaux.sens,niveaux.multiple,niveaux.tick_size)
        if cotation is None: return n
        if not isinstance(cotation,Cotation): raise ValueError('cotation attendue')
        prix=cotation.bid if n.sens is Sens.ACHAT else cotation.ask
        return replace(n,objectif_depasse=n.sens.signe*(prix-n.objectif)>=0)

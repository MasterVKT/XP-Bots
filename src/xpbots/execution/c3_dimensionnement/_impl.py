"""Implémentation de la couche 3 (dimensionnement). Révisable à comportement constant sous harnais complet."""
from dataclasses import dataclass,replace
from decimal import Context,Decimal,ROUND_FLOOR,localcontext
from xpbots.execution.c0a_types import (EtatCompte,Reservation,RefusExecution,ErreurExecution,OrdreCalcule,ControleNatif,decimal_fini,instant)
from xpbots.execution.c0d_prix import NiveauxExecutables,recalculer_objectif
from xpbots.execution.c1a_calcul import appeler_calcul
from xpbots.execution.c1b_gardes import GardesCompte
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.execution.c2a_risque import calculer_risque,verifier_profil,MesureRisque
from xpbots.noyau.c0b_nombres import decimal_depuis
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1c_domaine import CleIntention,SignalTechnique,Sens,Motif

@dataclass(frozen=True)
class PlanDimensionnement:
    reservation: Reservation
    niveaux: NiveauxExecutables
    mesure_risque: MesureRisque
    budget_gele: Decimal
    fonds_propres_reference: Decimal
    version_reservations: int
    instantane_ms: int
    controle_natif: ControleNatif
    marge_totale_consideree: Decimal
    remplacement: bool = False
    def __post_init__(self):
        if not isinstance(self.reservation,Reservation) or not isinstance(self.niveaux,NiveauxExecutables) or not isinstance(self.mesure_risque,MesureRisque) or not isinstance(self.controle_natif,ControleNatif):
            raise ErreurExecution('plan de dimensionnement mal typé')
        for n in ('budget_gele','fonds_propres_reference'): decimal_fini(getattr(self,n),n,Decimal(0),True)
        decimal_fini(self.marge_totale_consideree,'marge_totale_consideree',Decimal(0))
        instant(self.instantane_ms)
        if type(self.version_reservations) is not int or self.version_reservations<0 or type(self.remplacement) is not bool: raise ErreurExecution('version ou mode invalide')
        if self.reservation.risque_initial!=self.mesure_risque.total or self.mesure_risque.total>self.budget_gele: raise ErreurExecution('risque incohérent avec le plan')
    @property
    def volume(self): return self.reservation.volume
    @property
    def risque(self): return self.mesure_risque.total

def dimensionner(signal,niveaux,profil,compte,registre,gardes,port,commun,deploiement,*,plan_initial=None,volume_rempli=None,prix_reel=None,frais_entree_reels=None):
    return _dimensionner(signal,niveaux,profil,compte,registre,gardes,port,commun,deploiement,
        plan_initial=plan_initial,volume_rempli=volume_rempli,prix_reel=prix_reel,frais_entree_reels=frais_entree_reels)

def _dimensionner(signal,niveaux,profil,compte,registre,gardes,port,commun,deploiement,*,plan_initial=None,volume_rempli=None,prix_reel=None,frais_entree_reels=None,plan_prepare=None):
    if (not isinstance(signal,SignalTechnique) or not isinstance(niveaux,NiveauxExecutables) or not isinstance(compte,EtatCompte)
            or not isinstance(registre,RegistreReservations) or not isinstance(gardes,GardesCompte) or not isinstance(commun,ParametresCommuns)):
        raise ErreurExecution('signal, niveaux et composants réels attendus')
    cle=CleIntention(deploiement,signal.strategie,signal.symbole,signal.cloture_ms,signal.sens)
    if compte.instant_ms<signal.cloture_ms: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'instantane_compte')
    refus=gardes.observer(compte)
    if refus is not None: return refus
    refus=verifier_profil(profil,commun)
    if refus is not None: return refus
    if profil.symbole!=signal.symbole or niveaux.sens is not signal.sens: raise ErreurExecution('symbole ou sens incohérent')
    if niveaux.tick_size!=profil.tick_size: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'specifications_modifiees')
    droits={'FULL':(Sens.ACHAT,Sens.VENTE),'BUY_ONLY':(Sens.ACHAT,),'SELL_ONLY':(Sens.VENTE,)}
    if signal.sens not in droits.get(profil.mode_negociation,()): return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'mode_negociation')
    remplacement=plan_initial is not None
    with localcontext(Context(prec=48)):
        version=registre.etat.version
        if remplacement:
            if not isinstance(plan_initial,PlanDimensionnement) or plan_initial.reservation.cle!=cle or plan_initial.niveaux.stop!=niveaux.stop:
                raise ErreurExecution('plan initial de cette intention attendu')
            if volume_rempli is None or prix_reel is None or frais_entree_reels is None:
                return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'remplissage')
            decimal_fini(volume_rempli,'volume_rempli',Decimal(0),True)
            if volume_rempli>plan_initial.volume: raise ErreurExecution('volume rempli supérieur au plan')
            position=next((p for p in compte.positions if p.cle==cle),None)
            if position is None or position.volume!=volume_rempli: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'position_remplie')
            n=recalculer_objectif(niveaux,prix_reel)
            if not isinstance(n,NiveauxExecutables): return RefusExecution(n.motif,n.detail)
            budget=plan_initial.budget_gele
            eqt=plan_initial.fonds_propres_reference
            plafond=min(profil.volume_max,volume_rempli)
        else:
            if any(v is not None for v in (volume_rempli,prix_reel,frais_entree_reels)): raise ErreurExecution('remplissage sans plan initial')
            n=niveaux;eqt=compte.fonds_propres
            budget=decimal_depuis(commun.risk_fraction_per_entry)*eqt
            plafond=profil.volume_max
            if plan_prepare is not None:
                if plan_prepare.reservation.cle!=cle or plan_prepare.niveaux!=niveaux:
                    raise ErreurExecution('plan préparé de cette intention attendu')
                budget=plan_prepare.budget_gele;eqt=plan_prepare.fonds_propres_reference
                plafond=plan_prepare.volume
                if (plafond<profil.volume_min or plafond>profil.volume_max or plafond%profil.volume_pas
                        or profil.volume_limite>0 and plafond>profil.volume_limite):
                    return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'specifications_modifiees')
        compte_limites=replace(compte,fonds_propres=eqt)
        refus=registre.verifier_admission(cle,profil.sous_jacent,Decimal(0),compte_limites,remplacement=remplacement)
        if refus is not None: return refus
        if profil.volume_limite>0: plafond=min(plafond,profil.volume_limite)
        premier=int((plafond/profil.volume_pas).to_integral_value(rounding=ROUND_FLOOR))
        dernier=int(profil.volume_min/profil.volume_pas)
        if plan_prepare is not None:
            dernier=premier
        echec=RefusExecution(Motif.MIN_VOLUME_OR_RISK_REJECT)
        for nombre in range(premier,dernier-1,-1):
            volume=nombre*profil.volume_pas
            risque=calculer_risque(signal,n,volume,profil,commun,port,apres_remplissage=remplacement,frais_entree_reels=frais_entree_reels)
            if isinstance(risque,RefusExecution): return risque
            if risque.total>budget: continue
            if plan_prepare is not None and risque.total>plan_prepare.risque:
                return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'couts_avant_ordre')
            refus=registre.verifier_admission(cle,profil.sous_jacent,risque.total,compte_limites,remplacement=remplacement)
            if refus is not None:
                echec=refus;continue
            marge=appeler_calcul(port,'marge',profil,signal.sens,volume,n.entree)
            if isinstance(marge,RefusExecution): return marge
            ordre=OrdreCalcule(cle,profil.symbole_courtier,volume,n.entree,n.stop,n.objectif)
            controle=appeler_calcul(port,'controler',ordre,compte,remplacement=remplacement)
            if isinstance(controle,RefusExecution): return controle
            pending=registre.marge_en_attente(compte,cle if remplacement else None)
            totale=controle.marge_totale_apres+pending
            if totale>decimal_depuis(commun.max_margin_fraction_of_equity)*eqt:
                echec=RefusExecution(Motif.MARGIN_REJECT,'MARGE_TIERS');continue
            if not controle.admis or not controle.stop_out_respecte or controle.marge_libre_apres<pending:
                echec=RefusExecution(Motif.MARGIN_REJECT,'CONTROLE_NATIF');continue
            if registre.etat.version!=version: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'version_reservations')
            reservation=Reservation(cle,profil.sous_jacent,risque.total,marge,volume)
            return PlanDimensionnement(reservation,n,risque,budget,eqt,version,compte.instant_ms,controle,totale,remplacement)
        return echec

def revalider_avant_envoi(plan,signal,profil,compte,registre,gardes,port,commun):
    """Rejouer les mêmes contraintes sur le seul volume préparé ; ne modifie aucun risque réservé."""
    if not isinstance(plan,PlanDimensionnement) or plan.remplacement or not isinstance(registre,RegistreReservations):
        raise ErreurExecution('plan avant remplissage et registre réel attendus')
    etat=registre.etat
    propre=next((r for r in etat.reservations if r.cle==plan.reservation.cle),None)
    if propre!=plan.reservation:
        return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'reservation_avant_ordre')
    sans_propre=RegistreReservations(commun,replace(etat,reservations=tuple(r for r in etat.reservations if r.cle!=propre.cle)))
    resultat=_dimensionner(signal,plan.niveaux,profil,compte,sans_propre,gardes,port,commun,
        propre.cle.deploiement,plan_prepare=plan)
    if registre.etat.version!=etat.version:
        return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'version_reservations')
    return resultat

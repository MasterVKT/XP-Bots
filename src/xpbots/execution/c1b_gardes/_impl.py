"""Implémentation de la couche 1b (gardes_compte). Révisable à comportement constant sous harnais complet."""
from dataclasses import dataclass,replace
from datetime import date,timedelta
from decimal import Context,Decimal,localcontext
from xpbots.execution.c0a_types import EtatCompte,EtatGardes,RefusExecution,ErreurExecution,decimal_fini,instant,texte
from xpbots.noyau.c0a_temps import instant_vers_datetime,instant_depuis_datetime
from xpbots.noyau.c0b_nombres import decimal_depuis
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.noyau.c1c_domaine import Motif

@dataclass(frozen=True)
class MouvementCompte:
    reference: str
    instant_ms: int
    variation_solde: Decimal
    flux_externe: bool = False
    def __post_init__(self):
        texte(self.reference);instant(self.instant_ms);decimal_fini(self.variation_solde,'variation_solde')
        if type(self.flux_externe) is not bool: raise ErreurExecution('booléen attendu')

@dataclass(frozen=True)
class BaseReconstituee:
    jour_utc: date
    instant_ms: int
    solde_minuit: Decimal
    base_neutralisee: Decimal
    pic_solde_neutralise: Decimal
    references_flux: tuple[str,...] = ()
    flux_identifies: tuple[MouvementCompte,...] = ()
    def __post_init__(self):
        instant(self.instant_ms)
        if type(self.jour_utc) is not date or instant_vers_datetime(self.instant_ms).date()!=self.jour_utc: raise ErreurExecution('jour UTC incohérent')
        for n in ('solde_minuit','base_neutralisee','pic_solde_neutralise'): decimal_fini(getattr(self,n),n,Decimal(0),True)
        refs=tuple(self.references_flux)
        if len(set(refs))!=len(refs): raise ErreurExecution('références de flux dupliquées')
        for r in refs: texte(r)
        object.__setattr__(self,'references_flux',refs)
        flux=tuple(self.flux_identifies)
        if any(not isinstance(m,MouvementCompte) or not m.flux_externe for m in flux) or tuple(m.reference for m in flux)!=refs:
            raise ErreurExecution('flux identifiés incohérents')
        object.__setattr__(self,'flux_identifies',flux)

def reconstituer_base_utc(compte,mouvements,couverture,*,aucune_position_minuit):
    if not isinstance(compte,EtatCompte) or type(aucune_position_minuit) is not bool: raise ErreurExecution('compte et preuve de minuit attendus')
    moment=instant_vers_datetime(compte.instant_ms)
    borne=instant_depuis_datetime(moment.replace(hour=0,minute=0,second=0,microsecond=0))
    if (not aucune_position_minuit or not isinstance(couverture,Intervalle)
            or couverture.debut_ms>borne or couverture.fin_ms<=compte.instant_ms):
        return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'historique_minuit')
    mouvements=tuple(mouvements)
    if any(not isinstance(m,MouvementCompte) for m in mouvements): raise ErreurExecution('mouvement attendu')
    if len({m.reference for m in mouvements})!=len(mouvements): raise ErreurExecution('mouvements dupliqués')
    if any(m.instant_ms>compte.instant_ms for m in mouvements): raise ErreurExecution('mouvement futur')
    retenus=sorted((m for m in mouvements if m.instant_ms>=borne),key=lambda m:m.instant_ms)
    with localcontext(Context(prec=48)):
        base=compte.solde-sum((m.variation_solde for m in retenus),Decimal(0))
        externes=sum((m.variation_solde for m in retenus if m.flux_externe),Decimal(0))
        neutralisee=base+externes
        cumul=Decimal(0);pic=neutralisee
        for m in retenus:
            if not m.flux_externe: cumul+=m.variation_solde
            pic=max(pic,neutralisee+cumul)
        if base<=0 or neutralisee<=0: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'base_quotidienne')
        flux=tuple(m for m in retenus if m.flux_externe)
        return BaseReconstituee(moment.date(),compte.instant_ms,base,neutralisee,pic,tuple(m.reference for m in flux),flux)

class GardesCompte:
    def __init__(self,commun,etat=None):
        if not isinstance(commun,ParametresCommuns) or etat is not None and not isinstance(etat,EtatGardes): raise ErreurExecution('paramètres et état de gardes attendus')
        if etat is not None and instant_vers_datetime(etat.dernier_ms).date()!=etat.jour_utc: raise ErreurExecution('jour de garde incohérent')
        self._p,self._etat=commun,etat
    @property
    def etat(self): return self._etat
    def refus(self):
        if self._etat is None: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'base_quotidienne')
        if self._etat.arret_global: return RefusExecution(Motif.GLOBAL_DRAWDOWN_HALT)
        if self._etat.verrou_quotidien: return RefusExecution(Motif.DAILY_LOSS_LOCK)
        return None
    def observer(self,compte,reconstitution=None):
        if not isinstance(compte,EtatCompte): raise ErreurExecution('compte attendu')
        if self._etat is not None and compte.instant_ms<self._etat.dernier_ms: raise ErreurExecution('observation antérieure')
        if compte.flux_externe_non_neutralise: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'flux_externe')
        moment=instant_vers_datetime(compte.instant_ms);jour=moment.date()
        ancien=self._etat
        ajustement_pic=Decimal(0)
        nouveau=ancien is None or ancien.jour_utc!=jour
        if nouveau:
            minuit=moment.hour==moment.minute==moment.second==moment.microsecond==0
            if minuit:
                base=compte.fonds_propres;pic_reconstruit=compte.fonds_propres;refs=()
            else:
                if not isinstance(reconstitution,BaseReconstituee) or reconstitution.jour_utc!=jour or reconstitution.instant_ms!=compte.instant_ms:
                    return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'base_quotidienne')
                base=reconstitution.base_neutralisee;pic_reconstruit=reconstitution.pic_solde_neutralise
                refs=reconstitution.references_flux
                if ancien:
                    with localcontext(Context(prec=48)):
                        ajustement_pic=sum((m.variation_solde for m in reconstitution.flux_identifies if m.reference not in ancien.references),Decimal(0))
            if base<=0: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'base_quotidienne')
        else:
            base=ancien.base_quotidienne;pic_reconstruit=ancien.pic;refs=()
        with localcontext(Context(prec=48)):
            pic=max(compte.fonds_propres,pic_reconstruit,ancien.pic+ajustement_pic if ancien else pic_reconstruit)
            quotidien=(ancien.verrou_quotidien if ancien and not nouveau else False) or compte.fonds_propres<=base*(1-decimal_depuis(self._p.daily_equity_loss_limit_fraction))
            arret=bool(ancien and ancien.arret_global) or compte.fonds_propres<=pic*(1-decimal_depuis(self._p.peak_equity_drawdown_halt_fraction))
            references=tuple(dict.fromkeys((ancien.references if ancien else ())+refs))
            self._etat=EtatGardes(jour,base,pic,quotidien,arret,compte.instant_ms,references)
        return self.refus()
    def neutraliser_flux(self,montant,reference):
        decimal_fini(montant,'montant');texte(reference)
        if self._etat is None: raise ErreurExecution('garde non initialisée')
        e=self._etat
        if reference in e.references: return e
        with localcontext(Context(prec=48)):
            self._etat=replace(e,base_quotidienne=e.base_quotidienne+montant,pic=e.pic+montant,references=e.references+(reference,))
        return self._etat
    def reactiver(self,compte,decision,reconstitution=None):
        texte(decision)
        if self._etat is None or not self._etat.arret_global or decision in self._etat.references: raise ErreurExecution('nouvelle décision de déploiement attendue')
        resultat=self.observer(compte,reconstitution)
        if resultat is not None and resultat.motif is Motif.ENVIRONMENT_NOT_READY: return resultat
        self._etat=replace(self._etat,arret_global=False,pic=compte.fonds_propres,references=self._etat.references+(decision,))
        return self.refus()

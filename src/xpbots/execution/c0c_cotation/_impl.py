"""Implémentation de la couche 0c (garde_cotation). Révisable à comportement constant sous harnais complet."""
from dataclasses import dataclass
from datetime import timedelta
from decimal import Context,localcontext
from enum import StrEnum
from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.noyau.c0b_nombres import decimal_depuis
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1a_marche import Cotation
from xpbots.noyau.c1c_domaine import Motif,SignalTechnique,verifier_motif

class EtatCotation(StrEnum):
    ADMISSIBLE='ADMISSIBLE'
    ATTENDRE='ATTENDRE'
    EXPIREE='EXPIREE'

@dataclass(frozen=True)
class VerdictCotation:
    etat: EtatCotation
    motif: Motif | None = None
    detail: str | None = None
    derniere_cause: str | None = None
    def __post_init__(self):
        if not isinstance(self.etat,EtatCotation): raise ValueError('état de cotation attendu')
        if self.derniere_cause not in (None,'SPREAD_CAP','ENTRY_GAP','COTATION_INVALIDE','AUCUNE_COTATION'): raise ValueError('cause inconnue')
        if self.etat is EtatCotation.ADMISSIBLE:
            if any(v is not None for v in (self.motif,self.detail,self.derniere_cause)): raise ValueError('admission avec refus')
        elif self.etat is EtatCotation.EXPIREE:
            verifier_motif(self.motif,self.detail)
            if self.motif is not Motif.SIGNAL_EXPIRED or self.detail!=self.derniere_cause: raise ValueError('expiration incohérente')
        elif self.detail is not None or self.motif not in (None,Motif.SPREAD_CAP,Motif.ENTRY_GAP) or self.derniere_cause is None:
            raise ValueError('attente incohérente')

def evaluer_cotation(signal,cotation,instant_ms,commun,derniere_cause=None):
    verifier_instant(instant_ms)
    if not isinstance(signal,SignalTechnique) or not isinstance(commun,ParametresCommuns): raise ValueError('signal et paramètres attendus')
    if signal.symbole not in commun.universe_priority or signal.strategie not in commun.simultaneous_strategy_priority: raise ValueError('signal non configuré')
    causes=('SPREAD_CAP','ENTRY_GAP','COTATION_INVALIDE','AUCUNE_COTATION')
    if derniere_cause is not None and derniere_cause not in causes: raise ValueError('cause inconnue')
    ttl=timedelta(seconds=commun.entry_signal_ttl_seconds)//timedelta(milliseconds=1)
    if instant_ms >= signal.cloture_ms+ttl:
        cause=derniere_cause or ('AUCUNE_COTATION' if cotation is None else 'COTATION_INVALIDE')
        return VerdictCotation(EtatCotation.EXPIREE,Motif.SIGNAL_EXPIRED,cause,cause)
    age=timedelta(seconds=commun.quote_max_age_seconds)//timedelta(milliseconds=1)
    if cotation is None:
        return VerdictCotation(EtatCotation.ATTENDRE,derniere_cause='AUCUNE_COTATION')
    if (not isinstance(cotation,Cotation) or cotation.symbole!=signal.symbole or instant_ms<signal.cloture_ms
            or not signal.cloture_ms<=cotation.instant_fournisseur_ms<=instant_ms
            or not signal.cloture_ms<=cotation.instant_reception_ms<=instant_ms
            or instant_ms-cotation.instant_fournisseur_ms>age or instant_ms-cotation.instant_reception_ms>age
            or cotation.ask<cotation.bid):
        return VerdictCotation(EtatCotation.ATTENDRE,derniere_cause='COTATION_INVALIDE')
    with localcontext(Context(prec=48)):
        if cotation.spread>decimal_depuis(commun.max_spread_price[signal.symbole]):
            return VerdictCotation(EtatCotation.ATTENDRE,Motif.SPREAD_CAP,derniere_cause='SPREAD_CAP')
        if abs(cotation.bid-decimal_depuis(signal.cloture_prix))>decimal_depuis(commun.max_entry_bid_gap_atr)*decimal_depuis(signal.atr_reference):
            return VerdictCotation(EtatCotation.ATTENDRE,Motif.ENTRY_GAP,derniere_cause='ENTRY_GAP')
    return VerdictCotation(EtatCotation.ADMISSIBLE)

"""Implémentation de la couche 0a (types_execution). Révisable à comportement constant sous harnais complet."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Mapping

from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.noyau.c1a_marche import Cotation
from xpbots.noyau.c1c_domaine import CleIntention, Motif, Sens, SignalTechnique, verifier_motif
from xpbots.noyau.decisions import Signal as SignalEMA, CleIntention as CleEMA
from xpbots.noyau.marche import Tick as TickEMA

class ErreurExecution(ValueError):
    """Entrée de calcul ou état restauré incohérent."""

def decimal_fini(v, nom, minimum=None, strict=False):
    if type(v) is not Decimal or not v.is_finite() or (minimum is not None and (v <= minimum if strict else v < minimum)):
        raise ErreurExecution(f'{nom} : Decimal fini hors bornes')
    return v

def instant(v):
    try:
        return verifier_instant(v)
    except ValueError as e:
        raise ErreurExecution(str(e)) from e

def texte(v):
    if type(v) is not str or not v or v != v.strip():
        raise ErreurExecution('texte non vide sans espaces de bord attendu')
    return v

def _booleens(obj, noms):
    if any(type(getattr(obj,n)) is not bool for n in noms):
        raise ErreurExecution('booléen attendu')

@dataclass(frozen=True)
class RefusExecution:
    motif: Motif
    detail: str | None = None
    def __post_init__(self):
        m,d = verifier_motif(self.motif,self.detail)
        object.__setattr__(self,'motif',m)
        object.__setattr__(self,'detail',d)

class EtatIntention(StrEnum):
    EN_ATTENTE_COTATION='EN_ATTENTE_COTATION'
    RESERVEE='RESERVEE'
    ENVOYEE='ENVOYEE'
    INCONNUE='INCONNUE'
    REMPLIE_PARTIELLE='REMPLIE_PARTIELLE'
    OUVERTE='OUVERTE'
    CLOTURE_DEMANDEE='CLOTURE_DEMANDEE'
    CLOTUREE='CLOTUREE'
    REFUSEE='REFUSEE'
    EXPIREE='EXPIREE'

@dataclass(frozen=True)
class PositionCompte:
    identifiant: str
    symbole: str
    sous_jacent: str
    volume: Decimal
    risque_initial: Decimal | None
    cle: CleIntention | None = None
    def __post_init__(self):
        for n in ('identifiant','symbole','sous_jacent'): texte(getattr(self,n))
        decimal_fini(self.volume,'volume',Decimal(0),True)
        if self.cle is not None:
            if not isinstance(self.cle,CleIntention) or self.cle.symbole != self.symbole:
                raise ErreurExecution('clé possédée et symbole incohérents')
            decimal_fini(self.risque_initial,'risque_initial',Decimal(0))
        elif self.risque_initial is not None:
            decimal_fini(self.risque_initial,'risque_initial',Decimal(0))

@dataclass(frozen=True)
class EtatCompte:
    instant_ms: int
    fonds_propres: Decimal
    solde: Decimal
    marge_utilisee: Decimal
    positions: tuple[PositionCompte,...] = ()
    flux_externe_non_neutralise: bool = False
    def __post_init__(self):
        instant(self.instant_ms)
        for n in ('fonds_propres','solde'): decimal_fini(getattr(self,n),n)
        decimal_fini(self.marge_utilisee,'marge_utilisee',Decimal(0))
        _booleens(self,('flux_externe_non_neutralise',))
        if not isinstance(self.positions,(tuple,list)): raise ErreurExecution('collection de positions attendue')
        ps=tuple(self.positions)
        if any(not isinstance(p,PositionCompte) for p in ps) or len({p.identifiant for p in ps})!=len(ps):
            raise ErreurExecution('positions uniques attendues')
        cles=[p.cle for p in ps if p.cle is not None]
        if len(set(cles))!=len(cles): raise ErreurExecution('clés de positions dupliquées')
        object.__setattr__(self,'positions',ps)

@dataclass(frozen=True)
class Reservation:
    cle: CleIntention
    sous_jacent: str
    risque_initial: Decimal
    marge_initiale: Decimal
    volume: Decimal
    remplie: bool = False
    def __post_init__(self):
        if not isinstance(self.cle,CleIntention): raise ErreurExecution('clé attendue')
        texte(self.sous_jacent)
        for n in ('risque_initial','volume'): decimal_fini(getattr(self,n),n,Decimal(0),n=='volume')
        decimal_fini(self.marge_initiale,'marge_initiale',Decimal(0))
        _booleens(self,('remplie',))

@dataclass(frozen=True)
class EtatReservations:
    version: int = 0
    reservations: tuple[Reservation,...] = ()
    verrous: tuple[str,...] = ()
    terminees: tuple[CleIntention,...] = ()
    def __post_init__(self):
        if type(self.version) is not int or self.version<0: raise ErreurExecution('version naturelle attendue')
        for n in ('reservations','verrous','terminees'):
            if not isinstance(getattr(self,n),(tuple,list)): raise ErreurExecution('collection attendue')
            object.__setattr__(self,n,tuple(getattr(self,n)))
        if any(not isinstance(r,Reservation) for r in self.reservations): raise ErreurExecution('réservation attendue')
        if any(not isinstance(k,CleIntention) for k in self.terminees): raise ErreurExecution('clé terminée attendue')
        for v in self.verrous: texte(v)
        cles=[r.cle for r in self.reservations]
        if len(set(cles))!=len(cles) or len(set(self.terminees))!=len(self.terminees): raise ErreurExecution('clés uniques attendues')
        if any(not isinstance(k,CleIntention) for k in self.terminees) or set(cles)&set(self.terminees): raise ErreurExecution('clé terminée réservée')
        if len(set(self.verrous))!=len(self.verrous): raise ErreurExecution('verrous uniques attendus')
        for v in self.verrous: texte(v)

@dataclass(frozen=True)
class EtatGardes:
    jour_utc: date
    base_quotidienne: Decimal
    pic: Decimal
    verrou_quotidien: bool
    arret_global: bool
    dernier_ms: int
    references: tuple[str,...] = ()
    def __post_init__(self):
        if type(self.jour_utc) is not date: raise ErreurExecution('jour UTC attendu')
        for n in ('base_quotidienne','pic'): decimal_fini(getattr(self,n),n,Decimal(0),True)
        instant(self.dernier_ms)
        _booleens(self,('verrou_quotidien','arret_global'))
        if not isinstance(self.references,(tuple,list)): raise ErreurExecution('collection de références attendue')
        refs=tuple(self.references)
        for v in refs: texte(v)
        if len(set(refs))!=len(refs): raise ErreurExecution('références uniques attendues')
        for v in refs: texte(v)
        object.__setattr__(self,'references',refs)

@dataclass(frozen=True)
class ControleNatif:
    admis: bool
    marge_totale_apres: Decimal
    marge_libre_apres: Decimal
    stop_out_respecte: bool
    code: str
    def __post_init__(self):
        _booleens(self,('admis','stop_out_respecte'))
        decimal_fini(self.marge_totale_apres,'marge_totale_apres',Decimal(0))
        decimal_fini(self.marge_libre_apres,'marge_libre_apres')
        texte(self.code)

@dataclass(frozen=True)
class OrdreCalcule:
    cle: CleIntention
    symbole_courtier: str
    volume: Decimal
    entree: Decimal
    stop: Decimal
    objectif: Decimal
    def __post_init__(self):
        if not isinstance(self.cle,CleIntention): raise ErreurExecution('clé attendue')
        texte(self.symbole_courtier)
        for n in ('volume','entree','stop','objectif'): decimal_fini(getattr(self,n),n,Decimal(0),True)
        s=self.cle.sens.signe
        if s*(self.entree-self.stop)<=0 or s*(self.objectif-self.entree)<=0: raise ErreurExecution('protections incohérentes')

def _json(valeur):
    if isinstance(valeur,Decimal): return str(valeur)
    if isinstance(valeur,Mapping): return {k:_json(v) for k,v in valeur.items()}
    if isinstance(valeur,(list,tuple)): return tuple(_json(v) for v in valeur)
    return valeur

def adapter_signal_ema(signal):
    if not isinstance(signal,SignalEMA): raise ErreurExecution('Signal EMA attendu')
    cloture=float(signal.cloture_bid)
    if Decimal(repr(cloture))!=signal.cloture_bid: raise ErreurExecution('clôture non conservée par conversion flottante')
    sens=Sens.ACHAT if signal.sens>0 else Sens.VENTE
    return SignalTechnique(signal.strategie,signal.symbole,signal.cloture_ms,sens,cloture,signal.a_t,signal.b_sl,
                           signal.multiple_objectif,{'origine':'noyau_ema','etat_detecteur':_json(signal.etat_detecteur)})

def adapter_cotation_ema(tick,reception_ms):
    if not isinstance(tick,TickEMA): raise ErreurExecution('Tick EMA attendu')
    instant(reception_ms)
    return Cotation(tick.symbole,tick.bid,tick.ask,tick.instant.ms,reception_ms)

def adapter_cle_ema(cle):
    if not isinstance(cle,CleEMA): raise ErreurExecution('CleIntention EMA attendue')
    return CleIntention(cle.deployment_id,cle.strategie,cle.symbole,cle.cloture_ms,Sens.ACHAT if cle.sens>0 else Sens.VENTE)

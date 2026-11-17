"""Valeurs de transport, sans ressource ni horloge implicite."""
from dataclasses import dataclass
from decimal import Decimal
from math import isfinite
from xpbots.infra.c0a_types import ErreurInfra,entier_natif,champ_natif,nombre_decimal
from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.execution.c4_cycle import ReponseCourtier,StatutAccuse

_PRIX=('TRADE_RETCODE_REQUOTE','TRADE_RETCODE_PRICE_CHANGED','TRADE_RETCODE_PRICE_OFF','TRADE_RETCODE_TOO_MANY_REQUESTS')
_ACCEPTES=('TRADE_RETCODE_DONE','TRADE_RETCODE_DONE_PARTIAL','TRADE_RETCODE_PLACED')
_DEFINITIFS=('TRADE_RETCODE_INVALID_VOLUME','TRADE_RETCODE_LIMIT_VOLUME','TRADE_RETCODE_NO_MONEY',
    'TRADE_RETCODE_INVALID_STOPS','TRADE_RETCODE_LIMIT_POSITIONS','TRADE_RETCODE_LIMIT_ORDERS',
    'TRADE_RETCODE_MARKET_CLOSED','TRADE_RETCODE_TRADE_DISABLED','TRADE_RETCODE_CLIENT_DISABLES_AT',
    'TRADE_RETCODE_SERVER_DISABLES_AT','TRADE_RETCODE_LONG_ONLY','TRADE_RETCODE_SHORT_ONLY',
    'TRADE_RETCODE_CLOSE_ONLY','TRADE_RETCODE_ONLY_REAL','TRADE_RETCODE_INVALID_FILL')


def decimal_natif(v):return nombre_decimal(v)


def reel(v):
    if type(v) is not Decimal or not v.is_finite() or v<=0:raise ErreurInfra('valeur executable positive requise')
    r=float(v)
    if not isfinite(r) or r<=0:raise ErreurInfra('conversion executable impossible')
    return r


def ticket_natif(v,*,absent=False):
    if v is None:
        if absent:return None
        raise ErreurInfra('ticket absent')
    if type(v) is str:
        if not v.isascii() or not v.isdigit() or str(int(v))!=v:raise ErreurInfra('ticket non canonique')
        n=int(v)
    else:n=entier_natif(v)
    if n==0 and absent:return None
    if n<=0:raise ErreurInfra('ticket positif requis')
    return str(n)


def nom_retcode(sdk,code):
    code=entier_natif(code)
    noms=[n for n in dir(sdk) if n.startswith('TRADE_RETCODE_') and getattr(sdk,n)==code]
    return noms[0] if len(noms)==1 else 'CODE_NATIF_INCONNU_'+str(code)


def classer(sdk,code,*,precontrole=False):
    nom=nom_retcode(sdk,code)
    if nom in _PRIX:return StatutAccuse.REFUSE,False,nom
    if nom in _DEFINITIFS:return StatutAccuse.REFUSE,True,nom
    # Un precontrole termine avant order_send prouve qu'aucun ordre n'a ete emis.
    if precontrole:return StatutAccuse.REFUSE,True,nom
    if nom in _ACCEPTES:return StatutAccuse.ACCEPTE,False,nom
    return StatutAccuse.INCONNU,False,nom


@dataclass(frozen=True)
class PreparationNative:
    revision:int
    references:tuple
    def __post_init__(self):
        if type(self.revision) is not int or self.revision<0:raise ErreurInfra('revision native invalide')
        refs=tuple(self.references)
        if any(type(r) is not str or not r for r in refs) or len(set(refs))!=len(refs):raise ErreurInfra('references natives uniques requises')
        object.__setattr__(self,'references',refs)


@dataclass(frozen=True)
class ReceptionNative:
    instant_ms:int
    reponses:tuple=()
    alertes:tuple=()
    def __post_init__(self):
        verifier_instant(self.instant_ms)
        reponses,alertes=tuple(self.reponses),tuple(self.alertes)
        if any(not isinstance(r,ReponseCourtier) or r.instant_ms>self.instant_ms for r in reponses):raise ErreurInfra('reponse native future ou mal typee')
        if any(type(a) is not str or not a for a in alertes):raise ErreurInfra('code alerte natif requis')
        object.__setattr__(self,'reponses',reponses);object.__setattr__(self,'alertes',alertes)


@dataclass(frozen=True)
class RapportObservationMT5:
    instant_ms:int
    observation:object=None
    base_utc:object=None
    alertes:tuple=()
    def __post_init__(self):
        from xpbots.execution.c5b_reprise import ObservationNative
        from xpbots.execution.c1b_gardes import BaseReconstituee
        from xpbots.execution.c0a_types import RefusExecution
        verifier_instant(self.instant_ms)
        if self.observation is not None and (not isinstance(self.observation,ObservationNative)
                or self.observation.compte.instant_ms!=self.instant_ms):raise ErreurInfra('observation native courante requise')
        if self.base_utc is not None and not isinstance(self.base_utc,(BaseReconstituee,RefusExecution)):
            raise ErreurInfra('preuve monetaire reelle requise')
        codes=tuple(self.alertes)
        if any(type(v) is not str or not v for v in codes):raise ErreurInfra('codes alertes requis')
        object.__setattr__(self,'alertes',codes)

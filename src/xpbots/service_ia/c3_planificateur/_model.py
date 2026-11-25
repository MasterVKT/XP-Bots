"""Formats propres à la planification et aux agrégats calculés par le code."""
from dataclasses import dataclass
from datetime import date, timedelta, time
from decimal import Decimal, InvalidOperation
from xpbots.service_ia.c0_types import (ErreurService, canonique, decoder,
    empreinte, entier, instant, texte, montant)
from xpbots.noyau.c0a_temps import instant_vers_datetime, instant_depuis_datetime

PRIORITES={k:i for i,k in enumerate(('EXTRACTION','BRIEFING','JOURNAL','GOLDEN','WEEKLY_REVIEW'))}
MATERIEL=('event_class','temporal_status','policy_actor','stance')
_METRIQUES=frozenset(('item_id','period','strategy','symbol','arm','net_pnl','trade_count',
    'equity_drawdown','ai_cost_usd','known_at_ms','dimensions','refusals','data_gaps'))
_DECISIONS=frozenset(('strategy','symbol','bar_close','baseline_reasons','ai_reason',
    'snapshot_id','arm','known_at_ms'))
_DIMENSIONS=frozenset(('range_width_atr_h1','first_breakout_hour_london','direction',
    'local_stop_distance','market_cost_usd','new_signal_after_veto','blocked_winners',
    'too_late_opportunities','fill_ratio'))


def ms(s):return timedelta(seconds=s)//timedelta(milliseconds=1)


def jour_suivant(t):
    dt=instant_vers_datetime(t)
    return instant_depuis_datetime((dt+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0))


def slot(jour,heure,zone):
    from datetime import datetime
    return instant_depuis_datetime(datetime.combine(jour,time.fromisoformat(heure),zone))


def copie(v):return decoder(canonique(v))


@dataclass(frozen=True)
class CasDerive:
    case_id: str
    dossier: bytes
    attendu: bytes

    def __post_init__(self):
        texte(self.case_id);decoder(self.dossier);decoder(self.attendu)

    @property
    def signature(self):
        return empreinte(dict(case_id=self.case_id,dossier=decoder(self.dossier),attendu=decoder(self.attendu)))


def _identifiants(r,v):
    if (v['strategy'] not in r.configuration.technique.commun.simultaneous_strategy_priority
            or v['symbol'] not in r.configuration.technique.commun.universe_priority
            or v['arm'] not in ('REFERENCE','IA')):raise ErreurService('IDENTIFIANTS_METRIQUES_INVALIDES')


def valider_metrique(r,v,now,zone):
    if type(v) is not dict or set(v)!=_METRIQUES:raise ErreurService('CHAMPS_METRIQUES_INVALIDES')
    v=copie(v);_identifiants(r,v);texte(v['item_id']);texte(v['period']);instant(v['known_at_ms'])
    if v['known_at_ms']>now:raise ErreurService('METRIQUE_FUTURE')
    try:j=date.fromisoformat(v['period'])
    except ValueError:raise ErreurService('PERIODE_METRIQUE_INVALIDE') from None
    if j.isoformat()!=v['period'] or j>instant_vers_datetime(v['known_at_ms']).astimezone(zone).date():
        raise ErreurService('PERIODE_METRIQUE_FUTURE')
    for cle in ('net_pnl','equity_drawdown','ai_cost_usd'):
        texte(v[cle])
        try:d=Decimal(v[cle])
        except InvalidOperation:raise ErreurService('MONTANT_METRIQUE_INVALIDE') from None
        if not d.is_finite() or cle!='net_pnl' and d<0:raise ErreurService('MONTANT_METRIQUE_INVALIDE')
    entier(v['trade_count']);entier(v['data_gaps'])
    if type(v['refusals']) is not dict or type(v['dimensions']) is not dict:
        raise ErreurService('AXES_METRIQUES_INVALIDES')
    for k,n in v['refusals'].items():texte(k);entier(n)
    if set(v['dimensions'])-_DIMENSIONS:raise ErreurService('DIMENSION_INCONNUE')
    if any(type(x) not in (str,int,bool) for x in v['dimensions'].values()):
        raise ErreurService('DIMENSION_SCALAIRE_REQUISE')
    return v


def valider_decision(r,v,now):
    if type(v) is not dict or set(v)!=_DECISIONS:raise ErreurService('CHAMPS_DECISION_INVALIDES')
    v=copie(v);_identifiants(r,v);instant(v['bar_close']);instant(v['known_at_ms'])
    if not v['bar_close']<=v['known_at_ms']<=now:raise ErreurService('DECISION_NON_CAUSALE')
    if type(v['baseline_reasons']) is not list:raise ErreurService('RAISONS_DECISION_INVALIDES')
    for raison in v['baseline_reasons']:texte(raison)
    if v['ai_reason'] is not None:texte(v['ai_reason'])
    if v['snapshot_id'] is not None:
        if type(v['snapshot_id']) is int:entier(v['snapshot_id'],1)
        else:texte(v['snapshot_id'])
    return v

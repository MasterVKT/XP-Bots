"""Implémentation de la couche 0c (configuration). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, time
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any, Callable, Mapping

SCHEMA_PREUVE = 'xp-bots-resource-preservation-v1'
MODES = frozenset({'REJEU', 'PAPER', 'PAPER_AB', 'DEMO', 'REEL'})


class ErreurConfiguration(ValueError):
    """Export figé, preuve de conservation ou valeur de paramètre refusés."""


# ---------------------------------------------------------------- lecture stricte et empreintes

def _sans_doublon(paires: list[tuple[str, Any]]) -> dict[str, Any]:
    resultat: dict[str, Any] = {}
    for cle, valeur in paires:
        if cle in resultat:
            raise ErreurConfiguration(f'clé dupliquée : {cle!r}')
        resultat[cle] = valeur
    return resultat


def _refuser_constante(nom: str) -> Any:
    raise ErreurConfiguration(f'nombre non fini : {nom}')


def _lire_json(octets: bytes, nom: str) -> Any:
    if not isinstance(octets, bytes):
        raise ErreurConfiguration(f'{nom} : octets attendus')
    try:
        texte = octets.decode('utf-8')
    except UnicodeDecodeError as erreur:
        raise ErreurConfiguration(f'{nom} : octets non UTF-8') from erreur
    if texte.startswith('﻿'):
        raise ErreurConfiguration(f'{nom} : BOM refusé')
    try:
        return json.loads(texte, object_pairs_hook=_sans_doublon, parse_constant=_refuser_constante)
    except json.JSONDecodeError as erreur:
        raise ErreurConfiguration(f'{nom} : JSON invalide ({erreur})') from erreur
    except ErreurConfiguration as erreur:
        raise ErreurConfiguration(f'{nom} : {erreur}') from erreur


def _empreinte_canonique(valeur: Any) -> str:
    texte = json.dumps(valeur, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(texte.encode('utf-8')).hexdigest()


def _geler(valeur: Any) -> Any:
    if isinstance(valeur, dict):
        return MappingProxyType({cle: _geler(v) for cle, v in valeur.items()})
    if isinstance(valeur, list):
        return tuple(_geler(v) for v in valeur)
    return valeur


# ---------------------------------------------------------------- validateurs de valeurs

def _est_nombre(valeur: Any) -> bool:
    return (not isinstance(valeur, bool) and isinstance(valeur, (int, float))
            and math.isfinite(valeur))


def _texte(cle, v):
    if not isinstance(v, str) or not v:
        raise ErreurConfiguration(f'{cle} : texte non vide attendu')
    return v


def _egal(attendu: str) -> Callable[[str, Any], Any]:
    def valider(cle, v):
        if v != attendu:
            raise ErreurConfiguration(f'{cle} : valeur non prise en charge {v!r} (seule {attendu!r} est admise)')
        return v
    return valider


def _choix(admis: frozenset[str]) -> Callable[[str, Any], Any]:
    def valider(cle, v):
        if v not in admis:
            raise ErreurConfiguration(f'{cle} : valeur {v!r} hors de {sorted(admis)}')
        return v
    return valider


def _date(cle, v):
    try:
        return date.fromisoformat(_texte(cle, v))
    except ValueError as erreur:
        raise ErreurConfiguration(f'{cle} : date ISO attendue') from erreur


def _devise(cle, v):
    if not isinstance(v, str) or not re.fullmatch(r'[A-Z]{3}', v):
        raise ErreurConfiguration(f'{cle} : code de devise à trois lettres attendu')
    return v


def _entier(minimum: int) -> Callable[[str, Any], Any]:
    def valider(cle, v):
        if isinstance(v, bool) or not isinstance(v, int) or v < minimum:
            raise ErreurConfiguration(f'{cle} : entier ≥ {minimum} attendu, reçu {v!r}')
        return v
    return valider


def _nombre(strict: bool) -> Callable[[str, Any], Any]:
    def valider(cle, v):
        if not _est_nombre(v) or (v <= 0 if strict else v < 0):
            raise ErreurConfiguration(f'{cle} : nombre {"> 0" if strict else "≥ 0"} attendu, reçu {v!r}')
        return v
    return valider


def _fraction(cle, v):
    if not _est_nombre(v) or not 0 < v <= 1:
        raise ErreurConfiguration(f'{cle} : fraction dans ]0, 1] attendue, reçu {v!r}')
    return v


def _heure(cle, v):
    if not isinstance(v, str) or not re.fullmatch(r'\d{2}:\d{2}:\d{2}', v):
        raise ErreurConfiguration(f'{cle} : heure HH:MM:SS attendue')
    try:
        return time.fromisoformat(v)
    except ValueError as erreur:
        raise ErreurConfiguration(f'{cle} : heure invalide {v!r}') from erreur


def _identifiants(cle, v):
    if (not isinstance(v, list) or not v or len(set(map(str, v))) != len(v)
            or not all(isinstance(x, str) and x for x in v)):
        raise ErreurConfiguration(f'{cle} : liste non vide d\'identifiants uniques attendue')
    return tuple(v)


def _jours(cle, v):
    if (not isinstance(v, list) or not v or len(set(v)) != len(v)
            or not all(not isinstance(x, bool) and isinstance(x, int) and 0 <= x <= 6 for x in v)):
        raise ErreurConfiguration(f'{cle} : jours de semaine uniques de 0 à 6 attendus')
    return tuple(v)


def _delais(cle, v):
    if not isinstance(v, list) or not v or not all(_est_nombre(x) and x >= 0 for x in v):
        raise ErreurConfiguration(f'{cle} : liste non vide de délais ≥ 0 attendue')
    return tuple(v)


def _plafonds(cle, v):
    if (not isinstance(v, dict) or not v
            or not all(isinstance(k, str) and k and _est_nombre(x) and x > 0 for k, x in v.items())):
        raise ErreurConfiguration(f'{cle} : plafonds strictement positifs par symbole attendus')
    return MappingProxyType(dict(v))


def _faux(cle, v):
    if v is not False:
        raise ErreurConfiguration(f'{cle} : option exclue par la spécification, doit valoir false')
    return v


_ENTIER_POSITIF, _ENTIER_NATUREL = _entier(1), _entier(0)
_POSITIF, _NATUREL = _nombre(True), _nombre(False)
_OPTIONS_EXCLUES = ('allow_pyramiding', 'allow_averaging_down', 'allow_martingale', 'allow_trailing_stop',
                    'allow_break_even_move', 'allow_partial_take_profit', 'mandatory_retest',
                    'new_indicator_vote_score', 'dxy_enabled', 'mfi_enabled', 'bollinger_enabled',
                    'fibonacci_enabled', 'daily_pivots_enabled', 'extra_roc_momentum_enabled',
                    'fresh_ma_cross_enabled')

VALIDATEURS_COMMUNS: Mapping[str, Callable[[str, Any], Any]] = MappingProxyType({
    'version': _texte, 'frozen_date': _date, 'default_mode': _choix(MODES), 'account_currency': _devise,
    'initial_equity_usd': _POSITIF, 'account_leverage': _ENTIER_POSITIF, 'universe_priority': _identifiants,
    'timeframe_seconds': _ENTIER_POSITIF, 'h1_seconds': _ENTIER_POSITIF, 'bar_price': _egal('BID'),
    'bar_alignment': _egal('UTC'), 'session_timezone': _texte, 'active_weekdays_local': _jours,
    'warmup_closed_m15_bars': _ENTIER_POSITIF, 'warmup_closed_h1_bars': _ENTIER_POSITIF,
    'atr_period': _ENTIER_POSITIF, 'atr_method': _egal('WILDER'),
    'atr_signal_reference': _egal('PREVIOUS_CLOSED_M15'), 'structural_buffer_atr': _NATUREL,
    'minimum_chart_stop_atr': _POSITIF, 'maximum_chart_stop_atr': _POSITIF,
    'maximum_signal_true_range_atr': _POSITIF, 'slippage_budget_atr_per_leg': _NATUREL,
    'max_entry_bid_gap_atr': _NATUREL, 'max_spread_price': _plafonds, 'risk_fraction_per_entry': _fraction,
    'account_max_initial_reserved_risk_fraction': _fraction, 'account_max_positions': _ENTIER_POSITIF,
    'max_positions_per_canonical_symbol': _ENTIER_POSITIF, 'max_margin_fraction_of_equity': _fraction,
    'daily_equity_loss_limit_fraction': _fraction, 'peak_equity_drawdown_halt_fraction': _fraction,
    'risk_day_timezone': _egal('UTC'), 'simultaneous_strategy_priority': _identifiants,
    'entry_signal_ttl_seconds': _POSITIF, 'quote_max_age_seconds': _POSITIF,
    'request_ack_timeout_seconds': _POSITIF, 'reconcile_fast_poll_seconds': _POSITIF,
    'reconcile_fast_window_seconds': _POSITIF, 'reconcile_slow_poll_seconds': _POSITIF,
    'protective_update_max_attempts': _ENTIER_POSITIF, 'protective_update_retry_delays_seconds': _delais,
    'protective_update_deadline_seconds': _POSITIF, 'exit_retry_interval_seconds': _POSITIF,
    'native_market_close_guard_seconds': _NATUREL, 'rollover_blackout_utc_start': _heure,
    'rollover_blackout_utc_end': _heure, 'news_before_seconds': _ENTIER_NATUREL,
    'news_after_seconds': _ENTIER_NATUREL, 'news_calendar_max_age_seconds': _ENTIER_POSITIF,
    'news_forward_coverage_seconds': _ENTIER_POSITIF, 'fundamental_mode': _egal('EXTERNAL_REQUIRED'),
    'fundamental_max_validity_seconds': _ENTIER_POSITIF, 'fundamental_expected_heartbeat_seconds': _ENTIER_POSITIF,
    'fundamental_timestamp_future_tolerance_seconds': _ENTIER_NATUREL,
    'max_position_wallclock_seconds': _ENTIER_POSITIF,
    **{cle: _faux for cle in _OPTIONS_EXCLUES},
    'trade_count_retention_target': _fraction, 'combined_mean_fills_per_trading_day_target': _POSITIF,
})


@dataclass(frozen=True)
class ParametresCommuns:
    """Bloc `common` de l'export technique, typé clé par clé (noms identiques aux clés)."""

    version: str
    frozen_date: date
    default_mode: str
    account_currency: str
    initial_equity_usd: int | float
    account_leverage: int
    universe_priority: tuple[str, ...]
    timeframe_seconds: int
    h1_seconds: int
    bar_price: str
    bar_alignment: str
    session_timezone: str
    active_weekdays_local: tuple[int, ...]
    warmup_closed_m15_bars: int
    warmup_closed_h1_bars: int
    atr_period: int
    atr_method: str
    atr_signal_reference: str
    structural_buffer_atr: int | float
    minimum_chart_stop_atr: int | float
    maximum_chart_stop_atr: int | float
    maximum_signal_true_range_atr: int | float
    slippage_budget_atr_per_leg: int | float
    max_entry_bid_gap_atr: int | float
    max_spread_price: Mapping[str, int | float]
    risk_fraction_per_entry: int | float
    account_max_initial_reserved_risk_fraction: int | float
    account_max_positions: int
    max_positions_per_canonical_symbol: int
    max_margin_fraction_of_equity: int | float
    daily_equity_loss_limit_fraction: int | float
    peak_equity_drawdown_halt_fraction: int | float
    risk_day_timezone: str
    simultaneous_strategy_priority: tuple[str, ...]
    entry_signal_ttl_seconds: int | float
    quote_max_age_seconds: int | float
    request_ack_timeout_seconds: int | float
    reconcile_fast_poll_seconds: int | float
    reconcile_fast_window_seconds: int | float
    reconcile_slow_poll_seconds: int | float
    protective_update_max_attempts: int
    protective_update_retry_delays_seconds: tuple[int | float, ...]
    protective_update_deadline_seconds: int | float
    exit_retry_interval_seconds: int | float
    native_market_close_guard_seconds: int | float
    rollover_blackout_utc_start: time
    rollover_blackout_utc_end: time
    news_before_seconds: int
    news_after_seconds: int
    news_calendar_max_age_seconds: int
    news_forward_coverage_seconds: int
    fundamental_mode: str
    fundamental_max_validity_seconds: int
    fundamental_expected_heartbeat_seconds: int
    fundamental_timestamp_future_tolerance_seconds: int
    max_position_wallclock_seconds: int
    allow_pyramiding: bool
    allow_averaging_down: bool
    allow_martingale: bool
    allow_trailing_stop: bool
    allow_break_even_move: bool
    allow_partial_take_profit: bool
    mandatory_retest: bool
    new_indicator_vote_score: bool
    dxy_enabled: bool
    mfi_enabled: bool
    bollinger_enabled: bool
    fibonacci_enabled: bool
    daily_pivots_enabled: bool
    extra_roc_momentum_enabled: bool
    fresh_ma_cross_enabled: bool
    trade_count_retention_target: int | float
    combined_mean_fills_per_trading_day_target: int | float


@dataclass(frozen=True)
class ExportTechnique:
    commun: ParametresCommuns
    london: Mapping[str, Any]
    ema: Mapping[str, Any]
    empreinte_octets: str
    empreinte_canonique: str


@dataclass(frozen=True)
class ExportIA:
    parametres: Mapping[str, Any]
    empreinte_octets: str
    empreinte_canonique: str


@dataclass(frozen=True)
class ConfigurationFigee:
    technique: ExportTechnique
    ia: ExportIA


# ---------------------------------------------------------------- analyse des exports

def _commun(bloc: Any) -> ParametresCommuns:
    if not isinstance(bloc, dict):
        raise ErreurConfiguration('common : objet attendu')
    attendues = set(VALIDATEURS_COMMUNS)
    inconnues, manquantes = sorted(set(bloc) - attendues), sorted(attendues - set(bloc))
    if inconnues:
        raise ErreurConfiguration(f'common : clés inconnues {inconnues}')
    if manquantes:
        raise ErreurConfiguration(f'common : clés manquantes {manquantes}')
    commun = ParametresCommuns(**{cle: VALIDATEURS_COMMUNS[cle](cle, bloc[cle]) for cle in VALIDATEURS_COMMUNS})
    if commun.h1_seconds % commun.timeframe_seconds:
        raise ErreurConfiguration('h1_seconds doit être un multiple de timeframe_seconds')
    if set(commun.max_spread_price) != set(commun.universe_priority):
        raise ErreurConfiguration('max_spread_price doit couvrir exactement universe_priority')
    if commun.maximum_chart_stop_atr < commun.minimum_chart_stop_atr:
        raise ErreurConfiguration('maximum_chart_stop_atr inférieur à minimum_chart_stop_atr')
    return commun


def _bloc_strategie(racine: dict, nom: str, commun: ParametresCommuns) -> Mapping[str, Any]:
    bloc = racine[nom]
    if not isinstance(bloc, dict):
        raise ErreurConfiguration(f'{nom} : objet attendu')
    identifiant = _texte(f'{nom}.strategy_id', bloc.get('strategy_id'))
    if identifiant not in commun.simultaneous_strategy_priority:
        raise ErreurConfiguration(f'{nom}.strategy_id absent de simultaneous_strategy_priority')
    return _geler(bloc)


def analyser_export_technique(octets: bytes) -> ExportTechnique:
    racine = _lire_json(octets, 'export technique')
    if not isinstance(racine, dict) or set(racine) != {'common', 'ema', 'london'}:
        raise ErreurConfiguration('export technique : racine {common, ema, london} attendue')
    commun = _commun(racine['common'])
    return ExportTechnique(commun, _bloc_strategie(racine, 'london', commun), _bloc_strategie(racine, 'ema', commun),
                           hashlib.sha256(octets).hexdigest(), _empreinte_canonique(racine))


def analyser_export_ia(octets: bytes) -> ExportIA:
    racine = _lire_json(octets, 'export IA')
    if not isinstance(racine, dict):
        raise ErreurConfiguration('export IA : objet attendu')
    for cle in ('integration_version', 'document_version'):
        _texte(cle, racine.get(cle))
    for cle in ('local_inference_allowed', 'synchronous_llm_on_entry_allowed'):
        if racine.get(cle) is not False:
            raise ErreurConfiguration(f'{cle} : doit valoir false (A03)')
    return ExportIA(_geler(racine), hashlib.sha256(octets).hexdigest(), _empreinte_canonique(racine))


def charger_configuration_figee(octets_technique: bytes, octets_ia: bytes, octets_preuve: bytes) -> ConfigurationFigee:
    preuve = _lire_json(octets_preuve, 'preuve de conservation')
    if not isinstance(preuve, dict) or preuve.get('schema') != SCHEMA_PREUVE:
        raise ErreurConfiguration(f'preuve de conservation : schéma {SCHEMA_PREUVE} attendu')
    technique, ia = analyser_export_technique(octets_technique), analyser_export_ia(octets_ia)
    for nom, export, cle in (('technique', technique, 'frozen_technical_file_sha256'),
                             ('IA', ia, 'frozen_ai_file_sha256')):
        if export.empreinte_octets != preuve.get(cle):
            raise ErreurConfiguration(f'export {nom} : empreinte différente de la preuve de conservation ({cle})')
    return ConfigurationFigee(technique, ia)


CLES_COMMUNES = tuple(champ.name for champ in fields(ParametresCommuns))
if CLES_COMMUNES != tuple(VALIDATEURS_COMMUNS):
    raise RuntimeError('ParametresCommuns et VALIDATEURS_COMMUNS divergent')

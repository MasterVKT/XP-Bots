"""Couche 0 de `donnees-temps` : paramètres techniques du bloc `common` et séances natives des symboles.

Contrat : `mcl/donnees-temps/contrats/couche-0.md`. Sources : C02, C03 points 2, 3 et 5, C04.
"""
from __future__ import annotations

import bisect
import calendar
import math
import re
from dataclasses import dataclass
from datetime import date, time
from typing import Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from xpbots.noyau.config import BundleTechnique, ConfigurationInvalide, figer


class FonctionNonImplementee(ConfigurationInvalide):
    """La configuration demande une variante que le code n'implémente pas : le robot refuse de démarrer."""


class CalendrierInconnu(LookupError):
    """Question sur une période que le calendrier de séances ne couvre pas."""


# Variantes implémentées par cet artefact ; toute autre valeur de config/ est refusée au démarrage.
VARIANTES_IMPLEMENTEES = {
    'bar_price': 'BID',
    'bar_alignment': 'UTC',
    'atr_method': 'WILDER',
    'atr_signal_reference': 'PREVIOUS_CLOSED_M15',
}

_HEURE = re.compile(r'(\d{2}):(\d{2}):(\d{2})')
_DATE = re.compile(r'\d{4}-\d{2}-\d{2}')


def analyser_heure(texte: str) -> time:
    """Heure `HH:MM:SS` stricte."""
    trouve = _HEURE.fullmatch(texte) if type(texte) is str else None
    if trouve is None:
        raise ConfigurationInvalide(f'heure HH:MM:SS attendue, reçu {texte!r}')
    try:
        return time(*(int(partie) for partie in trouve.groups()))
    except ValueError as erreur:
        raise ConfigurationInvalide(f'heure invalide : {texte!r}') from erreur


def _texte(v):
    return type(v) is str and bool(v.strip())


def _date(v):
    if type(v) is not str or not _DATE.fullmatch(v):
        return False
    try:
        date.fromisoformat(v)
        return True
    except ValueError:
        return False


def _heure(v):
    try:
        analyser_heure(v)
        return True
    except ConfigurationInvalide:
        return False


def _fuseau(v):
    if not _texte(v):
        return False
    try:
        ZoneInfo(v)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def _nombre_fini(v):
    return type(v) in (int, float) and math.isfinite(v)


def _liste(v):
    return isinstance(v, (list, tuple))


GENRES = {
    'texte': _texte,
    'date': _date,
    'heure': _heure,
    'fuseau': _fuseau,
    'booleen': lambda v: type(v) is bool,
    'entier_positif': lambda v: type(v) is int and v > 0,
    'entier_positif_ou_nul': lambda v: type(v) is int and v >= 0,
    'nombre_positif': lambda v: _nombre_fini(v) and v > 0,
    'liste_textes': lambda v: _liste(v) and len(v) > 0 and all(_texte(x) for x in v) and len(set(v)) == len(v),
    'liste_jours': lambda v: _liste(v) and len(v) > 0
    and all(type(x) is int and calendar.MONDAY <= x <= calendar.SUNDAY for x in v)
    and len(set(v)) == len(v),
    'liste_nombres_positifs': lambda v: _liste(v) and len(v) > 0 and all(_nombre_fini(x) and x > 0 for x in v),
    'dict_nombres_positifs': lambda v: isinstance(v, Mapping) and len(v) > 0
    and all(_texte(k) and _nombre_fini(x) and x > 0 for k, x in v.items()),
}


def _schema():
    groupes = {
        'texte': ('version', 'default_mode', 'account_currency', 'bar_price', 'bar_alignment', 'atr_method',
                  'atr_signal_reference', 'risk_day_timezone', 'fundamental_mode'),
        'date': ('frozen_date',),
        'fuseau': ('session_timezone',),
        'heure': ('rollover_blackout_utc_start', 'rollover_blackout_utc_end'),
        'entier_positif': (
            'timeframe_seconds', 'h1_seconds', 'warmup_closed_m15_bars', 'warmup_closed_h1_bars', 'atr_period',
            'account_max_positions', 'max_positions_per_canonical_symbol', 'entry_signal_ttl_seconds',
            'quote_max_age_seconds', 'request_ack_timeout_seconds', 'reconcile_fast_poll_seconds',
            'reconcile_fast_window_seconds', 'reconcile_slow_poll_seconds', 'protective_update_max_attempts',
            'protective_update_deadline_seconds', 'exit_retry_interval_seconds', 'native_market_close_guard_seconds',
            'news_before_seconds', 'news_after_seconds', 'news_calendar_max_age_seconds',
            'news_forward_coverage_seconds', 'fundamental_max_validity_seconds',
            'fundamental_expected_heartbeat_seconds', 'max_position_wallclock_seconds'),
        'entier_positif_ou_nul': ('fundamental_timestamp_future_tolerance_seconds',),
        'nombre_positif': (
            'initial_equity_usd', 'account_leverage', 'structural_buffer_atr', 'minimum_chart_stop_atr',
            'maximum_chart_stop_atr', 'maximum_signal_true_range_atr', 'slippage_budget_atr_per_leg',
            'max_entry_bid_gap_atr', 'risk_fraction_per_entry', 'account_max_initial_reserved_risk_fraction',
            'max_margin_fraction_of_equity', 'daily_equity_loss_limit_fraction', 'peak_equity_drawdown_halt_fraction',
            'trade_count_retention_target', 'combined_mean_fills_per_trading_day_target'),
        'liste_textes': ('universe_priority', 'simultaneous_strategy_priority'),
        'liste_jours': ('active_weekdays_local',),
        'liste_nombres_positifs': ('protective_update_retry_delays_seconds',),
        'dict_nombres_positifs': ('max_spread_price',),
        'booleen': (
            'allow_pyramiding', 'allow_averaging_down', 'allow_martingale', 'allow_trailing_stop',
            'allow_break_even_move', 'allow_partial_take_profit', 'mandatory_retest', 'new_indicator_vote_score',
            'dxy_enabled', 'mfi_enabled', 'bollinger_enabled', 'fibonacci_enabled', 'daily_pivots_enabled',
            'extra_roc_momentum_enabled', 'fresh_ma_cross_enabled'),
    }
    return {cle: genre for genre, cles in groupes.items() for cle in cles}


SCHEMA_COMMON = _schema()


def valider_bloc_common(bloc: Mapping) -> list[str]:
    """Violations du schéma du bloc `common` (vide si conforme)."""
    if not isinstance(bloc, Mapping):
        return ['le bloc common doit être un objet']
    erreurs = []
    manquantes, en_trop = sorted(set(SCHEMA_COMMON) - set(bloc)), sorted(set(bloc) - set(SCHEMA_COMMON))
    if manquantes or en_trop:
        erreurs.append(f'clés manquantes {manquantes}, clés en trop {en_trop}')
    for cle, genre in SCHEMA_COMMON.items():
        if cle in bloc and not GENRES[genre](bloc[cle]):
            erreurs.append(f'{cle} : {genre} attendu, reçu {bloc[cle]!r}')
    return erreurs


class ParametresTechniques:
    """Bloc `common` validé, en lecture seule."""

    def __init__(self, bloc: Mapping, empreinte: str):
        erreurs = valider_bloc_common(bloc)
        if erreurs:
            raise ConfigurationInvalide('bloc common : ' + ' ; '.join(erreurs))
        for cle, attendue in VARIANTES_IMPLEMENTEES.items():
            if bloc[cle] != attendue:
                raise FonctionNonImplementee(f'{cle} = {bloc[cle]!r} : seule la variante {attendue!r} est implémentée')
        self._bloc = figer(bloc)
        self.empreinte = empreinte
        self._blackout = (analyser_heure(bloc['rollover_blackout_utc_start']),
                          analyser_heure(bloc['rollover_blackout_utc_end']))

    def valeur(self, cle: str):
        try:
            return self._bloc[cle]
        except KeyError as erreur:
            raise ConfigurationInvalide(f'clé absente du bloc common : {cle}') from erreur

    @property
    def periode_m15_s(self) -> int:
        return self._bloc['timeframe_seconds']

    @property
    def periode_h1_s(self) -> int:
        return self._bloc['h1_seconds']

    @property
    def prechauffage_m15(self) -> int:
        return self._bloc['warmup_closed_m15_bars']

    @property
    def prechauffage_h1(self) -> int:
        return self._bloc['warmup_closed_h1_bars']

    @property
    def periode_atr(self) -> int:
        return self._bloc['atr_period']

    @property
    def fuseau_sessions(self) -> str:
        return self._bloc['session_timezone']

    @property
    def jours_actifs(self) -> frozenset[int]:
        return frozenset(self._bloc['active_weekdays_local'])

    @property
    def blackout_debut(self) -> time:
        return self._blackout[0]

    @property
    def blackout_fin(self) -> time:
        return self._blackout[1]

    @property
    def univers(self) -> tuple[str, ...]:
        return tuple(self._bloc['universe_priority'])


def charger_parametres_techniques(bundle: BundleTechnique) -> ParametresTechniques:
    return ParametresTechniques(bundle.donnees['common'], bundle.empreinte)


def _entier(valeur, nom):
    if type(valeur) is not int:
        raise ValueError(f'{nom} doit être un entier')


@dataclass(frozen=True)
class CalendrierSeances:
    """Séances de cotation natives d'un symbole, intervalles UTC [début, fin) en ms, sur une période connue."""

    symbole: str
    ouvertures: tuple[tuple[int, int], ...]
    connu_de_ms: int
    connu_jusqua_ms: int

    def __post_init__(self):
        if type(self.symbole) is not str or not self.symbole:
            raise ValueError('symbole invalide')
        _entier(self.connu_de_ms, 'connu_de_ms')
        _entier(self.connu_jusqua_ms, 'connu_jusqua_ms')
        if not self.connu_de_ms < self.connu_jusqua_ms:
            raise ValueError('période connue vide')
        ouvertures = tuple((a, b) for a, b in self.ouvertures)
        precedente = self.connu_de_ms
        for a, b in ouvertures:
            _entier(a, 'début de séance')
            _entier(b, 'fin de séance')
            if not precedente <= a < b <= self.connu_jusqua_ms:
                raise ValueError(f'séances de {self.symbole} non triées, chevauchantes ou hors période connue')
            precedente = b
        object.__setattr__(self, 'ouvertures', ouvertures)
        object.__setattr__(self, '_debuts', tuple(a for a, _ in ouvertures))

    def _verifier_connu(self, debut, fin):
        if not self.connu_de_ms <= debut <= fin <= self.connu_jusqua_ms:
            raise CalendrierInconnu(f'séances de {self.symbole} inconnues sur [{debut}, {fin})')

    def en_seance(self, instant_ms: int) -> bool:
        if not self.connu_de_ms <= instant_ms < self.connu_jusqua_ms:
            raise CalendrierInconnu(f'séances de {self.symbole} inconnues à {instant_ms}')
        rang = bisect.bisect_right(self._debuts, instant_ms) - 1
        return rang >= 0 and instant_ms < self.ouvertures[rang][1]

    def portion_ouverte(self, debut_ms: int, fin_ms: int) -> tuple[tuple[int, int], ...]:
        """Intersection de [début, fin) avec les séances."""
        self._verifier_connu(debut_ms, fin_ms)
        rang = max(0, bisect.bisect_right(self._debuts, debut_ms) - 1)
        portions = []
        for a, b in self.ouvertures[rang:]:
            if a >= fin_ms:
                break
            if b > debut_ms:
                portions.append((max(a, debut_ms), min(b, fin_ms)))
        return tuple(portions)

    def prochaine_fermeture(self, instant_ms: int) -> int | None:
        """Fin de la séance en cours ; None si le marché est fermé à cet instant."""
        if not self.en_seance(instant_ms):
            return None
        return self.ouvertures[bisect.bisect_right(self._debuts, instant_ms) - 1][1]

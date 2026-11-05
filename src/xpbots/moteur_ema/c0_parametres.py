"""Couche 0 de `moteur-ema` : bloc `ema` de la configuration figée et seuils du bloc `common` utilisés par S01.

Contrat : `mcl/moteur-ema/contrats/couche-0.md`. Sources : C02, S01.1 à S01.4, C03 points 8 et 9, R18.
Aucune valeur normative n'est recopiée : toutes viennent de `config/parametres_figes_v3.json`.
"""
from __future__ import annotations

from datetime import time
from typing import Mapping

from xpbots.donnees_temps.c0_parametres_seances import GENRES, FonctionNonImplementee, analyser_heure
from xpbots.noyau.config import BundleTechnique, ConfigurationInvalide, figer

# Variantes implémentées ; toute autre valeur de config/ est refusée au démarrage (le robot ne démarre pas).
VARIANTES_IMPLEMENTEES = {
    'ema_seed': 'SMA_N',
    'rsi_method': 'WILDER',
    'pullback_touch_zone': 'EMA15_TO_EMA50',
    'require_directional_body': True,
    'require_signal_touch': False,
    'h1_directional_filter_enabled': False,
}

_GENRES = dict(GENRES, liste_periodes=lambda v: isinstance(v, (list, tuple)) and len(v) > 0
               and all(type(x) is int and x > 0 for x in v))

SCHEMA_EMA = {cle: genre for genre, cles in {
    'texte': ('strategy_id', 'ema_seed', 'rsi_method', 'pullback_touch_zone'),
    'liste_periodes': ('ema_periods',),
    'entier_positif': ('rsi_period', 'slow_ema_slope_lookback_bars', 'pullback_max_inclusive_bars',
                       'cooldown_closed_bars_after_signal_or_owned_exit', 'max_filled_entries_per_symbol_local_day'),
    'nombre_positif': ('long_pullback_rsi_min', 'short_pullback_rsi_max', 'long_signal_rsi_min', 'short_signal_rsi_max',
                       'maximum_close_beyond_ema50_atr', 'signal_close_location_min', 'take_profit_gross_price_r'),
    'heure': ('session_start_local', 'entry_end_local_exclusive', 'force_exit_local'),
    'booleen': ('require_directional_body', 'require_signal_touch', 'h1_directional_filter_enabled'),
}.items() for cle in cles}

# Seuils du bloc `common` lus par la méthode (S01.3, S01.4, C06).
CLES_COMMON = ('structural_buffer_atr', 'minimum_chart_stop_atr', 'maximum_chart_stop_atr',
               'maximum_signal_true_range_atr')


def valider_bloc_ema(bloc: Mapping) -> list[str]:
    """Violations du schéma du bloc `ema` (vide si conforme)."""
    if not isinstance(bloc, Mapping):
        return ['le bloc ema doit être un objet']
    erreurs = []
    manquantes, en_trop = sorted(set(SCHEMA_EMA) - set(bloc)), sorted(set(bloc) - set(SCHEMA_EMA))
    if manquantes or en_trop:
        erreurs.append(f'clés manquantes {manquantes}, clés en trop {en_trop}')
    for cle, genre in SCHEMA_EMA.items():
        if cle in bloc and not _GENRES[genre](bloc[cle]):
            erreurs.append(f'{cle} : {genre} attendu, reçu {bloc[cle]!r}')
    return erreurs


class ParametresEMA:
    """Bloc `ema` validé et seuils `common` de S01, en lecture seule ; une clé absente est une erreur."""

    def __init__(self, bloc: Mapping, common: Mapping, empreinte: str):
        erreurs = valider_bloc_ema(bloc)
        if erreurs:
            raise ConfigurationInvalide('bloc ema : ' + ' ; '.join(erreurs))
        for cle, attendue in VARIANTES_IMPLEMENTEES.items():
            if bloc[cle] != attendue or type(bloc[cle]) is not type(attendue):
                raise FonctionNonImplementee(f'{cle} = {bloc[cle]!r} : seule la variante {attendue!r} est implémentée')
        try:
            rapide, moyenne, lente = bloc['ema_periods']
        except ValueError as erreur:
            raise ConfigurationInvalide('ema_periods : trois périodes attendues (rapide, moyenne, lente)') from erreur
        if not rapide < moyenne < lente:
            raise ConfigurationInvalide('ema_periods : périodes strictement croissantes attendues')
        if not 0 < bloc['signal_close_location_min'] <= 1:
            raise ConfigurationInvalide('signal_close_location_min : fraction du range dans ]0, 1] attendue')
        seuils = {}
        for cle in CLES_COMMON:
            valeur = common.get(cle) if isinstance(common, Mapping) else None
            if not GENRES['nombre_positif'](valeur):
                raise ConfigurationInvalide(f'common.{cle} : nombre positif attendu, reçu {valeur!r}')
            seuils[cle] = valeur
        self._bloc = figer(dict(bloc))
        self._seuils = figer(seuils)
        self._heures = tuple(analyser_heure(bloc[cle]) for cle in
                             ('session_start_local', 'entry_end_local_exclusive', 'force_exit_local'))
        if not self._heures[0] < self._heures[1]:
            raise ConfigurationInvalide('fenêtre d\'entrée vide : session_start_local >= entry_end_local_exclusive')
        self.periodes_ema = (rapide, moyenne, lente)
        self.empreinte = empreinte

    def valeur(self, cle: str):
        try:
            return self._bloc[cle]
        except KeyError as erreur:
            raise ConfigurationInvalide(f'clé absente du bloc ema : {cle}') from erreur

    strategie_id = property(lambda self: self._bloc['strategy_id'])
    periode_rsi = property(lambda self: self._bloc['rsi_period'])
    decalage_pente = property(lambda self: self._bloc['slow_ema_slope_lookback_bars'])
    rsi_repli_long_min = property(lambda self: self._bloc['long_pullback_rsi_min'])
    rsi_repli_court_max = property(lambda self: self._bloc['short_pullback_rsi_max'])
    # R18 : le seuil RSI d'armement de S01.2 point 4 est celui du signal de S01.3 (même valeur, aucune clé dédiée).
    rsi_signal_long_min = property(lambda self: self._bloc['long_signal_rsi_min'])
    rsi_signal_court_max = property(lambda self: self._bloc['short_signal_rsi_max'])
    depassement_ema_lente_atr = property(lambda self: self._bloc['maximum_close_beyond_ema50_atr'])
    age_max_repli = property(lambda self: self._bloc['pullback_max_inclusive_bars'])
    position_cloture_min = property(lambda self: self._bloc['signal_close_location_min'])
    clotures_cooldown = property(lambda self: self._bloc['cooldown_closed_bars_after_signal_or_owned_exit'])
    entrees_max_jour = property(lambda self: self._bloc['max_filled_entries_per_symbol_local_day'])
    debut_session = property(lambda self: self._bloc['session_start_local'])
    fin_entrees_exclue = property(lambda self: self._bloc['entry_end_local_exclusive'])
    sortie_forcee = property(lambda self: self._bloc['force_exit_local'])
    multiple_objectif = property(lambda self: float(self._bloc['take_profit_gross_price_r']))
    tampon_structurel_atr = property(lambda self: self._seuils['structural_buffer_atr'])
    stop_min_atr = property(lambda self: self._seuils['minimum_chart_stop_atr'])
    stop_max_atr = property(lambda self: self._seuils['maximum_chart_stop_atr'])
    tr_max_atr = property(lambda self: self._seuils['maximum_signal_true_range_atr'])

    @property
    def heures(self) -> tuple[time, time, time]:
        """Début de session, fin exclue des entrées, sortie forcée (heures locales de Londres)."""
        return self._heures


def charger_parametres_ema(bundle: BundleTechnique) -> ParametresEMA:
    """Paramètres S01 du bundle technique figé ; refus de démarrer sur une variante non implémentée."""
    try:
        bloc, common = bundle.donnees['ema'], bundle.donnees['common']
    except KeyError as erreur:
        raise ConfigurationInvalide(f'bloc absent du bundle technique : {erreur}') from erreur
    return ParametresEMA(bloc, common, bundle.empreinte)

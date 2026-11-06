"""Implémentation de la couche 0a (parametres_london).

Révisable à comportement constant sous harnais complet.
"""
from dataclasses import dataclass, fields
from datetime import time
import math

from xpbots.noyau.c0c_configuration import ExportTechnique, ParametresCommuns


class ErreurParametresLondon(ValueError):
    """Bloc London incomplet, non pris en charge ou incohérent."""


def _secondes(heure: time) -> int:
    return heure.hour * 3600 + heure.minute * 60 + heure.second


@dataclass(frozen=True)
class ParametresLondon:
    commun: ParametresCommuns
    strategy_id: str
    range_start_local: time
    range_end_local_exclusive: time
    expected_range_m15_bars: int
    range_h1_atr_frozen_local: time
    range_min_h1_atr: float
    range_max_h1_atr: float
    session_start_local: time
    entry_end_local_exclusive: time
    force_exit_local: time
    breakout_buffer_atr: float
    boundary_stop_inside_atr: float
    signal_body_fraction_min: float
    signal_close_location_min: float
    fresh_close_cross_required: bool
    max_filled_entries_per_symbol_local_day: int
    max_filled_entries_per_direction_local_day: int
    take_profit_gross_price_r: float
    h1_directional_filter_enabled: bool
    exit_on_close_back_inside_range_enabled: bool

    def __post_init__(self) -> None:
        if not isinstance(self.commun, ParametresCommuns):
            raise ErreurParametresLondon('paramètres communs typés attendus')
        if not isinstance(self.strategy_id, str) or self.strategy_id not in self.commun.simultaneous_strategy_priority:
            raise ErreurParametresLondon('strategy_id absent des priorités communes')
        for nom in _HEURES:
            heure = getattr(self, nom)
            if not isinstance(heure, time) or heure.tzinfo is not None or heure.microsecond:
                raise ErreurParametresLondon(f'{nom} : heure locale entière sans fuseau attendue')
        for nom in _ENTIERS:
            valeur = getattr(self, nom)
            if type(valeur) is not int or valeur <= 0:
                raise ErreurParametresLondon(f'{nom} : entier strictement positif attendu')
        for nom in _NOMBRES:
            valeur = getattr(self, nom)
            if type(valeur) not in (int, float):
                raise ErreurParametresLondon(f'{nom} : nombre fini attendu')
            try:
                fini = math.isfinite(valeur)
            except OverflowError:
                fini = False
            if not fini or valeur < 0 or (nom not in _BUFFERS and valeur == 0):
                raise ErreurParametresLondon(f'{nom} : nombre hors bornes')
            if nom in _FRACTIONS and valeur > 1:
                raise ErreurParametresLondon(f'{nom} : fraction supérieure à un')
            object.__setattr__(self, nom, float(valeur))
        for nom in _OPTIONS:
            if getattr(self, nom) is not False:
                raise ErreurParametresLondon(f'{nom} : option non prise en charge')
        debut, fin = _secondes(self.range_start_local), _secondes(self.range_end_local_exclusive)
        gel = _secondes(self.range_h1_atr_frozen_local)
        session, entree, sortie = (_secondes(getattr(self, nom)) for nom in
                                    ('session_start_local', 'entry_end_local_exclusive', 'force_exit_local'))
        duree = self.commun.timeframe_seconds
        if (not debut < fin <= gel <= session < entree <= sortie
                or (fin - debut) != self.expected_range_m15_bars * duree
                or debut % duree or fin % duree or gel % self.commun.h1_seconds):
            raise ErreurParametresLondon('horaires, alignement ou nombre de bougies du range incohérents')
        if self.range_min_h1_atr > self.range_max_h1_atr:
            raise ErreurParametresLondon('bornes de largeur inversées')
        if self.max_filled_entries_per_direction_local_day > self.max_filled_entries_per_symbol_local_day:
            raise ErreurParametresLondon('quota du sens supérieur au quota total')


_HEURES = ('range_start_local', 'range_end_local_exclusive', 'range_h1_atr_frozen_local',
           'session_start_local', 'entry_end_local_exclusive', 'force_exit_local')
_ENTIERS = ('expected_range_m15_bars', 'max_filled_entries_per_symbol_local_day',
            'max_filled_entries_per_direction_local_day')
_BUFFERS = ('breakout_buffer_atr', 'boundary_stop_inside_atr')
_FRACTIONS = ('signal_body_fraction_min', 'signal_close_location_min')
_NOMBRES = ('range_min_h1_atr', 'range_max_h1_atr', *_BUFFERS, *_FRACTIONS, 'take_profit_gross_price_r')
_OPTIONS = ('fresh_close_cross_required', 'h1_directional_filter_enabled', 'exit_on_close_back_inside_range_enabled')
CLES_LONDON = tuple(champ.name for champ in fields(ParametresLondon) if champ.name != 'commun')


def charger_parametres_london(technique: ExportTechnique) -> ParametresLondon:
    if not isinstance(technique, ExportTechnique):
        raise ErreurParametresLondon('ExportTechnique attendu')
    valeurs = dict(technique.london)
    if set(valeurs) != set(CLES_LONDON):
        raise ErreurParametresLondon('clés London manquantes ou inconnues')
    for nom in _HEURES:
        valeur = valeurs[nom]
        if not isinstance(valeur, str):
            raise ErreurParametresLondon(f'{nom} : texte HH:MM:SS attendu')
        try:
            heure = time.fromisoformat(valeur)
        except ValueError as erreur:
            raise ErreurParametresLondon(f'{nom} : heure illisible') from erreur
        if heure.isoformat() != valeur:
            raise ErreurParametresLondon(f'{nom} : format HH:MM:SS attendu')
        valeurs[nom] = heure
    return ParametresLondon(commun=technique.commun, **valeurs)

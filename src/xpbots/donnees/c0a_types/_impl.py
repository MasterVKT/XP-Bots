"""Implémentation de la couche 0a (types_donnees). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
import math
import re

from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1a_marche import Bougie

_EMPREINTE = re.compile(r'[0-9a-f]{64}')


class ErreurDonneesTemps(ValueError):
    """Donnée, état ou paramètre du flux de données refusé."""


class UniteTemps(StrEnum):
    M15 = 'M15'
    H1 = 'H1'

    def duree_ms(self, commun: ParametresCommuns) -> int:
        secondes = commun.timeframe_seconds if self is UniteTemps.M15 else commun.h1_seconds
        return secondes * 1000


class StatutCouverture(StrEnum):
    COUVERT = 'COUVERT'
    FERMETURE_OFFICIELLE = 'FERMETURE_OFFICIELLE'
    TROU = 'TROU'
    INCONNU = 'INCONNU'


class NatureTrou(StrEnum):
    DEBUT = 'DEBUT'
    FIN = 'FIN'


def _texte(valeur, nom):
    if not isinstance(valeur, str) or not valeur:
        raise ErreurDonneesTemps(f'{nom} : texte non vide attendu')


def _entier(valeur, nom):
    if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 0:
        raise ErreurDonneesTemps(f'{nom} : entier ≥ 0 attendu')


def _flottant(valeur, nom, optionnel=False):
    if optionnel and valeur is None:
        return None
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur) or valeur < 0:
        raise ErreurDonneesTemps(f'{nom} : nombre fini ≥ 0 attendu')
    return float(valeur)


@dataclass(frozen=True)
class ChangementTrou:
    symbole: str
    nature: NatureTrou
    intervalle_ms: int
    instant_ms: int

    def __post_init__(self) -> None:
        _texte(self.symbole, 'symbole')
        try:
            object.__setattr__(self, 'nature', NatureTrou(self.nature))
        except ValueError as erreur:
            raise ErreurDonneesTemps(f'nature de trou inconnue : {self.nature!r}') from erreur
        _entier(self.intervalle_ms, 'intervalle_ms')
        _entier(self.instant_ms, 'instant_ms')


@dataclass(frozen=True)
class AnomalieDonnees:
    symbole: str
    raison: str
    instant_ms: int

    def __post_init__(self) -> None:
        _texte(self.symbole, 'symbole')
        _texte(self.raison, 'raison')
        _entier(self.instant_ms, 'instant_ms')


@dataclass(frozen=True)
class IndicateursBougie:
    tr: float
    atr: float | None
    a: float | None
    rang: int

    def __post_init__(self) -> None:
        object.__setattr__(self, 'tr', _flottant(self.tr, 'tr'))
        object.__setattr__(self, 'atr', _flottant(self.atr, 'atr', optionnel=True))
        object.__setattr__(self, 'a', _flottant(self.a, 'a', optionnel=True))
        _entier(self.rang, 'rang')


@dataclass(frozen=True)
class IdentitePrechargement:
    premiere_ms: int | None
    nombre: int
    empreinte: str

    def __post_init__(self) -> None:
        _entier(self.nombre, 'nombre')
        if self.premiere_ms is None:
            if self.nombre:
                raise ErreurDonneesTemps('un préchargement non vide a une première bougie')
        else:
            _entier(self.premiere_ms, 'premiere_ms')
            if not self.nombre:
                raise ErreurDonneesTemps('un préchargement vide n\'a pas de première bougie')
        if not isinstance(self.empreinte, str) or not _EMPREINTE.fullmatch(self.empreinte):
            raise ErreurDonneesTemps('empreinte SHA-256 hexadécimale attendue')


@dataclass(frozen=True)
class BougieEnrichie:
    bougie: Bougie
    unite: UniteTemps
    indicateurs: IndicateursBougie | None
    jour_londres: date
    ouverture_locale: datetime
    cloture_locale: datetime
    jour_utc: date

    def __post_init__(self) -> None:
        if not isinstance(self.bougie, Bougie):
            raise ErreurDonneesTemps('bougie du noyau attendue')
        try:
            object.__setattr__(self, 'unite', UniteTemps(self.unite))
        except ValueError as erreur:
            raise ErreurDonneesTemps(f'unité de temps inconnue : {self.unite!r}') from erreur
        if self.bougie.valide != isinstance(self.indicateurs, IndicateursBougie):
            raise ErreurDonneesTemps('indicateurs présents si et seulement si la bougie est valide')
        for nom in ('ouverture_locale', 'cloture_locale'):
            valeur = getattr(self, nom)
            if not isinstance(valeur, datetime) or valeur.tzinfo is None:
                raise ErreurDonneesTemps(f'{nom} : datetime conscient attendu')
        for nom in ('jour_londres', 'jour_utc'):
            valeur = getattr(self, nom)
            if not isinstance(valeur, date) or isinstance(valeur, datetime):
                raise ErreurDonneesTemps(f'{nom} : date attendue')

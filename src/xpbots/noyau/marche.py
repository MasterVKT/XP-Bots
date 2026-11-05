"""Ticks Bid/Ask, bougies Bid et bougies enrichies (C03 points 2, 4, 5 et 11)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from xpbots.noyau.temps import MS_PAR_SECONDE, Instant


class DonneeMarcheInvalide(ValueError):
    """Tick, bougie ou bougie enrichie qui viole un invariant de couture."""


def _symbole(valeur, nom):
    if type(valeur) is not str or not valeur or valeur != valeur.strip():
        raise DonneeMarcheInvalide(f'{nom} doit être un texte non vide sans espace de bord, reçu {valeur!r}')


def _prix(valeur, nom):
    # Les prix restent décimaux exacts : un flottant serait une conversion implicite interdite.
    if type(valeur) is not Decimal or not valeur.is_finite() or valeur <= 0:
        raise DonneeMarcheInvalide(f'{nom} doit être un Decimal fini strictement positif, reçu {valeur!r}')


def _entier(valeur, nom):
    if type(valeur) is not int:
        raise DonneeMarcheInvalide(f'{nom} doit être un entier, reçu {type(valeur).__name__}')


@dataclass(frozen=True)
class Tick:
    """Cotation Bid/Ask horodatée d'un symbole ; le croisement Bid/Ask est jugé par la garde de cotation (C06)."""

    symbole: str
    symbole_courtier: str
    instant: Instant
    bid: Decimal
    ask: Decimal

    def __post_init__(self):
        _symbole(self.symbole, 'symbole')
        _symbole(self.symbole_courtier, 'symbole_courtier')
        if type(self.instant) is not Instant:
            raise DonneeMarcheInvalide('instant doit être un Instant')
        _prix(self.bid, 'bid')
        _prix(self.ask, 'ask')


@dataclass(frozen=True)
class Bougie:
    """Bougie Bid de l'intervalle [ouverture, ouverture + période) aligné sur l'époque UTC, au moins un tick."""

    symbole: str
    periode_s: int
    ouverture_ms: int
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741 (notation OHLC de la spécification)
    c: Decimal
    nb_ticks: int
    valide: bool

    def __post_init__(self):
        _symbole(self.symbole, 'symbole')
        _entier(self.periode_s, 'periode_s')
        _entier(self.ouverture_ms, 'ouverture_ms')
        _entier(self.nb_ticks, 'nb_ticks')
        if self.periode_s <= 0:
            raise DonneeMarcheInvalide('la période doit être strictement positive')
        if self.ouverture_ms % (self.periode_s * MS_PAR_SECONDE):
            raise DonneeMarcheInvalide('ouverture non alignée sur l\'époque UTC')
        for nom in ('o', 'h', 'l', 'c'):
            _prix(getattr(self, nom), nom)
        if not self.l <= min(self.o, self.c) <= max(self.o, self.c) <= self.h:
            raise DonneeMarcheInvalide('OHLC incohérent : il faut L <= O, C <= H')
        if self.nb_ticks < 1:
            raise DonneeMarcheInvalide('une bougie contient au moins un tick')
        if type(self.valide) is not bool:
            raise DonneeMarcheInvalide('valide doit être un booléen')

    @property
    def cloture_ms(self) -> int:
        return self.ouverture_ms + self.periode_s * MS_PAR_SECONDE


class StatutBougie(StrEnum):
    """Statut d'une bougie clôturée pour les méthodes."""

    OK = 'OK'
    WARMUP = 'WARMUP'
    DATA_GAP = 'DATA_GAP'


@dataclass(frozen=True)
class BougieEnrichie:
    """Bougie clôturée, ses indicateurs disponibles, `A_t` (ATR de t−1), son jour Londres et son statut.

    Les clés d'indicateurs sont fixées par l'artefact `donnees-temps` ; le squelette n'en fournit aucune.
    """

    bougie: Bougie
    statut: StatutBougie
    indicateurs: Mapping[str, float] = field(default_factory=dict)
    a_t: float | None = None
    jour_londres: date | None = None

    def __post_init__(self):
        if type(self.bougie) is not Bougie:
            raise DonneeMarcheInvalide('bougie doit être une Bougie')
        if not isinstance(self.statut, StatutBougie):
            raise DonneeMarcheInvalide('statut doit être un StatutBougie')
        if not self.bougie.valide and self.statut is not StatutBougie.DATA_GAP:
            raise DonneeMarcheInvalide('une bougie invalide a obligatoirement le statut DATA_GAP')
        if not isinstance(self.indicateurs, Mapping):
            raise DonneeMarcheInvalide('indicateurs doit être un dictionnaire')
        for cle, valeur in self.indicateurs.items():
            if type(cle) is not str or type(valeur) is not float or not math.isfinite(valeur):
                raise DonneeMarcheInvalide(f'indicateur invalide : {cle!r}={valeur!r}')
        object.__setattr__(self, 'indicateurs', MappingProxyType(dict(self.indicateurs)))
        if self.a_t is not None and (type(self.a_t) is not float or not math.isfinite(self.a_t) or self.a_t <= 0):
            raise DonneeMarcheInvalide('A_t doit être un flottant fini strictement positif (C03 point 11)')
        if self.jour_londres is not None and type(self.jour_londres) is not date:
            raise DonneeMarcheInvalide('jour_londres doit être une date')


class NatureEvenementDonnees(StrEnum):
    """Événements de qualité des données (C03 points 6 et 7), journalisés par le coordinateur."""

    TROU = 'TROU'
    RECUPERATION = 'RECUPERATION'
    RECALCUL = 'RECALCUL'  # trou irrécupérable : recalcul sur les seules bougies valides (R6′)
    REINITIALISATION = 'REINITIALISATION'  # préchargement différent : nouvelle initialisation (C03.7)
    PRECHARGEMENT = 'PRECHARGEMENT'


@dataclass(frozen=True)
class EvenementDonnees:
    """Trou, récupération, réinitialisation ou fin de préchargement d'un symbole, avec ses bornes UTC."""

    symbole: str
    nature: NatureEvenementDonnees
    instant_ms: int
    debut_ms: int | None = None
    fin_ms: int | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        _symbole(self.symbole, 'symbole')
        if not isinstance(self.nature, NatureEvenementDonnees):
            raise DonneeMarcheInvalide('nature doit être une NatureEvenementDonnees')
        _entier(self.instant_ms, 'instant_ms')
        for nom in ('debut_ms', 'fin_ms'):
            if getattr(self, nom) is not None:
                _entier(getattr(self, nom), nom)
        if not isinstance(self.details, Mapping):
            raise DonneeMarcheInvalide('details doit être un dictionnaire')
        object.__setattr__(self, 'details', MappingProxyType(dict(self.details)))

"""Implémentation de la couche 0b (types_london). Révisable à comportement constant sous harnais complet."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import math

from xpbots.donnees.c0a_types import BougieEnrichie, UniteTemps
from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.noyau.c1c_domaine import CleIntention, Motif, Sens, verifier_motif


class ErreurLondon(ValueError):
    """Valeur ou événement hors contrat London."""


def nombre_fini(valeur, nom, minimum=None, strict=False) -> float:
    if type(valeur) not in (int, float):
        raise ErreurLondon(f'{nom} : nombre fini attendu')
    try:
        valeur = float(valeur)
    except OverflowError as erreur:
        raise ErreurLondon(f'{nom} : nombre non représentable') from erreur
    if not math.isfinite(valeur) or (minimum is not None and (valeur < minimum or strict and valeur == minimum)):
        raise ErreurLondon(f'{nom} : nombre hors bornes')
    return valeur


def _jour(jour) -> None:
    if type(jour) is not date:
        raise ErreurLondon('date civile attendue')


def _instant(instant) -> None:
    try:
        verifier_instant(instant)
    except ValueError as erreur:
        raise ErreurLondon('instant UTC entier attendu') from erreur


def tick_flottant(tick_size: Decimal) -> float:
    if not isinstance(tick_size, Decimal) or not tick_size.is_finite() or tick_size <= 0:
        raise ErreurLondon('tick_size : Decimal fini strictement positif attendu')
    return nombre_fini(float(tick_size), 'tick_size', 0, strict=True)


def verifier_bougie(enrichie, unite, duree_ms, symbole=None) -> None:
    if (not isinstance(enrichie, BougieEnrichie) or not isinstance(unite, UniteTemps)
            or enrichie.unite is not unite or enrichie.bougie.duree_ms != duree_ms
            or symbole is not None and enrichie.bougie.symbole != symbole):
        raise ErreurLondon('bougie enrichie, unité, durée ou symbole incohérent')


@dataclass(frozen=True)
class RangeLondon:
    jour: date
    haut: float
    bas: float
    disponible_ms: int

    def __post_init__(self):
        _jour(self.jour)
        _instant(self.disponible_ms)
        for nom in ('haut', 'bas'):
            object.__setattr__(self, nom, nombre_fini(getattr(self, nom), nom))
        if self.haut <= self.bas:
            raise ErreurLondon('largeur du range strictement positive attendue')

    @property
    def largeur(self) -> float:
        return self.haut - self.bas


@dataclass(frozen=True)
class GelATRH1:
    jour: date
    atr: float
    fin_h1_ms: int
    disponible_ms: int

    def __post_init__(self):
        _jour(self.jour)
        _instant(self.fin_h1_ms)
        _instant(self.disponible_ms)
        object.__setattr__(self, 'atr', nombre_fini(self.atr, 'atr', 0, strict=True))
        if self.disponible_ms < self.fin_h1_ms:
            raise ErreurLondon('gel disponible avant clôture H1')


@dataclass(frozen=True)
class Cassure:
    sens: Sens
    fraction_corps: float
    fraction_cloture: float
    buffer: float

    def __post_init__(self):
        if not isinstance(self.sens, Sens):
            raise ErreurLondon('sens typé attendu')
        for nom in ('fraction_corps', 'fraction_cloture'):
            valeur = nombre_fini(getattr(self, nom), nom, 0)
            if valeur > 1:
                raise ErreurLondon('fraction supérieure à un')
            object.__setattr__(self, nom, valeur)
        object.__setattr__(self, 'buffer', nombre_fini(self.buffer, 'buffer', 0, strict=True))


@dataclass(frozen=True)
class StopLocal:
    niveau: float
    multiple_objectif: float
    distance: float
    composantes: tuple[float, float, float]
    contraignantes: tuple[str, ...]

    def __post_init__(self):
        for nom in ('niveau', 'multiple_objectif', 'distance'):
            object.__setattr__(self, nom, nombre_fini(getattr(self, nom), nom,
                                                    None if nom == 'niveau' else 0, strict=True))
        if not isinstance(self.composantes, tuple) or len(self.composantes) != 3:
            raise ErreurLondon('trois composantes attendues')
        for valeur in self.composantes:
            nombre_fini(valeur, 'composante')
        if (not isinstance(self.contraignantes, tuple) or not self.contraignantes
                or len(set(self.contraignantes)) != len(self.contraignantes)
                or any(nom not in ('BOUGIE', 'FRONTIERE', 'PLANCHER_ATR') for nom in self.contraignantes)):
            raise ErreurLondon('composantes contraignantes inconnues')


@dataclass(frozen=True)
class EtatQuotas:
    jour: date | None = None
    remplissages: tuple[CleIntention, ...] = ()

    def __post_init__(self):
        if self.jour is not None:
            _jour(self.jour)
        if (not isinstance(self.remplissages, tuple)
                or any(not isinstance(cle, CleIntention) for cle in self.remplissages)
                or len(set(self.remplissages)) != len(self.remplissages)
                or self.remplissages and self.jour is None):
            raise ErreurLondon('état de quotas incohérent')


@dataclass(frozen=True)
class RefusLondon:
    motif: Motif
    detail: str | None

    def __post_init__(self):
        try:
            motif, detail = verifier_motif(self.motif, self.detail)
        except (ValueError, TypeError) as erreur:
            raise ErreurLondon('motif ou détail refusé') from erreur
        object.__setattr__(self, 'motif', motif)
        object.__setattr__(self, 'detail', detail)

"""Implémentation de la couche 1a (marche). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import math
import re

from xpbots.noyau.c0a_temps import CleEvenement, ErreurInstant, aligner, verifier_instant
from xpbots.noyau.c0b_nombres import ErreurNombre, decimal_depuis, est_sur_grille

_IDENTIFIANT = re.compile(r'[A-Z][A-Z0-9_]*')


class ErreurMarche(ValueError):
    """Tick, cotation ou bougie refusés."""


def _symbole(valeur: object, nom: str) -> None:
    if not isinstance(valeur, str) or not valeur:
        raise ErreurMarche(f'{nom} : texte non vide attendu')


def _instant(valeur: object, nom: str) -> None:
    try:
        verifier_instant(valeur)
    except ErreurInstant as erreur:
        raise ErreurMarche(f'{nom} : {erreur}') from erreur


def _entier_naturel(valeur: object, nom: str) -> None:
    if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 0:
        raise ErreurMarche(f'{nom} : entier ≥ 0 attendu')


def _prix_flottant(valeur: object, nom: str) -> float:
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur) or valeur <= 0:
        raise ErreurMarche(f'{nom} : nombre fini strictement positif attendu, reçu {valeur!r}')
    return float(valeur)


@dataclass(frozen=True)
class Tick:
    symbole: str
    symbole_courtier: str
    instant_fournisseur_ms: int
    instant_reception_ms: int
    numero: int
    bid: float
    ask: float
    drapeaux: int = 0

    def __post_init__(self) -> None:
        _symbole(self.symbole, 'symbole')
        _symbole(self.symbole_courtier, 'symbole_courtier')
        _instant(self.instant_fournisseur_ms, 'instant_fournisseur_ms')
        _instant(self.instant_reception_ms, 'instant_reception_ms')
        _entier_naturel(self.numero, 'numero')
        _entier_naturel(self.drapeaux, 'drapeaux')
        object.__setattr__(self, 'bid', _prix_flottant(self.bid, 'bid'))
        object.__setattr__(self, 'ask', _prix_flottant(self.ask, 'ask'))

    @property
    def cle(self) -> CleEvenement:
        return CleEvenement(self.instant_reception_ms, self.numero)


@dataclass(frozen=True)
class Cotation:
    symbole: str
    bid: Decimal
    ask: Decimal
    instant_fournisseur_ms: int
    instant_reception_ms: int

    def __post_init__(self) -> None:
        _symbole(self.symbole, 'symbole')
        for nom in ('bid', 'ask'):
            valeur = getattr(self, nom)
            if not isinstance(valeur, Decimal) or not valeur.is_finite() or valeur <= 0:
                raise ErreurMarche(f'{nom} : décimal fini strictement positif attendu')
        _instant(self.instant_fournisseur_ms, 'instant_fournisseur_ms')
        _instant(self.instant_reception_ms, 'instant_reception_ms')

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid


def cotation_depuis_tick(tick: Tick, pas: Decimal) -> Cotation:
    if not isinstance(tick, Tick):
        raise ErreurMarche('tick attendu')
    try:
        bid, ask = decimal_depuis(tick.bid), decimal_depuis(tick.ask)
        if not (est_sur_grille(bid, pas) and est_sur_grille(ask, pas)):
            raise ErreurMarche(f'cotation hors de la grille {pas} : {bid} / {ask}')
    except ErreurNombre as erreur:
        raise ErreurMarche(f'conversion de cotation impossible : {erreur}') from erreur
    return Cotation(tick.symbole, bid, ask, tick.instant_fournisseur_ms, tick.instant_reception_ms)


@dataclass(frozen=True)
class Bougie:
    symbole: str
    debut_ms: int
    duree_ms: int
    ouverture: float | None
    haut: float | None
    bas: float | None
    cloture: float | None
    nombre_evenements: int
    valide: bool
    motif_invalidite: str | None
    instant_disponibilite_ms: int

    def __post_init__(self) -> None:
        _symbole(self.symbole, 'symbole')
        _instant(self.debut_ms, 'debut_ms')
        _instant(self.instant_disponibilite_ms, 'instant_disponibilite_ms')
        try:
            if aligner(self.debut_ms, self.duree_ms) != self.debut_ms:
                raise ErreurMarche('debut_ms non aligné sur la durée')
        except ErreurInstant as erreur:
            raise ErreurMarche(f'duree_ms : {erreur}') from erreur
        _entier_naturel(self.nombre_evenements, 'nombre_evenements')
        if not isinstance(self.valide, bool):
            raise ErreurMarche('valide : booléen attendu')
        prix = (self.ouverture, self.haut, self.bas, self.cloture)
        if self.valide:
            if self.motif_invalidite is not None:
                raise ErreurMarche('une bougie valide ne porte pas de motif d\'invalidité')
            if self.nombre_evenements < 1:
                raise ErreurMarche('une bougie valide compte au moins un événement')
            self._verifier_prix(prix)
        else:
            if not isinstance(self.motif_invalidite, str) or not _IDENTIFIANT.fullmatch(self.motif_invalidite):
                raise ErreurMarche('motif d\'invalidité majuscule obligatoire')
            if any(p is not None for p in prix):
                self._verifier_prix(prix)
        if self.instant_disponibilite_ms < self.fin_ms:
            raise ErreurMarche('une bougie n\'est disponible qu\'à partir de sa fin')

    def _verifier_prix(self, prix: tuple) -> None:
        convertis = tuple(_prix_flottant(p, nom) for p, nom in zip(prix, ('ouverture', 'haut', 'bas', 'cloture')))
        ouverture, haut, bas, cloture = convertis
        if not bas <= min(ouverture, cloture) <= max(ouverture, cloture) <= haut:
            raise ErreurMarche('OHLC incohérents')
        for nom, valeur in zip(('ouverture', 'haut', 'bas', 'cloture'), convertis):
            object.__setattr__(self, nom, valeur)

    @property
    def fin_ms(self) -> int:
        return self.debut_ms + self.duree_ms

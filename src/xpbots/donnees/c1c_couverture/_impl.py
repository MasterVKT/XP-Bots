"""Implémentation de la couche 1c (couverture_flux). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from typing import Iterable, Protocol, Sequence

from xpbots.donnees.c0a_types import ErreurDonneesTemps, StatutCouverture
from xpbots.noyau.c1b_instrument import ErreurInstrument, HorairesCotation, Intervalle


def _intervalle(debut_ms: int, fin_ms: int) -> Intervalle:
    try:
        return Intervalle(debut_ms, fin_ms)
    except ErreurInstrument as erreur:
        raise ErreurDonneesTemps(str(erreur)) from erreur


def _fusionner(intervalles: Iterable[Intervalle]) -> tuple[Intervalle, ...]:
    fusion: list[list[int]] = []
    for i in sorted(intervalles):
        if fusion and i.debut_ms <= fusion[-1][1]:
            fusion[-1][1] = max(fusion[-1][1], i.fin_ms)
        else:
            fusion.append([i.debut_ms, i.fin_ms])
    return tuple(Intervalle(a, b) for a, b in fusion)


def _soustraire(base: Sequence[Intervalle], retraits: Sequence[Intervalle]) -> list[tuple[int, int]]:
    morceaux = [(i.debut_ms, i.fin_ms) for i in base]
    for retrait in retraits:
        suivants = []
        for a, b in morceaux:
            if retrait.fin_ms <= a or retrait.debut_ms >= b:
                suivants.append((a, b))
                continue
            if a < retrait.debut_ms:
                suivants.append((a, retrait.debut_ms))
            if retrait.fin_ms < b:
                suivants.append((retrait.fin_ms, b))
        morceaux = suivants
    return morceaux


def parties_ouvertes(horaires: HorairesCotation, debut_ms: int, fin_ms: int) -> tuple[Intervalle, ...]:
    if not isinstance(horaires, HorairesCotation):
        raise ErreurDonneesTemps('horaires de cotation du noyau attendus')
    fenetre = _intervalle(debut_ms, fin_ms)
    if fenetre.debut_ms < horaires.debut_validite_ms or fenetre.fin_ms > horaires.fin_validite_ms:
        raise ErreurDonneesTemps('intervalle hors de la période de validité des horaires')
    effectives = _soustraire(horaires.seances, horaires.fermetures)
    coupees = [(max(a, debut_ms), min(b, fin_ms)) for a, b in effectives]
    return _fusionner(Intervalle(a, b) for a, b in coupees if b > a)


class SourceCouverture(Protocol):
    def periodes(self, jusqua_ms: int) -> tuple[Intervalle, ...]:
        ...


def classer_intervalle(debut_ms: int, fin_ms: int, horaires: HorairesCotation,
                       couverture: SourceCouverture) -> StatutCouverture:
    try:
        ouvertes = parties_ouvertes(horaires, debut_ms, fin_ms)
    except ErreurDonneesTemps:
        if not isinstance(horaires, HorairesCotation) or fin_ms <= debut_ms:
            raise
        return StatutCouverture.INCONNU
    if not ouvertes:
        return StatutCouverture.FERMETURE_OFFICIELLE
    couvertes = couverture.periodes(fin_ms)
    for partie in ouvertes:
        if not any(c.debut_ms <= partie.debut_ms and partie.fin_ms <= c.fin_ms for c in couvertes):
            return StatutCouverture.TROU
    return StatutCouverture.COUVERT


class RegistreCouverture:
    """Couverture historique (P-01) : période de la source moins les trous déclarés par son registre."""

    def __init__(self, periodes: Sequence[Intervalle]) -> None:
        if not all(isinstance(p, Intervalle) for p in periodes):
            raise ErreurDonneesTemps('intervalles du noyau attendus')
        ordonnees = sorted(periodes)
        for precedente, suivante in zip(ordonnees, ordonnees[1:]):
            if suivante.debut_ms < precedente.fin_ms:
                raise ErreurDonneesTemps('périodes de couverture chevauchantes')
        self._periodes = _fusionner(ordonnees)

    @classmethod
    def depuis_registre_de_trous(cls, debut_ms: int, fin_ms: int, trous: Sequence[Intervalle]) -> 'RegistreCouverture':
        source = _intervalle(debut_ms, fin_ms)
        return cls([Intervalle(a, b) for a, b in _soustraire([source], list(trous)) if b > a])

    def periodes(self, jusqua_ms: int) -> tuple[Intervalle, ...]:
        return self._periodes


class JournalConnexions:
    """Couverture en direct (P-01) : périodes de connexion du robot."""

    def __init__(self) -> None:
        self._fermees: list[Intervalle] = []
        self._ouverte: int | None = None
        self._dernier: int | None = None

    def _ordonner(self, instant_ms: int) -> None:
        if isinstance(instant_ms, bool) or not isinstance(instant_ms, int) or instant_ms < 0:
            raise ErreurDonneesTemps('instant entier ≥ 0 attendu')
        if self._dernier is not None and instant_ms < self._dernier:
            raise ErreurDonneesTemps('événement de connexion hors d\'ordre')
        self._dernier = instant_ms

    def connecter(self, instant_ms: int) -> None:
        self._ordonner(instant_ms)
        if self._ouverte is not None:
            raise ErreurDonneesTemps('connexion déjà ouverte')
        self._ouverte = instant_ms

    def deconnecter(self, instant_ms: int) -> None:
        self._ordonner(instant_ms)
        if self._ouverte is None:
            raise ErreurDonneesTemps('aucune connexion ouverte')
        if instant_ms > self._ouverte:
            self._fermees.append(Intervalle(self._ouverte, instant_ms))
        self._ouverte = None

    def periodes(self, jusqua_ms: int) -> tuple[Intervalle, ...]:
        periodes = list(self._fermees)
        if self._ouverte is not None and jusqua_ms > self._ouverte:
            periodes.append(Intervalle(self._ouverte, jusqua_ms))
        return _fusionner(periodes)

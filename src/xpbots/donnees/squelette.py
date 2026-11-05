"""Segment minimal S2 du squelette : agrégation des ticks en bougies Bid closes.

Segment minimal du squelette, remplacé en phase 3 par l'artefact `donnees-temps`. Contrat de la couture :
mcl/squelette/COUTURES.md. Types du noyau : `Tick` et `Bougie` (`xpbots.noyau.c1a_marche`).

Règles appliquées : intervalle [T, T + durée) aligné sur les multiples de la durée depuis l'origine UTC ; le
tick dont l'heure fournisseur vaut exactement T + durée appartient à la bougie suivante et clôt la précédente
(C03.2) ; la bougie close est disponible à l'heure de réception de ce tick. Limites assumées : pas de H1, pas de
traitement des trous ni des intervalles vides (aucune bougie n'est inventée), pas d'indicateur.
"""
from __future__ import annotations

from dataclasses import dataclass

from xpbots.noyau.c0a_temps import aligner
from xpbots.noyau.c1a_marche import Bougie, Tick


class ErreurAgregation(ValueError):
    """Tick refusé par l'agrégateur (symbole ou ordre)."""


@dataclass
class _BougieOuverte:
    debut_ms: int
    ouverture: float
    haut: float
    bas: float
    cloture: float
    nombre_evenements: int


class AgregateurM15:
    """Agrège en bougies Bid closes les ticks ordonnés d'un seul symbole."""

    def __init__(self, symbole: str, duree_ms: int) -> None:
        if not symbole:
            raise ValueError('symbole vide')
        if isinstance(duree_ms, bool) or not isinstance(duree_ms, int) or duree_ms <= 0:
            raise ValueError('la durée de bougie doit être un entier strictement positif')
        self.symbole = symbole
        self.duree_ms = duree_ms
        self._ouverte: _BougieOuverte | None = None
        self._dernier: tuple[int, int] | None = None

    def ajouter(self, tick: Tick) -> tuple[Bougie, ...]:
        """Intégrer un tick ; rendre la bougie qu'il clôt, ou un tuple vide."""
        if tick.symbole != self.symbole:
            raise ErreurAgregation(f'tick {tick.symbole} transmis à l\'agrégateur {self.symbole}')
        cle = (tick.instant_fournisseur_ms, tick.numero)
        if self._dernier is not None and cle <= self._dernier:
            raise ErreurAgregation(f'tick hors ordre : {cle} après {self._dernier}')
        self._dernier = cle
        debut = aligner(tick.instant_fournisseur_ms, self.duree_ms)
        closes: tuple[Bougie, ...] = ()
        ouverte = self._ouverte
        if ouverte is not None and debut != ouverte.debut_ms:
            closes = (Bougie(self.symbole, ouverte.debut_ms, self.duree_ms, ouverte.ouverture, ouverte.haut,
                             ouverte.bas, ouverte.cloture, ouverte.nombre_evenements, True, None,
                             max(tick.instant_reception_ms, ouverte.debut_ms + self.duree_ms)),)
            ouverte = None
        if ouverte is None:
            self._ouverte = _BougieOuverte(debut, tick.bid, tick.bid, tick.bid, tick.bid, 1)
        else:
            ouverte.haut = max(ouverte.haut, tick.bid)
            ouverte.bas = min(ouverte.bas, tick.bid)
            ouverte.cloture = tick.bid
            ouverte.nombre_evenements += 1
        return closes

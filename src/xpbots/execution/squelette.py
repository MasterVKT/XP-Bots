"""Segment minimal S4 du squelette : coordinateur qui ne transmet jamais d'ordre.

Segment minimal du squelette, remplacé en phase 6 par l'artefact `execution-coordinateur` (puis enchaîné par
l'orchestration en phase 9). Contrat de la couture : mcl/squelette/COUTURES.md. Aucune logique C06 à C08 :
tout signal est refusé explicitement (`ENVIRONMENT_NOT_READY`, détail `SEGMENT_MINIMAL_S4`) ; un résultat sans
signal garde son motif. Les types de commande servent à l'exécution papier minimale S5.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import math

from xpbots.noyau.squelette import (ACHAT, DETAIL_COORDINATEUR_MINIMAL, MOTIF_ENVIRONMENT_NOT_READY, SENS,
                                    ResultatTechnique)


@dataclass(frozen=True)
class CommandeEntree:
    """Entrée au marché protégée par un SL et un TP transmis dans la même commande."""

    cle: str
    symbole: str
    sens: str
    volume: Decimal
    sl: float
    tp: float

    def __post_init__(self) -> None:
        if not self.cle or not self.symbole:
            raise ValueError('clé et symbole obligatoires')
        if self.sens not in SENS:
            raise ValueError(f'sens inconnu : {self.sens!r}')
        if not isinstance(self.volume, Decimal) or not self.volume.is_finite() or self.volume <= 0:
            raise ValueError('volume décimal strictement positif obligatoire')
        if not (math.isfinite(self.sl) and math.isfinite(self.tp)):
            raise ValueError('SL et TP doivent être finis')
        if (self.sl >= self.tp) if self.sens == ACHAT else (self.sl <= self.tp):
            raise ValueError('SL et TP incohérents avec le sens')


@dataclass(frozen=True)
class CommandeCloture:
    """Clôture au marché de la position ouverte sous la clé indiquée."""

    cle: str
    motif: str


@dataclass(frozen=True)
class Decision:
    """Issue du coordinateur pour un résultat technique : motif, détail et commandes à exécuter."""

    motif: str | None
    detail: str | None
    commandes: tuple[CommandeEntree | CommandeCloture, ...] = ()


class CoordinateurMinimal:
    """Refuse tout signal ; ne produit jamais de commande."""

    def decider(self, resultat: ResultatTechnique) -> Decision:
        if resultat.sens is None:
            return Decision(resultat.motif, resultat.detail)
        return Decision(MOTIF_ENVIRONMENT_NOT_READY, DETAIL_COORDINATEUR_MINIMAL)

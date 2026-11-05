"""Enchaînement minimal du squelette (segment S4) : tick → bougies closes → stratégie → coordinateur → journal.

Segment minimal du squelette, remplacé en phase 9 par le moteur de décision de l'artefact `orchestration`.
Contrat de la couture : mcl/squelette/COUTURES.md. Cœur pur : il reçoit des ticks et rend des enregistrements et
des commandes, sans horloge ni fichier. La stratégie est injectée (D-18) : ce module n'importe aucun moteur.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from xpbots.donnees.squelette import AgregateurM15
from xpbots.execution.squelette import CommandeCloture, CommandeEntree, CoordinateurMinimal
from xpbots.noyau.squelette import (Bougie, ConfigurationSquelette, ResultatTechnique, Tick, TYPE_CLOTURE,
                                    VERSION_SCHEMA_SQUELETTE)


class Strategie(Protocol):
    """Contrat structurel d'une stratégie injectée."""

    identifiant: str

    def sur_cloture(self, bougie: Bougie) -> ResultatTechnique:
        ...


@dataclass(frozen=True)
class SortieMoteur:
    """Ce que rend le moteur pour un événement : enregistrements de journal et commandes."""

    enregistrements: tuple[dict[str, Any], ...]
    commandes: tuple[CommandeEntree | CommandeCloture, ...]


class MoteurMinimal:
    """Moteur minimal : un agrégateur par symbole, une stratégie, le coordinateur minimal."""

    def __init__(self, strategie: Strategie, configuration: ConfigurationSquelette, mode: str) -> None:
        if not mode:
            raise ValueError('mode vide')
        self._strategie = strategie
        self._configuration = configuration
        self._mode = mode
        self._coordinateur = CoordinateurMinimal()
        self._agregateurs: dict[str, AgregateurM15] = {}
        self._numero = 0

    def traiter_tick(self, tick: Tick) -> SortieMoteur:
        agregateur = self._agregateurs.get(tick.symbole)
        if agregateur is None:
            agregateur = AgregateurM15(tick.symbole, self._configuration.duree_bougie_ms)
            self._agregateurs[tick.symbole] = agregateur
        enregistrements = []
        commandes: list[CommandeEntree | CommandeCloture] = []
        for bougie in agregateur.ajouter(tick):
            resultat = self._strategie.sur_cloture(bougie)
            decision = self._coordinateur.decider(resultat)
            self._numero += 1
            enregistrements.append({
                'type': TYPE_CLOTURE,
                'version_schema': VERSION_SCHEMA_SQUELETTE,
                'mode': self._mode,
                'numero': self._numero,
                'instant_utc_ms': tick.instant_ms,
                'strategie': resultat.strategie,
                'symbole': bougie.symbole,
                'bougie': {'debut_utc_ms': bougie.debut_ms, 'fin_utc_ms': bougie.fin_ms,
                           'ouverture': bougie.ouverture, 'haut': bougie.haut, 'bas': bougie.bas,
                           'cloture': bougie.cloture, 'ticks': bougie.nombre_ticks},
                'signal': resultat.sens,
                'motif': decision.motif,
                'detail': decision.detail,
            })
            commandes.extend(decision.commandes)
        return SortieMoteur(tuple(enregistrements), tuple(commandes))


def fabriquer_moteur_minimal(strategie: Strategie, configuration: ConfigurationSquelette,
                             mode: str) -> MoteurMinimal:
    """Point de composition du moteur minimal, appelé par la coquille."""
    return MoteurMinimal(strategie, configuration, mode)

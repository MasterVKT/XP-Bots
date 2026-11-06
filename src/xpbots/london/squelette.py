"""Segment minimal S3 du squelette : stratégie qui ne produit jamais de signal.

Segment minimal du squelette, remplacé en phase 4 par l'artefact `moteur-london` (méthode S02). Contrat de la
couture : mcl/squelette/COUTURES.md. Il satisfait le contrat structurel de stratégie de l'orchestration
(attribut `identifiant`, méthode `sur_bougie`) sans l'importer (D-18). Il reçoit les bougies enrichies M15 et H1
de l'artefact `donnees-temps` (`xpbots.donnees.c0a_types.BougieEnrichie`). Aucune logique S02.
"""
from __future__ import annotations

from xpbots.donnees.c0a_types import BougieEnrichie, UniteTemps
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1c_domaine import AbsenceDeSignal, Motif

DETAIL_STRATEGIE_MINIMALE = 'SEGMENT_MINIMAL_S3'


class StrategieMinimale:
    """Rend une absence de signal `NO_SETUP`, détail `SEGMENT_MINIMAL_S3`, à chaque M15 close ; rien pour une H1."""

    def __init__(self, identifiant: str) -> None:
        if not identifiant:
            raise ValueError('identifiant de stratégie vide')
        self.identifiant = identifiant

    def sur_bougie(self, enrichie: BougieEnrichie) -> AbsenceDeSignal | None:
        if enrichie.unite is not UniteTemps.M15:
            return None
        return AbsenceDeSignal(self.identifiant, enrichie.bougie.symbole, enrichie.bougie.fin_ms, Motif.NO_SETUP,
                               DETAIL_STRATEGIE_MINIMALE)


def fabriquer_strategie(configuration: ConfigurationFigee) -> StrategieMinimale:
    """Fabrique injectée par la coquille ; l'identifiant vient de `london.strategy_id`."""
    return StrategieMinimale(configuration.technique.london['strategy_id'])

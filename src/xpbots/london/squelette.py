"""Segment minimal S3 du squelette : stratégie qui ne produit jamais de signal.

Segment minimal du squelette, remplacé en phase 4 par l'artefact `moteur-london` (méthode S02). Contrat de la
couture : mcl/squelette/COUTURES.md. Il satisfait le contrat structurel de stratégie de l'orchestration
(attribut `identifiant`, méthode `sur_cloture`) sans l'importer (D-18). Aucune logique S02.
"""
from __future__ import annotations

from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1a_marche import Bougie
from xpbots.noyau.c1c_domaine import AbsenceDeSignal, Motif

DETAIL_STRATEGIE_MINIMALE = 'SEGMENT_MINIMAL_S3'


class StrategieMinimale:
    """Rend une absence de signal `NO_SETUP`, détail `SEGMENT_MINIMAL_S3`, à chaque bougie close."""

    def __init__(self, identifiant: str) -> None:
        if not identifiant:
            raise ValueError('identifiant de stratégie vide')
        self.identifiant = identifiant

    def sur_cloture(self, bougie: Bougie) -> AbsenceDeSignal:
        return AbsenceDeSignal(self.identifiant, bougie.symbole, bougie.fin_ms, Motif.NO_SETUP,
                               DETAIL_STRATEGIE_MINIMALE)


def fabriquer_strategie(configuration: ConfigurationFigee) -> StrategieMinimale:
    """Fabrique injectée par la coquille ; l'identifiant vient de `london.strategy_id`."""
    return StrategieMinimale(configuration.technique.london['strategy_id'])

"""Segment minimal S3 du squelette : stratégie qui ne produit jamais de signal.

Segment minimal du squelette, remplacé en phase 4 par l'artefact `moteur-london` (méthode S02). Contrat de la
couture : mcl/squelette/COUTURES.md. Il satisfait le contrat structurel de stratégie de l'orchestration
(attribut `identifiant`, méthode `sur_cloture`) sans l'importer (D-18). Aucune logique S02.
"""
from __future__ import annotations

from xpbots.noyau.squelette import (Bougie, ConfigurationSquelette, DETAIL_STRATEGIE_MINIMALE, MOTIF_NO_SETUP,
                                    ResultatTechnique)


class StrategieMinimale:
    """Rend `NO_SETUP`, détail `SEGMENT_MINIMAL_S3`, à chaque bougie close."""

    def __init__(self, identifiant: str) -> None:
        if not identifiant:
            raise ValueError('identifiant de stratégie vide')
        self.identifiant = identifiant

    def sur_cloture(self, bougie: Bougie) -> ResultatTechnique:
        return ResultatTechnique(strategie=self.identifiant, symbole=bougie.symbole, cloture_ms=bougie.fin_ms,
                                 sens=None, motif=MOTIF_NO_SETUP, detail=DETAIL_STRATEGIE_MINIMALE)


def fabriquer_strategie(configuration: ConfigurationSquelette) -> StrategieMinimale:
    """Fabrique injectée par la coquille ; l'identifiant vient de `london.strategy_id`."""
    return StrategieMinimale(configuration.identifiant_strategie)

"""Couche 2b de london-execution-coordinateur — arbitrage.

Interface publique figée ; contrat : mcl/london-execution-coordinateur/contrats/couche-2b.md.
"""
from xpbots.execution.c2b_arbitrage._impl import (CandidatArbitrage, ordonner_signaux, candidats_admission)

__all__ = ['CandidatArbitrage', 'ordonner_signaux', 'candidats_admission']

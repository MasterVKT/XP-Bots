"""Couche 0c de london-execution-coordinateur — garde_cotation.

Interface publique figée ; contrat : mcl/london-execution-coordinateur/contrats/couche-0c.md.
"""
from xpbots.execution.c0c_cotation._impl import (EtatCotation, VerdictCotation, evaluer_cotation)

__all__ = ['EtatCotation', 'VerdictCotation', 'evaluer_cotation']

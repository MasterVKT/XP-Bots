"""Couche 3 de london-execution-coordinateur — dimensionnement.

Interface publique figée ; contrat : mcl/london-execution-coordinateur/contrats/couche-3.md.
"""
from xpbots.execution.c3_dimensionnement._impl import (PlanDimensionnement, dimensionner)

__all__ = ['PlanDimensionnement', 'dimensionner']

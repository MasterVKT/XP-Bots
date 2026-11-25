"""Couche 1b du service IA — validation : extraction et notes strictes.

Interface publique figée ; contrat : mcl/london-service-ia/contrats/couche-1b.md.
"""
from ._impl import valider_extraction, valider_note

__all__ = ('valider_extraction', 'valider_note')

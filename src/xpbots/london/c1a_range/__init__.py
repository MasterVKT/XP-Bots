"""Couche 1a de moteur-london — range_londres : range exact S02.

Interface publique figée ; contrat : mcl/moteur-london/contrats/couche-1a.md.
"""
from ._impl import construire_range

__all__ = ['construire_range']

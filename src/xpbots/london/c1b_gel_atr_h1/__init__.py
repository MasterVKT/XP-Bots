"""Couche 1b de moteur-london — gel_atr_h1 : candidate H1 causale de S02 et P-09.

Interface publique figée ; contrat : mcl/moteur-london/contrats/couche-1b.md.
"""
from ._impl import construire_gel

__all__ = ['construire_gel']

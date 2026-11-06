"""Couche 1d de moteur-london — stop_local : trois composantes de S02.4.

Interface publique figée ; contrat : mcl/moteur-london/contrats/couche-1d.md.
"""
from ._impl import calculer_stop

__all__ = ['calculer_stop']

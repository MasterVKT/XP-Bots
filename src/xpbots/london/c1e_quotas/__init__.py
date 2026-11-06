"""Couche 1e de moteur-london — quotas_london : quotas au premier remplissage confirmé.

Interface publique figée ; contrat : mcl/moteur-london/contrats/couche-1e.md.
"""
from ._impl import QuotasLondon

__all__ = ['QuotasLondon']

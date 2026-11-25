"""Couche 1f du service IA — snapshot : archive, séquence et publication A10.

Interface publique figée ; contrat : mcl/london-service-ia/contrats/couche-1f.md.
"""
from ._impl import PublicationSnapshot, fabriquer_snapshot, EcrivainSnapshot

__all__ = ('PublicationSnapshot', 'fabriquer_snapshot', 'EcrivainSnapshot')

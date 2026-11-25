"""Couche 1e du service IA — fournisseurs : formats A08 sans transport.

Interface publique figée ; contrat : mcl/london-service-ia/contrats/couche-1e.md.
"""
from ._impl import UsageFournisseur, RetourFournisseur, construire_requete, decoder_reponse, extraire_usage

__all__ = ('UsageFournisseur', 'RetourFournisseur', 'construire_requete', 'decoder_reponse', 'extraire_usage')

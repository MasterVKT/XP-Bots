"""Couche 1a du service IA — tokens : borne conservatrice du corps complet.

Interface publique figée ; contrat : mcl/london-service-ia/contrats/couche-1a.md.
"""
from ._impl import RequeteBornee, compter_entree, preparer_requete

__all__ = ('RequeteBornee', 'compter_entree', 'preparer_requete')

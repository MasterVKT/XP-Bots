"""Couche 2b de london-donnees-temps — `etat_indicateurs` : chaîne d'indicateurs, préchargement, reprise (C03.7, P-03, P-10).

Interface publique figée ; contrat : mcl/london-donnees-temps/contrats/couche-2b.md.
"""
from xpbots.donnees.c2b_etat_indicateurs._impl import SCHEMA_ETAT, ChaineIndicateurs

__all__ = ['SCHEMA_ETAT', 'ChaineIndicateurs']

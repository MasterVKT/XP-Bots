"""Couche 2 de moteur-london — moteur_london : enveloppe pure S02 par symbole.

Interface publique figée ; contrat : mcl/moteur-london/contrats/couche-2.md.
"""
from ._impl import MoteurLondon, StrategieLondon, fabriquer_strategie

__all__ = ['MoteurLondon', 'StrategieLondon', 'fabriquer_strategie']

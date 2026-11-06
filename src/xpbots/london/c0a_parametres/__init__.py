"""Couche 0a de moteur-london — parametres_london : paramètres S02 typés.

Interface publique figée ; contrat : mcl/moteur-london/contrats/couche-0a.md.
"""
from ._impl import CLES_LONDON, ErreurParametresLondon, ParametresLondon, charger_parametres_london

__all__ = ['CLES_LONDON', 'ErreurParametresLondon', 'ParametresLondon', 'charger_parametres_london']

"""Couche 0b du noyau — `nombres` : décimaux sûrs et arrondis sur la grille avec contrôle d'erreur (C03.12).

Interface publique figée ; contrat : mcl/noyau/contrats/couche-0b.md.
"""
from xpbots.noyau.c0b_nombres._impl import (EPSILON_GRILLE, Arrondi, ErreurNombre, arrondir_sur_grille,
                                            decimal_depuis, est_sur_grille)

__all__ = ['EPSILON_GRILLE', 'Arrondi', 'ErreurNombre', 'arrondir_sur_grille', 'decimal_depuis', 'est_sur_grille']

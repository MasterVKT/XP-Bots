"""Couche 2a de donnees-temps — `validation_bougies` : bougie valide ou invalide motivée, trous (C03.5, C03.6, P-02).

Interface publique figée ; contrat : mcl/donnees-temps/contrats/couche-2a.md.
"""
from xpbots.donnees.c2a_validation._impl import (AUCUN_BID, HORAIRES_INCONNUS, MARCHE_FERME, TROU_DONNEES,
                                                 ResultatValidation, ValidateurBougies)

__all__ = ['AUCUN_BID', 'HORAIRES_INCONNUS', 'MARCHE_FERME', 'TROU_DONNEES', 'ResultatValidation', 'ValidateurBougies']

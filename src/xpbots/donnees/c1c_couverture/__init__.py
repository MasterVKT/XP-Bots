"""Couche 1c de donnees-temps — `couverture_flux` : intervalle couvert, fermeture officielle, trou (C03.5, P-01).

Interface publique figée ; contrat : mcl/donnees-temps/contrats/couche-1c.md.
"""
from xpbots.donnees.c1c_couverture._impl import (JournalConnexions, RegistreCouverture, SourceCouverture,
                                                 classer_intervalle, parties_ouvertes)

__all__ = ['JournalConnexions', 'RegistreCouverture', 'SourceCouverture', 'classer_intervalle', 'parties_ouvertes']

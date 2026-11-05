"""Couche 1b du noyau — `instrument` : profils d'instrument et de compte de C04, horaires de cotation.

Interface publique figée ; contrat : mcl/noyau/contrats/couche-1b.md.
"""
from xpbots.noyau.c1b_instrument._impl import (CHAMPS_COMPTE, CHAMPS_INSTRUMENT, ErreurInstrument,
                                               HorairesCotation, Intervalle, ProfilCompte, ProfilInstrument,
                                               ResultatProfil, construire_profil_compte,
                                               construire_profil_instrument)

__all__ = ['CHAMPS_COMPTE', 'CHAMPS_INSTRUMENT', 'ErreurInstrument', 'HorairesCotation', 'Intervalle',
           'ProfilCompte', 'ProfilInstrument', 'ResultatProfil', 'construire_profil_compte',
           'construire_profil_instrument']

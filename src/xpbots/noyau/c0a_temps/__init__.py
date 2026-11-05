"""Couche 0a du noyau — `instant` : instants UTC en millisecondes entières et ordre stable des événements.

Interface publique figée ; contrat : mcl/noyau/contrats/couche-0a.md.
"""
from xpbots.noyau.c0a_temps._impl import (CleEvenement, ErreurInstant, aligner, instant_depuis_datetime,
                                          instant_depuis_iso, instant_vers_datetime, instant_vers_iso,
                                          verifier_instant)

__all__ = ['CleEvenement', 'ErreurInstant', 'aligner', 'instant_depuis_datetime', 'instant_depuis_iso',
           'instant_vers_datetime', 'instant_vers_iso', 'verifier_instant']

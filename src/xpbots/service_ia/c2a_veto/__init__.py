"""Couche 2a du service IA — veto : appariement causal et seul événement A06.

Interface publique figée ; contrat : mcl/london-service-ia/contrats/couche-2a.md.
"""
from ._impl import (CorrespondanceCalendrier, TableAppariement, AppariementCalendrier,
    apparier_calendrier, construire_veto)

__all__ = ('CorrespondanceCalendrier', 'TableAppariement', 'AppariementCalendrier',
           'apparier_calendrier', 'construire_veto')

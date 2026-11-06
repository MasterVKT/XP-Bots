"""Couche 0b de donnees-temps — `sessions_londres` : jours et heures de Londres, fenêtres, jour UTC, blackout.

Interface publique figée ; contrat : mcl/donnees-temps/contrats/couche-0b.md.
"""
from xpbots.donnees.c0b_sessions._impl import CalendrierLondres, ErreurSessions

__all__ = ['CalendrierLondres', 'ErreurSessions']

"""Couche 1c de london-execution-coordinateur — registre_reservations.

Interface publique figée ; contrat : mcl/london-execution-coordinateur/contrats/couche-1c.md.
"""
from xpbots.execution.c1c_reservations._impl import (RegistreReservations)

__all__ = ['RegistreReservations']

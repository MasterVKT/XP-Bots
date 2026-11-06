"""Couche 1c de moteur-london — bougie_cassure : prédicats exacts S02.3.

Interface publique figée ; contrat : mcl/moteur-london/contrats/couche-1c.md.
"""
from ._impl import evaluer_cassure

__all__ = ['evaluer_cassure']

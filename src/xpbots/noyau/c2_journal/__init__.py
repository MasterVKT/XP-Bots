"""Couche 2 du noyau — `journal` (enveloppe) : enregistrements C09 et sérialisation canonique.

Interface publique figée ; contrat : mcl/noyau/contrats/couche-2.md.
"""
from xpbots.noyau.c2_journal._impl import (BRAS, CHAMPS_OBLIGATOIRES, MODES, VERSION_SCHEMA, Enregistrement,
                                           Enveloppe, ErreurJournal, TypeEnregistrement, empreintes_regles,
                                           enregistrement, enregistrement_cloture, enregistrement_intention,
                                           serialiser)

__all__ = ['BRAS', 'CHAMPS_OBLIGATOIRES', 'MODES', 'VERSION_SCHEMA', 'Enregistrement', 'Enveloppe', 'ErreurJournal',
           'TypeEnregistrement', 'empreintes_regles', 'enregistrement', 'enregistrement_cloture',
           'enregistrement_intention', 'serialiser']

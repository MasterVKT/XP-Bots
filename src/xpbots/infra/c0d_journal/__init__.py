"""Frontière physique journal ; contrat couche-0d.md."""
from ._impl import JournalFichiers, ecrire_atomique, lire_octets, lire_json, ecrire_json, alerter

__all__ = ('JournalFichiers', 'ecrire_atomique', 'lire_octets', 'lire_json', 'ecrire_json', 'alerter')

"""Instants UTC à la milliseconde avec départage stable des égalités (C03 point 1)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# Seules conversions d'unités du projet : toute autre valeur temporelle vient de config/.
MS_PAR_SECONDE = 1000
MICROSECONDES_PAR_MS = 1000

_EPOQUE = datetime(1970, 1, 1, tzinfo=timezone.utc)
_UNE_MS = timedelta(milliseconds=1)
_FORMAT_ISO = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z')


class InstantInvalide(ValueError):
    """Horodatage non entier, séquence négative ou texte hors du format UTC exigé."""


def _entier(valeur, nom):
    # bool est un sous-type d'int : il est refusé explicitement.
    if type(valeur) is not int:
        raise InstantInvalide(f'{nom} doit être un entier, reçu {type(valeur).__name__}')
    return valeur


@dataclass(frozen=True, order=True)
class Instant:
    """Instant UTC en millisecondes depuis l'époque Unix, départagé par une séquence stable.

    L'ordre naturel est (ms, sequence) : deux événements de la même milliseconde conservent leur ordre
    d'origine.
    """

    ms: int
    sequence: int = 0

    def __post_init__(self):
        _entier(self.ms, 'ms')
        _entier(self.sequence, 'sequence')
        if self.sequence < 0:
            raise InstantInvalide('la séquence doit être positive ou nulle')

    def iso(self) -> str:
        return iso_depuis_ms(self.ms)


def iso_depuis_ms(ms: int) -> str:
    """Texte UTC `AAAA-MM-JJTHH:MM:SS.mmmZ` d'un instant en millisecondes, par arithmétique entière."""
    _entier(ms, 'ms')
    moment = _EPOQUE + timedelta(milliseconds=ms)
    return moment.strftime('%Y-%m-%dT%H:%M:%S.') + f'{moment.microsecond // MICROSECONDES_PAR_MS:03d}Z'


def ms_depuis_iso(texte: str) -> int:
    """Millisecondes UTC d'un texte au format exact `AAAA-MM-JJTHH:MM:SS.mmmZ` (aucun autre format admis)."""
    if type(texte) is not str or not _FORMAT_ISO.fullmatch(texte):
        raise InstantInvalide(f'format attendu AAAA-MM-JJTHH:MM:SS.mmmZ, reçu {texte!r}')
    try:
        moment = datetime.strptime(texte, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
    except ValueError as erreur:
        raise InstantInvalide(f'date invalide : {texte!r}') from erreur
    return (moment - _EPOQUE) // _UNE_MS

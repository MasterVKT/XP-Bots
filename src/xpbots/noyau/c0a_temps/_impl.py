"""Implémentation de la couche 0a (instant). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

_ORIGINE = datetime(1970, 1, 1, tzinfo=timezone.utc)
_UNE_MS = timedelta(milliseconds=1)


class ErreurInstant(ValueError):
    """Instant, durée ou clé d'ordre refusés."""


def _entier(valeur: object, nom: str, minimum: int) -> int:
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        raise ErreurInstant(f'{nom} doit être un entier, reçu {type(valeur).__name__}')
    if valeur < minimum:
        raise ErreurInstant(f'{nom} doit être ≥ {minimum}, reçu {valeur}')
    return valeur


def verifier_instant(valeur: object) -> int:
    return _entier(valeur, 'instant (ms UTC)', 0)


def instant_depuis_datetime(moment: datetime) -> int:
    if not isinstance(moment, datetime):
        raise ErreurInstant('datetime attendu')
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ErreurInstant('datetime sans fuseau refusé')
    if moment.microsecond % 1000:
        raise ErreurInstant('précision inférieure à la milliseconde refusée')
    return verifier_instant((moment - _ORIGINE) // _UNE_MS)


def instant_depuis_iso(texte: str) -> int:
    if not isinstance(texte, str):
        raise ErreurInstant('texte ISO-8601 attendu')
    try:
        moment = datetime.fromisoformat(texte.replace('Z', '+00:00'))
    except ValueError as erreur:
        raise ErreurInstant(f'texte ISO-8601 illisible : {texte!r}') from erreur
    if moment.tzinfo is None or moment.utcoffset() != timedelta(0):
        raise ErreurInstant(f'décalage UTC nul exigé : {texte!r}')
    return instant_depuis_datetime(moment)


def instant_vers_datetime(instant_ms: int) -> datetime:
    return _ORIGINE + verifier_instant(instant_ms) * _UNE_MS


def instant_vers_iso(instant_ms: int) -> str:
    moment = instant_vers_datetime(instant_ms)
    return moment.strftime('%Y-%m-%dT%H:%M:%S.') + f'{moment.microsecond // 1000:03d}Z'


def aligner(instant_ms: int, duree_ms: int) -> int:
    instant = verifier_instant(instant_ms)
    duree = _entier(duree_ms, 'durée (ms)', 1)
    return instant - instant % duree


@dataclass(frozen=True, order=True)
class CleEvenement:
    """Clé d'ordre stable d'un événement : instant, puis numéro (de réception ou d'ordre natif)."""

    instant_ms: int
    numero: int

    def __post_init__(self) -> None:
        verifier_instant(self.instant_ms)
        _entier(self.numero, 'numéro', 0)

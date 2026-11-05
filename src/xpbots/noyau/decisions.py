"""Motifs C09, signaux, résultats techniques, clés d'intention, issues et décisions de contrôle."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from enum import IntEnum, StrEnum
from types import MappingProxyType
from typing import Mapping, Union

from xpbots.noyau.json_canonique import serialiser
from xpbots.noyau.temps import iso_depuis_ms


class DecisionInvalide(ValueError):
    """Signal, résultat, issue ou décision qui viole un invariant de couture."""


class MotifRefus(StrEnum):
    """Motifs minimaux de C09, plus AI_CONTEXT_VETO (A07) et ENVIRONMENT_NOT_READY (C04) ; liste fermée."""

    OUTSIDE_SESSION = 'OUTSIDE_SESSION'
    WARMUP = 'WARMUP'
    DATA_GAP = 'DATA_GAP'
    NO_SETUP = 'NO_SETUP'
    STOP_TOO_WIDE = 'STOP_TOO_WIDE'
    FUNDAMENTAL_INVALID = 'FUNDAMENTAL_INVALID'
    FUNDAMENTAL_DIRECTION = 'FUNDAMENTAL_DIRECTION'
    NEWS_WINDOW = 'NEWS_WINDOW'
    SPREAD_CAP = 'SPREAD_CAP'
    ENTRY_GAP = 'ENTRY_GAP'
    SIGNAL_EXPIRED = 'SIGNAL_EXPIRED'
    SYMBOL_BUSY = 'SYMBOL_BUSY'
    DAILY_ENTRY_CAP = 'DAILY_ENTRY_CAP'
    MIN_VOLUME_OR_RISK_REJECT = 'MIN_VOLUME_OR_RISK_REJECT'
    ACCOUNT_RISK_CAP = 'ACCOUNT_RISK_CAP'
    MARGIN_REJECT = 'MARGIN_REJECT'
    UNKNOWN_ORDER_STATE = 'UNKNOWN_ORDER_STATE'
    PROTECTION_ERROR = 'PROTECTION_ERROR'
    DAILY_LOSS_LOCK = 'DAILY_LOSS_LOCK'
    GLOBAL_DRAWDOWN_HALT = 'GLOBAL_DRAWDOWN_HALT'
    AI_CONTEXT_VETO = 'AI_CONTEXT_VETO'
    ENVIRONMENT_NOT_READY = 'ENVIRONMENT_NOT_READY'


MOTIFS_COMPLEMENTAIRES = (MotifRefus.AI_CONTEXT_VETO, MotifRefus.ENVIRONMENT_NOT_READY)
MOTIFS_FONDAMENTAUX = (MotifRefus.FUNDAMENTAL_INVALID, MotifRefus.FUNDAMENTAL_DIRECTION, MotifRefus.NEWS_WINDOW)


class Sens(IntEnum):
    """Sens d'un signal : +1 achat, −1 vente (le « sens » des formules C06 et C07)."""

    ACHAT = 1
    VENTE = -1


def _texte(valeur, nom):
    if type(valeur) is not str or not valeur or valeur != valeur.strip():
        raise DecisionInvalide(f'{nom} doit être un texte non vide sans espace de bord, reçu {valeur!r}')


def _entier(valeur, nom):
    if type(valeur) is not int:
        raise DecisionInvalide(f'{nom} doit être un entier, reçu {type(valeur).__name__}')


def _flottant_fini(valeur, nom):
    if type(valeur) is not float or not math.isfinite(valeur):
        raise DecisionInvalide(f'{nom} doit être un flottant fini, reçu {valeur!r}')


def _decimal_positif(valeur, nom):
    if type(valeur) is not Decimal or not valeur.is_finite() or valeur <= 0:
        raise DecisionInvalide(f'{nom} doit être un Decimal fini strictement positif, reçu {valeur!r}')


def _figer_etat(etat, nom):
    if not isinstance(etat, Mapping):
        raise DecisionInvalide(f'{nom} doit être un dictionnaire')
    return MappingProxyType(dict(etat))


@dataclass(frozen=True)
class Signal:
    """Signal technique d'une méthode à la clôture T d'une M15 ; B_SL est non arrondi, sur l'échelle Bid (C06)."""

    strategie: str
    symbole: str
    cloture_ms: int
    sens: Sens
    cloture_bid: Decimal
    a_t: float
    b_sl: float
    multiple_objectif: float
    etat_detecteur: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        _texte(self.strategie, 'strategie')
        _texte(self.symbole, 'symbole')
        _entier(self.cloture_ms, 'cloture_ms')
        if not isinstance(self.sens, Sens):
            raise DecisionInvalide('sens doit être un Sens')
        _decimal_positif(self.cloture_bid, 'cloture_bid')
        _flottant_fini(self.a_t, 'a_t')
        _flottant_fini(self.b_sl, 'b_sl')
        _flottant_fini(self.multiple_objectif, 'multiple_objectif')
        if self.a_t <= 0:
            raise DecisionInvalide('A_t doit être strictement positif (C03 point 11)')
        if self.multiple_objectif <= 0:
            raise DecisionInvalide('le multiple d\'objectif doit être strictement positif')
        if not self.sens * (float(self.cloture_bid) - self.b_sl) > 0:
            raise DecisionInvalide('B_SL doit être du côté protecteur : 0 < sens × (C − B_SL) (C06)')
        object.__setattr__(self, 'etat_detecteur', _figer_etat(self.etat_detecteur, 'etat_detecteur'))


@dataclass(frozen=True)
class ResultatTechnique:
    """Résultat d'une méthode à une clôture : exactement un signal ou un motif technique."""

    signal: Signal | None
    motif: MotifRefus | None
    etat_detecteur: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        if (self.signal is None) == (self.motif is None):
            raise DecisionInvalide('un résultat technique porte exactement un signal ou un motif')
        if self.signal is not None and type(self.signal) is not Signal:
            raise DecisionInvalide('signal doit être un Signal')
        if self.motif is not None and not isinstance(self.motif, MotifRefus):
            raise DecisionInvalide('motif doit être un MotifRefus')
        object.__setattr__(self, 'etat_detecteur', _figer_etat(self.etat_detecteur, 'etat_detecteur'))


@dataclass(frozen=True)
class CleIntention:
    """Clé persistante d'intention `(deployment_id, strategy_id, symbole, cloture_M15_UTC, sens)` (C08)."""

    deployment_id: str
    strategie: str
    symbole: str
    cloture_ms: int
    sens: Sens

    def __post_init__(self):
        _texte(self.deployment_id, 'deployment_id')
        _texte(self.strategie, 'strategie')
        _texte(self.symbole, 'symbole')
        _entier(self.cloture_ms, 'cloture_ms')
        if not isinstance(self.sens, Sens):
            raise DecisionInvalide('sens doit être un Sens')

    @classmethod
    def du_signal(cls, deployment_id: str, signal: Signal) -> CleIntention:
        return cls(deployment_id, signal.strategie, signal.symbole, signal.cloture_ms, signal.sens)

    def en_json(self) -> dict:
        return {'deployment_id': self.deployment_id, 'strategie': self.strategie, 'symbole': self.symbole,
                'cloture_utc': iso_depuis_ms(self.cloture_ms), 'sens': int(self.sens)}

    def texte(self) -> str:
        """Forme canonique stable de la clé (journal, idempotence)."""
        return serialiser(self.en_json())


@dataclass(frozen=True)
class Rempli:
    """Issue d'un signal rempli, même partiellement : volume réellement exécuté et prix moyen (C08)."""

    volume: Decimal
    prix_moyen: Decimal
    instant_ms: int

    def __post_init__(self):
        _decimal_positif(self.volume, 'volume')
        _decimal_positif(self.prix_moyen, 'prix_moyen')
        _entier(self.instant_ms, 'instant_ms')


@dataclass(frozen=True)
class Refuse:
    """Issue d'un signal refusé définitivement, avec son motif C09."""

    motif: MotifRefus
    instant_ms: int

    def __post_init__(self):
        if not isinstance(self.motif, MotifRefus):
            raise DecisionInvalide('motif doit être un MotifRefus')
        _entier(self.instant_ms, 'instant_ms')


IssueSignal = Union[Rempli, Refuse]


@dataclass(frozen=True)
class DecisionFondamentale:
    """Résultat du contrôle C05 : autorisation, ou refus FUNDAMENTAL_INVALID, FUNDAMENTAL_DIRECTION, NEWS_WINDOW.

    `permission` est le message réellement connu (ou l'injection d'un scénario nommé), recopié au journal C09.
    """

    autorise: bool
    motif: MotifRefus | None
    permission: Mapping[str, object] | None = None
    scenario: str | None = None

    def __post_init__(self):
        if type(self.autorise) is not bool:
            raise DecisionInvalide('autorise doit être un booléen')
        if self.autorise != (self.motif is None):
            raise DecisionInvalide('une autorisation n\'a pas de motif ; un refus en a un')
        if self.motif is not None and self.motif not in MOTIFS_FONDAMENTAUX:
            raise DecisionInvalide(f'motif fondamental inattendu : {self.motif}')
        if self.permission is not None:
            object.__setattr__(self, 'permission', _figer_etat(self.permission, 'permission'))
        if self.scenario is not None:
            _texte(self.scenario, 'scenario')


class EtatContexteIA(StrEnum):
    """Contexte IA : BLOCK ajoute un refus, NEUTRAL n'ajoute rien ; il n'existe aucun état ALLOW (A12)."""

    BLOCK = 'BLOCK'
    NEUTRAL = 'NEUTRAL'


@dataclass(frozen=True)
class DecisionContexteIA:
    """Décision du complément IA pour un symbole et un instant, avec la référence du snapshot et des preuves."""

    etat: EtatContexteIA
    sequence_snapshot: int | None = None
    evenements: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.etat, EtatContexteIA):
            raise DecisionInvalide('etat doit être un EtatContexteIA')
        if self.sequence_snapshot is not None:
            _entier(self.sequence_snapshot, 'sequence_snapshot')
        if type(self.evenements) is not tuple or any(type(e) is not str for e in self.evenements):
            raise DecisionInvalide('evenements doit être un tuple de textes')

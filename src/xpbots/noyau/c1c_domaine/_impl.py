"""Implémentation de la couche 1c (domaine). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import math
import re
from types import MappingProxyType
from typing import Any, Mapping

from xpbots.noyau.c0a_temps import ErreurInstant, verifier_instant


class ErreurDomaine(ValueError):
    """Valeur ou combinaison du domaine refusée."""


class Sens(StrEnum):
    ACHAT = 'ACHAT'
    VENTE = 'VENTE'

    @property
    def signe(self) -> int:
        return 1 if self is Sens.ACHAT else -1

    def oppose(self) -> 'Sens':
        return Sens.VENTE if self is Sens.ACHAT else Sens.ACHAT


class Motif(StrEnum):
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
    ENVIRONMENT_NOT_READY = 'ENVIRONMENT_NOT_READY'
    AI_CONTEXT_VETO = 'AI_CONTEXT_VETO'


VERSION_DETAILS = '1'
_RANGE = frozenset({'RANGE_INCOMPLET', 'RANGE_BOUGIE_INVALIDE'})
DETAILS_ENUMERES: Mapping[Motif, frozenset[str]] = MappingProxyType({
    Motif.OUTSIDE_SESSION: frozenset({'HORS_FENETRE', 'JOUR_INACTIF'}),
    Motif.WARMUP: frozenset({'M15_INSUFFISANTES', 'ATR_M15_INDISPONIBLE', 'ATR_H1_INDISPONIBLE'}),
    Motif.DATA_GAP: frozenset({'TROU_ACTIF', 'ATTENTE_RECALCUL'}) | _RANGE,
    Motif.NO_SETUP: frozenset({'ATR_NON_POSITIF', 'RANGE_HORS_BORNES', 'GEL_ATR_H1_POSTERIEUR', 'PAS_DE_CASSURE',
                               'BOUGIE_PLATE', 'CORPS_INSUFFISANT', 'CLOTURE_ELOIGNEE', 'TR_EXCESSIF',
                               'SEGMENT_MINIMAL_S3'}) | _RANGE,
    Motif.STOP_TOO_WIDE: frozenset(),
    Motif.FUNDAMENTAL_INVALID: frozenset({'ABSENTE', 'PERIMEE', 'INVALIDE', 'INTERRUPTION'}),
    Motif.FUNDAMENTAL_DIRECTION: frozenset({'LONG_ONLY', 'SHORT_ONLY', 'RISK_STATE_NO_NEW', 'RISK_STATE_FLATTEN'}),
    Motif.NEWS_WINDOW: frozenset({'ANNONCE_HIGH', 'CALENDRIER_PERIME', 'COUVERTURE_INSUFFISANTE'}),
    Motif.SPREAD_CAP: frozenset(),
    Motif.ENTRY_GAP: frozenset(),
    Motif.SIGNAL_EXPIRED: frozenset({'SPREAD_CAP', 'ENTRY_GAP', 'COTATION_INVALIDE', 'AUCUNE_COTATION'}),
    Motif.SYMBOL_BUSY: frozenset({'POSITION_METHODE', 'POSITION_AUTRE_METHODE', 'ETAT_ORDRE_INCONNU',
                                  'CLOTURE_EN_ATTENTE', 'VERROU_PROPRIETE'}),
    Motif.DAILY_ENTRY_CAP: frozenset({'SENS_DEJA_REMPLI', 'MAXIMUM_JOURNALIER'}),
    Motif.MIN_VOLUME_OR_RISK_REJECT: frozenset(),
    Motif.ACCOUNT_RISK_CAP: frozenset({'RESERVE_TOTALE', 'NOMBRE_POSITIONS', 'POSITIONS_EXTERNES'}),
    Motif.MARGIN_REJECT: frozenset({'MARGE_TIERS', 'CONTROLE_NATIF'}),
    Motif.UNKNOWN_ORDER_STATE: frozenset(),
    Motif.PROTECTION_ERROR: frozenset({'CONTRAINTE_NATIVE_AVANT_ORDRE', 'SL_ABSENT', 'TP_NON_RETABLI', 'TP_DEPASSE'}),
    Motif.DAILY_LOSS_LOCK: frozenset(),
    Motif.GLOBAL_DRAWDOWN_HALT: frozenset(),
})
_DETAIL_LIBRE = {Motif.ENVIRONMENT_NOT_READY: re.compile(r'[A-Za-z][A-Za-z0-9_.]*'),
                 Motif.AI_CONTEXT_VETO: re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]*')}
MOTIFS_A_DETAIL_LIBRE = frozenset(_DETAIL_LIBRE)


def _enum(type_: type, valeur: object, nom: str):
    try:
        return type_(valeur)
    except ValueError as erreur:
        raise ErreurDomaine(f'{nom} inconnu : {valeur!r}') from erreur


def verifier_motif(motif: object, detail: object) -> tuple[Motif, str | None]:
    code = _enum(Motif, motif, 'motif')
    if code in _DETAIL_LIBRE:
        if not isinstance(detail, str) or not _DETAIL_LIBRE[code].fullmatch(detail):
            raise ErreurDomaine(f'{code} : détail identifiant obligatoire')
        return code, detail
    admis = DETAILS_ENUMERES[code]
    if not admis:
        if detail is not None:
            raise ErreurDomaine(f'{code} : aucun détail admis')
        return code, None
    if detail not in admis:
        raise ErreurDomaine(f'{code} : détail {detail!r} hors de la version {VERSION_DETAILS}')
    return code, detail


def _texte(valeur: object, nom: str) -> None:
    if not isinstance(valeur, str) or not valeur:
        raise ErreurDomaine(f'{nom} : texte non vide attendu')


def _instant(valeur: object, nom: str) -> None:
    try:
        verifier_instant(valeur)
    except ErreurInstant as erreur:
        raise ErreurDomaine(f'{nom} : {erreur}') from erreur


def _flottant(valeur: object, nom: str) -> float:
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur):
        raise ErreurDomaine(f'{nom} : nombre fini attendu')
    return float(valeur)


def _geler(valeur: Any, chemin: str = 'contexte') -> Any:
    if isinstance(valeur, Mapping):
        if not all(isinstance(cle, str) for cle in valeur):
            raise ErreurDomaine(f'{chemin} : clés textuelles attendues')
        return MappingProxyType({cle: _geler(v, f'{chemin}.{cle}') for cle, v in valeur.items()})
    if isinstance(valeur, (list, tuple)):
        return tuple(_geler(v, chemin) for v in valeur)
    if valeur is None or isinstance(valeur, (str, bool, int)):
        return valeur
    if isinstance(valeur, float) and math.isfinite(valeur):
        return valeur
    raise ErreurDomaine(f'{chemin} : valeur non représentable en JSON {valeur!r}')


@dataclass(frozen=True)
class CleIntention:
    deploiement: str
    strategie: str
    symbole: str
    cloture_ms: int
    sens: Sens

    def __post_init__(self) -> None:
        for nom in ('deploiement', 'strategie', 'symbole'):
            _texte(getattr(self, nom), nom)
            if '|' in getattr(self, nom):
                raise ErreurDomaine(f'{nom} : caractère « | » interdit')
        _instant(self.cloture_ms, 'cloture_ms')
        object.__setattr__(self, 'sens', _enum(Sens, self.sens, 'sens'))

    def texte(self) -> str:
        return f'{self.deploiement}|{self.strategie}|{self.symbole}|{self.cloture_ms}|{self.sens}'

    def empreinte(self, longueur: int) -> str:
        if isinstance(longueur, bool) or not isinstance(longueur, int) or not 1 <= longueur <= 64:
            raise ErreurDomaine('longueur d\'empreinte de 1 à 64 attendue')
        return hashlib.sha256(self.texte().encode('utf-8')).hexdigest()[:longueur]


@dataclass(frozen=True)
class SignalTechnique:
    strategie: str
    symbole: str
    cloture_ms: int
    sens: Sens
    cloture_prix: float
    atr_reference: float
    stop_technique: float
    multiple_objectif: float
    contexte: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _texte(self.strategie, 'strategie')
        _texte(self.symbole, 'symbole')
        _instant(self.cloture_ms, 'cloture_ms')
        object.__setattr__(self, 'sens', _enum(Sens, self.sens, 'sens'))
        for nom in ('cloture_prix', 'atr_reference', 'stop_technique', 'multiple_objectif'):
            object.__setattr__(self, nom, _flottant(getattr(self, nom), nom))
        if self.atr_reference <= 0 or self.multiple_objectif <= 0:
            raise ErreurDomaine('atr_reference et multiple_objectif doivent être strictement positifs')
        if self.sens.signe * (self.cloture_prix - self.stop_technique) <= 0:
            raise ErreurDomaine('stop technique du mauvais côté de la clôture')
        object.__setattr__(self, 'contexte', _geler(self.contexte))


@dataclass(frozen=True)
class AbsenceDeSignal:
    strategie: str
    symbole: str
    cloture_ms: int
    motif: Motif
    detail: str | None = None
    contexte: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _texte(self.strategie, 'strategie')
        _texte(self.symbole, 'symbole')
        _instant(self.cloture_ms, 'cloture_ms')
        motif, detail = verifier_motif(self.motif, self.detail)
        object.__setattr__(self, 'motif', motif)
        object.__setattr__(self, 'detail', detail)
        object.__setattr__(self, 'contexte', _geler(self.contexte))


ResultatTechnique = SignalTechnique | AbsenceDeSignal


class NatureIssue(StrEnum):
    REMPLIE = 'REMPLIE'
    REFUSEE = 'REFUSEE'
    EXPIREE = 'EXPIREE'
    CLOTUREE = 'CLOTUREE'


class CauseCloture(StrEnum):
    STOP_LOSS = 'STOP_LOSS'
    TAKE_PROFIT = 'TAKE_PROFIT'
    GARDE_QUOTIDIENNE = 'GARDE_QUOTIDIENNE'
    ARRET_GLOBAL = 'ARRET_GLOBAL'
    FLATTEN = 'FLATTEN'
    ANNONCE = 'ANNONCE'
    HEURE_SORTIE = 'HEURE_SORTIE'
    DUREE_MAXIMALE = 'DUREE_MAXIMALE'
    FERMETURE_NATIVE = 'FERMETURE_NATIVE'
    BLACKOUT = 'BLACKOUT'
    PROTECTION = 'PROTECTION'
    RISQUE_APRES_REMPLISSAGE = 'RISQUE_APRES_REMPLISSAGE'


@dataclass(frozen=True)
class Issue:
    cle: CleIntention
    nature: NatureIssue
    instant_ms: int
    motif: Motif | None = None
    detail: str | None = None
    cause: CauseCloture | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.cle, CleIntention):
            raise ErreurDomaine('clé d\'intention attendue')
        nature = _enum(NatureIssue, self.nature, 'nature')
        object.__setattr__(self, 'nature', nature)
        _instant(self.instant_ms, 'instant_ms')
        if self.motif is None:
            if self.detail is not None:
                raise ErreurDomaine('un détail exige un motif')
        else:
            motif, detail = verifier_motif(self.motif, self.detail)
            object.__setattr__(self, 'motif', motif)
            object.__setattr__(self, 'detail', detail)
        if self.cause is not None:
            object.__setattr__(self, 'cause', _enum(CauseCloture, self.cause, 'cause'))
        if nature is NatureIssue.REMPLIE and (self.motif is not None or self.cause is not None):
            raise ErreurDomaine('une issue remplie ne porte ni motif ni cause')
        if nature is NatureIssue.REFUSEE and (self.motif in (None, Motif.SIGNAL_EXPIRED) or self.cause is not None):
            raise ErreurDomaine('un refus porte un motif autre que SIGNAL_EXPIRED et aucune cause')
        if nature is NatureIssue.EXPIREE and (self.motif is not Motif.SIGNAL_EXPIRED or self.cause is not None):
            raise ErreurDomaine('une expiration porte le motif SIGNAL_EXPIRED et aucune cause')
        if nature is NatureIssue.CLOTUREE and self.cause is None:
            raise ErreurDomaine('une clôture porte une cause')


_MOTIFS_FONDAMENTAUX = frozenset({Motif.FUNDAMENTAL_INVALID, Motif.FUNDAMENTAL_DIRECTION, Motif.NEWS_WINDOW})


@dataclass(frozen=True)
class DecisionFondamentale:
    admise: bool
    motif: Motif | None = None
    detail: str | None = None
    cloture_obligatoire: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.admise, bool) or not isinstance(self.cloture_obligatoire, bool):
            raise ErreurDomaine('admise et cloture_obligatoire sont des booléens')
        if self.admise:
            if self.motif is not None or self.detail is not None or self.cloture_obligatoire:
                raise ErreurDomaine('une décision admise ne porte ni motif ni clôture')
            return
        motif, detail = verifier_motif(self.motif, self.detail)
        if motif not in _MOTIFS_FONDAMENTAUX:
            raise ErreurDomaine(f'motif fondamental attendu, reçu {motif}')
        object.__setattr__(self, 'motif', motif)
        object.__setattr__(self, 'detail', detail)


class ContexteIA(StrEnum):
    BLOCK = 'BLOCK'
    NEUTRAL = 'NEUTRAL'


@dataclass(frozen=True)
class DecisionContexteIA:
    etat: ContexteIA
    evenement: str | None = None

    def __post_init__(self) -> None:
        etat = _enum(ContexteIA, self.etat, 'état du contexte IA')
        object.__setattr__(self, 'etat', etat)
        if etat is ContexteIA.BLOCK:
            verifier_motif(Motif.AI_CONTEXT_VETO, self.evenement)
        elif self.evenement is not None:
            raise ErreurDomaine('un contexte neutre ne porte pas d\'événement')

    def motif_et_detail(self) -> tuple[Motif, str] | None:
        if self.etat is ContexteIA.BLOCK:
            return Motif.AI_CONTEXT_VETO, self.evenement
        return None

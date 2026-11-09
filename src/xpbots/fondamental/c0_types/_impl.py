"""Valeurs C05 et décodage JSON strict partagé ; les décisions restent aux couches suivantes."""
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import json
import re
from types import MappingProxyType

from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.noyau.c1b_instrument import Intervalle


class ErreurFondamental(ValueError):
    """Donnée ou état du contrôle fondamental refusé."""


def instant(valeur):
    try:
        return verifier_instant(valeur)
    except ValueError as erreur:
        raise ErreurFondamental('instant UTC invalide') from erreur


def entier(valeur, minimum=0):
    if type(valeur) is not int or valeur < minimum:
        raise ErreurFondamental('entier hors contrat')
    return valeur


def texte(valeur):
    if type(valeur) is not str or not valeur.strip():
        raise ErreurFondamental('texte non vide requis')
    try:
        valeur.encode('utf-8')
    except UnicodeEncodeError as erreur:
        raise ErreurFondamental('texte UTF-8 requis') from erreur
    return valeur


def millisecondes(secondes):
    entier(secondes)
    try:
        return timedelta(seconds=secondes) // timedelta(milliseconds=1)
    except OverflowError as erreur:
        raise ErreurFondamental('durée hors représentation') from erreur


def decoder_json_strict(octets):
    if type(octets) is not bytes:
        raise ErreurFondamental('octets UTF-8 requis')

    def objet(paires):
        resultat = {}
        for cle, valeur in paires:
            if cle in resultat:
                raise ErreurFondamental('clé JSON répétée')
            resultat[cle] = valeur
        return resultat

    def constante(_):
        raise ErreurFondamental('constante JSON non finie')

    try:
        resultat = json.loads(octets.decode('utf-8'), object_pairs_hook=objet,
                              parse_float=Decimal, parse_constant=constante)
    except (ValueError, UnicodeError, RecursionError, InvalidOperation) as erreur:
        raise ErreurFondamental('objet JSON UTF-8 strict requis') from erreur
    if type(resultat) is not dict:
        raise ErreurFondamental('objet JSON racine requis')
    return resultat


class DirectionFondamentale(StrEnum):
    ANY = 'ANY'
    LONG_ONLY = 'LONG_ONLY'
    SHORT_ONLY = 'SHORT_ONLY'


class EtatRisque(StrEnum):
    ALLOW = 'ALLOW'
    NO_NEW = 'NO_NEW'
    FLATTEN = 'FLATTEN'


# C05 : l'or ne dépend que de USD ; les symboles ne sont pas découpés en devises supposées.
_DEVISES = MappingProxyType({'EURUSD': ('EUR', 'USD'), 'GBPUSD': ('GBP', 'USD'), 'XAUUSD': ('USD',)})


def devises_pour(symbole):
    try:
        return _DEVISES[symbole]
    except (KeyError, TypeError) as erreur:
        raise ErreurFondamental('symbole hors table C05') from erreur


@dataclass(frozen=True)
class MessagePermission:
    symbole: str
    sequence: int
    issued_at_ms: int
    known_at_ms: int
    valid_from_ms: int
    valid_until_ms: int
    direction: DirectionFondamentale
    risk_state: EtatRisque
    model_version: str
    input_snapshot_id: str

    def __post_init__(self):
        devises_pour(self.symbole)
        entier(self.sequence, 1)
        for v in (self.issued_at_ms, self.known_at_ms, self.valid_from_ms, self.valid_until_ms):
            instant(v)
        try:
            object.__setattr__(self, 'direction', DirectionFondamentale(self.direction))
            object.__setattr__(self, 'risk_state', EtatRisque(self.risk_state))
        except (ValueError, TypeError) as erreur:
            raise ErreurFondamental('énumération de permission inconnue') from erreur
        texte(self.model_version)
        texte(self.input_snapshot_id)


@dataclass(frozen=True)
class TableImportance:
    fournisseur: str
    version: str
    hautes: frozenset[str]

    def __post_init__(self):
        texte(self.fournisseur)
        texte(self.version)
        if not isinstance(self.hautes, (tuple, list, set, frozenset)) or not self.hautes:
            raise ErreurFondamental('classification haute explicite requise')
        for v in self.hautes:
            texte(v)
        object.__setattr__(self, 'hautes', frozenset(self.hautes))


@dataclass(frozen=True)
class Annonce:
    id_valeur: int
    id_evenement: int
    code: str
    nom: str
    devise: str
    importance: str
    type: str
    secteur: str
    heure_serveur: str
    instant_ms: int
    revision: int
    known_at_ms: int

    def __post_init__(self):
        entier(self.id_valeur, 1)
        entier(self.id_evenement, 1)
        entier(self.revision)
        for v in (self.code, self.nom, self.devise, self.importance, self.type, self.secteur, self.heure_serveur):
            texte(v)
        if re.fullmatch('[A-Z]{3}', self.devise) is None:
            raise ErreurFondamental('devise native invalide')
        instant(self.instant_ms)
        instant(self.known_at_ms)


@dataclass(frozen=True)
class VersionCalendrier:
    version: int
    export_ms: int
    reception_ms: int
    couverture: Intervalle
    annonces: tuple[Annonce, ...]
    table: TableImportance
    empreinte: str

    def __post_init__(self):
        entier(self.version, 1)
        instant(self.export_ms)
        instant(self.reception_ms)
        if self.reception_ms < self.export_ms:
            raise ErreurFondamental('export futur')
        if not isinstance(self.couverture, Intervalle) or not isinstance(self.table, TableImportance):
            raise ErreurFondamental('couverture et table réelles requises')
        annonces = tuple(self.annonces)
        if any(not isinstance(a, Annonce) for a in annonces):
            raise ErreurFondamental('annonces réelles requises')
        if len({a.id_valeur for a in annonces}) != len(annonces):
            raise ErreurFondamental('id_valeur répété dans le calendrier')
        if any(a.known_at_ms > self.reception_ms for a in annonces):
            raise ErreurFondamental('annonce connue après réception')
        if type(self.empreinte) is not str or re.fullmatch('[0-9a-f]{64}', self.empreinte) is None:
            raise ErreurFondamental('empreinte SHA-256 requise')
        object.__setattr__(self, 'annonces', annonces)

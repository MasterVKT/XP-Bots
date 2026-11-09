"""Valeurs A10 ; aucune permission, horloge ou source d'IPC implicite."""
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import json
import re

from xpbots.noyau.c0a_temps import instant_depuis_iso, verifier_instant
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1c_domaine import Motif, verifier_motif

RAISON_VETO = 'OFFICIAL_UNSCHEDULED_POLICY'
SCHEMA_SNAPSHOT = 'xp-ai-context-v1'


class ErreurContexte(ValueError):
    """Donnée ou état du lecteur IA hors contrat."""


def entier(v, minimum=0):
    if type(v) is not int or v < minimum:
        raise ErreurContexte('entier hors contrat')
    return v


def instant(v):
    try:return verifier_instant(v)
    except ValueError as e:raise ErreurContexte('instant UTC invalide') from e


def texte(v):
    if type(v) is not str or not v.strip():raise ErreurContexte('texte non vide requis')
    try:v.encode('utf-8')
    except UnicodeError as e:raise ErreurContexte('texte UTF-8 requis') from e
    return v


def sha256_hex(v):
    if type(v) is not str or re.fullmatch('[0-9a-f]{64}',v) is None:
        raise ErreurContexte('SHA-256 hexadécimal requis')
    return v


def utc(v):
    texte(v)
    try:return instant_depuis_iso(v)
    except ValueError as e:raise ErreurContexte('ISO UTC en millisecondes requis') from e


def en_ms(secondes):
    entier(secondes)
    try:return timedelta(seconds=secondes)//timedelta(milliseconds=1)
    except OverflowError as e:raise ErreurContexte('durée hors représentation') from e


def canonique(objet):
    try:
        return json.dumps(objet,ensure_ascii=False,sort_keys=True,separators=(',',':'),
            allow_nan=False).encode('utf-8')
    except (ValueError,TypeError,UnicodeError,OverflowError,RecursionError) as e:
        raise ErreurContexte('JSON canonique non représentable') from e


def empreinte(objet):return hashlib.sha256(canonique(objet)).hexdigest()


def decoder_objet(octets):
    if type(octets) is not bytes:raise ErreurContexte('octets UTF-8 requis')
    def objet(paires):
        r={}
        for cle,valeur in paires:
            if cle in r:raise ErreurContexte('clé JSON répétée')
            r[cle]=valeur
        return r
    def constante(_):raise ErreurContexte('constante JSON non finie')
    try:
        r=json.loads(octets.decode('utf-8'),object_pairs_hook=objet,parse_constant=constante)
        if type(r) is not dict:raise ErreurContexte('objet JSON racine requis')
        # Détecte aussi un overflow numérique JSON 1e999, que parse_constant ne reçoit pas.
        canonique(r)
        return r
    except (ValueError,TypeError,UnicodeError,OverflowError,RecursionError) as e:
        raise ErreurContexte('objet JSON strict requis') from e


def _collection(v):
    if not isinstance(v,(tuple,list,set,frozenset)):raise ErreurContexte('collection explicite requise')
    return tuple(v)


@dataclass(frozen=True)
class ParametresContexte:
    max_octets: int
    age_max_ms: int
    empreinte_integration: str
    fournisseurs: frozenset[str]
    symboles: tuple[str,...]
    validation_financiere_requise: bool

    def __post_init__(self):
        entier(self.max_octets,1);instant(self.age_max_ms);sha256_hex(self.empreinte_integration)
        fournisseurs=_collection(self.fournisseurs);symboles=_collection(self.symboles)
        for v in fournisseurs+symboles:texte(v)
        if not fournisseurs or not symboles or len(set(symboles))!=len(symboles):
            raise ErreurContexte('fournisseurs et symboles uniques non vides requis')
        if type(self.validation_financiere_requise) is not bool:raise ErreurContexte('politique booléenne requise')
        object.__setattr__(self,'fournisseurs',frozenset(fournisseurs))
        object.__setattr__(self,'symboles',symboles)


def charger_parametres(configuration):
    if not isinstance(configuration,ConfigurationFigee):raise ErreurContexte('configuration chargée requise')
    p=configuration.ia.parametres
    return ParametresContexte(p['snapshot_max_bytes'],en_ms(p['snapshot_max_age_seconds']),
        configuration.ia.empreinte_canonique,frozenset(v['id'] for v in p['providers']),
        configuration.technique.commun.universe_priority,p['live_veto_requires_financial_validation'])


@dataclass(frozen=True)
class PolitiqueVeto:
    bras_ia: bool
    execution_reelle: bool = False
    validation_financiere: bool = False

    def __post_init__(self):
        if any(type(v) is not bool for v in (self.bras_ia,self.execution_reelle,self.validation_financiere)):
            raise ErreurContexte('trois booléens stricts requis')


@dataclass(frozen=True)
class Veto:
    event_id: str
    symboles: tuple[str,...]
    valid_from_ms: int
    valid_until_ms: int
    item_id: str
    provider_id: str
    reason_code: str = RAISON_VETO

    def __post_init__(self):
        texte(self.event_id);texte(self.item_id);texte(self.provider_id)
        try:verifier_motif(Motif.AI_CONTEXT_VETO,self.event_id)
        except ValueError as e:raise ErreurContexte('identifiant non représentable en C09') from e
        if self.reason_code!=RAISON_VETO:raise ErreurContexte('raison de veto inconnue')
        symboles=_collection(self.symboles)
        for s in symboles:texte(s)
        if not symboles or len(set(symboles))!=len(symboles):raise ErreurContexte('symboles distincts requis')
        instant(self.valid_from_ms);instant(self.valid_until_ms)
        if self.valid_until_ms<=self.valid_from_ms:raise ErreurContexte('fenêtre positive requise')
        object.__setattr__(self,'symboles',symboles)


@dataclass(frozen=True)
class SnapshotIA:
    sequence: int
    genere_ms: int
    empreinte_integration: str
    vetos: tuple[Veto,...]
    empreinte_payload: str
    octets: bytes

    def __post_init__(self):
        entier(self.sequence,1);instant(self.genere_ms)
        sha256_hex(self.empreinte_integration);sha256_hex(self.empreinte_payload)
        vetos=_collection(self.vetos)
        if any(not isinstance(v,Veto) for v in vetos):raise ErreurContexte('vetos typés requis')
        if type(self.octets) is not bytes or not self.octets:raise ErreurContexte('octets originaux requis')
        object.__setattr__(self,'vetos',vetos)


@dataclass(frozen=True)
class SnapshotRecu:
    snapshot: SnapshotIA
    reception_ms: int

    def __post_init__(self):
        instant(self.reception_ms)
        if not isinstance(self.snapshot,SnapshotIA) or self.snapshot.genere_ms>self.reception_ms:
            raise ErreurContexte('réception antérieure à la génération')


@dataclass(frozen=True)
class VetoConnu:
    veto: Veto
    connu_ms: int
    preuve: SnapshotRecu

    def __post_init__(self):
        instant(self.connu_ms)
        if (not isinstance(self.veto,Veto) or not isinstance(self.preuve,SnapshotRecu)
                or self.connu_ms!=self.preuve.reception_ms or self.veto not in self.preuve.snapshot.vetos):
            raise ErreurContexte('preuve de connaissance du veto incohérente')

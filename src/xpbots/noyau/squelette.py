"""Segments minimaux S1 (types) et S6 (format du journal) du squelette composite.

Segment minimal du squelette, remplacé en phase 2 par l'artefact `noyau` (temps, nombres, configuration figée,
marché, domaine, journal). Contrat des coutures : mcl/squelette/COUTURES.md. Bibliothèque standard seulement,
aucune entrée-sortie : les octets de la configuration sont fournis par la coquille.

Limites assumées du segment : prix en flottants 64 bits (la politique décimale de C03.12 pour les prix
exécutables arrive avec les phases 2, 5 et 6) ; enregistrement de clôture réduit aux champs du squelette
(l'enveloppe complète du document 08, §7, arrive en phase 2).
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

VERSION_SCHEMA_SQUELETTE = 'squelette-1'
TYPE_CLOTURE = 'CLOTURE'

# Codes de motif de C09 et de C04 (identifiants de la spécification, pas des paramètres).
MOTIF_NO_SETUP = 'NO_SETUP'
MOTIF_ENVIRONMENT_NOT_READY = 'ENVIRONMENT_NOT_READY'
# Détails énumérés propres au squelette (P-07 : champ `detail` versionné).
DETAIL_STRATEGIE_MINIMALE = 'SEGMENT_MINIMAL_S3'
DETAIL_COORDINATEUR_MINIMAL = 'SEGMENT_MINIMAL_S4'

ACHAT = 'ACHAT'
VENTE = 'VENTE'
SENS = (ACHAT, VENTE)


class ErreurDonnees(ValueError):
    """Donnée d'entrée refusée : format, ordre ou valeur invalide."""


@dataclass(frozen=True)
class Tick:
    """Cotation Bid/Ask d'un symbole, instant UTC en millisecondes, numéro d'ordre natif."""

    symbole: str
    symbole_courtier: str
    instant_ms: int
    sequence: int
    bid: float
    ask: float


@dataclass(frozen=True)
class Bougie:
    """Bougie Bid close de l'intervalle [debut_ms, fin_ms)."""

    symbole: str
    debut_ms: int
    fin_ms: int
    ouverture: float
    haut: float
    bas: float
    cloture: float
    nombre_ticks: int


@dataclass(frozen=True)
class ResultatTechnique:
    """Résultat d'une stratégie à la clôture d'une bougie : un sens, ou un motif d'absence de signal."""

    strategie: str
    symbole: str
    cloture_ms: int
    sens: str | None
    motif: str | None
    detail: str | None

    def __post_init__(self) -> None:
        if self.sens is not None and self.sens not in SENS:
            raise ValueError(f'sens inconnu : {self.sens!r}')
        if self.sens is None and not self.motif:
            raise ValueError('un résultat sans signal exige un motif')
        if self.sens is not None and self.motif is not None:
            raise ValueError('un signal ne porte pas de motif de refus')


@dataclass(frozen=True)
class ConfigurationSquelette:
    """Valeurs de la configuration figée dont le squelette a besoin, lues et jamais recopiées."""

    duree_bougie_ms: int
    identifiant_strategie: str


def _objet_sans_doublon(paires: list[tuple[str, Any]]) -> dict[str, Any]:
    resultat: dict[str, Any] = {}
    for cle, valeur in paires:
        if cle in resultat:
            raise ErreurDonnees(f'clé dupliquée dans la configuration : {cle!r}')
        resultat[cle] = valeur
    return resultat


def _refuser_constante(nom: str) -> Any:
    raise ErreurDonnees(f'nombre non fini dans la configuration : {nom}')


def lire_configuration_squelette(octets: bytes) -> ConfigurationSquelette:
    """Lire strictement les octets de `config/parametres_figes_v3.json` (clés uniques, nombres finis).

    Rend `common.timeframe_seconds` (en millisecondes) et `london.strategy_id`. Le contrôle d'empreinte contre
    la preuve de conservation arrive avec le chargeur complet du noyau (phase 2).
    """
    try:
        racine = json.loads(octets.decode('utf-8'), object_pairs_hook=_objet_sans_doublon,
                            parse_constant=_refuser_constante)
    except UnicodeDecodeError as erreur:
        raise ErreurDonnees(f'configuration non UTF-8 : {erreur}') from erreur
    except json.JSONDecodeError as erreur:
        raise ErreurDonnees(f'configuration JSON invalide : {erreur}') from erreur
    try:
        duree = racine['common']['timeframe_seconds']
        identifiant = racine['london']['strategy_id']
    except (KeyError, TypeError) as erreur:
        raise ErreurDonnees(f'clé de configuration absente : {erreur}') from erreur
    if isinstance(duree, bool) or not isinstance(duree, int) or duree <= 0:
        raise ErreurDonnees('common.timeframe_seconds doit être un entier strictement positif')
    if not isinstance(identifiant, str) or not identifiant:
        raise ErreurDonnees('london.strategy_id doit être un texte non vide')
    return ConfigurationSquelette(duree_bougie_ms=duree * 1000, identifiant_strategie=identifiant)


def serialiser_enregistrement(enregistrement: Mapping[str, Any]) -> str:
    """Forme canonique d'un enregistrement : clés triées, sans espace, UTF-8, aucun nombre non fini."""
    try:
        return json.dumps(enregistrement, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                          allow_nan=False)
    except ValueError as erreur:
        raise ErreurDonnees(f'enregistrement non sérialisable : {erreur}') from erreur

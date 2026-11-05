"""JSON strict en lecture et canonique en écriture, empreinte SHA-256 (journal, configuration, snapshot)."""
from __future__ import annotations

import hashlib
import json
import math


class JSONInvalide(ValueError):
    """Texte JSON mal formé, clé dupliquée ou nombre non fini."""


def _sans_doublon(paires):
    resultat = {}
    for cle, valeur in paires:
        if cle in resultat:
            raise JSONInvalide(f'clé JSON dupliquée : {cle!r}')
        resultat[cle] = valeur
    return resultat


def _constante_interdite(nom):
    raise JSONInvalide(f'nombre non fini interdit : {nom}')


def _flottant_fini(texte):
    valeur = float(texte)
    if not math.isfinite(valeur):
        raise JSONInvalide(f'nombre non fini interdit : {texte}')
    return valeur


def charger_strict(donnees: str | bytes):
    """Décoder un JSON en refusant doublons de clés, NaN, Infinity et nombres débordants."""
    if isinstance(donnees, bytes):
        try:
            donnees = donnees.decode('utf-8-sig')
        except UnicodeDecodeError as erreur:
            raise JSONInvalide(f'encodage UTF-8 invalide : {erreur}') from erreur
    if type(donnees) is not str:
        raise JSONInvalide(f'texte ou octets attendus, reçu {type(donnees).__name__}')
    try:
        return json.loads(donnees, object_pairs_hook=_sans_doublon, parse_constant=_constante_interdite,
                          parse_float=_flottant_fini)
    except json.JSONDecodeError as erreur:
        raise JSONInvalide(str(erreur)) from erreur


def serialiser(valeur) -> str:
    """Forme canonique : clés triées, séparateurs sans espace, UTF-8 non échappé, aucun nombre non fini."""
    try:
        return json.dumps(valeur, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError) as erreur:
        raise JSONInvalide(f'valeur non sérialisable en JSON canonique : {erreur}') from erreur


def empreinte(valeur) -> str:
    """SHA-256 hexadécimal de la forme canonique (identique à `reference.llm_contracts.digest`)."""
    return hashlib.sha256(serialiser(valeur).encode('utf-8')).hexdigest()

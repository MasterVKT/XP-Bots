"""Lecture stricte et figée des exports normatifs de `config/` (aucune valeur recopiée dans le code)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from xpbots.noyau.json_canonique import JSONInvalide, charger_strict, empreinte

CHEMIN_BUNDLE_TECHNIQUE = Path('config') / 'parametres_figes_v3.json'
# Racine du dépôt : premier parent qui contient l'export technique figé.
RACINE_PROJET = next((p for p in Path(__file__).resolve().parents if (p / CHEMIN_BUNDLE_TECHNIQUE).is_file()),
                     Path(__file__).resolve().parent)
BLOCS_TECHNIQUES = ('common', 'ema', 'london')


class ConfigurationInvalide(ValueError):
    """Fichier de configuration illisible, non strict ou de structure inattendue."""


def lire_json_strict(chemin: Path):
    """Lire un fichier JSON en refusant doublons et nombres non finis."""
    chemin = Path(chemin)
    try:
        return charger_strict(chemin.read_bytes())
    except (OSError, JSONInvalide) as erreur:
        raise ConfigurationInvalide(f'{chemin} : {erreur}') from erreur


def figer(valeur):
    """Copie en lecture seule : dictionnaires en `MappingProxyType`, listes en tuples, récursivement."""
    if isinstance(valeur, Mapping):
        return MappingProxyType({cle: figer(element) for cle, element in valeur.items()})
    if isinstance(valeur, (list, tuple)):
        return tuple(figer(element) for element in valeur)
    return valeur


@dataclass(frozen=True)
class BundleTechnique:
    """Bundle technique figé (`common`, `ema`, `london`) et son empreinte canonique pour le journal C09."""

    donnees: Mapping[str, Mapping[str, object]]
    empreinte: str

    def valeur(self, bloc: str, cle: str):
        """Valeur d'une clé d'un bloc ; une clé absente est une configuration invalide, jamais un défaut."""
        try:
            return self.donnees[bloc][cle]
        except KeyError as erreur:
            raise ConfigurationInvalide(f'clé absente du bundle technique : {bloc}.{cle}') from erreur


def charger_bundle_technique(racine: Path | None = None) -> BundleTechnique:
    """Charger `config/parametres_figes_v3.json` tel quel, avec contrôle de ses trois blocs."""
    chemin = Path(racine or RACINE_PROJET) / CHEMIN_BUNDLE_TECHNIQUE
    donnees = lire_json_strict(chemin)
    if type(donnees) is not dict or set(donnees) != set(BLOCS_TECHNIQUES):
        raise ConfigurationInvalide(f'{chemin} : blocs attendus {BLOCS_TECHNIQUES}')
    for bloc in BLOCS_TECHNIQUES:
        if type(donnees[bloc]) is not dict:
            raise ConfigurationInvalide(f'{chemin} : le bloc {bloc} doit être un objet')
    return BundleTechnique(figer(donnees), empreinte(donnees))

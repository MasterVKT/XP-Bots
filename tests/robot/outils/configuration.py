"""Accès des tests aux exports figés : octets réels, configuration chargée, copies modifiées (non-recopie)."""
from __future__ import annotations

import copy
import json
from typing import Callable

from robot.outils.chemins import CONFIGURATION_IA, CONFIGURATION_TECHNIQUE, PREUVE_CONSERVATION


def octets_exports() -> tuple[bytes, bytes, bytes]:
    """Octets de l'export technique, de l'export IA et de la preuve de conservation du dépôt."""
    return CONFIGURATION_TECHNIQUE.read_bytes(), CONFIGURATION_IA.read_bytes(), PREUVE_CONSERVATION.read_bytes()


def json_technique() -> dict:
    return json.loads(CONFIGURATION_TECHNIQUE.read_text(encoding='utf-8'))


def json_ia() -> dict:
    return json.loads(CONFIGURATION_IA.read_text(encoding='utf-8'))


def octets_technique_modifies(modifier: Callable[[dict], None]) -> bytes:
    """Copie de l'export technique modifiée en place par `modifier`, sérialisée en JSON."""
    racine = copy.deepcopy(json_technique())
    modifier(racine)
    return json.dumps(racine, ensure_ascii=False).encode('utf-8')


def octets_ia_modifies(modifier: Callable[[dict], None]) -> bytes:
    racine = copy.deepcopy(json_ia())
    modifier(racine)
    return json.dumps(racine, ensure_ascii=False).encode('utf-8')


def configuration_figee():
    """Configuration du dépôt chargée par le chargeur de production (empreintes contrôlées)."""
    from xpbots.noyau.c0c_configuration import charger_configuration_figee
    return charger_configuration_figee(*octets_exports())

"""Valeurs dérivées des sources normatives pour les tests, jamais recopiées à la main."""
from __future__ import annotations

import json
import re

from robot.outils.chemins import CONFIGURATION_TECHNIQUE, SPECIFICATION_LONDON

# P-07 (plan, §4) : le champ `motif` admet les codes de C09, plus ENVIRONMENT_NOT_READY (C04) et AI_CONTEXT_VETO (A07).
MOTIFS_HORS_C09 = ('ENVIRONMENT_NOT_READY', 'AI_CONTEXT_VETO')


def motifs_c09() -> tuple[str, ...]:
    """Motifs minimaux de C09, lus dans la spécification 02."""
    texte = SPECIFICATION_LONDON.read_text(encoding='utf-8')
    trouve = re.search(r'Motifs minimaux : (.*?)\.\n', texte)
    if not trouve:
        raise AssertionError('liste des motifs minimaux de C09 introuvable dans la spécification')
    return tuple(code.strip() for code in trouve.group(1).split(','))


def motifs_admis() -> frozenset[str]:
    return frozenset(motifs_c09()) | frozenset(MOTIFS_HORS_C09)


def table_des_motifs_document_01() -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    """Lignes du tableau du document 01, §9.3 : (codes de motif cités, détails cités en code)."""
    from robot.outils.chemins import DOCUMENT_ARCHITECTURE
    texte = DOCUMENT_ARCHITECTURE.read_text(encoding='utf-8')
    debut = texte.index('### 9.3 ')
    fin = texte.index('\n## ', debut)
    lignes = []
    for ligne in texte[debut:fin].splitlines():
        cellules = [c.strip() for c in ligne.strip().strip('|').split('|')]
        if not ligne.startswith('|') or len(cellules) < 3 or set(cellules[0]) <= set('-: '):
            continue
        motifs = tuple(re.findall(r'`([A-Z][A-Z0-9_]*)`', cellules[1]))
        details = tuple(re.findall(r'`([A-Z][A-Z0-9_]*)`', cellules[2]))
        if motifs:
            lignes.append((motifs, details))
    return lignes


def configuration_technique() -> dict:
    """Export technique figé, lu tel quel (pour comparer, jamais pour recopier une valeur dans le code)."""
    return json.loads(CONFIGURATION_TECHNIQUE.read_text(encoding='utf-8'))


def octets_configuration_modifiee(**remplacements) -> bytes:
    """Copie de l'export avec des valeurs remplacées, pour prouver qu'aucune valeur n'est codée en dur.

    Clés acceptées : `timeframe_seconds` (bloc common) et `strategy_id` (bloc london).
    """
    configuration = configuration_technique()
    for cle, valeur in remplacements.items():
        bloc = 'london' if cle == 'strategy_id' else 'common'
        configuration[bloc][cle] = valeur
    return json.dumps(configuration).encode('utf-8')

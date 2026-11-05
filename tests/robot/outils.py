"""Aides communes des tests du robot : chemins, lecture de la spécification, fabriques de valeurs valides."""
from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SRC = RACINE / 'src'
SPECIFICATION_EMA = RACINE / 'livrables' / 'strategies_m15' / '01_Triple_EMA_RSI_Repli_M15_Specification_IA.md'
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
FIXTURE_TICKS = FIXTURES / 'squelette_ticks.csv'
FIXTURE_MANIFESTE = FIXTURES / 'squelette_manifeste.json'


def texte_specification() -> str:
    return SPECIFICATION_EMA.read_text(encoding='utf-8')


def motifs_c09_de_la_specification() -> list[str]:
    """Liste « Motifs minimaux » de C09, lue dans le texte normatif."""
    trouve = re.search(r'^Motifs minimaux : (.+)\.$', texte_specification(), re.MULTILINE)
    if trouve is None:
        raise AssertionError('ligne « Motifs minimaux » introuvable dans C09')
    return [m.strip() for m in trouve.group(1).split(',')]


def empreinte_bundle_de_la_specification() -> str:
    trouve = re.search(r'Empreinte du bundle technique V3\.0 des deux conceptions : ([0-9a-f]{64})\.',
                       texte_specification())
    if trouve is None:
        raise AssertionError('empreinte du bundle technique introuvable dans la spécification')
    return trouve.group(1)


def signal_valide(**changements):
    """Signal d'achat cohérent avec l'exemple S01.5 (C = 1,10000, A = 0,00050, B_SL = 1,09945)."""
    from xpbots.noyau.decisions import Sens, Signal
    valeurs = dict(strategie='EMA_V3', symbole='EURUSD', cloture_ms=1793780100000, sens=Sens.ACHAT,
                   cloture_bid=Decimal('1.10000'), a_t=0.0005, b_sl=1.09945, multiple_objectif=1.5,
                   etat_detecteur={'etat': 'PULLBACK_LONG', 'age': 3})
    valeurs.update(changements)
    return Signal(**valeurs)

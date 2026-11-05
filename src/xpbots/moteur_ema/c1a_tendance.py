"""Couche 1a de `moteur-ema` : tendance S01.1 (ordre EMA rapide/moyenne/lente et pente de l'EMA lente).

Contrat : `mcl/moteur-ema/contrats/couche-1a.md`. Inégalités strictes : une égalité ou une pente nulle ne donne
aucune tendance (S01.6, C11.2).
"""
from __future__ import annotations

import math

from xpbots.noyau.decisions import Sens


def _fini(nom, valeur) -> float:
    if type(valeur) not in (int, float) or not math.isfinite(valeur):
        raise ValueError(f'{nom} : nombre fini attendu, reçu {valeur!r}')
    return valeur


def sens_tendance(e_rapide: float, e_moyenne: float, e_lente: float, e_lente_decalee: float) -> Sens | None:
    """ACHAT si rapide > moyenne > lente et lente > lente(t−k) ; VENTE si l'inverse strict ; sinon None."""
    r, m, l, d = (_fini(n, v) for n, v in (('e_rapide', e_rapide), ('e_moyenne', e_moyenne),
                                            ('e_lente', e_lente), ('e_lente_decalee', e_lente_decalee)))
    if r > m > l and l > d:
        return Sens.ACHAT
    if r < m < l and l < d:
        return Sens.VENTE
    return None

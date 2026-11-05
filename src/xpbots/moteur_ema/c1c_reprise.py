"""Couche 1c de `moteur-ema` : bougie de reprise S01.3.

Contrat : `mcl/moteur-ema/contrats/couche-1c.md`. Range R = H − L > 0, TR ≤ plafond × A, clôture au-delà de l'EMA
rapide, corps directionnel (O = C refusé), RSI au seuil du signal, position de la clôture dans le range.
"""
from __future__ import annotations

import math

from xpbots.moteur_ema.c0_parametres import ParametresEMA
from xpbots.noyau.decisions import Sens


def _fini(nom, valeur) -> float:
    if type(valeur) not in (int, float) or not math.isfinite(valeur):
        raise ValueError(f'{nom} : nombre fini attendu, reçu {valeur!r}')
    return valeur


def est_reprise(sens: Sens, o: float, h: float, l: float, c: float, tr: float, e_rapide: float, rsi: float,  # noqa: E741
                a_t: float, p: ParametresEMA) -> bool:
    """Vrai seulement si toutes les conditions S01.3 du sens sont vraies (le repli valide relève de la couche 2)."""
    if type(sens) is not Sens:
        raise ValueError(f'sens attendu (Sens), reçu {sens!r}')
    o, h, l, c, tr, e, r, a = (_fini(n, v) for n, v in (  # noqa: E741
        ('o', o), ('h', h), ('l', l), ('c', c), ('tr', tr), ('e_rapide', e_rapide), ('rsi', rsi), ('a_t', a_t)))
    if not a > 0:
        raise ValueError('A_t doit être strictement positif')
    etendue = h - l
    if etendue <= 0 or tr > p.tr_max_atr * a:
        return False
    if sens is Sens.ACHAT:
        return c > e and c > o and r >= p.rsi_signal_long_min and (c - l) / etendue >= p.position_cloture_min
    return c < e and c < o and r <= p.rsi_signal_court_max and (h - c) / etendue >= p.position_cloture_min

"""Couche 1b de `moteur-ema` : contexte d'armement, validité du repli et contact avec la zone EMA rapide–lente.

Contrat : `mcl/moteur-ema/contrats/couche-1b.md`. Sources : S01.2 points 4 à 6, S01.6, R18. Les seuils viennent de
`ParametresEMA` (couche 0) ; aucune valeur n'est recopiée.
"""
from __future__ import annotations

import math

from xpbots.moteur_ema.c0_parametres import ParametresEMA
from xpbots.noyau.decisions import Sens


def _fini(nom, valeur) -> float:
    if type(valeur) not in (int, float) or not math.isfinite(valeur):
        raise ValueError(f'{nom} : nombre fini attendu, reçu {valeur!r}')
    return valeur


def _sens(sens) -> Sens:
    if type(sens) is not Sens:
        raise ValueError(f'sens attendu (Sens), reçu {sens!r}')
    return sens


def contexte_armement(sens: Sens, cloture: float, e_rapide: float, rsi: float, p: ParametresEMA) -> bool:
    """S01.2 point 4 : achat si C > EMA rapide et RSI ≥ seuil ; vente si C < EMA rapide et RSI ≤ seuil (R18)."""
    c, e, r = _fini('cloture', cloture), _fini('e_rapide', e_rapide), _fini('rsi', rsi)
    if _sens(sens) is Sens.ACHAT:
        return c > e and r >= p.rsi_signal_long_min
    return c < e and r <= p.rsi_signal_court_max


def repli_valide(sens: Sens, cloture: float, e_lente: float, rsi: float, a_t: float, p: ParametresEMA) -> bool:
    """S01.2 point 5 : achat si C ≥ EMA lente − x·A et RSI ≥ min ; vente si C ≤ EMA lente + x·A et RSI ≤ max.

    Seule la clôture compte : une mèche au-delà de l'EMA lente n'annule pas le repli (S01.6).
    """
    c, e, r, a = _fini('cloture', cloture), _fini('e_lente', e_lente), _fini('rsi', rsi), _fini('a_t', a_t)
    if not a > 0:
        raise ValueError('A_t doit être strictement positif')
    if _sens(sens) is Sens.ACHAT:
        return c >= e - p.depassement_ema_lente_atr * a and r >= p.rsi_repli_long_min
    return c <= e + p.depassement_ema_lente_atr * a and r <= p.rsi_repli_court_max


def contact(haut: float, bas: float, e_rapide: float, e_lente: float) -> bool:
    """S01.2 point 6 : [L, H] intersecte [min(EMA rapide, EMA lente), max(EMA rapide, EMA lente)], bornes incluses."""
    h, l, er, el = (_fini(n, v) for n, v in (('haut', haut), ('bas', bas), ('e_rapide', e_rapide),
                                              ('e_lente', e_lente)))
    if l > h:
        raise ValueError('bas > haut')
    return l <= max(er, el) and h >= min(er, el)

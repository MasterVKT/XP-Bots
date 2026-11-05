"""Couche 1d de `moteur-ema` : stop technique B_SL non arrondi sur l'échelle Bid (S01.4, C06).

Contrat : `mcl/moteur-ema/contrats/couche-1d.md`. tampon = max(tick, x·A) ; achat : B_SL = min(bas du repli −
tampon, C − plancher·A) ; vente symétrique ; trop large si sens·(C − B_SL) > plafond·A. L'arrondi au tick et la
conversion en SL exécutable relèvent de C06 (couche d'exécution).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from xpbots.moteur_ema.c0_parametres import ParametresEMA
from xpbots.noyau.decisions import Sens


@dataclass(frozen=True)
class StopTechnique:
    """B_SL non arrondi, tampon structurel, distance technique sens·(C − B_SL) et refus éventuel."""

    b_sl: float
    tampon: float
    distance: float
    trop_large: bool


def _fini(nom, valeur) -> float:
    if type(valeur) not in (int, float) or not math.isfinite(valeur):
        raise ValueError(f'{nom} : nombre fini attendu, reçu {valeur!r}')
    return valeur


def stop_technique(sens: Sens, cloture: float, extreme_repli: float, a_t: float, tick_size: Decimal,
                   p: ParametresEMA) -> StopTechnique:
    """Stop structurel de S01.4 ; `extreme_repli` est le plus bas (achat) ou le plus haut (vente) du repli, signal
    compris."""
    if type(sens) is not Sens:
        raise ValueError(f'sens attendu (Sens), reçu {sens!r}')
    c, x, a = _fini('cloture', cloture), _fini('extreme_repli', extreme_repli), _fini('a_t', a_t)
    if not a > 0:
        raise ValueError('A_t doit être strictement positif')
    if type(tick_size) is not Decimal or not tick_size.is_finite() or not tick_size > 0:
        raise ValueError(f'tick_size : décimal fini strictement positif attendu, reçu {tick_size!r}')
    tampon = max(float(tick_size), p.tampon_structurel_atr * a)
    if sens is Sens.ACHAT:
        b_sl = min(x - tampon, c - p.stop_min_atr * a)
    else:
        b_sl = max(x + tampon, c + p.stop_min_atr * a)
    distance = int(sens) * (c - b_sl)
    return StopTechnique(b_sl, tampon, distance, distance > p.stop_max_atr * a)

"""Outils partagés des tests de `moteur-ema` : paramètres réels et recherche de cas d'égalité flottante exacte."""
import math

from xpbots.moteur_ema.c0_parametres import charger_parametres_ema
from xpbots.noyau.config import charger_bundle_technique

BUNDLE = charger_bundle_technique()
P = charger_parametres_ema(BUNDLE)


def juste_en_dessous(x):
    return math.nextafter(x, -math.inf)


def juste_au_dessus(x):
    return math.nextafter(x, math.inf)


def fraction_exacte(fraction, vente=False, bas=1.09900, pas=1e-5, essais=20000):
    """(bas, haut, clôture) flottants où la position de clôture (achat : (C − L)/R ; vente : (H − C)/R) vaut
    exactement `fraction`."""
    for i in range(1, essais):
        haut = bas + i * pas
        centre = haut - fraction * (haut - bas) if vente else bas + fraction * (haut - bas)
        for c in (centre, juste_au_dessus(centre), juste_en_dessous(centre)):
            if ((haut - c) if vente else (c - bas)) / (haut - bas) == fraction:
                return bas, haut, c
    raise AssertionError('aucun cas exact trouvé')

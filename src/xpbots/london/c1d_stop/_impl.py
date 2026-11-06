"""Implémentation de la couche 1d (stop_local). Révisable à comportement constant sous harnais complet."""
from decimal import Decimal

from xpbots.donnees.c0a_types import BougieEnrichie, UniteTemps
from xpbots.london.c0a_parametres import ParametresLondon
from xpbots.london.c0b_types import ErreurLondon, RangeLondon, RefusLondon, StopLocal, tick_flottant, verifier_bougie
from xpbots.noyau.c1c_domaine import Motif, Sens


def calculer_stop(bougie: BougieEnrichie, range_: RangeLondon, sens: Sens, tick_size: Decimal,
                  parametres: ParametresLondon) -> StopLocal | RefusLondon:
    if not isinstance(parametres, ParametresLondon) or not isinstance(range_, RangeLondon) or not isinstance(sens, Sens):
        raise ErreurLondon('paramètres, range et sens London attendus')
    verifier_bougie(bougie, UniteTemps.M15, parametres.commun.timeframe_seconds * 1000)
    if bougie.jour_londres != range_.jour:
        raise ErreurLondon('range d’un autre jour')
    tick = tick_flottant(tick_size)
    b, i = bougie.bougie, bougie.indicateurs
    if not b.valide or i.a is None or i.a <= 0:
        raise ErreurLondon('bougie valide et A strictement positif attendus')
    a = i.a
    guard = max(tick, parametres.commun.structural_buffer_atr * a)
    if sens is Sens.ACHAT:
        composantes = (b.bas - guard, range_.haut - parametres.boundary_stop_inside_atr * a,
                       b.cloture - parametres.commun.minimum_chart_stop_atr * a)
        niveau = min(composantes)
    else:
        composantes = (b.haut + guard, range_.bas + parametres.boundary_stop_inside_atr * a,
                       b.cloture + parametres.commun.minimum_chart_stop_atr * a)
        niveau = max(composantes)
    distance = sens.signe * (b.cloture - niveau)
    if distance <= 0 or distance > parametres.commun.maximum_chart_stop_atr * a:
        return RefusLondon(Motif.STOP_TOO_WIDE, None)
    noms = ('BOUGIE', 'FRONTIERE', 'PLANCHER_ATR')
    return StopLocal(niveau, parametres.take_profit_gross_price_r, distance, composantes,
                     tuple(nom for nom, valeur in zip(noms, composantes) if valeur == niveau))

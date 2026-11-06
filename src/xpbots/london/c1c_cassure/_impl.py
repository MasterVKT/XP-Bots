"""Implémentation de la couche 1c (bougie_cassure). Révisable à comportement constant sous harnais complet."""
from decimal import Decimal

from xpbots.donnees.c0a_types import BougieEnrichie, UniteTemps
from xpbots.london.c0a_parametres import ParametresLondon
from xpbots.london.c0b_types import Cassure, ErreurLondon, RangeLondon, RefusLondon, tick_flottant, verifier_bougie
from xpbots.noyau.c1c_domaine import Motif, Sens


def evaluer_cassure(bougie: BougieEnrichie, range_: RangeLondon, tick_size: Decimal,
                    parametres: ParametresLondon) -> Cassure | RefusLondon:
    if not isinstance(parametres, ParametresLondon) or not isinstance(range_, RangeLondon):
        raise ErreurLondon('paramètres et range London attendus')
    verifier_bougie(bougie, UniteTemps.M15, parametres.commun.timeframe_seconds * 1000)
    if bougie.jour_londres != range_.jour:
        raise ErreurLondon('range d’un autre jour')
    tick = tick_flottant(tick_size)
    b, i = bougie.bougie, bougie.indicateurs
    if not b.valide:
        return RefusLondon(Motif.NO_SETUP, 'PAS_DE_CASSURE')
    if i.a is None:
        return RefusLondon(Motif.WARMUP, 'ATR_M15_INDISPONIBLE')
    if i.a <= 0:
        return RefusLondon(Motif.NO_SETUP, 'ATR_NON_POSITIF')
    amplitude = b.haut - b.bas
    if amplitude <= 0:
        return RefusLondon(Motif.NO_SETUP, 'BOUGIE_PLATE')
    if i.tr > parametres.commun.maximum_signal_true_range_atr * i.a:
        return RefusLondon(Motif.NO_SETUP, 'TR_EXCESSIF')
    corps = abs(b.cloture - b.ouverture) / amplitude
    if corps < parametres.signal_body_fraction_min:
        return RefusLondon(Motif.NO_SETUP, 'CORPS_INSUFFISANT')
    buffer = max(tick, parametres.breakout_buffer_atr * i.a)
    if b.cloture > range_.haut + buffer and b.cloture > b.ouverture:
        sens = Sens.ACHAT
        fraction = (b.cloture - b.bas) / amplitude
    elif b.cloture < range_.bas - buffer and b.cloture < b.ouverture:
        sens = Sens.VENTE
        fraction = (b.haut - b.cloture) / amplitude
    else:
        return RefusLondon(Motif.NO_SETUP, 'PAS_DE_CASSURE')
    if fraction < parametres.signal_close_location_min:
        return RefusLondon(Motif.NO_SETUP, 'CLOTURE_ELOIGNEE')
    return Cassure(sens, corps, fraction, buffer)

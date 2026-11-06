"""Journées London synthétiques issues de ticks, avec préchargement M15 et H1 de TR constant.

La fabrique garde chaque clôture historique dans l'intersection des quatre intervalles M15 d'une H1.
Elle sait donc produire TR_M15 et TR_H1 constants distincts lorsque A ≤ A_H1 ≤ 2 A. Cette contrainte de
fabrique ne constitue aucune règle de trading. La journée finale permet un range et une cassure voulus.
Les ATR de cette journée sont recalculés par le flux réel ; ils ne sont jamais injectés dans le robot.
"""
from datetime import date, time, timedelta
from decimal import Decimal

from robot.outils.fabrique_ticks import (PAS, BougieVoulue, TickFabrique, bornes_journee_londres,
                                        ticks_de_bougies)
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.noyau.c0c_configuration import ExportTechnique


def journee_london_prechargee(jour: date, technique: ExportTechnique, *, symbole='EURUSD',
                            tr_m15=Decimal('0.125'), tr_h1=Decimal('0.125'),
                            base=Decimal('16'), largeur_range=None, signal=None):
    """Rend (bougies voulues, ticks fabriqués), au moins treize jours avant le jour cible.

    `signal` : tuple Decimal (O, H, L, C) de la bougie ouverte au début configuré de séance.
    Sans tuple, une cassure longue valide est fabriquée. Aucun prix réel n'est utilisé.
    """
    if not (isinstance(tr_m15, Decimal) and isinstance(tr_h1, Decimal) and 0 < tr_m15 <= tr_h1 <= 2*tr_m15):
        raise ValueError('TR constants : 0 < A ≤ A_H1 ≤ 2 A attendu')
    c = technique.commun
    duree = c.timeframe_seconds * 1000
    calendrier = CalendrierLondres.depuis_parametres(c)
    # Un jour supplémentaire couvre les variations de longueur du jour aux changements d'heure.
    secondes_requises = max(c.warmup_closed_m15_bars*c.timeframe_seconds, c.warmup_closed_h1_bars*c.h1_seconds)
    jours = secondes_requises // 86400 + 2
    debut, _ = bornes_journee_londres(jour-timedelta(days=jours))
    cible, fin = bornes_journee_londres(jour)
    range_debut = calendrier.instant_local(jour, time.fromisoformat(technique.london['range_start_local']))
    range_fin = calendrier.instant_local(jour, time.fromisoformat(technique.london['range_end_local_exclusive']))
    session = calendrier.instant_local(jour, time.fromisoformat(technique.london['session_start_local']))
    largeur = tr_h1 if largeur_range is None else Decimal(largeur_range)
    bas_range, haut_range = base-tr_m15/2, base-tr_m15/2+largeur
    bougies = []
    for t in range(debut, fin, duree):
        quart = ((t // duree) % (c.h1_seconds // c.timeframe_seconds))
        decalage = (tr_h1-tr_m15) if quart % 2 else Decimal(0)
        l, h = base-tr_m15/2+decalage, base+tr_m15/2+decalage
        o = cloture = base-tr_m15/2+(tr_h1-tr_m15)
        if range_debut <= t < range_fin:
            l, h = bas_range, haut_range
            o = cloture = (l+h)/2
        if t == session:
            o, h, l, cloture = signal or (haut_range-tr_m15/8, haut_range+tr_m15,
                                         haut_range-tr_m15/4, haut_range+7*tr_m15/8)
        # Même grille synthétique que la fabrique de ticks ; les attendus OHLC sont donc exacts.
        bougies.append(BougieVoulue(t, *(str(prix.quantize(PAS)) for prix in (o, h, l, cloture))))
    ticks = ticks_de_bougies(symbole, bougies)
    ticks.append(TickFabrique(symbole, symbole, fin, ticks[-1].sequence+1, bougies[-1].cloture,
                              str(Decimal(bougies[-1].cloture)+Decimal('0.00010'))))
    return bougies, ticks

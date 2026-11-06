"""Implémentation de la couche 1b (gel_atr_h1). Révisable à comportement constant sous harnais complet."""
from datetime import date

from xpbots.donnees.c0a_types import UniteTemps
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.london.c0a_parametres import ParametresLondon
from xpbots.london.c0b_types import ErreurLondon, GelATRH1, verifier_bougie


def construire_gel(jour: date, bougies, parametres: ParametresLondon) -> GelATRH1 | None:
    if type(jour) is not date or not isinstance(parametres, ParametresLondon):
        raise ErreurLondon('jour et paramètres London attendus')
    calendrier = CalendrierLondres.depuis_parametres(parametres.commun)
    fin_gel = calendrier.instant_local(jour, parametres.range_h1_atr_frozen_local)
    duree = parametres.commun.h1_seconds * 1000
    candidates = []
    symbole = None
    for enrichie in bougies:
        verifier_bougie(enrichie, UniteTemps.H1, duree, symbole)
        symbole = enrichie.bougie.symbole
        if enrichie.bougie.valide and enrichie.bougie.fin_ms <= fin_gel:
            candidates.append(enrichie)
    if not candidates:
        return None
    candidate = max(candidates, key=lambda e: e.bougie.fin_ms)
    b, i = candidate.bougie, candidate.indicateurs
    if (fin_gel - b.fin_ms > duree or i.rang < parametres.commun.warmup_closed_h1_bars - 1
            or i.atr is None or i.atr <= 0):
        return None
    return GelATRH1(jour, i.atr, b.fin_ms, b.instant_disponibilite_ms)

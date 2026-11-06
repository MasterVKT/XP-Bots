"""Implémentation de la couche 1a (range_londres). Révisable à comportement constant sous harnais complet."""
from datetime import date

from xpbots.donnees.c0a_types import BougieEnrichie, UniteTemps
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.london.c0a_parametres import ParametresLondon
from xpbots.london.c0b_types import ErreurLondon, RangeLondon, RefusLondon, verifier_bougie
from xpbots.noyau.c1c_domaine import Motif


def construire_range(jour: date, bougies, parametres: ParametresLondon) -> RangeLondon | RefusLondon:
    if type(jour) is not date or not isinstance(parametres, ParametresLondon):
        raise ErreurLondon('jour et paramètres London attendus')
    calendrier = CalendrierLondres.depuis_parametres(parametres.commun)
    if not calendrier.jour_actif(jour):
        return RefusLondon(Motif.OUTSIDE_SESSION, 'JOUR_INACTIF')
    duree = parametres.commun.timeframe_seconds * 1000
    attendues = calendrier.ouvertures(jour, parametres.range_start_local, parametres.range_end_local_exclusive, duree)
    if len(attendues) != parametres.expected_range_m15_bars:
        raise ErreurLondon('nombre d’ouvertures du range incohérent')
    retenues = {}
    symbole = None
    for enrichie in bougies:
        if not isinstance(enrichie, BougieEnrichie):
            raise ErreurLondon('bougie enrichie attendue')
        if enrichie.bougie.debut_ms not in attendues:
            continue
        verifier_bougie(enrichie, UniteTemps.M15, duree, symbole)
        symbole = enrichie.bougie.symbole
        if enrichie.bougie.debut_ms in retenues:
            raise ErreurLondon('ouverture du range en double')
        retenues[enrichie.bougie.debut_ms] = enrichie.bougie
    if len(retenues) != len(attendues):
        return RefusLondon(Motif.NO_SETUP, 'RANGE_INCOMPLET')
    invalides = [b for b in retenues.values() if not b.valide]
    if invalides:
        trou = any(b.motif_invalidite in ('TROU_DONNEES', 'HORAIRES_INCONNUS') for b in invalides)
        return RefusLondon(Motif.DATA_GAP if trou else Motif.NO_SETUP, 'RANGE_BOUGIE_INVALIDE')
    haut = max(b.haut for b in retenues.values())
    bas = min(b.bas for b in retenues.values())
    if haut <= bas:
        return RefusLondon(Motif.NO_SETUP, 'RANGE_HORS_BORNES')
    return RangeLondon(jour, haut, bas, max(b.instant_disponibilite_ms for b in retenues.values()))

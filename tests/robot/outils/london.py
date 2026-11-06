"""Valeurs synthétiques du contrat S02 : helpers de tests, jamais données de marché réelles."""
from dataclasses import replace
from datetime import date, time
from decimal import Decimal

from robot.outils.configuration import configuration_figee, octets_technique_modifies
from xpbots.donnees.c0a_types import BougieEnrichie, IndicateursBougie, UniteTemps
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.london.c0a_parametres import charger_parametres_london
from xpbots.london.c0b_types import RangeLondon
from xpbots.noyau.c0c_configuration import analyser_export_technique
from xpbots.noyau.c1a_marche import Bougie
from xpbots.noyau.c1c_domaine import CleIntention, Issue, NatureIssue, Sens

JOUR = date(2026, 1, 12)
TICK = Decimal('0.0625')


def parametres(modifier=None):
    technique = (analyser_export_technique(octets_technique_modifies(modifier)) if modifier
                 else configuration_figee().technique)
    return charger_parametres_london(technique)


def strategie_squelette(configuration):
    """Vraie stratégie London ; tailles de tick synthétiques explicitement fournies par les tests."""
    from xpbots.london.c2_moteur import fabriquer_strategie
    return fabriquer_strategie(configuration, {s: Decimal('0.00001') for s in configuration.technique.commun.universe_priority})


def dyadiques():
    def modifier(j):
        j['common'].update(structural_buffer_atr=0.125, minimum_chart_stop_atr=0.5)
        j['london'].update(breakout_buffer_atr=0.125, signal_body_fraction_min=0.5, signal_close_location_min=0.75)
    return parametres(modifier)


def bougie(*, p=None, jour=JOUR, heure='08:00:00', unite=UniteTemps.M15, symbole='EURUSD',
            o=100.0, h=101.0, l=99.75, c=100.875, a=1.0, atr=1.0, tr=1.25,
            rang=None, retard_ms=0, valide=True, motif=None):
    p = p or parametres()
    calendrier = CalendrierLondres.depuis_parametres(p.commun)
    debut = calendrier.instant_local(jour, time.fromisoformat(heure))
    duree = unite.duree_ms(p.commun)
    if rang is None:
        rang = (p.commun.warmup_closed_m15_bars if unite is UniteTemps.M15 else p.commun.warmup_closed_h1_bars) - 1
    b = Bougie(symbole, debut, duree, o, h, l, c, 4, valide, motif, debut + duree + retard_ms)
    i = IndicateursBougie(tr, atr, a, rang) if valide else None
    return BougieEnrichie(b, unite, i, jour, calendrier.datetime_local(debut),
                          calendrier.datetime_local(b.fin_ms), calendrier.jour_utc(debut))


def range_connu(*, p=None, jour=JOUR, haut=100.0, bas=98.0):
    p = p or parametres()
    cal = CalendrierLondres.depuis_parametres(p.commun)
    return RangeLondon(jour, haut, bas, cal.instant_local(jour, p.range_end_local_exclusive))


def bougies_range(p=None, jour=JOUR, symbole='EURUSD'):
    p = p or parametres()
    cal = CalendrierLondres.depuis_parametres(p.commun)
    ouvertures = cal.ouvertures(jour, p.range_start_local, p.range_end_local_exclusive,
                               p.commun.timeframe_seconds * 1000)
    return [bougie(p=p, jour=jour, symbole=symbole, heure=cal.datetime_local(t).time().isoformat(),
                   o=99, h=100, l=98, c=99, tr=2) for t in ouvertures]


def miroir(enrichie, centre=100.0):
    b = enrichie.bougie
    return replace(enrichie, bougie=replace(b, ouverture=2*centre-b.ouverture, haut=2*centre-b.bas,
                                            bas=2*centre-b.haut, cloture=2*centre-b.cloture))


def issue(*, p=None, jour=JOUR, heure='08:15:00', sens=Sens.ACHAT, nature=NatureIssue.REMPLIE,
          symbole='EURUSD', cloture_ms=None, motif=None, detail=None, cause=None):
    p = p or parametres()
    cal = CalendrierLondres.depuis_parametres(p.commun)
    instant = cal.instant_local(jour, time.fromisoformat(heure))
    cle = CleIntention('test', p.strategy_id, symbole, instant if cloture_ms is None else cloture_ms, sens)
    return Issue(cle, nature, instant, motif, detail, cause)

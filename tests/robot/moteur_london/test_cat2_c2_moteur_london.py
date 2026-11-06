"""Catégorie 2, couche 2 : ticks → flux réel → S02, oracle london_setups et causalité C11.1."""
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
import math
import typing
import unittest

import pandas as pd

from reference.technical import add_indicators, london_setups
from robot.outils.configuration import configuration_figee
from robot.outils.fabrique_journees_london import journee_london_prechargee
from robot.outils.london import TICK, bougie, issue, parametres
from xpbots.donnees.c0a_types import BougieEnrichie, UniteTemps
from xpbots.donnees.c1c_couverture import RegistreCouverture
from xpbots.donnees.c3_flux import FluxBougies
from xpbots.london.c2_moteur import MoteurLondon, fabriquer_strategie
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle
from xpbots.noyau.c1c_domaine import CauseCloture, NatureIssue, SignalTechnique
from xpbots.orchestration.squelette import Strategie

CONFIGURATION = configuration_figee()


def ticks_reels(jour, **kwargs):
    _, fabriques = journee_london_prechargee(jour, CONFIGURATION.technique, **kwargs)
    return [Tick(t.symbole, t.symbole_courtier, t.instant_ms, t.instant_ms, t.sequence,
                 float(t.bid), float(t.ask)) for t in fabriques]


def enrichir(ticks, technique=None):
    technique = technique or CONFIGURATION.technique
    debut = ticks[0].instant_fournisseur_ms
    fin = ticks[-1].instant_fournisseur_ms + technique.commun.h1_seconds*1000
    intervalle = Intervalle(debut, fin)
    flux = FluxBougies('EURUSD', technique, HorairesCotation((intervalle,), (), debut, fin),
                       RegistreCouverture((intervalle,)))
    return [e for t in ticks for e in flux.sur_tick(t) if isinstance(e, BougieEnrichie)]


def cadre(suite):
    return add_indicators(pd.DataFrame(
        {'O': [e.bougie.ouverture for e in suite], 'H': [e.bougie.haut for e in suite],
         'L': [e.bougie.bas for e in suite], 'C': [e.bougie.cloture for e in suite]},
        index=pd.to_datetime([e.bougie.debut_ms for e in suite], unit='ms', utc=True)))


def decider(suite, p=None):
    moteur = MoteurLondon(p or parametres(), 'EURUSD', Decimal('0.00001'))
    return [r for e in suite if (r := moteur.sur_bougie(e)) is not None]


class TestJonctionMoteur(unittest.TestCase):
    def test_egalite_complete_a_london_setups_ete_hiver_et_apres_changement(self):
        for jour in (date(2026, 1, 12), date(2026, 7, 1), date(2026, 3, 30), date(2026, 10, 26)):
            suite = enrichir(ticks_reels(jour))
            m15 = [e for e in suite if e.unite is UniteTemps.M15]
            h1 = [e for e in suite if e.unite is UniteTemps.H1]
            attendu = london_setups(cadre(m15), cadre(h1), 0.00001)
            reel = [r for r in decider(suite) if isinstance(r, SignalTechnique)]
            with self.subTest(jour=jour):
                self.assertGreaterEqual(len(m15), CONFIGURATION.technique.commun.warmup_closed_m15_bars)
                self.assertGreaterEqual(len(h1), CONFIGURATION.technique.commun.warmup_closed_h1_bars)
                self.assertTrue(attendu, 'le cas doit réellement produire au moins une cassure')
                self.assertEqual(len(reel), len(attendu))
                for signal, oracle in zip(reel, attendu):
                    self.assertEqual(signal.cloture_ms, oracle['decision_time'].value // 1000000)
                    self.assertEqual(signal.sens.signe, oracle['side'])
                    for valeur, reference in ((signal.cloture_prix, oracle['signal_close_bid']),
                                               (signal.atr_reference, oracle['atr_reference']),
                                               (signal.stop_technique, oracle['stop_chart_bid']),
                                               (signal.contexte['range_haut'], oracle['range_high']),
                                               (signal.contexte['range_bas'], oracle['range_low']),
                                               (signal.contexte['atr_h1'], oracle['range_h1_atr'])):
                        self.assertTrue(math.isclose(valeur, reference, rel_tol=1e-12, abs_tol=1e-15))

    def test_fabrique_precharge_de_vrais_ticks_a_tr_constant_m15_et_h1(self):
        jour = date(2026, 7, 1)
        a, ah = Decimal('0.125'), Decimal('0.1875')
        suite = enrichir(ticks_reels(jour, tr_m15=a, tr_h1=ah))
        avant = [e for e in suite if e.jour_londres < jour]
        for unite, tr_attendu in ((UniteTemps.M15, float(a)), (UniteTemps.H1, float(ah))):
            barres = [e for e in avant if e.unite is unite]
            minimum = (CONFIGURATION.technique.commun.warmup_closed_m15_bars if unite is UniteTemps.M15
                       else CONFIGURATION.technique.commun.warmup_closed_h1_bars)
            self.assertGreaterEqual(len(barres), minimum)
            self.assertTrue(all(e.indicateurs.tr == tr_attendu for e in barres))
            self.assertEqual(barres[-1].indicateurs.atr, tr_attendu)

    def test_prefixe_de_ticks_et_future_modifie_identiques_avant_la_coupe(self):
        ticks = ticks_reels(date(2026, 1, 12))
        complet = decider(enrichir(ticks))
        for coupure in (len(ticks)-250, len(ticks)-200, len(ticks)-100):
            prefixe = decider(enrichir(ticks[:coupure]))
            self.assertEqual(prefixe, complet[:len(prefixe)])
            futur = [*ticks[:coupure], *(replace(t, bid=t.bid+8, ask=t.ask+8) for t in ticks[coupure:])]
            modifie = decider(enrichir(futur))
            self.assertEqual(modifie[:len(prefixe)], prefixe)

    def test_parametres_de_largeur_et_de_prechargement_changent_la_decision(self):
        suite = enrichir(ticks_reels(date(2026, 7, 1)))
        p = parametres()
        self.assertTrue(any(isinstance(r, SignalTechnique) for r in decider(suite, p)))
        autres = (replace(p, range_min_h1_atr=2),
                  replace(p, commun=replace(p.commun, warmup_closed_m15_bars=len(suite)+1)),
                  replace(p, commun=replace(p.commun, warmup_closed_h1_bars=len(suite)+1)))
        for autre in autres:
            self.assertFalse(any(isinstance(r, SignalTechnique) for r in decider(suite, autre)))

    def test_protocole_structurel_d18_et_rejeu_des_issues_identique(self):
        strategie = fabriquer_strategie(CONFIGURATION, {'EURUSD': TICK})
        for membre in typing.get_protocol_members(Strategie):
            self.assertTrue(hasattr(strategie, membre), membre)
        suite = enrichir(ticks_reels(date(2026, 1, 12)))
        def rejouer():
            moteur = MoteurLondon(parametres(), 'EURUSD', Decimal('0.00001'))
            sortie = []
            for e in suite:
                r = moteur.sur_bougie(e)
                if r is None:
                    continue
                sortie.append(r)
                if isinstance(r, SignalTechnique):
                    rempli = issue(jour=e.jour_londres, heure=e.cloture_locale.time().isoformat(), sens=r.sens,
                                    cloture_ms=r.cloture_ms)
                    moteur.sur_issue(rempli)
                    moteur.sur_issue(replace(rempli, nature=NatureIssue.CLOTUREE, cause=CauseCloture.STOP_LOSS))
            return sortie
        self.assertEqual(rejouer(), rejouer())

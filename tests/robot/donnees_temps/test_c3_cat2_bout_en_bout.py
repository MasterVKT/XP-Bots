"""Couche 3, catégorie 2 — bloc réel {0 → 3} : causalité C11.1, changement d'heure, récupération, référence."""
import dataclasses
import importlib.util
import math
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

from robot.fixtures.series import DEBUT_LUNDI, M15, ticks_bougies
from xpbots.donnees_temps.c0_parametres_seances import CalendrierSeances, charger_parametres_techniques
from xpbots.donnees_temps.c1a_sessions import SessionsLondres
from xpbots.donnees_temps.c2_etat_indicateurs import SpecIndicateurs
from xpbots.donnees_temps.c3_pipeline import PipelineMarche
from xpbots.noyau.config import charger_bundle_technique
from xpbots.noyau.marche import BougieEnrichie, EvenementDonnees, NatureEvenementDonnees, StatutBougie

BUNDLE = charger_bundle_technique().donnees
PARAMETRES = charger_parametres_techniques(charger_bundle_technique())
SESSIONS = SessionsLondres(PARAMETRES)
PERIODES = tuple(BUNDLE['ema']['ema_periods'])
SPEC = SpecIndicateurs(PERIODES, BUNDLE['ema']['rsi_period'], PARAMETRES.periode_atr,
                       ((max(PERIODES), BUNDLE['ema']['slow_ema_slope_lookback_bars']),), PARAMETRES.prechauffage_m15)
NB = 1100
FIN = DEBUT_LUNDI + NB * M15
REFERENCE_DISPONIBLE = all(importlib.util.find_spec(nom) for nom in ('numpy', 'pandas'))


def ms(*args):
    return int(datetime(*args, tzinfo=timezone.utc).timestamp() * 1000)


def instant(sortie):
    return sortie.bougie.cloture_ms if isinstance(sortie, BougieEnrichie) else sortie.instant_ms


def jouer(liste_ticks, fin, transitions=(), recuperation=None, calendrier=None, debut=DEBUT_LUNDI):
    calendrier = calendrier or CalendrierSeances('EURUSD', ((debut, FIN + M15),), debut, FIN + M15)
    pipeline = PipelineMarche('EURUSD', PARAMETRES.periode_m15_s, calendrier, SESSIONS, SPEC, debut, recuperation)
    transitions = sorted([(debut, True)] + list(transitions))
    sorties = []
    for tick in liste_ticks:
        while transitions and transitions[0][0] <= tick.instant.ms:
            sorties += pipeline.sur_couverture(*transitions.pop(0))
        sorties += pipeline.sur_horloge(tick.instant.ms)
        sorties += pipeline.sur_tick(tick)
    for transition in transitions:
        if transition[0] < fin:
            sorties += pipeline.sur_couverture(*transition)
    return sorties + pipeline.terminer(fin), pipeline


class TestBoutEnBout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ticks = ticks_bougies('EURUSD', DEBUT_LUNDI, NB, graine=21)
        cls.sorties, cls.pipeline = jouer(cls.ticks, FIN)

    def test_prechauffage_de_la_configuration(self):
        bougies = [s for s in self.sorties if isinstance(s, BougieEnrichie)]
        self.assertEqual(len(bougies), NB)
        premier_ok = next(i for i, b in enumerate(bougies) if b.statut is StatutBougie.OK)
        self.assertEqual(premier_ok, PARAMETRES.prechauffage_m15 - 1)
        self.assertEqual(set(bougies[-1].indicateurs),
                         {'ema_15', 'ema_25', 'ema_50', 'ema_50_t_moins_4', 'rsi_14', 'atr_14', 'tr'})

    def test_c11_1_causalite_ticks_futurs_retires_ou_modifies(self):
        limite = DEBUT_LUNDI + 1050 * M15 + 123
        passe = [s for s in self.sorties if instant(s) <= limite]
        prefixe, _ = jouer([t for t in self.ticks if t.instant.ms < limite], limite)
        self.assertEqual(prefixe, passe)
        modifies = [dataclasses.replace(t, bid=t.bid + Decimal('0.01000'), ask=t.ask + Decimal('0.01000'))
                    if t.instant.ms >= limite else t for t in self.ticks]
        sorties_modifiees, _ = jouer(modifies, FIN)
        self.assertEqual([s for s in sorties_modifiees if instant(s) <= limite], passe)
        self.assertNotEqual(sorties_modifiees[-1], self.sorties[-1])

    def test_recuperations_identiques_au_flux_continu(self):
        trous = [(DEBUT_LUNDI + k * M15 + 200, DEBUT_LUNDI + k * M15 + 70_000) for k in (40, 999, 1060)]
        transitions = [(a, False) for a, _ in trous] + [(b, True) for _, b in trous]
        manquants = [t for t in self.ticks if not any(a <= t.instant.ms < b for a, b in trous)]

        def recuperer(symbole, debut, fin):
            return [t for t in self.ticks if debut <= t.instant.ms < fin]

        sorties, pipeline = jouer(manquants, FIN, transitions, recuperer)
        self.assertEqual(len([s for s in sorties if isinstance(s, EvenementDonnees)
                              and s.nature is NatureEvenementDonnees.RECUPERATION]), 3)
        self.assertEqual(pipeline.etat.exporter(), self.pipeline.etat.exporter())
        attendues = {b.bougie.ouverture_ms: b for b in self.sorties if isinstance(b, BougieEnrichie)}
        for b in sorties:
            if isinstance(b, BougieEnrichie) and b.statut is not StatutBougie.DATA_GAP:
                self.assertEqual(b, attendues[b.bougie.ouverture_ms])

    @unittest.skipUnless(REFERENCE_DISPONIBLE, 'numpy et pandas requis par reference.technical')
    def test_concordance_avec_reference_add_indicators(self):
        import numpy as np
        import pandas as pd
        from reference import technical
        bougies = [s for s in self.sorties if isinstance(s, BougieEnrichie)]
        cadre = technical.add_indicators(pd.DataFrame(
            [(float(b.bougie.o), float(b.bougie.h), float(b.bougie.l), float(b.bougie.c)) for b in bougies],
            columns=['O', 'H', 'L', 'C']))
        lent, k = max(PERIODES), BUNDLE['ema']['slow_ema_slope_lookback_bars']
        for i, b in enumerate(bougies):
            ligne = cadre.iloc[i]
            attendus = {f'ema_{n}': ligne[f'E{n}'] for n in PERIODES}
            attendus.update(rsi_14=ligne.RSI, atr_14=ligne.ATR, tr=ligne.TR)
            if i >= k:
                attendus[f'ema_{lent}_t_moins_{k}'] = cadre[f'E{lent}'].iloc[i - k]
            for cle, valeur in attendus.items():
                if np.isnan(valeur):
                    self.assertNotIn(cle, b.indicateurs)
                else:
                    self.assertTrue(math.isclose(b.indicateurs[cle], valeur, rel_tol=1e-12), (i, cle))
            if not np.isnan(ligne.A):
                self.assertTrue(math.isclose(b.a_t, ligne.A, rel_tol=1e-12))


class TestChangementDHeure(unittest.TestCase):
    def test_jour_londres_et_fermeture_du_week_end(self):
        # Jeudi 22 octobre 2026 22:00 UTC → vendredi 22:00 UTC, puis dimanche 25 octobre 22:00 → lundi 01:00 UTC.
        semaine = (ms(2026, 10, 22, 22), ms(2026, 10, 23, 22))
        reprise = (ms(2026, 10, 25, 22), ms(2026, 10, 26, 1))
        calendrier = CalendrierSeances('EURUSD', (semaine, reprise), semaine[0], reprise[1])
        liste = ticks_bougies('EURUSD', semaine[0], 96, graine=4)
        liste += ticks_bougies('EURUSD', reprise[0], 12, graine=8, sequence_depart=len(liste) + 1,
                               prix=liste[-1].bid)
        sorties, _ = jouer(liste, reprise[1], calendrier=calendrier, debut=semaine[0])
        self.assertEqual([s for s in sorties if isinstance(s, EvenementDonnees)], [])  # fermeture officielle ≠ trou
        jours = {b.bougie.cloture_ms: b.jour_londres for b in sorties}
        self.assertEqual(jours[ms(2026, 10, 22, 23, 15)], date(2026, 10, 23))  # BST : 00:15 à Londres
        self.assertEqual(jours[ms(2026, 10, 25, 23, 15)], date(2026, 10, 25))  # GMT : 23:15 à Londres
        self.assertEqual(jours[ms(2026, 10, 26, 0, 15)], date(2026, 10, 26))
        premiere_lundi = next(b for b in sorties if b.bougie.ouverture_ms == reprise[0])
        derniere_vendredi = next(b for b in sorties if b.bougie.cloture_ms == semaine[1])
        ecart = abs(float(premiere_lundi.bougie.h) - float(derniere_vendredi.bougie.c))
        self.assertGreaterEqual(premiere_lundi.indicateurs['tr'], ecart)  # le TR enjambe la fermeture normale


if __name__ == '__main__':
    unittest.main()

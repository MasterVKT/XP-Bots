"""Couche 0 — `parametres_techniques` : schéma exact du bloc `common`, genres de valeurs, variantes implémentées."""
import copy
import json
import unittest
from datetime import time

from robot.outils import RACINE
from xpbots.donnees_temps.c0_parametres_seances import (SCHEMA_COMMON, VARIANTES_IMPLEMENTEES,
                                                         FonctionNonImplementee, ParametresTechniques,
                                                         analyser_heure, charger_parametres_techniques,
                                                         valider_bloc_common)
from xpbots.noyau.config import ConfigurationInvalide, charger_bundle_technique


def common_brut():
    return json.loads((RACINE / 'config' / 'parametres_figes_v3.json').read_text(encoding='utf-8'))['common']


class TestSchemaCommon(unittest.TestCase):
    def test_schema_couvre_exactement_le_bloc_fige(self):
        self.assertEqual(set(SCHEMA_COMMON), set(common_brut()))
        self.assertEqual(valider_bloc_common(common_brut()), [])

    def test_cles_manquantes_ou_en_trop(self):
        bloc = common_brut()
        del bloc['atr_period']
        self.assertTrue(valider_bloc_common(bloc))
        bloc = dict(common_brut(), cle_inventee=1)
        self.assertTrue(valider_bloc_common(bloc))

    def test_genres_de_valeurs(self):
        cas = {'atr_period': [None, True, 14.0, 0, -1], 'warmup_closed_m15_bars': ['1000'],
               'risk_fraction_per_entry': [0, -0.005, float('nan'), float('inf'), True],
               'session_timezone': ['Fuseau/Inconnu', ''], 'rollover_blackout_utc_start': ['21:00', '25:00:00'],
               'frozen_date': ['2026-13-01', '04/11/2026'], 'active_weekdays_local': [[0, 7], [], [1, 1]],
               'universe_priority': [[], ['EURUSD', 'EURUSD'], ['']], 'allow_martingale': [0, 'false'],
               'max_spread_price': [{}, {'EURUSD': 0}], 'protective_update_retry_delays_seconds': [[], [0.25, -1]],
               'fundamental_timestamp_future_tolerance_seconds': [-1, 0.0]}
        for cle, valeurs in cas.items():
            for valeur in valeurs:
                bloc = common_brut()
                bloc[cle] = valeur
                with self.subTest(cle=cle, valeur=valeur):
                    self.assertTrue(valider_bloc_common(bloc))


class TestParametresTechniques(unittest.TestCase):
    def setUp(self):
        self.bundle = charger_bundle_technique()
        self.parametres = charger_parametres_techniques(self.bundle)
        self.brut = common_brut()

    def test_proprietes_lues_dans_config(self):
        p, b = self.parametres, self.brut
        self.assertEqual((p.periode_m15_s, p.periode_h1_s, p.prechauffage_m15, p.prechauffage_h1, p.periode_atr),
                         (b['timeframe_seconds'], b['h1_seconds'], b['warmup_closed_m15_bars'],
                          b['warmup_closed_h1_bars'], b['atr_period']))
        self.assertEqual(p.fuseau_sessions, b['session_timezone'])
        self.assertEqual(p.jours_actifs, frozenset(b['active_weekdays_local']))
        self.assertEqual(p.univers, tuple(b['universe_priority']))
        self.assertEqual(p.blackout_debut, analyser_heure(b['rollover_blackout_utc_start']))
        self.assertEqual(p.blackout_fin, analyser_heure(b['rollover_blackout_utc_end']))
        self.assertEqual(p.empreinte, self.bundle.empreinte)
        self.assertEqual(p.valeur('max_spread_price')['EURUSD'], b['max_spread_price']['EURUSD'])

    def test_lecture_seule(self):
        with self.assertRaises(TypeError):
            self.parametres.valeur('max_spread_price')['EURUSD'] = 1.0
        with self.assertRaises(ConfigurationInvalide):
            self.parametres.valeur('cle_inventee')

    def test_bloc_invalide_refuse(self):
        bloc = copy.deepcopy(self.brut)
        bloc['timeframe_seconds'] = True
        with self.assertRaises(ConfigurationInvalide):
            ParametresTechniques(bloc, self.bundle.empreinte)

    def test_variantes_non_implementees(self):
        for cle in VARIANTES_IMPLEMENTEES:
            bloc = copy.deepcopy(self.brut)
            bloc[cle] = 'AUTRE_VARIANTE'
            with self.subTest(cle=cle), self.assertRaises(FonctionNonImplementee):
                ParametresTechniques(bloc, self.bundle.empreinte)

    def test_variantes_conformes_a_la_configuration_figee(self):
        for cle, attendue in VARIANTES_IMPLEMENTEES.items():
            self.assertEqual(self.brut[cle], attendue)


class TestAnalyserHeure(unittest.TestCase):
    def test_format_strict(self):
        self.assertEqual(analyser_heure('08:00:00'), time(8, 0, 0))
        self.assertEqual(analyser_heure('23:59:59'), time(23, 59, 59))
        for texte in ('8:00:00', '08:00', '24:00:00', '08:60:00', ' 08:00:00', 800):
            with self.subTest(texte=texte), self.assertRaises(ConfigurationInvalide):
                analyser_heure(texte)


if __name__ == '__main__':
    unittest.main()

"""Catégorie 1, couche 0a (parametres_london) : clés, types, bornes et configuration réelle."""
from dataclasses import FrozenInstanceError, replace
from datetime import time
import unittest

from robot.outils.configuration import configuration_figee, octets_technique_modifies
from xpbots.london.c0a_parametres import (CLES_LONDON, ErreurParametresLondon, charger_parametres_london)
from xpbots.noyau.c0c_configuration import analyser_export_technique


class TestParametresLondon(unittest.TestCase):
    def setUp(self):
        self.technique = configuration_figee().technique
        self.p = charger_parametres_london(self.technique)

    def charger(self, cle, valeur):
        return charger_parametres_london(analyser_export_technique(octets_technique_modifies(
            lambda j: j['london'].__setitem__(cle, valeur))))

    def test_champs_exacts_et_heures_typees_immuables(self):
        self.assertEqual(set(CLES_LONDON), set(self.technique.london))
        self.assertIs(self.p.commun, self.technique.commun)
        for cle in CLES_LONDON:
            valeur = getattr(self.p, cle)
            self.assertEqual(valeur.isoformat() if isinstance(valeur, time) else valeur, self.technique.london[cle])
        with self.assertRaises(FrozenInstanceError):
            self.p.strategy_id = 'AUTRE'

    def test_cles_manquantes_ou_inconnues_et_type_export_refuses(self):
        for cle in CLES_LONDON:
            with self.subTest(cle=cle), self.assertRaises(ValueError):
                charger_parametres_london(analyser_export_technique(octets_technique_modifies(
                    lambda j: j['london'].pop(cle))))
        with self.assertRaises(ValueError):
            self.charger('nouveau', 1)
        with self.assertRaises(ErreurParametresLondon):
            charger_parametres_london({})

    def test_options_desactivees_refusees_au_demarrage(self):
        for cle in ('fresh_close_cross_required', 'h1_directional_filter_enabled',
                    'exit_on_close_back_inside_range_enabled'):
            for valeur in (True, 0, 'false', None):
                with self.subTest(cle=cle, valeur=valeur), self.assertRaises(ValueError):
                    self.charger(cle, valeur)

    def test_entiers_et_nombres_hors_bornes_refuses(self):
        for cle in ('expected_range_m15_bars', 'max_filled_entries_per_symbol_local_day',
                    'max_filled_entries_per_direction_local_day'):
            for valeur in (True, 0, -1, 1.5, None, '2'):
                with self.subTest(cle=cle, valeur=valeur), self.assertRaises(ValueError):
                    self.charger(cle, valeur)
        for cle in ('range_min_h1_atr', 'range_max_h1_atr', 'breakout_buffer_atr', 'boundary_stop_inside_atr',
                    'signal_body_fraction_min', 'signal_close_location_min', 'take_profit_gross_price_r'):
            for valeur in (True, -1, '0.5', None, float('inf'), float('nan')):
                with self.subTest(cle=cle, valeur=valeur), self.assertRaises(ValueError):
                    replace(self.p, **{cle: valeur})
        for cle in ('signal_body_fraction_min', 'signal_close_location_min'):
            for valeur in (0, 1.01):
                with self.assertRaises(ValueError):
                    self.charger(cle, valeur)

    def test_heures_et_coherences_refusees(self):
        cas = [('range_start_local', '02:00'), ('range_start_local', '02:00:01'),
               ('range_end_local_exclusive', '01:00:00'), ('range_h1_atr_frozen_local', '07:30:00'),
               ('expected_range_m15_bars', self.p.expected_range_m15_bars + 1),
               ('session_start_local', self.p.entry_end_local_exclusive.isoformat()),
               ('force_exit_local', self.p.session_start_local.isoformat()),
               ('range_min_h1_atr', self.p.range_max_h1_atr + 1),
               ('max_filled_entries_per_direction_local_day', self.p.max_filled_entries_per_symbol_local_day + 1)]
        for cle, valeur in cas:
            with self.subTest(cle=cle), self.assertRaises(ValueError):
                self.charger(cle, valeur)

    def test_valeurs_modifiees_conservees_sans_seuil_recopie(self):
        for cle in ('breakout_buffer_atr', 'boundary_stop_inside_atr', 'signal_body_fraction_min',
                    'signal_close_location_min', 'take_profit_gross_price_r'):
            valeur = getattr(self.p, cle) / 2
            with self.subTest(cle=cle):
                self.assertEqual(getattr(self.charger(cle, valeur), cle), valeur)

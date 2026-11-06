"""Catégorie 1, couche 0c (configuration) : lecture stricte, typage clé par clé, empreintes, valeurs exclues."""
from datetime import date, time
import hashlib
import json
import unittest

from reference.technical import canonical_hash
from robot.outils.chemins import DIAGNOSTIC_FAISABILITE, PREUVE_CONSERVATION
from robot.outils.configuration import (json_ia, json_technique, octets_exports, octets_ia_modifies,
                                        octets_technique_modifies)
from xpbots.noyau.c0c_configuration import (CLES_COMMUNES, ErreurConfiguration, analyser_export_ia,
                                            analyser_export_technique, charger_configuration_figee)


def poser(bloc, cle, valeur):
    def modifier(racine):
        racine[bloc][cle] = valeur
    return modifier


class TestExportsReels(unittest.TestCase):
    def setUp(self):
        self.technique, self.ia, self.preuve = octets_exports()
        self.configuration = charger_configuration_figee(self.technique, self.ia, self.preuve)

    def test_empreintes(self):
        preuve = json.loads(PREUVE_CONSERVATION.read_text(encoding='utf-8'))
        technique = self.configuration.technique
        self.assertEqual(technique.empreinte_octets, preuve['frozen_technical_file_sha256'])
        self.assertEqual(self.configuration.ia.empreinte_octets, preuve['frozen_ai_file_sha256'])
        diagnostic = json.loads(DIAGNOSTIC_FAISABILITE.read_text(encoding='utf-8'))
        self.assertEqual(technique.empreinte_canonique, diagnostic['design_sha256'])
        self.assertEqual(technique.empreinte_canonique, canonical_hash(json_technique()))
        self.assertEqual(self.configuration.ia.empreinte_canonique, canonical_hash(json_ia()))

    def test_chaque_cle_de_common_est_typee(self):
        attendu = json_technique()['common']
        self.assertEqual(CLES_COMMUNES, tuple(attendu))
        self.assertEqual(len(CLES_COMMUNES), 73)
        commun = self.configuration.technique.commun
        for cle, valeur in attendu.items():
            with self.subTest(cle=cle):
                type_ = getattr(commun, cle)
                if isinstance(valeur, list):
                    self.assertEqual(type_, tuple(valeur))
                elif isinstance(valeur, dict):
                    self.assertEqual(dict(type_), valeur)
                elif cle == 'frozen_date':
                    self.assertEqual(type_, date.fromisoformat(valeur))
                elif cle.startswith('rollover_blackout'):
                    self.assertEqual(type_, time.fromisoformat(valeur))
                else:
                    self.assertEqual((type_, type(type_)), (valeur, type(valeur)))

    def test_blocs_de_strategie_et_ia_figes(self):
        london = self.configuration.technique.london
        self.assertEqual(dict(london), json_technique()['london'])
        with self.assertRaises(TypeError):
            london['strategy_id'] = 'AUTRE'
        self.assertIsInstance(self.configuration.ia.parametres['providers'], tuple)
        with self.assertRaises(TypeError):
            self.configuration.ia.parametres['providers'][0]['id'] = 'X'
        with self.assertRaises(Exception):
            self.configuration.technique.commun.timeframe_seconds = 60

    def test_fraction_de_marge_est_la_representation_de_un_tiers(self):
        self.assertEqual(self.configuration.technique.commun.max_margin_fraction_of_equity, 1 / 3)


class TestRefus(unittest.TestCase):
    def setUp(self):
        self.technique, self.ia, self.preuve = octets_exports()

    def test_json_strict(self):
        cas = {'clé dupliquée': b'{"common": {}, "common": {}}', 'NaN': b'{"common": NaN}',
               'Infinity': b'{"common": Infinity}', 'BOM': b'\xef\xbb\xbf{}', 'non UTF-8': b'\xff',
               'invalide': b'{', 'racine': b'[]', 'blocs': b'{"common": {}, "london": {}}'}
        for nom, octets in cas.items():
            with self.subTest(cas=nom), self.assertRaises(ErreurConfiguration):
                analyser_export_technique(octets)

    def test_cle_inconnue_ou_manquante(self):
        with self.assertRaises(ErreurConfiguration):
            analyser_export_technique(octets_technique_modifies(poser('common', 'cle_inconnue', 1)))
        with self.assertRaises(ErreurConfiguration):
            analyser_export_technique(octets_technique_modifies(lambda r: r['common'].pop('atr_period')))

    def test_valeurs_non_prises_en_charge(self):
        for cle, valeur in (('bar_price', 'MID'), ('bar_alignment', 'BROKER'), ('atr_method', 'SMA'),
                            ('atr_signal_reference', 'CURRENT_M15'), ('fundamental_mode', 'OPTIONAL'),
                            ('risk_day_timezone', 'Europe/London'), ('default_mode', 'LIVE')):
            with self.subTest(cle=cle), self.assertRaises(ErreurConfiguration):
                analyser_export_technique(octets_technique_modifies(poser('common', cle, valeur)))

    def test_options_exclues_activees(self):
        options = [cle for cle in json_technique()['common']
                   if cle.startswith('allow_') or cle.endswith('_enabled')
                   or cle in ('mandatory_retest', 'new_indicator_vote_score')]
        self.assertEqual(len(options), 15)
        for cle in options:
            with self.subTest(cle=cle), self.assertRaises(ErreurConfiguration):
                analyser_export_technique(octets_technique_modifies(poser('common', cle, True)))

    def test_types_et_bornes(self):
        for cle, valeur in (('timeframe_seconds', 900.0), ('timeframe_seconds', True), ('account_leverage', 0),
                            ('risk_fraction_per_entry', 0), ('risk_fraction_per_entry', 1.5),
                            ('rollover_blackout_utc_start', '21:00'), ('rollover_blackout_utc_end', '25:00:00'),
                            ('active_weekdays_local', [0, 7]), ('universe_priority', ['EURUSD', 'EURUSD']),
                            ('protective_update_retry_delays_seconds', [-1]), ('account_currency', 'usd'),
                            ('frozen_date', '04/11/2026'), ('version', ''), ('structural_buffer_atr', -0.1)):
            with self.subTest(cle=cle, valeur=valeur), self.assertRaises(ErreurConfiguration):
                analyser_export_technique(octets_technique_modifies(poser('common', cle, valeur)))

    def test_incoherences(self):
        cas = {'h1': poser('common', 'h1_seconds', 1000),
               'plafonds': lambda r: r['common']['max_spread_price'].pop('XAUUSD'),
               'stops': poser('common', 'maximum_chart_stop_atr', 0.5),
               'priorité': poser('london', 'strategy_id', 'LONDON_V4')}
        for nom, modifier in cas.items():
            with self.subTest(cas=nom), self.assertRaises(ErreurConfiguration):
                analyser_export_technique(octets_technique_modifies(modifier))

    def test_export_ia(self):
        for cle in ('local_inference_allowed', 'synchronous_llm_on_entry_allowed'):
            with self.subTest(cle=cle), self.assertRaises(ErreurConfiguration):
                analyser_export_ia(octets_ia_modifies(lambda r, c=cle: r.__setitem__(c, True)))
        with self.assertRaises(ErreurConfiguration):
            analyser_export_ia(octets_ia_modifies(lambda r: r.pop('integration_version')))

    def test_valeur_modifiee_lue_mais_refusee_par_le_chargeur(self):
        modifies = octets_technique_modifies(poser('common', 'timeframe_seconds', 300))
        self.assertEqual(analyser_export_technique(modifies).commun.timeframe_seconds, 300)
        with self.assertRaises(ErreurConfiguration):
            charger_configuration_figee(modifies, self.ia, self.preuve)
        with self.assertRaises(ErreurConfiguration):
            charger_configuration_figee(self.technique, octets_ia_modifies(poser_ia('max_api_attempts_per_utc_day', 25)),
                                        self.preuve)

    def test_preuve(self):
        with self.assertRaises(ErreurConfiguration):
            charger_configuration_figee(self.technique, self.ia, b'{"schema": "autre"}')
        self.assertEqual(hashlib.sha256(self.technique).hexdigest(),
                         analyser_export_technique(self.technique).empreinte_octets)


def poser_ia(cle, valeur):
    def modifier(racine):
        racine[cle] = valeur
    return modifier


if __name__ == '__main__':
    unittest.main()

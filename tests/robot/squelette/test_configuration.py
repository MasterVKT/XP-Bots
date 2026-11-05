"""Chargeur minimal de la configuration figée : lecture stricte et absence de valeur codée en dur."""
import unittest

from robot.outils.chemins import CONFIGURATION_TECHNIQUE
from robot.outils.specification import configuration_technique, octets_configuration_modifiee
from xpbots.noyau.squelette import ErreurDonnees, lire_configuration_squelette


class TestConfigurationSquelette(unittest.TestCase):
    def test_export_reel(self):
        configuration = lire_configuration_squelette(CONFIGURATION_TECHNIQUE.read_bytes())
        attendu = configuration_technique()
        self.assertEqual(configuration.duree_bougie_ms, attendu['common']['timeframe_seconds'] * 1000)
        self.assertEqual(configuration.identifiant_strategie, attendu['london']['strategy_id'])

    def test_valeurs_lues_et_non_recopiees(self):
        configuration = lire_configuration_squelette(
            octets_configuration_modifiee(timeframe_seconds=300, strategy_id='AUTRE'))
        self.assertEqual((configuration.duree_bougie_ms, configuration.identifiant_strategie), (300_000, 'AUTRE'))

    def test_refus(self):
        cas = {
            'clé dupliquée': b'{"common": {"timeframe_seconds": 900}, "common": {}}',
            'nombre non fini': b'{"common": {"timeframe_seconds": NaN}, "london": {"strategy_id": "X"}}',
            'clé absente': b'{"common": {}, "london": {"strategy_id": "X"}}',
            'JSON invalide': b'{',
            'non UTF-8': b'\xff\xfe',
            'durée nulle': octets_configuration_modifiee(timeframe_seconds=0),
            'durée booléenne': octets_configuration_modifiee(timeframe_seconds=True),
            'durée décimale': octets_configuration_modifiee(timeframe_seconds=900.5),
            'identifiant vide': octets_configuration_modifiee(strategy_id=''),
        }
        for nom, octets in cas.items():
            with self.subTest(cas=nom), self.assertRaises(ErreurDonnees):
                lire_configuration_squelette(octets)


if __name__ == '__main__':
    unittest.main()

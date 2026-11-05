"""JSON strict et canonique, empreintes et chargeur figé de la configuration technique."""
import importlib.util
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from robot.outils import RACINE, empreinte_bundle_de_la_specification
from xpbots.noyau.config import (BLOCS_TECHNIQUES, ConfigurationInvalide, charger_bundle_technique,
                                 lire_json_strict)
from xpbots.noyau.json_canonique import JSONInvalide, charger_strict, empreinte, serialiser

DEPENDANCES_REFERENCE = all(importlib.util.find_spec(nom) for nom in ('numpy', 'pandas'))


class TestJSONStrict(unittest.TestCase):
    def test_refus_doublons_et_non_finis(self):
        for texte in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}', '{"a":1e400}', '{"a":'):
            with self.subTest(texte=texte), self.assertRaises(JSONInvalide):
                charger_strict(texte)

    def test_octets_utf8_avec_ou_sans_bom(self):
        self.assertEqual(charger_strict('{"é":1}'.encode('utf-8')), {'é': 1})
        self.assertEqual(charger_strict('﻿{"a":1}'.encode('utf-8')), {'a': 1})
        with self.assertRaises(JSONInvalide):
            charger_strict(b'\xff\xfe')

    def test_forme_canonique(self):
        self.assertEqual(serialiser({'b': 1, 'a': [1.5, 'é']}), '{"a":[1.5,"é"],"b":1}')
        for valeur in (float('nan'), Decimal('1.1'), {1: 'a'.encode()}):
            with self.subTest(valeur=valeur), self.assertRaises(JSONInvalide):
                serialiser(valeur)

    def test_empreinte_identique_a_la_reference(self):
        from reference import llm_contracts
        valeur = {'z': [1, 2.5, 'é'], 'a': {'c': None, 'b': True}}
        self.assertEqual(empreinte(valeur), llm_contracts.digest(valeur))


class TestBundleTechnique(unittest.TestCase):
    def setUp(self):
        self.bundle = charger_bundle_technique()

    def test_blocs_et_lecture_seule(self):
        self.assertEqual(tuple(self.bundle.donnees), BLOCS_TECHNIQUES)
        with self.assertRaises(TypeError):
            self.bundle.donnees['common']['risk_fraction_per_entry'] = 0.01
        self.assertIsInstance(self.bundle.valeur('common', 'universe_priority'), tuple)

    def test_empreinte_egale_a_celle_publiee_par_la_specification(self):
        self.assertEqual(self.bundle.empreinte, empreinte_bundle_de_la_specification())
        brut = json.loads((RACINE / 'config' / 'parametres_figes_v3.json').read_text(encoding='utf-8'))
        self.assertEqual(self.bundle.empreinte, empreinte(brut))

    @unittest.skipUnless(DEPENDANCES_REFERENCE, 'numpy et pandas requis par reference.technical')
    def test_empreinte_egale_a_reference_technical(self):
        from reference import technical
        self.assertEqual(self.bundle.empreinte, technical.canonical_hash(technical.frozen_bundle()))

    def test_cle_absente_jamais_remplacee_par_un_defaut(self):
        with self.assertRaises(ConfigurationInvalide):
            self.bundle.valeur('common', 'cle_inexistante')
        with self.assertRaises(ConfigurationInvalide):
            self.bundle.valeur('bloc_inexistant', 'version')

    def test_fichiers_invalides(self):
        with tempfile.TemporaryDirectory() as dossier:
            racine = Path(dossier)
            (racine / 'config').mkdir()
            chemin = racine / 'config' / 'parametres_figes_v3.json'
            for contenu in ('{"common":{},"ema":{}}', '{"common":{},"ema":{},"london":[]}',
                            '{"common":{},"common":{},"ema":{},"london":{}}', 'non json'):
                with self.subTest(contenu=contenu):
                    chemin.write_text(contenu, encoding='utf-8')
                    with self.assertRaises(ConfigurationInvalide):
                        charger_bundle_technique(racine)
            with self.assertRaises(ConfigurationInvalide):
                lire_json_strict(racine / 'absent.json')


if __name__ == '__main__':
    unittest.main()

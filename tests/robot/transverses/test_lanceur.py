"""Le lanceur `tools/run_london_tests.py` : un test en échec rend un code de sortie non nul (phase 1, étape 1).

Chaque cas construit un arbre de tests jetable dans un dossier temporaire et lance le vrai lanceur dans un
processus séparé, avec `--racine-tests` et `--rapport` pointant hors du dépôt.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

from robot.outils.chemins import LANCEUR

REUSSITE = 'import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n'
ECHEC = 'import unittest\nclass T(unittest.TestCase):\n    def test_ko(self):\n        self.assertTrue(False)\n'


class TestLanceur(unittest.TestCase):
    def setUp(self):
        self._dossier = tempfile.TemporaryDirectory()
        self.racine = Path(self._dossier.name) / 'arbre'
        self.racine.mkdir()
        (self.racine / '__init__.py').write_text('', encoding='utf-8')
        self.rapport = Path(self._dossier.name) / 'rapport.json'

    def tearDown(self):
        self._dossier.cleanup()

    def ecrire(self, relatif, contenu):
        chemin = self.racine / relatif
        chemin.parent.mkdir(parents=True, exist_ok=True)
        if chemin.parent != self.racine and not (chemin.parent / '__init__.py').exists():
            (chemin.parent / '__init__.py').write_text('', encoding='utf-8')
        chemin.write_text(textwrap.dedent(contenu), encoding='utf-8')

    def lancer(self, *options):
        execution = subprocess.run([sys.executable, '-B', str(LANCEUR), '--racine-tests', str(self.racine),
                                    '--rapport', str(self.rapport), *options],
                                   capture_output=True, text=True, timeout=120)
        rapport = json.loads(self.rapport.read_text(encoding='utf-8')) if self.rapport.exists() else None
        return execution.returncode, rapport

    def test_tous_verts(self):
        self.ecrire('test_a.py', REUSSITE)
        code, rapport = self.lancer()
        self.assertEqual((code, rapport['statut'], rapport['tests']), (0, 'PASS', 1))

    def test_un_echec_rend_un_code_non_nul(self):
        self.ecrire('test_a.py', REUSSITE)
        self.ecrire('test_b.py', ECHEC)
        code, rapport = self.lancer()
        self.assertEqual(code, 1)
        self.assertEqual((rapport['statut'], rapport['tests'], rapport['echecs']), ('ECHEC', 2, 1))
        self.assertTrue(rapport['en_defaut'][0].endswith('test_ko'))

    def test_module_non_importable_est_une_erreur(self):
        self.ecrire('test_a.py', 'import module_qui_n_existe_pas\n')
        code, rapport = self.lancer()
        self.assertEqual((code, rapport['erreurs']), (1, 1))

    def test_selection_par_artefact_couche_et_categorie(self):
        self.ecrire('demo_art/test_cat1_c0_alpha.py', REUSSITE)
        self.ecrire('demo_art/test_cat2_c1_beta.py', ECHEC)
        self.ecrire('demo_art/test_libre.py', ECHEC)
        self.ecrire('autre/test_cat1_c0_gamma.py', ECHEC)
        code, rapport = self.lancer('--artefact', 'demo-art', '--couche', '0', '--categorie', '1')
        self.assertEqual((code, rapport['tests']), (0, 1))
        code, rapport = self.lancer('--artefact', 'demo-art', '--categorie', '2')
        self.assertEqual((code, rapport['tests'], rapport['echecs']), (1, 1, 1))
        code, rapport = self.lancer('--artefact', 'demo-art')
        self.assertEqual((code, rapport['tests']), (1, 3))

    def test_selection_vide_rend_un_code_non_nul(self):
        self.ecrire('demo_art/test_cat1_c0_alpha.py', REUSSITE)
        code, rapport = self.lancer('--artefact', 'demo-art', '--couche', '2')
        self.assertEqual((code, rapport['statut'], rapport['tests']), (1, 'ECHEC', 0))

    def test_usage_invalide(self):
        self.ecrire('test_a.py', REUSSITE)
        self.assertEqual(self.lancer('--couche', '0')[0], 2)
        self.assertEqual(self.lancer('--artefact', 'inexistant')[0], 2)
        self.assertEqual(self.lancer('--artefact', 'x', '--couche', '0;rm')[0], 2)


if __name__ == '__main__':
    unittest.main()

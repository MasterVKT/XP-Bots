"""Carte MCL composite `mcl/robot-london-v3/` : vérification du code réel et preuve de détection.

Le premier cas exécute `mcl.py verifier` sur le dépôt : toute dépendance non déclarée entre artefacts, toute
dépendance entre artefacts parallèles et toute frontière externe importée hors de ses couches font échouer la
suite. Le second rejoue la vérification sur une copie jetable contenant une violation volontaire.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from robot.outils.chemins import OUTIL_MCL, RACINE_DEPOT

DOSSIER_COMPOSITE = 'mcl/robot-london-v3'


def verifier(racine: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, '-B', str(OUTIL_MCL), '--racine', str(racine), '--dossier',
                           DOSSIER_COMPOSITE, 'verifier'], capture_output=True, text=True, timeout=120)


class TestCarteComposite(unittest.TestCase):
    def test_code_reel_conforme(self):
        execution = verifier(RACINE_DEPOT)
        self.assertEqual(execution.returncode, 0, execution.stdout + execution.stderr)
        self.assertIn('VERT', execution.stdout)

    def test_toutes_les_cartes_sans_avertissement(self):
        """Cas révélé en phase 2 : une dépendance réelle absente d'une carte ne doit jamais passer en simple
        avertissement. Chaque carte d'artefact de `mcl/` se vérifie sans violation ni avertissement."""
        dossiers = sorted(p.parent.name for p in (RACINE_DEPOT / 'mcl').glob('*/carte.json'))
        self.assertIn('noyau', dossiers)
        for nom in dossiers:
            with self.subTest(carte=nom):
                execution = subprocess.run([sys.executable, '-B', str(OUTIL_MCL), '--racine', str(RACINE_DEPOT),
                                            '--dossier', f'mcl/{nom}', 'verifier'],
                                           capture_output=True, text=True, timeout=120)
                self.assertEqual(execution.returncode, 0, execution.stdout)
                self.assertNotIn('AVERTISSEMENTS', execution.stdout)

    def test_violation_detectee(self):
        with tempfile.TemporaryDirectory() as dossier:
            racine = Path(dossier)
            shutil.copytree(RACINE_DEPOT / DOSSIER_COMPOSITE, racine / DOSSIER_COMPOSITE)
            for paquet in ('london', 'execution'):
                (racine / 'src' / 'xpbots' / paquet).mkdir(parents=True)
                (racine / 'src' / 'xpbots' / paquet / '__init__.py').write_text('', encoding='utf-8')
            (racine / 'src' / 'xpbots' / 'london' / 'mauvais.py').write_text(
                'from xpbots.execution import squelette\n', encoding='utf-8')
            execution = verifier(racine)
        self.assertEqual(execution.returncode, 1)
        self.assertIn('paralleles', execution.stdout)


if __name__ == '__main__':
    unittest.main()

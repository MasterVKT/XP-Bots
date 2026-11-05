"""Segment S7 : point d'entrée du rejeu du squelette, codes de sortie et messages d'erreur."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from robot.outils.chemins import CONFIGURATION_TECHNIQUE
from robot.outils.fabrique_ticks import BougieVoulue, ecrire_csv, ticks_de_bougies
from xpbots.app.rejeu_squelette import main


def executer(arguments):
    sortie, erreurs = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(sortie), contextlib.redirect_stderr(erreurs):
        try:
            code = main(arguments)
        except SystemExit as arret:
            code = arret.code
    return code, sortie.getvalue(), erreurs.getvalue()


class TestPointEntree(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.racine = Path(self.dossier.name)

    def tearDown(self):
        self.dossier.cleanup()

    def test_usage_invalide(self):
        code, _, erreurs = executer(['--ticks', 'x.csv'])
        self.assertEqual(code, 2)
        self.assertIn('--configuration', erreurs)

    def test_fichier_absent(self):
        code, sortie, erreurs = executer(['--configuration', str(CONFIGURATION_TECHNIQUE),
                                          '--ticks', str(self.racine / 'absent.csv'),
                                          '--sortie', str(self.racine / 'sortie')])
        self.assertEqual((code, sortie), (1, ''))
        self.assertIn('rejeu_squelette :', erreurs)
        self.assertFalse((self.racine / 'sortie').exists(), 'aucun journal partiel')

    def test_ticks_invalides(self):
        chemin = self.racine / 'ticks.csv'
        chemin.write_text('mauvais,en-tete\n', encoding='utf-8')
        code, _, erreurs = executer(['--configuration', str(CONFIGURATION_TECHNIQUE), '--ticks', str(chemin),
                                     '--sortie', str(self.racine / 'sortie')])
        self.assertEqual(code, 1)
        self.assertIn('en-tête', erreurs)

    def test_configuration_invalide(self):
        configuration = self.racine / 'config.json'
        configuration.write_text('{"common": {}}', encoding='utf-8')
        ticks = ecrire_csv(self.racine / 'ticks.csv',
                           ticks_de_bougies('EURUSD', [BougieVoulue(0, '1.1', '1.1', '1.1', '1.1')]))
        code, _, erreurs = executer(['--configuration', str(configuration), '--ticks', str(ticks),
                                     '--sortie', str(self.racine / 'sortie')])
        self.assertEqual(code, 1)
        self.assertIn('configuration', erreurs)


if __name__ == '__main__':
    unittest.main()

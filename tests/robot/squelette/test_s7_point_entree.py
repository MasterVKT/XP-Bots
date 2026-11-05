"""Segment S7 : point d'entrée du rejeu du squelette, codes de sortie et messages d'erreur."""
import contextlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest

from robot.outils.chemins import CONFIGURATION_IA, CONFIGURATION_TECHNIQUE, PREUVE_CONSERVATION, RACINE_DEPOT
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
        self.assertIn('--sortie', erreurs)

    def test_fichier_absent(self):
        code, sortie, erreurs = executer(['--racine-depot', str(RACINE_DEPOT),
                                          '--ticks', str(self.racine / 'absent.csv'),
                                          '--sortie', str(self.racine / 'sortie')])
        self.assertEqual((code, sortie), (1, ''))
        self.assertIn('rejeu_squelette :', erreurs)
        self.assertFalse((self.racine / 'sortie').exists(), 'aucun journal partiel')

    def test_ticks_invalides(self):
        chemin = self.racine / 'ticks.csv'
        chemin.write_text('mauvais,en-tete\n', encoding='utf-8')
        code, _, erreurs = executer(['--racine-depot', str(RACINE_DEPOT), '--ticks', str(chemin),
                                     '--sortie', str(self.racine / 'sortie')])
        self.assertEqual(code, 1)
        self.assertIn('en-tête', erreurs)

    def depot_copie(self, modifier=None):
        depot = self.racine / 'depot'
        for source, relatif in ((CONFIGURATION_TECHNIQUE, 'config/parametres_figes_v3.json'),
                                (CONFIGURATION_IA, 'config/parametres_IA_integration_v1.json'),
                                (PREUVE_CONSERVATION, 'docs/validation/conservation_ressources.json')):
            (depot / relatif).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, depot / relatif)
        if modifier:
            modifier(depot)
        return depot

    def ticks(self):
        return ecrire_csv(self.racine / 'ticks.csv',
                          ticks_de_bougies('EURUSD', [BougieVoulue(0, '1.1', '1.1', '1.1', '1.1')]))

    def test_configuration_reelle_dans_une_copie_du_depot(self):
        code, sortie, erreurs = executer(['--racine-depot', str(self.depot_copie()), '--ticks', str(self.ticks()),
                                          '--sortie', str(self.racine / 'sortie')])
        self.assertEqual((code, erreurs), (0, ''))

    def test_export_modifie_refuse_par_empreinte(self):
        def alterer(depot):
            chemin = depot / 'config' / 'parametres_figes_v3.json'
            chemin.write_text(chemin.read_text(encoding='utf-8').replace('"timeframe_seconds": 900',
                                                                         '"timeframe_seconds": 300'), encoding='utf-8')
        code, _, erreurs = executer(['--racine-depot', str(self.depot_copie(alterer)), '--ticks', str(self.ticks()),
                                     '--sortie', str(self.racine / 'sortie')])
        self.assertEqual(code, 1)
        self.assertIn('empreinte', erreurs)
        self.assertFalse((self.racine / 'sortie').exists())

    def test_configuration_absente(self):
        code, _, erreurs = executer(['--racine-depot', str(self.racine / 'vide'), '--ticks', str(self.ticks()),
                                     '--sortie', str(self.racine / 'sortie')])
        self.assertEqual(code, 1)
        self.assertIn('rejeu_squelette :', erreurs)


if __name__ == '__main__':
    unittest.main()

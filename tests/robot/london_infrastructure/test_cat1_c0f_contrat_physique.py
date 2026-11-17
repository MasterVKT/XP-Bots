"""Catégorie 1, couche 0f : contrat physique écrit en phase 11, activé en 13.1."""
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF, RAISON, sdk_contrat, registre_contrat
from xpbots.infra.c0f_ticks import LectureTicks

class TestContratTicksPoste(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF, RAISON)
    def test_jeu_mensuel_reel_et_deux_empreintes(self):
        r = registre_contrat()
        with sdk_contrat():
            source = r['contrats_physiques']['ticks']
            with LectureTicks(source['chemin']) as lecture:
                nombre = sum(1 for _ in lecture.lignes())
                self.assertGreater(nombre, 1)
                self.assertEqual(lecture.sha256_fichier, source['sha256_fichier'])
                self.assertEqual(lecture.sha256_contenu, source['sha256_contenu'])

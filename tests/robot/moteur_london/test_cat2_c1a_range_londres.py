"""Catégorie 2, couche 1a : configuration réelle, calendrier réel et extrêmes exacts du range."""
import unittest

from robot.outils.london import JOUR, bougies_range, parametres
from xpbots.london.c1a_range import construire_range


class TestJonctionRange(unittest.TestCase):
    def test_reduction_exacte_des_vingt_m15_du_calendrier(self):
        p = parametres()
        suite = bougies_range(p)
        r = construire_range(JOUR, reversed(suite), p)
        self.assertEqual((r.haut, r.bas), (max(e.bougie.haut for e in suite), min(e.bougie.bas for e in suite)))
        self.assertEqual(r.disponible_ms, max(e.bougie.instant_disponibilite_ms for e in suite))

"""Couche 1a — `tendance_ema` : ordre strict des trois EMA et pente de l'EMA lente (S01.1, S01.6, C11.2)."""
import unittest

from xpbots.moteur_ema.c1a_tendance import sens_tendance
from xpbots.noyau.decisions import Sens


class TestTendance(unittest.TestCase):
    def test_tendances_strictes(self):
        self.assertIs(sens_tendance(1.103, 1.102, 1.101, 1.100), Sens.ACHAT)
        self.assertIs(sens_tendance(1.100, 1.101, 1.102, 1.103), Sens.VENTE)

    def test_ema_egales_aucune_tendance(self):
        for valeurs in ((1.102, 1.102, 1.101, 1.100), (1.103, 1.101, 1.101, 1.100), (1.1, 1.1, 1.1, 1.0),
                        (1.100, 1.101, 1.101, 1.103), (1.101, 1.101, 1.102, 1.103)):
            with self.subTest(valeurs=valeurs):
                self.assertIsNone(sens_tendance(*valeurs))

    def test_pente_nulle_ou_contraire_aucune_tendance(self):
        self.assertIsNone(sens_tendance(1.103, 1.102, 1.101, 1.101))
        self.assertIsNone(sens_tendance(1.103, 1.102, 1.101, 1.102))
        self.assertIsNone(sens_tendance(1.100, 1.101, 1.102, 1.102))
        self.assertIsNone(sens_tendance(1.100, 1.101, 1.102, 1.101))

    def test_ordre_non_aligne(self):
        self.assertIsNone(sens_tendance(1.102, 1.103, 1.101, 1.100))  # EMA rapide sous la moyenne
        self.assertIsNone(sens_tendance(1.103, 1.100, 1.101, 1.099))

    def test_valeurs_indisponibles_refusees(self):
        for valeurs in ((None, 1.0, 1.0, 1.0), (1.0, float('nan'), 1.0, 1.0), (1.0, 1.0, float('inf'), 1.0),
                        (True, 1.0, 1.0, 1.0)):
            with self.subTest(valeurs=valeurs), self.assertRaises(ValueError):
                sens_tendance(*valeurs)


if __name__ == '__main__':
    unittest.main()

"""Couche 1d — `stop_objectif_ema` : tampon, B_SL, plancher, refus au-delà du plafond (S01.4, S01.5)."""
import unittest
from decimal import Decimal

from robot.moteur_ema.outils_ema import P
from xpbots.moteur_ema.c1d_stop import stop_technique
from xpbots.noyau.decisions import Sens

TICK = Decimal('0.00001')
A = 0.00050


class TestExempleS015(unittest.TestCase):
    def test_achat(self):
        stop = stop_technique(Sens.ACHAT, 1.10000, 1.09950, A, TICK, P)
        self.assertAlmostEqual(stop.tampon, 0.00005, places=12)
        self.assertAlmostEqual(stop.b_sl, 1.09945, places=12)
        self.assertAlmostEqual(stop.distance, 0.00055, places=12)
        self.assertFalse(stop.trop_large)

    def test_vente(self):
        stop = stop_technique(Sens.VENTE, 1.10000, 1.10050, A, TICK, P)
        self.assertAlmostEqual(stop.b_sl, 1.10055, places=12)
        self.assertAlmostEqual(stop.distance, 0.00055, places=12)
        self.assertGreater(stop.distance, 0)


class TestRegles(unittest.TestCase):
    def test_plancher_atr(self):
        # Repli peu profond : le stop technique est imposé par le plancher C − 0,80 A.
        stop = stop_technique(Sens.ACHAT, 1.10000, 1.09999, A, TICK, P)
        self.assertEqual(stop.b_sl, 1.10000 - P.stop_min_atr * A)
        stop = stop_technique(Sens.VENTE, 1.10000, 1.10001, A, TICK, P)
        self.assertEqual(stop.b_sl, 1.10000 + P.stop_min_atr * A)

    def test_extreme_donne_utilise_tel_quel(self):
        stop = stop_technique(Sens.ACHAT, 1.10000, 1.09900, A, TICK, P)
        self.assertEqual(stop.b_sl, 1.09900 - stop.tampon)

    def test_tick_superieur_au_tampon_atr(self):
        petit_a = 0.00002
        stop = stop_technique(Sens.ACHAT, 1.10000, 1.09990, petit_a, TICK, P)
        self.assertEqual(stop.tampon, float(TICK))

    def test_trop_large(self):
        extreme = 1.10000 - P.stop_max_atr * A  # tampon en plus : distance > 2,5 A
        stop = stop_technique(Sens.ACHAT, 1.10000, extreme, A, TICK, P)
        self.assertTrue(stop.trop_large)
        self.assertGreater(stop.distance, P.stop_max_atr * A)
        stop = stop_technique(Sens.VENTE, 1.10000, 1.10000 + P.stop_max_atr * A, A, TICK, P)
        self.assertTrue(stop.trop_large)

    def test_entrees_invalides(self):
        for args in ((Sens.ACHAT, 1.1, 1.09, 0.0, TICK), (Sens.ACHAT, 1.1, 1.09, A, 0.00001),
                     (Sens.ACHAT, 1.1, 1.09, A, Decimal('0')), (1, 1.1, 1.09, A, TICK),
                     (Sens.ACHAT, None, 1.09, A, TICK)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                stop_technique(*args, P)


if __name__ == '__main__':
    unittest.main()

"""Couche 1b — `conditions_repli` : armement (R18), validité du repli, contact avec la zone EMA rapide–lente."""
import unittest

from robot.moteur_ema.outils_ema import BUNDLE, P, juste_au_dessus, juste_en_dessous
from xpbots.moteur_ema.c1b_repli import contact, contexte_armement, repli_valide
from xpbots.noyau.decisions import Sens

ACHAT, VENTE = Sens.ACHAT, Sens.VENTE
A = 0.0005
E_LENTE = 1.1000


class TestArmement(unittest.TestCase):
    def test_seuil_armement_r18(self):
        ema = BUNDLE.donnees['ema']
        self.assertTrue(contexte_armement(ACHAT, 1.1010, 1.1005, ema['long_signal_rsi_min'], P))
        self.assertFalse(contexte_armement(ACHAT, 1.1010, 1.1005, juste_en_dessous(ema['long_signal_rsi_min']), P))
        self.assertTrue(contexte_armement(VENTE, 1.1000, 1.1005, ema['short_signal_rsi_max'], P))
        self.assertFalse(contexte_armement(VENTE, 1.1000, 1.1005, juste_au_dessus(ema['short_signal_rsi_max']), P))

    def test_cloture_strictement_au_dela_de_l_ema_rapide(self):
        self.assertFalse(contexte_armement(ACHAT, 1.1005, 1.1005, 60.0, P))
        self.assertFalse(contexte_armement(VENTE, 1.1005, 1.1005, 40.0, P))
        self.assertFalse(contexte_armement(ACHAT, 1.1000, 1.1005, 60.0, P))


class TestValiditeRepli(unittest.TestCase):
    def test_rsi_de_repli_au_seuil_admis(self):
        self.assertTrue(repli_valide(ACHAT, E_LENTE, E_LENTE, P.rsi_repli_long_min, A, P))
        self.assertFalse(repli_valide(ACHAT, E_LENTE, E_LENTE, juste_en_dessous(P.rsi_repli_long_min), A, P))
        self.assertTrue(repli_valide(VENTE, E_LENTE, E_LENTE, P.rsi_repli_court_max, A, P))
        self.assertFalse(repli_valide(VENTE, E_LENTE, E_LENTE, juste_au_dessus(P.rsi_repli_court_max), A, P))

    def test_cloture_exactement_a_la_limite_admise(self):
        limite_achat = E_LENTE - P.depassement_ema_lente_atr * A
        self.assertTrue(repli_valide(ACHAT, limite_achat, E_LENTE, 50.0, A, P))
        self.assertFalse(repli_valide(ACHAT, juste_en_dessous(limite_achat), E_LENTE, 50.0, A, P))
        limite_vente = E_LENTE + P.depassement_ema_lente_atr * A
        self.assertTrue(repli_valide(VENTE, limite_vente, E_LENTE, 50.0, A, P))
        self.assertFalse(repli_valide(VENTE, juste_au_dessus(limite_vente), E_LENTE, 50.0, A, P))

    def test_meche_seule_n_annule_pas(self):
        # Seule la clôture est jugée : la fonction ne reçoit pas le plus bas ; une clôture au-dessus de l'EMA
        # lente, quelle que soit la mèche, reste valide.
        self.assertTrue(repli_valide(ACHAT, E_LENTE + 0.0001, E_LENTE, 45.0, A, P))

    def test_a_t_strictement_positif(self):
        for a in (0.0, -A, float('nan')):
            with self.subTest(a=a), self.assertRaises(ValueError):
                repli_valide(ACHAT, E_LENTE, E_LENTE, 50.0, a, P)


class TestContact(unittest.TestCase):
    def test_bornes_incluses(self):
        self.assertTrue(contact(1.1000, 1.0990, 1.1005, 1.1000))  # haut = min de la zone
        self.assertTrue(contact(1.1010, 1.1005, 1.1005, 1.1000))  # bas = max de la zone
        self.assertFalse(contact(juste_en_dessous(1.1000), 1.0990, 1.1005, 1.1000))
        self.assertFalse(contact(1.1010, juste_au_dessus(1.1005), 1.1005, 1.1000))

    def test_zone_dans_les_deux_ordres(self):
        self.assertTrue(contact(1.1003, 1.1002, 1.1000, 1.1005))  # EMA rapide sous la lente (tendance courte)
        self.assertTrue(contact(1.1010, 1.0990, 1.1002, 1.1001))  # bougie englobant la zone

    def test_bas_superieur_au_haut_refuse(self):
        with self.assertRaises(ValueError):
            contact(1.0990, 1.1000, 1.1, 1.1)


if __name__ == '__main__':
    unittest.main()

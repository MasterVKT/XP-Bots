"""Couche 1c — `bougie_reprise` : conditions S01.3 et cas d'acceptation S01.6."""
import unittest

from robot.moteur_ema.outils_ema import P, fraction_exacte, juste_au_dessus, juste_en_dessous
from xpbots.moteur_ema.c1c_reprise import est_reprise
from xpbots.noyau.decisions import Sens

ACHAT, VENTE = Sens.ACHAT, Sens.VENTE
A = 0.0005


def achat(**changements):
    v = dict(o=1.0995, h=1.1002, l=1.0990, c=1.1000, tr=0.0012, e_rapide=1.0996, rsi=55.0, a_t=A)
    v.update(changements)
    return est_reprise(ACHAT, p=P, **v)


def vente(**changements):
    v = dict(o=1.1005, h=1.1010, l=1.0998, c=1.1000, tr=0.0012, e_rapide=1.1004, rsi=45.0, a_t=A)
    v.update(changements)
    return est_reprise(VENTE, p=P, **v)


class TestReprise(unittest.TestCase):
    def test_cas_nominaux(self):
        self.assertTrue(achat())
        self.assertTrue(vente())

    def test_rsi_du_signal(self):
        self.assertTrue(achat(rsi=P.rsi_signal_long_min))
        self.assertFalse(achat(rsi=P.rsi_signal_long_min - 0.001))  # 49,999 refusé (S01.6)
        self.assertTrue(vente(rsi=P.rsi_signal_court_max))
        self.assertFalse(vente(rsi=P.rsi_signal_court_max + 0.001))

    def test_corps_directionnel_obligatoire(self):
        self.assertFalse(achat(o=1.1000))  # O = C : pas de corps directionnel
        self.assertFalse(vente(o=1.1000))
        self.assertFalse(achat(o=1.1001))

    def test_cloture_au_dela_de_l_ema_rapide(self):
        self.assertFalse(achat(e_rapide=1.1000))
        self.assertFalse(vente(e_rapide=1.1000))

    def test_position_de_cloture_exacte_admise(self):
        bas, haut, c = fraction_exacte(P.position_cloture_min)
        self.assertTrue(achat(l=bas, h=haut, c=c, o=bas, e_rapide=bas, tr=haut - bas))
        self.assertFalse(achat(l=bas, h=haut, c=juste_en_dessous(c), o=bas, e_rapide=bas, tr=haut - bas))
        bas, haut, c = fraction_exacte(P.position_cloture_min, vente=True)
        self.assertTrue(vente(l=bas, h=haut, c=c, o=haut, e_rapide=haut, tr=haut - bas))
        self.assertFalse(vente(l=bas, h=haut, c=juste_au_dessus(c), o=haut, e_rapide=haut, tr=haut - bas))

    def test_true_range_au_plafond(self):
        self.assertTrue(achat(tr=P.tr_max_atr * A))
        self.assertFalse(achat(tr=juste_au_dessus(P.tr_max_atr * A)))  # bougie trop grande > 2,5 A refusée

    def test_range_nul_refuse(self):
        self.assertFalse(achat(o=1.1, h=1.1, l=1.1, c=1.1))

    def test_entrees_invalides(self):
        with self.assertRaises(ValueError):
            achat(a_t=0.0)
        with self.assertRaises(ValueError):
            achat(rsi=None)
        with self.assertRaises(ValueError):
            est_reprise(1, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 50.0, A, P)


if __name__ == '__main__':
    unittest.main()

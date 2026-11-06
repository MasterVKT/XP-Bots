"""Catégorie 1, couche 0b (nombres) : conversion décimale et arrondis sur grille, sémantique de `rounded_levels`."""
from decimal import Decimal, getcontext
import math
import unittest

from xpbots.noyau.c0b_nombres import EPSILON_GRILLE, Arrondi, ErreurNombre, arrondir_sur_grille, decimal_depuis, est_sur_grille


def bas_reference(valeur, pas):
    """Arrondi vers le bas de `rounded_levels` (SL achat, TP vente), en flottants."""
    return math.floor(valeur / pas + 1e-8)


def haut_reference(valeur, pas):
    """Arrondi vers le haut de `rounded_levels` (SL vente, TP achat), en flottants."""
    return math.ceil(valeur / pas - 1e-8)


class TestConversion(unittest.TestCase):
    def test_representation_la_plus_courte(self):
        self.assertEqual(decimal_depuis(0.1), Decimal('0.1'))
        self.assertEqual(decimal_depuis(1.10003), Decimal('1.10003'))
        self.assertEqual(decimal_depuis(1 / 3), Decimal('0.3333333333333333'))
        self.assertEqual(decimal_depuis(100), Decimal(100))
        self.assertEqual(decimal_depuis('15.00'), Decimal('15.00'))
        self.assertEqual(decimal_depuis(Decimal('2.5')), Decimal('2.5'))

    def test_refus(self):
        for valeur in (float('nan'), float('inf'), -float('inf'), True, 'abc', Decimal('NaN'), Decimal('Infinity'), None, [1]):
            with self.subTest(valeur=valeur), self.assertRaises(ErreurNombre):
                decimal_depuis(valeur)
        for pas in (0, -0.00001, 'x'):
            with self.subTest(pas=pas), self.assertRaises(ErreurNombre):
                arrondir_sur_grille(1.0, pas, Arrondi.BAS)
        with self.assertRaises(ErreurNombre):
            arrondir_sur_grille(1.0, 0.1, 'BAS')


class TestGrille(unittest.TestCase):
    def test_sens_et_exposant(self):
        pas = Decimal('0.00001')
        self.assertEqual(arrondir_sur_grille(1.100037, pas, Arrondi.BAS), Decimal('1.10003'))
        self.assertEqual(arrondir_sur_grille(1.100031, pas, Arrondi.HAUT), Decimal('1.10004'))
        self.assertEqual(arrondir_sur_grille(1.1, pas, Arrondi.BAS), Decimal('1.10000'))
        self.assertEqual(arrondir_sur_grille(1.1, pas, Arrondi.BAS).as_tuple().exponent, -5)
        self.assertEqual(arrondir_sur_grille(Decimal('0.237'), Decimal('0.01'), Arrondi.BAS), Decimal('0.23'))

    def test_correction_d_erreur_flottante(self):
        """Une valeur à moins de ε unité de grille d'un point de grille est ramenée sur ce point."""
        pas = Decimal('0.00001')
        sous = 1.10003 - 1e-14
        dessus = 1.10003 + 1e-14
        self.assertEqual(arrondir_sur_grille(sous, pas, Arrondi.BAS), Decimal('1.10003'))
        self.assertEqual(arrondir_sur_grille(dessus, pas, Arrondi.HAUT), Decimal('1.10003'))
        self.assertEqual(arrondir_sur_grille(1.10003 - 2e-13, pas, Arrondi.BAS), Decimal('1.10002'))

    def test_egalite_avec_rounded_levels(self):
        """Comparaison exhaustive sur des valeurs proches et éloignées des points de grille."""
        for pas_texte in ('0.00001', '0.001', '0.01', '0.1'):
            pas_decimal, pas_flottant = Decimal(pas_texte), float(pas_texte)
            for base in range(0, 2000, 7):
                for derive in (0.0, 0.3, 0.5, 0.9999, 1e-10, -1e-10):
                    valeur = (110000 + base + derive) * pas_flottant
                    with self.subTest(pas=pas_texte, valeur=valeur):
                        self.assertEqual(arrondir_sur_grille(valeur, pas_decimal, Arrondi.BAS),
                                         Decimal(bas_reference(valeur, pas_flottant)) * pas_decimal)
                        self.assertEqual(arrondir_sur_grille(valeur, pas_decimal, Arrondi.HAUT),
                                         Decimal(haut_reference(valeur, pas_flottant)) * pas_decimal)

    def test_appartenance(self):
        self.assertTrue(est_sur_grille(1.10003, Decimal('0.00001')))
        self.assertFalse(est_sur_grille(1.100035, Decimal('0.00001')))
        self.assertTrue(est_sur_grille(Decimal('0.20'), '0.01'))

    def test_contexte_global_intact(self):
        precision = getcontext().prec
        arrondir_sur_grille(1.123456789, '0.00001', Arrondi.HAUT)
        self.assertEqual(getcontext().prec, precision)
        self.assertEqual(EPSILON_GRILLE, Decimal('1e-8'))


if __name__ == '__main__':
    unittest.main()

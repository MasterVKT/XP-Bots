"""Catégorie 2, couche 1a (marche) : jonction sur le bloc réel {0a, 0b, 1a}, par chemins représentatifs."""
from decimal import Decimal
import unittest

from xpbots.noyau.c0a_temps import aligner, instant_depuis_iso
from xpbots.noyau.c0b_nombres import Arrondi, arrondir_sur_grille
from xpbots.noyau.c1a_marche import Bougie, Tick, cotation_depuis_tick


class TestJonctionMarche(unittest.TestCase):
    def test_tick_horodate_en_texte_puis_cotation_sur_grille_puis_niveau_arrondi(self):
        instant = instant_depuis_iso('2026-07-15T08:15:00.004Z')
        t = Tick('EURUSD', 'EURUSD', instant, instant + 2, 1, 1.0849, 1.08502)
        cotation = cotation_depuis_tick(t, Decimal('0.00001'))
        stop_vente = arrondir_sur_grille(1.0861234 + float(cotation.spread), Decimal('0.00001'), Arrondi.HAUT)
        self.assertEqual((cotation.bid, cotation.spread, stop_vente), (Decimal('1.08490'), Decimal('0.00012'),
                                                                      Decimal('1.08625')))

    def test_bougie_alignee_sur_l_instant_du_tick_de_frontiere(self):
        duree = 900_000
        frontiere = instant_depuis_iso('2026-07-15T08:15:00Z')
        debut = aligner(frontiere - 1, duree)
        bougie = Bougie('EURUSD', debut, duree, 1.1, 1.1, 1.1, 1.1, 1, True, None, frontiere)
        self.assertEqual((bougie.debut_ms, bougie.fin_ms), (instant_depuis_iso('2026-07-15T08:00:00Z'), frontiere))
        self.assertEqual(aligner(frontiere, duree), bougie.fin_ms, 'le tick de frontière ouvre la bougie suivante')


if __name__ == '__main__':
    unittest.main()

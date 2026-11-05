"""Coutures `Tick`, `Bougie`, `BougieEnrichie` : prix décimaux exacts, intervalle aligné UTC, statuts."""
import unittest
from datetime import date
from decimal import Decimal

from xpbots.noyau.marche import Bougie, BougieEnrichie, DonneeMarcheInvalide, StatutBougie, Tick
from xpbots.noyau.temps import Instant

T = 1793779200000  # 2026-11-04 08:00:00.000 UTC, aligné M15 et H1


def bougie(**changements):
    valeurs = dict(symbole='EURUSD', periode_s=900, ouverture_ms=T, o=Decimal('1.10000'), h=Decimal('1.10020'),
                   l=Decimal('1.09990'), c=Decimal('1.10010'), nb_ticks=3, valide=True)
    valeurs.update(changements)
    return Bougie(**valeurs)


class TestTick(unittest.TestCase):
    def test_tick_valide(self):
        tick = Tick('EURUSD', 'EURUSDsynth', Instant(T, 1), Decimal('1.10000'), Decimal('1.10008'))
        self.assertEqual(tick.ask - tick.bid, Decimal('0.00008'))

    def test_prix_decimaux_finis_positifs(self):
        for bid in (1.1, Decimal('0'), Decimal('-1.1'), Decimal('NaN'), Decimal('Infinity')):
            with self.subTest(bid=bid), self.assertRaises(DonneeMarcheInvalide):
                Tick('EURUSD', 'X', Instant(T), bid, Decimal('1.1'))

    def test_croisement_non_juge_ici(self):
        # Le refus d'une cotation croisée appartient à la garde de cotation C06 (R3), pas au type.
        Tick('EURUSD', 'X', Instant(T), Decimal('1.10010'), Decimal('1.10000'))

    def test_symboles_et_instant(self):
        with self.assertRaises(DonneeMarcheInvalide):
            Tick(' EURUSD', 'X', Instant(T), Decimal('1.1'), Decimal('1.1'))
        with self.assertRaises(DonneeMarcheInvalide):
            Tick('EURUSD', 'X', T, Decimal('1.1'), Decimal('1.1'))


class TestBougie(unittest.TestCase):
    def test_intervalle_et_cloture(self):
        b = bougie()
        self.assertEqual(b.cloture_ms, T + 900 * 1000)
        self.assertEqual(bougie(periode_s=3600).cloture_ms, T + 3600 * 1000)

    def test_alignement_sur_l_epoque_utc(self):
        with self.assertRaises(DonneeMarcheInvalide):
            bougie(ouverture_ms=T + 1)
        with self.assertRaises(DonneeMarcheInvalide):
            bougie(ouverture_ms=T + 900 * 1000, periode_s=3600)

    def test_ohlc_coherent_et_au_moins_un_tick(self):
        with self.assertRaises(DonneeMarcheInvalide):
            bougie(h=Decimal('1.10005'))
        with self.assertRaises(DonneeMarcheInvalide):
            bougie(l=Decimal('1.10001'))
        with self.assertRaises(DonneeMarcheInvalide):
            bougie(nb_ticks=0)
        with self.assertRaises(DonneeMarcheInvalide):
            bougie(valide=1)


class TestBougieEnrichie(unittest.TestCase):
    def test_bougie_invalide_toujours_data_gap(self):
        BougieEnrichie(bougie(valide=False), StatutBougie.DATA_GAP)
        for statut in (StatutBougie.OK, StatutBougie.WARMUP):
            with self.subTest(statut=statut), self.assertRaises(DonneeMarcheInvalide):
                BougieEnrichie(bougie(valide=False), statut)

    def test_indicateurs_flottants_finis_et_figes(self):
        be = BougieEnrichie(bougie(), StatutBougie.OK, {'E15': 1.1}, a_t=0.0005, jour_londres=date(2026, 11, 4))
        with self.assertRaises(TypeError):
            be.indicateurs['E15'] = 2.0
        for indicateurs in ({'E15': 1}, {'E15': float('nan')}, {1: 1.0}):
            with self.subTest(indicateurs=indicateurs), self.assertRaises(DonneeMarcheInvalide):
                BougieEnrichie(bougie(), StatutBougie.OK, indicateurs)

    def test_a_t_strictement_positif(self):
        for a_t in (0.0, -0.1, float('inf'), 1):
            with self.subTest(a_t=a_t), self.assertRaises(DonneeMarcheInvalide):
                BougieEnrichie(bougie(), StatutBougie.OK, a_t=a_t)


if __name__ == '__main__':
    unittest.main()

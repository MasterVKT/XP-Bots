"""Catégorie 1, couche 1a (marche) : contrat propre des ticks, cotations et bougies."""
from decimal import Decimal
import unittest

from xpbots.noyau.c0a_temps import CleEvenement
from xpbots.noyau.c1a_marche import Bougie, Cotation, ErreurMarche, Tick, cotation_depuis_tick

PAS = Decimal('0.00001')


def tick(**changements):
    champs = dict(symbole='EURUSD', symbole_courtier='EURUSDmicro', instant_fournisseur_ms=1000,
                  instant_reception_ms=1005, numero=7, bid=1.10003, ask=1.10013)
    champs.update(changements)
    return Tick(**champs)


def bougie(**changements):
    champs = dict(symbole='EURUSD', debut_ms=900_000, duree_ms=900_000, ouverture=1.1, haut=1.2, bas=1.0,
                  cloture=1.15, nombre_evenements=4, valide=True, motif_invalidite=None,
                  instant_disponibilite_ms=1_800_000)
    champs.update(changements)
    return Bougie(**champs)


class TestTick(unittest.TestCase):
    def test_valide(self):
        t = tick(bid=1, drapeaux=6)
        self.assertEqual((t.bid, type(t.bid), t.drapeaux), (1.0, float, 6))
        self.assertEqual(t.cle, CleEvenement(1005, 7))
        self.assertEqual(tick().drapeaux, 0)

    def test_refus(self):
        for changement in ({'symbole': ''}, {'symbole_courtier': None}, {'instant_fournisseur_ms': -1},
                           {'instant_reception_ms': 1.5}, {'numero': -1}, {'numero': True}, {'bid': 0},
                           {'ask': -1.0}, {'bid': float('nan')}, {'ask': float('inf')}, {'bid': True},
                           {'bid': '1.1'}, {'drapeaux': -2}):
            with self.subTest(changement=changement), self.assertRaises(ErreurMarche):
                tick(**changement)


class TestCotation(unittest.TestCase):
    def test_depuis_tick(self):
        cotation = cotation_depuis_tick(tick(), PAS)
        self.assertEqual((cotation.bid, cotation.ask, cotation.spread), (Decimal('1.10003'), Decimal('1.10013'), Decimal('0.00010')))
        self.assertEqual((cotation.instant_fournisseur_ms, cotation.instant_reception_ms), (1000, 1005))

    def test_cotation_croisee_representable(self):
        cotation = cotation_depuis_tick(tick(bid=1.10013, ask=1.10003), PAS)
        self.assertLess(cotation.spread, 0)

    def test_refus(self):
        with self.assertRaises(ErreurMarche):
            cotation_depuis_tick(tick(bid=1.100035), PAS)
        with self.assertRaises(ErreurMarche):
            cotation_depuis_tick(tick(), Decimal('0'))
        with self.assertRaises(ErreurMarche):
            cotation_depuis_tick('tick', PAS)
        for bid in (1.1, Decimal('NaN'), Decimal('0')):
            with self.subTest(bid=bid), self.assertRaises(ErreurMarche):
                Cotation('EURUSD', bid, Decimal('1.2'), 0, 0)


class TestBougie(unittest.TestCase):
    def test_valide(self):
        b = bougie(haut=2, bas=1)
        self.assertEqual((b.fin_ms, b.haut, type(b.haut)), (1_800_000, 2.0, float))

    def test_invalide_sans_prix(self):
        b = bougie(ouverture=None, haut=None, bas=None, cloture=None, nombre_evenements=0, valide=False,
                   motif_invalidite='AUCUN_BID')
        self.assertFalse(b.valide)

    def test_refus(self):
        for changement in ({'debut_ms': 900_001}, {'duree_ms': 0}, {'bas': 1.12}, {'haut': 1.14},
                           {'ouverture': None}, {'nombre_evenements': 0}, {'motif_invalidite': 'X'},
                           {'valide': 1}, {'instant_disponibilite_ms': 1_799_999}, {'cloture': float('nan')},
                           {'valide': False, 'motif_invalidite': None}, {'valide': False, 'motif_invalidite': 'aucun'},
                           {'valide': False, 'motif_invalidite': 'TROU', 'haut': None}):
            with self.subTest(changement=changement), self.assertRaises(ErreurMarche):
                bougie(**changement)

    def test_immuable(self):
        with self.assertRaises(Exception):
            bougie().haut = 3.0


if __name__ == '__main__':
    unittest.main()

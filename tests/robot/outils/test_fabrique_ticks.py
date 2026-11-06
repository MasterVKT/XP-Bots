"""Contrôles de la fabrique de ticks : reproductibilité, ordre, frontières, jours de changement d'heure."""
from datetime import date
from decimal import Decimal
import unittest

from robot.outils.fabrique_ticks import (DECALAGES_MS, BougieVoulue, bornes_journee_londres, journee_londres,
                                         lignes_csv, ticks_de_bougies)
from robot.outils.specification import configuration_technique

DUREE_MS = configuration_technique()['common']['timeframe_seconds'] * 1000


class TestFabriqueTicks(unittest.TestCase):
    def test_reproductible(self):
        self.assertEqual(journee_londres(date(2026, 7, 15), duree_ms=DUREE_MS),
                         journee_londres(date(2026, 7, 15), duree_ms=DUREE_MS))

    def test_ordre_strict_et_frontieres(self):
        bougies, ticks = journee_londres(date(2026, 7, 15), duree_ms=DUREE_MS)
        cles = [(t.instant_ms, t.sequence) for t in ticks]
        self.assertEqual(cles, sorted(set(cles)))
        debuts = {t.instant_ms for t in ticks}
        self.assertTrue(all(b.debut_ms in debuts for b in bougies), 'chaque bougie commence par un tick de frontière')
        self.assertEqual(ticks[-1].instant_ms, bornes_journee_londres(date(2026, 7, 15))[1])

    def test_ohlc_respectes(self):
        bougie = BougieVoulue(0, '1.10000', '1.10050', '1.09950', '1.09980')
        ticks = ticks_de_bougies('EURUSD', [bougie])
        self.assertEqual([t.instant_ms for t in ticks], list(DECALAGES_MS))
        self.assertEqual([t.bid for t in ticks], ['1.10000', '1.10050', '1.09950', '1.09980'])
        self.assertTrue(all(Decimal(t.ask) - Decimal(t.bid) == Decimal('0.00010') for t in ticks))
        with self.assertRaises(ValueError):
            ticks_de_bougies('EURUSD', [BougieVoulue(0, '1.1', '1.0', '1.2', '1.1')])

    def test_jours_de_londres(self):
        attendus = {date(2026, 7, 15): 24, date(2026, 1, 14): 24, date(2026, 3, 29): 23, date(2026, 10, 25): 25}
        for jour, heures in attendus.items():
            with self.subTest(jour=jour):
                debut, fin = bornes_journee_londres(jour)
                self.assertEqual(fin - debut, heures * 3_600_000)
                bougies, _ = journee_londres(jour, duree_ms=DUREE_MS)
                self.assertEqual(len(bougies) * DUREE_MS, heures * 3_600_000)

    def test_lignes_csv(self):
        lignes = lignes_csv(ticks_de_bougies('EURUSD', [BougieVoulue(0, '1.1', '1.1', '1.1', '1.1')]))
        self.assertEqual(lignes[0], 'canonical_symbol,broker_symbol,time_utc_ms,sequence,bid,ask')
        self.assertEqual(lignes[1], 'EURUSD,EURUSD,0,1,1.10000,1.10010')


if __name__ == '__main__':
    unittest.main()

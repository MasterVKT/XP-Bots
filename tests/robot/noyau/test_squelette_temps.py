"""Couture `Instant` : millisecondes UTC, départage stable, format ISO strict (C03 point 1)."""
import unittest

from xpbots.noyau.temps import Instant, InstantInvalide, iso_depuis_ms, ms_depuis_iso


class TestInstant(unittest.TestCase):
    def test_ordre_ms_puis_sequence(self):
        self.assertLess(Instant(1000, 5), Instant(1001, 0))
        self.assertLess(Instant(1000, 1), Instant(1000, 2))
        self.assertEqual(sorted([Instant(2, 0), Instant(1, 9), Instant(1, 3)]),
                         [Instant(1, 3), Instant(1, 9), Instant(2, 0)])

    def test_entiers_stricts(self):
        for valeur in (1.0, True, '1', None):
            with self.subTest(valeur=valeur), self.assertRaises(InstantInvalide):
                Instant(valeur)
        with self.assertRaises(InstantInvalide):
            Instant(0, -1)

    def test_iso_aller_retour_a_la_milliseconde(self):
        # Exemple du cahier de données : 1609747200123 ms.
        self.assertEqual(iso_depuis_ms(1609747200123), '2021-01-04T08:00:00.123Z')
        for ms in (0, 1, 999, 1609747200123, 1793779200000, 1793786399999):
            with self.subTest(ms=ms):
                self.assertEqual(ms_depuis_iso(iso_depuis_ms(ms)), ms)
        self.assertEqual(Instant(1609747200123, 4).iso(), '2021-01-04T08:00:00.123Z')

    def test_formats_refuses(self):
        for texte in ('2021-01-04T08:00:00Z', '2021-01-04T08:00:00.123+00:00', '2021-01-04 08:00:00.123Z',
                      '2021-13-01T00:00:00.000Z', '2021-01-04T08:00:00.1234Z', 1609747200123):
            with self.subTest(texte=texte), self.assertRaises(InstantInvalide):
                ms_depuis_iso(texte)


if __name__ == '__main__':
    unittest.main()

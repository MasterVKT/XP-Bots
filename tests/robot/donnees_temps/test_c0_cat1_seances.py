"""Couche 0 — `calendrier_seances` : séances natives [début, fin), période connue, portions ouvertes."""
import unittest

from xpbots.donnees_temps.c0_parametres_seances import CalendrierInconnu, CalendrierSeances

H = 3_600_000
T0 = 1793779200000  # mercredi 2026-11-04 08:00 UTC


def calendrier():
    # Période connue [T0, T0+24h) ; deux séances séparées par une pause d'une heure.
    return CalendrierSeances('EURUSD', ((T0, T0 + 13 * H), (T0 + 14 * H, T0 + 24 * H)), T0, T0 + 24 * H)


class TestCalendrierSeances(unittest.TestCase):
    def test_debut_inclus_fin_exclue(self):
        c = calendrier()
        self.assertTrue(c.en_seance(T0))
        self.assertTrue(c.en_seance(T0 + 13 * H - 1))
        self.assertFalse(c.en_seance(T0 + 13 * H))
        self.assertFalse(c.en_seance(T0 + 14 * H - 1))
        self.assertTrue(c.en_seance(T0 + 14 * H))

    def test_portion_ouverte(self):
        c = calendrier()
        self.assertEqual(c.portion_ouverte(T0 + 12 * H, T0 + 15 * H), ((T0 + 12 * H, T0 + 13 * H),
                                                                        (T0 + 14 * H, T0 + 15 * H)))
        self.assertEqual(c.portion_ouverte(T0 + 13 * H, T0 + 14 * H), ())
        self.assertEqual(c.portion_ouverte(T0, T0 + 900_000), ((T0, T0 + 900_000),))

    def test_prochaine_fermeture(self):
        c = calendrier()
        self.assertEqual(c.prochaine_fermeture(T0 + H), T0 + 13 * H)
        self.assertIsNone(c.prochaine_fermeture(T0 + 13 * H + 1))
        self.assertEqual(c.prochaine_fermeture(T0 + 20 * H), T0 + 24 * H)

    def test_hors_periode_connue(self):
        c = calendrier()
        for appel in (lambda: c.en_seance(T0 - 1), lambda: c.en_seance(T0 + 24 * H),
                      lambda: c.portion_ouverte(T0 - 1, T0 + H), lambda: c.portion_ouverte(T0, T0 + 25 * H)):
            with self.assertRaises(CalendrierInconnu):
                appel()

    def test_intervalles_mal_formes(self):
        for ouvertures in (((T0 + H, T0),), ((T0, T0 + 2 * H), (T0 + H, T0 + 3 * H)),
                           ((T0 + 2 * H, T0 + 3 * H), (T0, T0 + H)), ((T0 - 1, T0 + H),),
                           ((T0, T0 + 25 * H),), ((T0, float(T0 + H)),)):
            with self.subTest(ouvertures=ouvertures), self.assertRaises(ValueError):
                CalendrierSeances('EURUSD', ouvertures, T0, T0 + 24 * H)
        with self.assertRaises(ValueError):
            CalendrierSeances('EURUSD', (), T0, T0)

    def test_seances_adjacentes_admises_et_marche_ferme(self):
        c = CalendrierSeances('EURUSD', ((T0, T0 + H), (T0 + H, T0 + 2 * H)), T0, T0 + 3 * H)
        self.assertTrue(c.en_seance(T0 + H))
        ferme = CalendrierSeances('EURUSD', (), T0, T0 + H)
        self.assertFalse(ferme.en_seance(T0))
        self.assertEqual(ferme.portion_ouverte(T0, T0 + H), ())


if __name__ == '__main__':
    unittest.main()

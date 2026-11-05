"""Couche 1b — `constructeur_bougies` : frontières, couverture, séances, trous R4, H1 invisible avant clôture."""
import unittest
from decimal import Decimal

from xpbots.donnees_temps.c0_parametres_seances import CalendrierInconnu, CalendrierSeances
from xpbots.donnees_temps.c1b_bougies import (MOTIF_COUVERTURE, MOTIF_SANS_BID, ConstructeurBougies,
                                              HorlogeEnRecul, TickHorsOrdre)
from xpbots.noyau.marche import Tick
from xpbots.noyau.temps import Instant

T0 = 1793779200000  # mercredi 08:00 UTC
M15, H = 900_000, 3_600_000


def tick(t, bid='1.10000', sequence=0, symbole='EURUSD'):
    b = Decimal(bid)
    return Tick(symbole, symbole + 'synth', Instant(t, sequence), b, b + Decimal('0.00008'))


def ouvert(debut=T0, fin=T0 + 24 * H):
    return CalendrierSeances('EURUSD', ((debut, fin),), debut, fin)


def constructeur(seances=None, debut=T0, periode=900, couverture=True):
    c = ConstructeurBougies('EURUSD', periode, seances or ouvert(), debut)
    if couverture:
        c.couverture(debut, True)
    return c


class TestFrontieres(unittest.TestCase):
    def test_tick_de_frontiere_dans_l_intervalle_suivant(self):
        c = constructeur()
        self.assertEqual(c.ajouter_tick(tick(T0 + 1, '1.10000', 1)), [])
        self.assertEqual(c.ajouter_tick(tick(T0 + M15 - 1, '1.10020', 2)), [])
        closes = c.ajouter_tick(tick(T0 + M15, '1.10500', 3))
        self.assertEqual(len(closes), 1)
        b = closes[0].bougie
        self.assertEqual((closes[0].ouverture_ms, closes[0].cloture_ms), (T0, T0 + M15))
        self.assertEqual((b.o, b.h, b.l, b.c, b.nb_ticks, b.valide),
                         (Decimal('1.10000'), Decimal('1.10020'), Decimal('1.10000'), Decimal('1.10020'), 2, True))
        suivante = c.avancer(T0 + 2 * M15)[0].bougie
        self.assertEqual((suivante.o, suivante.nb_ticks), (Decimal('1.10500'), 1))

    def test_egalites_de_milliseconde_par_sequence(self):
        c = constructeur()
        c.ajouter_tick(tick(T0 + 5, sequence=1))
        c.ajouter_tick(tick(T0 + 5, '1.10010', sequence=2))
        with self.assertRaises(TickHorsOrdre):
            c.ajouter_tick(tick(T0 + 5, sequence=2))
        with self.assertRaises(TickHorsOrdre):
            c.ajouter_tick(tick(T0 + 4, sequence=9))
        self.assertEqual(c.avancer(T0 + M15)[0].bougie.c, Decimal('1.10010'))

    def test_cloture_par_l_horloge_et_minute_inchangee(self):
        c = constructeur()
        for i in range(10):  # même Bid pendant dix minutes : aucun trou
            c.ajouter_tick(tick(T0 + i * 60_000 + 1, sequence=i + 1))
        self.assertEqual(c.avancer(T0 + M15 - 1), [])
        cloture, = c.avancer(T0 + M15)
        self.assertTrue(cloture.complet)
        self.assertTrue(cloture.bougie.valide)

    def test_h1_invisible_avant_sa_cloture(self):
        c = constructeur(periode=3600)
        c.ajouter_tick(tick(T0 + 10))
        c.ajouter_tick(tick(T0 + H - 10, '1.10100', 1))
        self.assertEqual(c.avancer(T0 + H - 1), [])
        h1, = c.avancer(T0 + H)
        self.assertEqual((h1.bougie.periode_s, h1.bougie.c, h1.cloture_ms), (3600, Decimal('1.10100'), T0 + H))


class TestQualification(unittest.TestCase):
    def test_interruption_inexpliquee(self):
        c = constructeur()
        c.ajouter_tick(tick(T0 + 1))
        c.couverture(T0 + 300_000, False)
        c.couverture(T0 + 600_000, True)
        cloture, = c.avancer(T0 + M15)
        self.assertEqual((cloture.attendu, cloture.complet, cloture.motif_incomplet),
                         (True, False, MOTIF_COUVERTURE))
        self.assertFalse(cloture.bougie.valide)

    def test_intervalle_attendu_sans_bid_r4(self):
        c = constructeur()
        c.ajouter_tick(tick(T0 + 1))
        premiere, vide = c.avancer(T0 + 2 * M15)
        self.assertTrue(premiere.complet)
        self.assertEqual((vide.bougie, vide.attendu, vide.complet, vide.motif_incomplet),
                         (None, True, False, MOTIF_SANS_BID))

    def test_fermeture_officielle_n_est_pas_un_trou(self):
        seances = CalendrierSeances('EURUSD', ((T0, T0 + H), (T0 + 2 * H, T0 + 24 * H)), T0, T0 + 24 * H)
        c = constructeur(seances, debut=T0 + H - M15)  # observation à partir du dernier quart d'heure ouvert
        closes = c.ajouter_tick(tick(T0 + H - 1))
        closes += c.couverture(T0 + H + 1, False)       # flux coupé pendant la fermeture : sans effet
        closes += c.couverture(T0 + 2 * H, True)
        closes += c.ajouter_tick(tick(T0 + 2 * H + 1, sequence=1))
        closes += c.avancer(T0 + 2 * H + M15)
        self.assertEqual([(cl.ouverture_ms, cl.complet) for cl in closes],
                         [(T0 + H - M15, True), (T0 + 2 * H, True)])

    def test_tick_pendant_une_fermeture_officielle(self):
        seances = CalendrierSeances('EURUSD', ((T0, T0 + H),), T0, T0 + 24 * H)
        c = constructeur(seances)
        c.couverture(T0 + H, False)
        c.ajouter_tick(tick(T0 + H + 1))
        cloture, = c.avancer(T0 + H + M15)
        self.assertEqual((cloture.attendu, cloture.complet, cloture.motif_incomplet), (False, True, None))

    def test_transition_a_l_instant_de_cloture(self):
        c = constructeur()
        c.ajouter_tick(tick(T0 + 1))
        cloture, = c.couverture(T0 + M15, False)
        self.assertTrue(cloture.complet)
        self.assertTrue(cloture.couverture_etablie)  # la transition à l'instant de clôture vaut pour la suite
        self.assertFalse(c.couverture_etablie)
        c.ajouter_tick(tick(T0 + M15 + 1, sequence=1))
        self.assertEqual(c.avancer(T0 + 2 * M15)[0].motif_incomplet, MOTIF_COUVERTURE)

    def test_sans_couverture_initiale(self):
        c = constructeur(couverture=False)
        c.ajouter_tick(tick(T0 + 1))
        self.assertEqual(c.avancer(T0 + M15)[0].motif_incomplet, MOTIF_COUVERTURE)


class TestObservation(unittest.TestCase):
    def test_debut_non_aligne_ignore_l_intervalle_partiel(self):
        c = constructeur(debut=T0 + 100)
        c.ajouter_tick(tick(T0 + 200))
        c.ajouter_tick(tick(T0 + M15 + 1, sequence=1))
        self.assertEqual(c.ticks_ignores, 1)
        cloture, = c.avancer(T0 + 2 * M15)
        self.assertEqual(cloture.ouverture_ms, T0 + M15)

    def test_intervalle_final_abandonne(self):
        c = constructeur()
        c.ajouter_tick(tick(T0 + 5))
        self.assertEqual(c.terminer(T0 + 10), [])
        self.assertTrue(c.intervalle_final_abandonne)
        with self.assertRaises(RuntimeError):
            c.avancer(T0 + M15)

    def test_horloge_et_symbole(self):
        c = constructeur()
        c.avancer(T0 + 10)
        with self.assertRaises(HorlogeEnRecul):
            c.avancer(T0 + 5)
        with self.assertRaises(TickHorsOrdre):
            c.ajouter_tick(tick(T0 + 20, symbole='GBPUSD'))
        with self.assertRaises(ValueError):
            ConstructeurBougies('GBPUSD', 900, ouvert(), T0)

    def test_seances_inconnues(self):
        c = ConstructeurBougies('EURUSD', 900, ouvert(T0, T0 + H), T0)
        c.couverture(T0, True)
        c.avancer(T0 + H)
        with self.assertRaises(CalendrierInconnu):
            c.avancer(T0 + H + M15)


if __name__ == '__main__':
    unittest.main()

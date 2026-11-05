"""Segment S2 : agrégation Bid en bougies closes, tick de frontière (C03.2), ordre des ticks."""
import unittest

from robot.outils.fabrique_ticks import BougieVoulue, ticks_de_bougies
from robot.outils.specification import configuration_technique
from xpbots.donnees.squelette import AgregateurM15, ErreurAgregation as ErreurDonnees
from xpbots.noyau.c1a_marche import Bougie, Tick

DUREE = configuration_technique()['common']['timeframe_seconds'] * 1000


def tick(instant, bid, sequence=0, symbole='EURUSD'):
    return Tick(symbole, symbole, instant, instant, sequence, bid, bid + 0.0001)


class TestAgregation(unittest.TestCase):
    def test_tick_de_frontiere_clot_la_bougie_precedente(self):
        agregateur = AgregateurM15('EURUSD', DUREE)
        self.assertEqual(agregateur.ajouter(tick(0, 1.0)), ())
        self.assertEqual(agregateur.ajouter(tick(DUREE - 1, 1.5, 1)), ())
        closes = agregateur.ajouter(tick(DUREE, 2.0, 2))
        self.assertEqual(closes, (Bougie('EURUSD', 0, DUREE, 1.0, 1.5, 1.0, 1.5, 2, True, None, DUREE),))
        self.assertEqual(closes[0].instant_disponibilite_ms, DUREE, 'disponible à la réception du tick de frontière')
        closes = agregateur.ajouter(tick(2 * DUREE, 3.0, 3))
        self.assertEqual(closes[0].ouverture, 2.0, 'le tick de frontière ouvre la bougie suivante')

    def test_ohlc_des_bougies_voulues(self):
        voulues = [BougieVoulue(i * DUREE, '1.10000', '1.10040', '1.09970', c)
                   for i, c in enumerate(('1.10020', '1.09980'))]
        ticks = ticks_de_bougies('EURUSD', voulues)
        ticks.append(ticks_de_bougies('EURUSD', [BougieVoulue(2 * DUREE, '1.1', '1.1', '1.1', '1.1')],
                                      sequence_initiale=99)[0])
        agregateur = AgregateurM15('EURUSD', DUREE)
        closes = [b for t in ticks for b in agregateur.ajouter(
            Tick(t.symbole, t.symbole_courtier, t.instant_ms, t.instant_ms, t.sequence, float(t.bid), float(t.ask)))]
        self.assertEqual([(b.ouverture, b.haut, b.bas, b.cloture, b.nombre_evenements) for b in closes],
                         [(float(v.ouverture), float(v.haut), float(v.bas), float(v.cloture), 4) for v in voulues])

    def test_le_prix_ask_est_ignore(self):
        agregateur = AgregateurM15('EURUSD', DUREE)
        agregateur.ajouter(Tick('EURUSD', 'EURUSD', 0, 0, 0, 1.0, 9.0))
        bougie = agregateur.ajouter(tick(DUREE, 1.0, 1))[0]
        self.assertEqual((bougie.haut, bougie.bas), (1.0, 1.0))

    def test_intervalle_sans_tick_ne_cree_aucune_bougie(self):
        agregateur = AgregateurM15('EURUSD', DUREE)
        agregateur.ajouter(tick(0, 1.0))
        closes = agregateur.ajouter(tick(3 * DUREE + 5, 1.0, 1))
        self.assertEqual([(b.debut_ms, b.fin_ms) for b in closes], [(0, DUREE)])

    def test_meme_milliseconde_ordonnee_par_sequence(self):
        agregateur = AgregateurM15('EURUSD', DUREE)
        agregateur.ajouter(tick(10, 1.0, 5))
        agregateur.ajouter(tick(10, 1.2, 6))
        self.assertEqual(agregateur.ajouter(tick(DUREE, 1.0, 7))[0].cloture, 1.2)

    def test_refus(self):
        agregateur = AgregateurM15('EURUSD', DUREE)
        agregateur.ajouter(tick(100, 1.0, 1))
        for nom, mauvais in {'recul': tick(50, 1.0, 2), 'doublon': tick(100, 1.0, 1),
                             'autre symbole': tick(200, 1.0, 3, 'GBPUSD')}.items():
            with self.subTest(cas=nom), self.assertRaises(ErreurDonnees):
                agregateur.ajouter(mauvais)
        for duree in (0, -1, True):
            with self.subTest(duree=duree), self.assertRaises(ValueError):
                AgregateurM15('EURUSD', duree)


if __name__ == '__main__':
    unittest.main()

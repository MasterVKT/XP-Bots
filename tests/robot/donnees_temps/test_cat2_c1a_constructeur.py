"""Catégorie 2, couche 1a : jonction {0a, 1a} et noyau sur une journée synthétique, M15 et H1 depuis les mêmes ticks."""
from datetime import date
import unittest

from robot.outils.configuration import configuration_figee
from robot.outils.fabrique_ticks import journee_londres
from xpbots.donnees.c0a_types import UniteTemps
from xpbots.donnees.c1a_constructeur import ConstructeurBougies
from xpbots.noyau.c1a_marche import Tick

COMMUN = configuration_figee().technique.commun


class TestJonctionConstructeur(unittest.TestCase):
    def test_m15_et_h1_d_une_journee_de_londres(self):
        m15, h1 = UniteTemps.M15.duree_ms(COMMUN), UniteTemps.H1.duree_ms(COMMUN)
        voulues, ticks = journee_londres(date(2026, 7, 15), duree_ms=m15)
        constructeurs = {u: ConstructeurBougies('EURUSD', u.duree_ms(COMMUN)) for u in UniteTemps}
        sorties = {u: [] for u in UniteTemps}
        for t in ticks:
            tick = Tick(t.symbole, t.symbole_courtier, t.instant_ms, t.instant_ms, t.sequence, float(t.bid), float(t.ask))
            for unite, constructeur in constructeurs.items():
                sorties[unite].extend(constructeur.ajouter(tick).bougies)
        self.assertEqual([(b.debut_ms, b.ouverture, b.haut, b.bas, b.cloture) for b in sorties[UniteTemps.M15]],
                         [(v.debut_ms, float(v.ouverture), float(v.haut), float(v.bas), float(v.cloture)) for v in voulues])
        horaires = sorties[UniteTemps.H1]
        self.assertEqual(len(horaires), 24)
        for i, bougie in enumerate(horaires):
            quatre = sorties[UniteTemps.M15][4 * i:4 * i + 4]
            self.assertEqual((bougie.debut_ms, bougie.duree_ms), (quatre[0].debut_ms, h1))
            self.assertEqual((bougie.haut, bougie.bas, bougie.ouverture, bougie.cloture),
                             (max(b.haut for b in quatre), min(b.bas for b in quatre), quatre[0].ouverture, quatre[-1].cloture))


if __name__ == '__main__':
    unittest.main()

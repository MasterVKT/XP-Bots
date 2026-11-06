"""Catégorie 2, couche 1b : chaîne TR/ATR/A sur les bougies réelles du constructeur, comparée à `add_indicators`."""
from datetime import date
import math
import unittest

import pandas as pd

from reference.technical import add_indicators
from robot.outils.configuration import configuration_figee
from robot.outils.fabrique_ticks import journee_londres
from xpbots.donnees.c0a_types import UniteTemps
from xpbots.donnees.c1a_constructeur import ConstructeurBougies
from xpbots.donnees.c1b_indicateurs import avancer, etat_initial
from xpbots.noyau.c1a_marche import Tick

COMMUN = configuration_figee().technique.commun


class TestJonctionIndicateurs(unittest.TestCase):
    def test_journee_construite_puis_indicateurs_egaux_a_add_indicators(self):
        duree = UniteTemps.M15.duree_ms(COMMUN)
        _, ticks = journee_londres(date(2026, 1, 14), duree_ms=duree)
        constructeur, bougies = ConstructeurBougies('EURUSD', duree), []
        for t in ticks:
            bougies.extend(constructeur.ajouter(Tick(t.symbole, t.symbole, t.instant_ms, t.instant_ms, t.sequence,
                                                     float(t.bid), float(t.ask))).bougies)
        etat, robot = etat_initial(COMMUN.atr_period), []
        for b in bougies:
            resultat = avancer(etat, b.haut, b.bas, b.cloture)
            etat = resultat.etat
            robot.append((resultat.tr, resultat.atr, resultat.a))
        cadre = pd.DataFrame({'O': [b.ouverture for b in bougies], 'H': [b.haut for b in bougies],
                              'L': [b.bas for b in bougies], 'C': [b.cloture for b in bougies]},
                             index=pd.to_datetime([b.debut_ms for b in bougies], unit='ms', utc=True))
        reference = add_indicators(cadre)
        for i, (tr, atr, a) in enumerate(robot):
            with self.subTest(i=i):
                self.assertTrue(math.isclose(tr, reference.TR.iloc[i], rel_tol=1e-12, abs_tol=1e-15))
                for valeur, attendu in ((atr, reference.ATR.iloc[i]), (a, reference.A.iloc[i])):
                    if valeur is None:
                        self.assertTrue(math.isnan(attendu))
                    else:
                        self.assertTrue(math.isclose(valeur, attendu, rel_tol=1e-12))


if __name__ == '__main__':
    unittest.main()

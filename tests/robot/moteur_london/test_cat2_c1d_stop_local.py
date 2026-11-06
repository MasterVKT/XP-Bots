"""Catégorie 2, couche 1d : stop et symétrie comparés à london_signal, exemple S02.5 cité."""
from decimal import Decimal
import math
from types import SimpleNamespace
import unittest

from reference.technical import london_signal
from robot.outils.london import TICK, bougie, miroir, parametres, range_connu
from xpbots.london.c1d_stop import calculer_stop
from xpbots.noyau.c1c_domaine import Sens


class TestJonctionStop(unittest.TestCase):
    def test_stop_egal_a_l_oracle_et_objectif_lu(self):
        p = parametres()
        exemple = bougie(o=1.09995, h=1.10055, l=1.09990, c=1.10050, a=0.00050, tr=0.00065)
        cas = [(bougie(), range_connu(), TICK, Sens.ACHAT),
               (miroir(bougie()), range_connu(haut=102, bas=100), TICK, Sens.VENTE),
               (exemple, range_connu(haut=1.10000, bas=1.09800), Decimal('0.00001'), Sens.ACHAT)]
        for e, r, tick, sens in cas:
            b, i = e.bougie, e.indicateurs
            row = SimpleNamespace(O=b.ouverture, H=b.haut, L=b.bas, C=b.cloture, A=i.a, TR=i.tr)
            attendu = london_signal(row, b.ouverture, r.haut, r.bas, float(tick))
            reel = calculer_stop(e, r, sens, tick, p)
            self.assertIsNotNone(attendu)
            self.assertTrue(math.isclose(reel.niveau, attendu[1], rel_tol=1e-12))
            self.assertEqual(reel.multiple_objectif, p.take_profit_gross_price_r)
        self.assertTrue(math.isclose(calculer_stop(exemple, cas[-1][1], Sens.ACHAT, cas[-1][2], p).niveau,
                                     1.09985, rel_tol=1e-12))

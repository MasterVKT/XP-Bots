"""Catégorie 2, couche 1c : prédicats de cassure comparés à london_signal, exemple S02.5 et miroirs."""
from decimal import Decimal
from types import SimpleNamespace
import unittest

from reference.technical import london_signal
from robot.outils.london import TICK, bougie, miroir, parametres, range_connu
from xpbots.london.c0b_types import Cassure
from xpbots.london.c1c_cassure import evaluer_cassure


class TestJonctionCassure(unittest.TestCase):
    def test_egalite_a_l_oracle_sur_cas_eloignes_des_seuils_et_exemple_s02_5(self):
        p = parametres()
        exemple = bougie(p=p, o=1.09995, h=1.10055, l=1.09990, c=1.10050, a=0.00050, tr=0.00065)
        cas = [(bougie(p=p), range_connu(), TICK),
               (miroir(bougie(p=p)), range_connu(haut=102, bas=100), TICK),
               (exemple, range_connu(haut=1.10000, bas=1.09800), Decimal('0.00001'))]
        for enrichie, r, tick in cas:
            b, i = enrichie.bougie, enrichie.indicateurs
            row = SimpleNamespace(O=b.ouverture, H=b.haut, L=b.bas, C=b.cloture, A=i.a, TR=i.tr)
            # Une clôture précédente déjà hors range ne change aucun prédicat V3.
            attendu = london_signal(row, b.cloture, r.haut, r.bas, float(tick))
            reel = evaluer_cassure(enrichie, r, tick, p)
            self.assertIsNotNone(attendu)
            self.assertIsInstance(reel, Cassure)
            self.assertEqual(reel.sens.signe, attendu[0])

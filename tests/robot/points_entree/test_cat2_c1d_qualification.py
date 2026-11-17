"""Jonction de qualification avec le bloc physique réel et le seul FauxMT5."""
import unittest
from robot.points_entree.test_cat1_c1d_qualification import HarnaisQualification
from robot.outils.assemblage_mt5 import installer_controles
from xpbots.app.c1d_cli_qualification import qualifier
from xpbots.infra.c2a_specifications import SpecificationsMT5
from xpbots.infra.c2c_calculs import CalculsMT5


class TestJonctionQualification(HarnaisQualification,unittest.TestCase):
    def test_bloc_reel_des_adaptateurs_sans_changement_du_compte_ou_du_depot(self):
        installer_controles(self.infra.session.etat.common_files)
        avant=(self.sdk.compte,self.sdk.positions[:],self.sdk.ordres[:],self.infra.depot.charger())
        qualifier(self.app,self.infra,self.table,self.q)
        self.assertIsInstance(self.infra.courtier.specifications,SpecificationsMT5)
        self.assertIsInstance(self.infra.courtier.calculs,CalculsMT5)
        self.assertEqual((self.sdk.compte,self.sdk.positions,self.sdk.ordres,self.infra.depot.charger()),avant)

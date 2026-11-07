"""Catégorie 2, couche 1a (port_calcul) : contrat et bornes des sources C04–C09."""
from decimal import Decimal as D
import unittest
from robot.outils.execution_partagee import *
from robot.doublures.calculs_execution import CalculSynthetique
from xpbots.execution.c0a_types import OrdreCalcule
from xpbots.execution.c1a_calcul import appeler_calcul

class TestJonctionCalcul(unittest.TestCase):
    def test_commande_reelle_et_controle_compte_total(self):
        c=CalculSynthetique();o=OrdreCalcule(cle(),c.profil.symbole_courtier,D('.2'),D('1.1004'),D('1.0998'),D('1.1016'))
        n=appeler_calcul(c,'controler',o,c.compte)
        self.assertEqual((n.marge_totale_apres,n.marge_libre_apres),(D('.2'),D('99.8')))

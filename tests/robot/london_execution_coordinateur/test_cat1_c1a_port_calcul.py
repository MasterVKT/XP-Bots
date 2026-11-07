"""Catégorie 1, couche 1a (port_calcul) : contrat et bornes des sources C04–C09."""
from decimal import Decimal as D
import unittest
from robot.doublures.calculs_execution import CalculSynthetique
from xpbots.execution.c1a_calcul import *
from xpbots.execution.c0a_types import RefusExecution
from xpbots.noyau.c1c_domaine import Motif

class TestPortCalcul(unittest.TestCase):
    def test_protocole_et_resultats_connus(self):
        c=CalculSynthetique();self.assertIsInstance(c,CalculCourtier)
        self.assertEqual(appeler_calcul(c,'marge',c.profil,None,D('.1'),D(1)),D('.1'))
        self.assertIs(appeler_calcul(c,'etat_compte'),c.compte)
    def test_exception_frontiere_et_none_ne_sont_pas_des_zeros(self):
        class P:
            def marge(self,*a): raise RuntimeError('panne synthétique')
            def profit(self,*a): return None
        for nom in ('marge','profit','specifications'):
            r=appeler_calcul(P(),nom)
            self.assertEqual((r.motif,r.detail),(Motif.ENVIRONMENT_NOT_READY,nom))
    def test_resultats_montants_stricts(self):
        for v in (0,False,D('NaN'),D('Infinity'),D(-1)):
            class P:
                def marge(self): return v
            with self.subTest(v=v):self.assertIsInstance(appeler_calcul(P(),'marge'),RefusExecution)
        with self.assertRaises(ValueError): appeler_calcul(object(),'envoyer')

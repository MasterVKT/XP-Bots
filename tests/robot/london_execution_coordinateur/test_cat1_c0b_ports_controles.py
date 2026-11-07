"""Catégorie 1, couche 0b (ports_controles) : contrat et bornes des sources C04–C09."""
import unittest
from xpbots.execution.c0b_controles import *
from xpbots.noyau.c1c_domaine import Sens,ContexteIA

class TestPortsControles(unittest.TestCase):
    def test_neutres_explicites_et_protocoles(self):
        fond=ControleTechniqueNeutre(); ia=ComplementAbsent()
        self.assertIsInstance(fond,ControleFondamental); self.assertIsInstance(ia,LecteurContexteIA)
        self.assertEqual(fond.scenario,'TECHNICAL_CONTROL_NEUTRAL')
        for s in Sens:
            d=fond.evaluer('EURUSD',s,1000)
            self.assertTrue(d.admise); self.assertFalse(d.cloture_obligatoire)
        self.assertEqual(fond.clotures_obligatoires(1000),())
        self.assertIs(ia.evaluer('EURUSD',1000).etat,ContexteIA.NEUTRAL)
    def test_entrees_refusees(self):
        for a in (('',Sens.ACHAT,0),('EURUSD','ACHAT',0),('EURUSD',Sens.ACHAT,True)):
            with self.assertRaises(ValueError): ControleTechniqueNeutre().evaluer(*a)

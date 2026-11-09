"""Catégorie 2 : port canonique, garde réelle et absence de contournement par IA."""
import unittest
from robot.outils.fondamental import (T, commun, message, octets, calendrier, evenement,
    table_importance, ConversionServeurScenario)
from xpbots.execution.c0b_controles import ControleFondamental, ComplementAbsent
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.noyau.c1c_domaine import ContexteIA, Sens, Motif


class TestJonctionPermissions(unittest.TestCase):
    def test_a14_6_et_8_socle_absence_ia_ne_cree_pas_permission(self):
        p=PermissionsFondamentales(commun(),ConversionServeurScenario())
        self.assertIsInstance(p,ControleFondamental)
        self.assertIs(ComplementAbsent().evaluer('EURUSD',T).etat,ContexteIA.NEUTRAL)
        self.assertEqual(p.evaluer('EURUSD',Sens.ACHAT,T).motif,Motif.FUNDAMENTAL_INVALID)

    def test_c11_8_permission_entre_signal_et_envoi(self):
        p=PermissionsFondamentales(commun(),ConversionServeurScenario())
        p.recevoir_calendrier(octets(calendrier()),T,table_importance())
        p.recevoir_permission('EURUSD',octets(message(valid_until_utc='2026-11-09T08:01:00.000Z')),T+200)
        self.assertTrue(p.evaluer('EURUSD',Sens.ACHAT,T+59999).admise)
        self.assertEqual(p.evaluer('EURUSD',Sens.ACHAT,T+60000).detail,'PERIMEE')

    def test_c11_9_l14_bornes_et_devises(self):
        p=PermissionsFondamentales(commun(),ConversionServeurScenario())
        p.recevoir_calendrier(octets(calendrier(evenements=[evenement(T+1800000,devise='GBP')])),T,table_importance())
        self.assertEqual(p.prochaine_echeance_ms(T),T+900000)
        self.assertEqual(p.clotures_obligatoires(T+899999),())
        self.assertEqual(p.clotures_obligatoires(T+900000),('GBPUSD',))
        self.assertEqual(p.clotures_obligatoires(T+2700000),())

    def test_prefixes_permissions_et_revisions_calendrier(self):
        complet=PermissionsFondamentales(commun(),ConversionServeurScenario())
        prefixe=PermissionsFondamentales(commun(),ConversionServeurScenario())
        for p in (complet,prefixe):
            p.recevoir_calendrier(octets(calendrier()),T,table_importance())
            p.recevoir_permission('EURUSD',octets(message()),T+200)
        complet.recevoir_calendrier(octets(calendrier(version=2,evenements=[evenement(T+600000)])),T+400,table_importance())
        for t in (T+199,T+200,T+399):
            for sens in Sens:self.assertEqual(complet.evaluer('EURUSD',sens,t),prefixe.evaluer('EURUSD',sens,t))
        prefixe.recevoir_calendrier(octets(calendrier(version=2,evenements=[evenement(T+600000)])),T+400,table_importance())
        self.assertEqual(complet.etat,prefixe.etat)

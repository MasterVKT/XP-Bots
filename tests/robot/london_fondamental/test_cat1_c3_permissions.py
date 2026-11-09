"""Catégorie 1 : effets C05, priorités, horloge et reprise."""
from dataclasses import replace
import unittest
from robot.outils.fondamental import (T, commun, message, octets, calendrier, evenement,
    table_importance, ConversionServeurScenario)
from xpbots.fondamental.c0_types import ErreurFondamental
from xpbots.fondamental.c3_permissions import EtatFondamental, PermissionsFondamentales
from xpbots.noyau.c1c_domaine import Motif, Sens


class TestPermissions(unittest.TestCase):
    def setUp(self):
        self.p=PermissionsFondamentales(commun(),ConversionServeurScenario())
        self.p.recevoir_calendrier(octets(calendrier()),T,table_importance())

    def permission(self,**changements):
        return self.p.recevoir_permission('EURUSD',octets(message(**changements)),T+200)

    def decision(self,t=T+200,sens=Sens.ACHAT):return self.p.evaluer('EURUSD',sens,t)

    def test_absence_et_invalide_bloquent_sans_liquider(self):
        self.assertEqual(self.decision().detail,'ABSENTE')
        self.assertFalse(self.p.recevoir_permission('EURUSD',b'{}',T+200).acceptee)
        self.assertFalse(self.decision().admise)
        self.assertEqual(self.p.clotures_obligatoires(T+200),())

    def test_any_allow_et_deux_directions(self):
        self.permission()
        self.assertTrue(all(self.decision(sens=s).admise for s in Sens))
        self.permission(sequence=2,direction='LONG_ONLY')
        self.assertTrue(self.decision().admise)
        self.assertEqual(self.decision(sens=Sens.VENTE).detail,'LONG_ONLY')
        self.permission(sequence=3,direction='SHORT_ONLY')
        self.assertTrue(self.decision(sens=Sens.VENTE).admise)
        self.assertEqual(self.decision().detail,'SHORT_ONLY')
        self.assertEqual(self.p.clotures_obligatoires(T+200),())

    def test_no_new_bloque_sans_cloture(self):
        self.permission(risk_state='NO_NEW')
        self.assertEqual(self.decision().detail,'RISK_STATE_NO_NEW')
        self.assertFalse(self.decision().cloture_obligatoire)

    def test_flatten_prime_calendrier_et_annonce_et_expire(self):
        self.permission(risk_state='FLATTEN',valid_until_utc='2026-11-09T08:01:00.000Z')
        self.p.recevoir_calendrier(octets(calendrier(version=2,evenements=[evenement(T+600000)])),T+200,table_importance())
        self.assertEqual(self.decision().detail,'RISK_STATE_FLATTEN')
        self.assertEqual(self.p.clotures_obligatoires(T+200),('EURUSD','GBPUSD','XAUUSD'))
        self.assertEqual(self.decision(T+60000).detail,'ANNONCE_HIGH')
        sans_annonce=PermissionsFondamentales(commun(),ConversionServeurScenario())
        sans_annonce.recevoir_permission('EURUSD',octets(message(risk_state='FLATTEN',
            valid_until_utc='2026-11-09T08:01:00.000Z')),T+200)
        self.assertEqual(sans_annonce.clotures_obligatoires(T+60000),())

    def test_annonce_tardive_cloture_meme_permission_absente_ou_perimee(self):
        avant=self.decision(T+300)
        self.p.recevoir_calendrier(octets(calendrier(version=2,evenements=[evenement(T+600000)])),T+400,table_importance())
        self.assertEqual(self.decision(T+399),avant)
        self.assertEqual(self.decision(T+400).detail,'ANNONCE_HIGH')
        self.assertTrue(self.decision(T+400).cloture_obligatoire)
        self.assertFalse(self.decision(T+1500000).cloture_obligatoire)

    def test_calendrier_absent_perime_et_couverture_ne_liquident_pas(self):
        p=PermissionsFondamentales(commun(),ConversionServeurScenario())
        p.recevoir_permission('EURUSD',octets(message()),T+200)
        self.assertEqual(p.evaluer('EURUSD',Sens.ACHAT,T+200).detail,'CALENDRIER_PERIME')
        self.permission()
        self.p.recevoir_calendrier(octets(calendrier(version=2,
            fenetre_fin_serveur='2026.11.09 11:00:00')),T+200,table_importance())
        self.assertEqual(self.decision().detail,'COUVERTURE_INSUFFISANTE')
        self.assertEqual(self.p.clotures_obligatoires(T+200),())

    def test_interruption_relecture_et_heartbeat(self):
        self.permission()
        self.assertEqual(self.p.prochaine_echeance_ms(T+200),T+60000)
        self.assertEqual(self.p.avancer(T+60000)[0].nature,'HEARTBEAT_MANQUE')
        self.assertTrue(self.decision(T+60000).admise)
        self.p.interrompre('EURUSD',T+60000)
        self.p.recevoir_permission('EURUSD',octets(message()),T+60000)
        self.assertEqual(self.decision(T+60000).detail,'INTERRUPTION')

    def test_reprise_ne_renouvelle_rien_et_refuse_incoherence(self):
        self.permission()
        self.p.avancer(T+60000)
        e=self.p.etat
        reprise=PermissionsFondamentales(commun(),ConversionServeurScenario(),e)
        self.assertEqual(reprise.etat,e)
        self.assertEqual(reprise.avancer(T+60000),())
        self.assertEqual(reprise.evaluer('EURUSD',Sens.ACHAT,T+900000).detail,'PERIMEE')
        with self.assertRaises(ErreurFondamental):replace(e,dernier_ms=T)
        for appel in (lambda:reprise.avancer(T),lambda:reprise.recevoir_calendrier(b'{}',T,table_importance()),
            lambda:reprise.recevoir_permission('EURUSD',b'{}',T),lambda:reprise.evaluer('EURUSD','ACHAT',T)):
            with self.assertRaises(ErreurFondamental):appel()

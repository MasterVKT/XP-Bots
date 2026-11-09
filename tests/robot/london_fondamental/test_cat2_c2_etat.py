"""Catégorie 2 : vrai validateur C05, préfixes causaux et paramètres réels."""
import unittest
from robot.outils.configuration import octets_technique_modifies
from robot.outils.fondamental import T, commun, message, octets
from xpbots.fondamental.c2_etat_permissions import RegistrePermissions
from xpbots.noyau.c0c_configuration import analyser_export_technique


class TestJonctionEtat(unittest.TestCase):
    def test_prefixe_de_receptions_egale_histoire_complete(self):
        complet=RegistrePermissions(commun())
        complet.recevoir('EURUSD',octets(message()),T+200)
        complet.interrompre('EURUSD',T+300)
        complet.recevoir('EURUSD',octets(message(sequence=2,direction='SHORT_ONLY')),T+400)
        prefixe=RegistrePermissions(commun())
        for t in (T+199,T+200,T+299,T+300,T+399,T+400):
            if t==T+200:prefixe.recevoir('EURUSD',octets(message()),t)
            if t==T+300:prefixe.interrompre('EURUSD',t)
            if t==T+400:prefixe.recevoir('EURUSD',octets(message(sequence=2,direction='SHORT_ONLY')),t)
            self.assertEqual(complet.consulter('EURUSD',t),prefixe.consulter('EURUSD',t))

    def test_cadence_chargee_et_validateur_reel(self):
        def changer(p):p['common']['fundamental_expected_heartbeat_seconds']=15
        c=analyser_export_technique(octets_technique_modifies(changer)).commun
        r=RegistrePermissions(c)
        self.assertFalse(r.recevoir('EURUSD',octets(message(known_at_utc='2026-11-09T09:00:00.000Z')),T+200).acceptee)
        self.assertTrue(r.recevoir('EURUSD',octets(message()),T+200).acceptee)
        self.assertEqual(r.prochaine_echeance_ms(T+200),T+15000)

    def test_c11_8_controle_validite_a_chaque_instant(self):
        r=RegistrePermissions(commun())
        r.recevoir('EURUSD',octets(message(valid_until_utc='2026-11-09T08:01:00.000Z')),T+200)
        self.assertIsNone(r.consulter('EURUSD',T+59999).detail)
        self.assertEqual(r.consulter('EURUSD',T+60000).detail,'PERIMEE')

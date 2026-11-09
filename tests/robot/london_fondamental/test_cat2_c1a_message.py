"""Catégorie 2, couche 1a : vrai décodage, noyau et paramètres chargés."""
import unittest
from robot.outils.configuration import octets_technique_modifies
from robot.outils.fondamental import T, commun, message, octets
from xpbots.noyau.c0c_configuration import analyser_export_technique
from xpbots.noyau.c0a_temps import instant_vers_iso
from xpbots.fondamental.c1a_message import decoder_message, valider_message, ErreurPermission


class TestJonctionMessage(unittest.TestCase):
    def test_precision_ms_et_connaissance_distincte_de_la_reception(self):
        m=decoder_message(octets(message(known_at_utc=instant_vers_iso(T+137))),'EURUSD',T+251,T+300,commun())
        self.assertEqual(m.known_at_ms,T+137)
        self.assertIs(valider_message(m,T+251,T+300,commun()),m)
        self.assertEqual((m.model_version,m.input_snapshot_id),('MODELE_SYNTHETIQUE_V1','SYNTHETIQUE_1'))

    def test_duree_vient_du_parametre_charge(self):
        def changer(p):p['common']['fundamental_max_validity_seconds']=30
        c=analyser_export_technique(octets_technique_modifies(changer)).commun
        with self.assertRaises(ErreurPermission): decoder_message(octets(message()),'EURUSD',T+200,T+200,c)
        m=decoder_message(octets(message(valid_until_utc=instant_vers_iso(T+30000))),'EURUSD',T+200,T+200,c)
        self.assertEqual(m.valid_until_ms-m.issued_at_ms,30000)

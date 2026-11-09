"""Catégorie 2, couche 1 : noyau/configuration réels et limite explicite de l'oracle A10."""
import unittest
from robot.outils.configuration import configuration_figee,octets_ia_modifies
from robot.outils.contexte_ia import T,evenement,octets,parametres,snapshot
from reference.llm_contracts import digest,overlay_decision
from xpbots.contexte_ia.c0_types import charger_parametres
from xpbots.contexte_ia.c1_snapshot import decoder_snapshot,ErreurSnapshot
from xpbots.noyau.c0c_configuration import ConfigurationFigee,analyser_export_ia


class TestJonctionSnapshot(unittest.TestCase):
    def test_empreinte_et_format_identiques_a_la_reference(self):
        s=snapshot();r=decoder_snapshot(octets(s),T+120000,parametres())
        self.assertEqual(r.snapshot.empreinte_payload,digest(s['payload']))
        self.assertEqual(overlay_decision(s,'2026-11-09T08:02:00Z','EURUSD'),'BLOCK')
        self.assertEqual(r.snapshot.vetos[0].symboles,('EURUSD',))

    def test_age_vient_de_l_export_charge(self):
        def changer(p):p['snapshot_max_age_seconds']=1
        c=configuration_figee();p=charger_parametres(ConfigurationFigee(c.technique,analyser_export_ia(octets_ia_modifies(changer))))
        s=snapshot(integration_digest=p.empreinte_integration)
        decoder_snapshot(octets(s),T+121000,p)
        with self.assertRaises(ErreurSnapshot) as e:decoder_snapshot(octets(s),T+121001,p)
        self.assertEqual(e.exception.raison,'PERIME')

    def test_limite_oracle_retour_anticipe_ne_valide_pas_toute_liste(self):
        s=snapshot(evenements=[evenement(),{**evenement(event_id='e2'),'inconnu':True}])
        self.assertEqual(overlay_decision(s,'2026-11-09T08:02:00Z','EURUSD'),'BLOCK')
        with self.assertRaises(ErreurSnapshot) as e:decoder_snapshot(octets(s),T+120000,parametres())
        self.assertEqual(e.exception.raison,'EVENEMENT')

"""Le nouveau checkpoint a un constructeur public et un sceau obligatoire."""
from dataclasses import replace
import unittest
from robot.outils.orchestration import ticks_courts
from robot.outils.pilote_orchestration import duo
from xpbots.orchestration.c0_contrats import ErreurOrchestration
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur


class TestCodecCheckpointJournal(unittest.TestCase):
    def test_aller_retour_et_sceau_altere_refuse(self):
        m,_,_,_,_=duo(ticks_courts());cp=m.exporter_checkpoint_journal()
        self.assertEqual(deserialiser_valeur(serialiser_valeur(cp)),cp)
        mauvais=replace(cp,instant_ms=cp.instant_ms+1)
        with self.assertRaises(ErreurOrchestration):deserialiser_valeur(serialiser_valeur(mauvais))

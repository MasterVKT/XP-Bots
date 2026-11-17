"""Catégorie 1, couche 0d : contrat physique écrit en phase 11, activé en 13.1."""
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF, RAISON, sdk_contrat, registre_contrat
from tempfile import TemporaryDirectory
from pathlib import Path
from robot.london_infrastructure.test_cat1_c0d_journal import evenement
from xpbots.infra.c0d_journal import JournalFichiers

class TestContratJournalPoste(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF, RAISON)
    def test_projection_canonique_et_remplacement_windows(self):
        registre_contrat()
        with sdk_contrat(), TemporaryDirectory() as d:
            ev = (evenement(1, 0),)
            j = JournalFichiers(d, 'FIXTURE'); j.ajouter(ev)
            p = Path(d)/'logs/FIXTURE/decisions_1970-01-01.jsonl'
            attendu = p.read_bytes()
            JournalFichiers(d, 'FIXTURE').publier(ev)
            self.assertEqual(p.read_bytes(), attendu)

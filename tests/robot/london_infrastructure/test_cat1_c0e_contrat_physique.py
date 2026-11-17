"""Catégorie 1, couche 0e : contrat physique écrit en phase 11, activé en 13.1."""
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF, RAISON, sdk_contrat, registre_contrat
from pathlib import Path
from xpbots.infra.c0e_snapshot import LecteurSnapshot

class TestContratSnapshotPoste(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF, RAISON)
    def test_racine_common_files_et_lecture_fermee_du_snapshot(self):
        r = registre_contrat()
        with sdk_contrat() as sdk:
            p = Path(sdk.terminal_info().commondata_path)/'Files/XPBots/ai/v1/context_latest.json'
            b, t, erreur = LecteurSnapshot(p, r['ingenierie']['snapshot_max_octets']).lire(1)
            self.assertEqual(t, 1)
            self.assertIsNone(erreur, 'publier un snapshot de contrat avant 13.1')
            self.assertEqual(b, p.read_bytes())

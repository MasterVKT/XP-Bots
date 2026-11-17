"""Catégorie 1, couche 0g : contrat physique écrit en phase 11, activé en 13.1."""
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF, RAISON, sdk_contrat, registre_contrat
from pathlib import Path
from xpbots.infra.c0g_controles import SourcesControles

class TestContratEchangesPoste(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF, RAISON)
    def test_dossiers_d11_d12_reels_sans_ecriture(self):
        r = registre_contrat()
        with sdk_contrat() as sdk:
            root = Path(sdk.terminal_info().commondata_path)/'Files'
            recus = SourcesControles(root, r['liaisons'], r['ingenierie']['max_octets_echange']).lire(1)
            self.assertEqual(len(recus), 2*len(r['liaisons'])+2)
            for recu in recus:
                self.assertIsNone(recu.erreur, 'fichiers externes obligatoires à préparer en 13.1')
                self.assertIsInstance(recu.octets, bytes)

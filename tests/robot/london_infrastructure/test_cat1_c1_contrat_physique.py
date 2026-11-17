"""Catégorie 1, couche 1 : contrat terminal réel limité au compte démo en 13.1."""
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF, RAISON, sdk_contrat, registre_contrat
from xpbots.infra.c1_session import SessionMT5


class TestContratSessionPoste(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF, RAISON)
    def test_attachement_versions_racine_et_type_compte_demo(self):
        r = registre_contrat()
        with sdk_contrat() as sdk:
            s = SessionMT5(sdk, 'DEMO', common_files_attendu=r['common_files'])
            try:
                etat = s.attacher()
                self.assertTrue(etat.connecte); self.assertTrue(etat.droits)
                self.assertEqual(etat.version_paquet, '5.0.6231'); self.assertEqual(etat.alertes, ())
            finally: s.fermer()

"""Catégorie 1, couche 0c : contrat physique écrit en phase 11, activé en 13.1."""
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF, RAISON, sdk_contrat, registre_contrat
from tempfile import TemporaryDirectory
from pathlib import Path
from xpbots.infra.c0c_sqlite import DepotSQLite

class TestContratSQLitePoste(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF, RAISON)
    def test_wal_commit_et_reouverture_du_fichier_windows(self):
        registre_contrat()
        with sdk_contrat(), TemporaryDirectory() as d:
            p = Path(d)/'etat.sqlite'
            with DepotSQLite(p, {'mode': 'DEMO', 'deploiement': 'CONTRAT_TEMPORAIRE'}) as db:
                db.persister(1, 1, b'{}')
                self.assertEqual(db.connexion.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
            with DepotSQLite(p, {'mode': 'DEMO', 'deploiement': 'CONTRAT_TEMPORAIRE'}) as db:
                self.assertEqual(db.charger(), b'{}')

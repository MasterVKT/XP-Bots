"""Catégorie 1, couche 0e : vraie lecture bornée et descripteur fermé."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from xpbots.infra.c0e_snapshot import LecteurSnapshot


class TestSnapshotPhysique(unittest.TestCase):
    def test_plafond_exact_et_depassement(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'context_latest.json'; p.write_bytes(b'1234')
            r = LecteurSnapshot(p, 4)
            self.assertEqual(r.lire(10), (b'1234', 10, None))
            p.write_bytes(b'12345')
            self.assertEqual(r.lire(20), (None, 20, 'SNAPSHOT_TROP_GRAND'))

    def test_absence_et_remplacement_apres_lecture(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'context_latest.json'; r = LecteurSnapshot(p, 4)
            self.assertEqual(r.lire(10), (None, 10, 'SNAPSHOT_ABSENT'))
            p.write_bytes(b'{}'); self.assertEqual(r.lire(20)[0], b'{}')
            q = Path(d)/'nouveau'; q.write_bytes(b'[]'); q.replace(p)
            self.assertEqual(r.lire(30)[0], b'[]')

    def test_plafonds_et_instants_invalides(self):
        for n in (0, -1, True, 2.0):
            with self.assertRaises(ValueError): LecteurSnapshot('inutilise', n)
        with self.assertRaises(ValueError): LecteurSnapshot('inutilise', 4).lire(True)

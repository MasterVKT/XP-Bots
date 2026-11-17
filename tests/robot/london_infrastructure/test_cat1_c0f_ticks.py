"""Catégorie 1, couche 0f : octets gzip et contenu, ordre et CRC exacts."""
from pathlib import Path
from tempfile import TemporaryDirectory
import gzip
import hashlib
import unittest
from xpbots.infra.c0f_ticks import LectureTicks


class TestLectureTicksPhysique(unittest.TestCase):
    def test_hash_comprime_et_contenu_crlf_conserves(self):
        contenu = b'canonical_symbol,broker_symbol,time_utc_ms,sequence,bid,ask\r\nEURUSD,EURUSD.micro,100,0,1.1,1.2\r\n'
        with TemporaryDirectory() as d:
            p = Path(d)/'2026-11.csv.gz'; p.write_bytes(gzip.compress(contenu, mtime=0))
            with LectureTicks(p) as r:
                self.assertEqual(''.join(r.lignes()).encode(), contenu)
                self.assertEqual(r.sha256_fichier, hashlib.sha256(p.read_bytes()).hexdigest())
                self.assertEqual(r.sha256_contenu, hashlib.sha256(contenu).hexdigest())
            p.replace(Path(d)/'ferme.csv.gz')

    def test_lecture_inachevee_ne_produit_aucune_qualification(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'2026-11.csv.gz'; p.write_bytes(gzip.compress(b'a\nb\n'))
            with LectureTicks(p) as r:
                g = r.lignes(); self.assertEqual(next(g), 'a\n')
                self.assertIsNone(r.sha256_fichier); self.assertIsNone(r.sha256_contenu)
                g.close()
            p.replace(Path(d)/'ferme.csv.gz')

    def test_crc_et_troncature_refuses(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'2026-11.csv.gz'; b = gzip.compress(b'a\nb\n')
            for corrompu in (b[:-3], b[:-8]+b'\x00'*8):
                p.write_bytes(corrompu)
                with LectureTicks(p) as r:
                    with self.assertRaises((EOFError, OSError)): tuple(r.lignes())
                    self.assertIsNone(r.sha256_fichier)

    def test_utf8_strict_et_extension(self):
        with self.assertRaises(ValueError): LectureTicks('ticks.csv')
        with TemporaryDirectory() as d:
            p = Path(d)/'2026-11.csv.gz'; p.write_bytes(gzip.compress(b'\xff\n'))
            with LectureTicks(p) as r:
                with self.assertRaises(UnicodeError): tuple(r.lignes())

"""Catégorie 1, couche 0c : vraies transactions temporaires, crash et reprise."""
from pathlib import Path
from tempfile import TemporaryDirectory
from decimal import Decimal
import sqlite3
import unittest
from xpbots.infra.c0c_sqlite import DepotSQLite

META = {'deploiement': 'FIXTURE', 'mode': 'PAPER', 'empreintes': {'technique': 'a'*64, 'ia': 'b'*64}, 'commit': 'c'*40}


class TestDepotDurable(unittest.TestCase):
    def test_commit_reprise_et_metadonnees_incompatibles(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'etat.sqlite'
            with DepotSQLite(p, META) as db:
                self.assertIsNone(db.charger())
                self.assertEqual(db.persister(1, 100, b'{"etat":1}', entrees=((1, b'{"n":1}'),), decisions=(b'{"decision":1}',)), 1)
                self.assertEqual(db.connexion.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
                self.assertEqual(db.connexion.execute('PRAGMA synchronous').fetchone()[0], 2)
            with DepotSQLite(p, META) as db:
                self.assertEqual(db.charger(), b'{"etat":1}')
                self.assertEqual(db.entrees(), (b'{"n":1}',))
                self.assertEqual(db.evenements(), ((1, 100, (b'{"decision":1}',), (b'{"n":1}',)),))
            with self.assertRaises(ValueError): DepotSQLite(p, dict(META, mode='REEL'))
            with DepotSQLite(p, META) as db: self.assertEqual(db.dernier_numero, 1)

    def test_repetition_idempotente_et_divergence_refusee(self):
        with TemporaryDirectory() as d, DepotSQLite(Path(d)/'etat.sqlite', META) as db:
            args = (1, 100, b'{}')
            db.persister(*args, entrees=((1, b'{}'),))
            db.persister(*args, entrees=((1, b'{}'),))
            self.assertEqual(len(db.evenements()), 1)
            with self.assertRaises(ValueError): db.persister(1, 100, b'{"autre":1}')
            with self.assertRaises(ValueError): db.persister(3, 300, b'{}')
            self.assertEqual(db.dernier_numero, 1)

    def test_rollback_du_bloc_complet_sur_erreur_de_reservation(self):
        with TemporaryDirectory() as d, DepotSQLite(Path(d)/'etat.sqlite', META) as db:
            db.persister(1, 100, b'{"etat":1}')
            reserve = ('REFERENCE/cle', Decimal('.4'), Decimal('.1'))
            with self.assertRaises(sqlite3.IntegrityError):
                db.persister(2, 200, b'{"etat":2}', entrees=((1, b'{}'),), decisions=(b'{}',),
                             intentions=(('REFERENCE/cle', 'PREPAREE', b'{}'),), reservations=(reserve, reserve))
            self.assertEqual(db.charger(), b'{"etat":1}')
            self.assertEqual(db.entrees(), ())
            self.assertEqual(db.connexion.execute('SELECT COUNT(*) FROM intentions').fetchone()[0], 0)
            self.assertEqual(db.dernier_numero, 1)

    def test_transaction_concurrente_exclue_sans_etat_partiel(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'etat.sqlite'
            with DepotSQLite(p, META) as a, DepotSQLite(p, META) as b:
                a.connexion.execute('BEGIN IMMEDIATE')
                try:
                    with self.assertRaises(sqlite3.OperationalError): b.persister(1, 100, b'{}')
                    self.assertIsNone(b.charger())
                finally: a.connexion.execute('ROLLBACK')
                b.persister(1, 100, b'{}')
                self.assertEqual(a.dernier_numero, 1)

    def test_arret_persiste_et_ne_se_leve_pas_par_redemarrage(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'etat.sqlite'
            with DepotSQLite(p, META) as db:
                db.persister(1, 100, b'{}', arrets=(('REFERENCE', 'GLOBAL', True, None),))
            with DepotSQLite(p, META) as db:
                self.assertEqual(db.arrets()[0][:4], ('REFERENCE', 'GLOBAL', True, 100))
                with self.assertRaises(ValueError): db.persister(2, 200, b'{}', arrets=(('REFERENCE', 'GLOBAL', False, None),))
                self.assertEqual(db.dernier_numero, 1)
                decision = dict(decision_id='HUMAIN_FIXTURE', instant_utc_ms=190, motif='reprise autorisée pour test')
                db.persister(2, 200, b'{}', arrets=(('REFERENCE', 'GLOBAL', False, decision),))
                self.assertEqual(db.arrets()[0], ('REFERENCE', 'GLOBAL', False, 200, decision))

    def test_json_octets_et_numerotation_stricts(self):
        with TemporaryDirectory() as d, DepotSQLite(Path(d)/'etat.sqlite', META) as db:
            for b in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{ "x": 1 }', b'\xff'):
                with self.assertRaises(ValueError): db.persister(1, 100, b)
            for n in (True, 0, -1, 1.0):
                with self.assertRaises(ValueError): db.persister(n, 100, b'{}')
            with self.assertRaises(ValueError): db.persister(1, 100, b'{}', entrees=((2, b'{}'),))
            self.assertIsNone(db.charger())

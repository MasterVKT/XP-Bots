"""Catégorie 1, couche 0g : vrais chemins D11/D12, jamais de cache de fraîcheur."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from xpbots.infra.c0g_controles import SourcesControles


class TestControlesPhysiques(unittest.TestCase):
    def test_chemins_exactes_et_date_de_lecture(self):
        with TemporaryDirectory() as d:
            base = Path(d)/'XPBots'
            chemins = [('fondamental/v1/permission_EURUSD.json', b'{"p":1}'),
                       ('export/v1/calendrier.json', b'{"c":1}'),
                       ('export/v1/fermetures_exceptionnelles.json', b'{"f":1}'),
                       ('export/v1/seances_EURUSD.micro.json', b'{"s":1}')]
            for chemin, b in chemins:
                p = base/chemin; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b)
            src = SourcesControles(d, {'EURUSD': 'EURUSD.micro'}, 100)
            rec = src.lire(123)
            self.assertEqual(tuple(x.octets for x in rec), tuple(b for _, b in chemins))
            self.assertEqual(tuple(x.instant_ms for x in rec), (123,)*4)
            self.assertTrue(all(x.erreur is None for x in rec))
            p = base/chemins[0][0]; q = p.with_name('remplacement'); q.write_bytes(b'{}'); q.replace(p)
            self.assertEqual(src.lire(456)[0].octets, b'{}')

    def test_absences_plafond_et_aucune_ecriture(self):
        with TemporaryDirectory() as d:
            src = SourcesControles(d, {'EURUSD': 'EURUSD.micro'}, 2)
            self.assertTrue(all(x.erreur == 'FICHIER_ABSENT' for x in src.lire(10)))
            self.assertEqual(list(Path(d).iterdir()), [])
            p = Path(d)/'XPBots/fondamental/v1/permission_EURUSD.json'; p.parent.mkdir(parents=True); p.write_bytes(b'{}')
            self.assertEqual(src.lire(20)[0].octets, b'{}')
            p.write_bytes(b'123')
            self.assertEqual(src.lire(30)[0].erreur, 'FICHIER_TROP_GRAND')

    def test_chemins_hostiles_refuses(self):
        for n in ('../x', 'C:/x', 'x\\y', '..', 'x.', 'x '):
            with self.assertRaises(ValueError): SourcesControles('.', {'EURUSD': n}, 100)
        for n in (True, 0, -1):
            with self.assertRaises(ValueError): SourcesControles('.', {'EURUSD': 'EURUSD'}, n)
        with self.assertRaises(ValueError): SourcesControles('.', {'EURUSD': 'meme', 'GBPUSD': 'meme'}, 100)

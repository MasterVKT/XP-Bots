"""Catégorie 2, couche 1 : vraies conversions 0a et session injectée."""
from datetime import datetime, timezone
from tempfile import TemporaryDirectory
import unittest
from robot.outils.faux_mt5 import FauxMT5
from xpbots.infra.c0a_types import TableHeureServeur, SegmentServeur, entier_natif, nombre_decimal
from xpbots.infra.c1_session import SessionMT5


class TestJonctionSession(unittest.TestCase):
    def test_structures_natives_converties_par_la_vraie_feuille(self):
        with TemporaryDirectory() as d:
            sdk = FauxMT5(d); sdk.ajouter_tick('EURUSD.micro', 1000, 1.1, 1.2)
            s = SessionMT5(sdk, 'PAPER'); s.attacher()
            table = TableHeureServeur('SERVEUR_FIXTURE', 1, '2026-11-10T00:00:00.000Z', ('synthétique S01',), (SegmentServeur(0, 10000, 0),))
            ticks = s.appeler('copy_ticks_from', 'EURUSD.micro', datetime(1970, 1, 1, tzinfo=timezone.utc), 10, sdk.COPY_TICKS_ALL)
            self.assertEqual(table.utc_de_serveur(entier_natif(ticks[0]['time_msc'])), 1000)
            self.assertEqual(str(nombre_decimal(ticks[0]['ask'])), '1.2'); s.fermer()

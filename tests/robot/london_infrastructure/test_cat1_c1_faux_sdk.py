"""Catégorie 1, couche 1 : fidélité de la seule doublure externe MT5."""
from pathlib import Path
import inspect
import json
import re
from threading import Event, Thread
import unittest
import numpy as np
from robot.outils.faux_mt5 import FauxMT5, TICK_DTYPE

RACINE = Path(__file__).resolve().parents[3]


class TestFideliteSDK(unittest.TestCase):
    def test_constantes_exactes_du_texte_officiel_et_noms_du_document_08(self):
        faits = json.loads((RACINE/'tests/robot/fixtures/mt5_5_0_6231_constantes.json').read_text(encoding='utf-8'))
        self.assertEqual(faits['version'], '5.0.6231')
        self.assertEqual(len(faits['constantes']), 213)
        self.assertEqual(faits['sha256_init'], '2e3bc321ab35b5c9e6c777665f381bc686bbf60791160838a0e84406dc0052cf')
        for nom, valeur in faits['constantes'].items(): self.assertEqual(getattr(FauxMT5, nom), valeur, nom)
        doc = (RACINE/'docs/architecture/robot_london_v3/08_contrats_frontieres.md').read_text(encoding='utf-8')
        table = doc.split('### 2.2 Constantes utilisées', 1)[1].split('### 2.3', 1)[0]
        constantes = set(re.findall(r'`((?:COPY_TICKS|TICK_FLAG|TRADE_ACTION|ORDER_TYPE|ORDER_FILLING|ORDER_TIME|SYMBOL_|ACCOUNT_|DEAL_|TRADE_RETCODE_|RES_)[A-Z0-9_]*)`', table))
        self.assertGreater(len(constantes), 25)
        self.assertTrue(constantes <= set(faits['constantes']), constantes-set(faits['constantes']))

    def test_32_fonctions_documentees_et_signatures_utilisees(self):
        doc = (RACINE/'docs/architecture/robot_london_v3/08_contrats_frontieres.md').read_text(encoding='utf-8')
        paragraphe = doc.split('Le module expose 32 fonctions :', 1)[1].split('. Aucune', 1)[0]
        noms = re.findall(r'`([a-z_]+)`', paragraphe)
        self.assertEqual(len(noms), 32)
        for nom in noms: self.assertTrue(callable(getattr(FauxMT5, nom)), nom)
        self.assertEqual(tuple(inspect.signature(FauxMT5.copy_ticks_from).parameters), ('self', 'symbol', 'date_from', 'count', 'flags'))
        self.assertEqual(tuple(inspect.signature(FauxMT5.order_calc_profit).parameters), ('self', 'action', 'symbol', 'volume', 'price_open', 'price_close'))

    def test_structures_nommees_et_ticks_numpy_structures(self):
        sdk = FauxMT5()
        self.assertEqual(sdk.account_info()._asdict()['currency'], 'USD')
        self.assertIn('commondata_path', sdk.terminal_info()._fields)
        sdk.ajouter_tick('EURUSD.micro', 100, 1.1, 1.2)
        from datetime import datetime, timezone
        ts = sdk.copy_ticks_from('EURUSD.micro', datetime(1970, 1, 1, tzinfo=timezone.utc), 10, sdk.COPY_TICKS_ALL)
        self.assertIsInstance(ts, np.ndarray)
        self.assertEqual(ts.dtype.names, tuple(n for n, _ in TICK_DTYPE))
        self.assertEqual(ts[0]['time_msc'], 100)

    def test_none_last_error_refus_deconnexion_et_blocage(self):
        sdk = FauxMT5(); sdk.erreur = (sdk.RES_E_INTERNAL_FAIL, 'message sensible synthétique')
        sdk.scenarios['account_info'].append(None)
        self.assertIsNone(sdk.account_info()); self.assertEqual(sdk.last_error()[0], sdk.RES_E_INTERNAL_FAIL)
        sdk.terminal = sdk.terminal._replace(connected=False)
        self.assertFalse(sdk.terminal_info().connected)
        arrive, libere = Event(), Event()
        def bloque(req):
            arrive.set(); libere.wait(2); return None
        sdk.scenarios['order_send'].append(bloque)
        t = Thread(target=lambda: sdk.order_send({}), daemon=True); t.start()
        self.assertTrue(arrive.wait(1)); self.assertTrue(t.is_alive())
        libere.set(); t.join(1); self.assertFalse(t.is_alive())
        with self.assertRaises(AssertionError): sdk.login()

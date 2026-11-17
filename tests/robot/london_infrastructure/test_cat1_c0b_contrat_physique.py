"""Catégorie 1, couche 0b : contrat physique écrit en phase 11, activé en 13.1."""
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF, RAISON, sdk_contrat, registre_contrat
from datetime import datetime, timezone
from xpbots.infra.c0b_horloge import HorlogeSysteme

class TestContratHorlogePhysique(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF, RAISON)
    def test_utc_monotone_et_derivation_mesurable_sur_poste(self):
        h = HorlogeSysteme()
        avant = int(datetime.now(timezone.utc).timestamp()*1000)
        a, n = h.utc_ms(), h.monotone_ns()
        h.attendre_ms(10)
        b, m = h.utc_ms(), h.monotone_ns()
        apres = int(datetime.now(timezone.utc).timestamp()*1000)
        self.assertLessEqual(avant, a)
        self.assertLessEqual(a, b)
        self.assertLessEqual(b, apres)
        self.assertGreater(m, n)
        with sdk_contrat() as sdk:
            symbole = next(iter(registre_contrat()['liaisons'].values()))
            tick = sdk.symbol_info_tick(symbole)
            self.assertIsNotNone(tick)
            self.assertGreater(tick.time_msc, 0)  # la dérive est un relevé, jamais une correction de tick

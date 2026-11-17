"""Catégorie 1, couche 0a : contrat physique écrit en phase 11, activé en 13.1."""
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF, RAISON, sdk_contrat, registre_contrat
from xpbots.infra.c0a_types import entier_natif, nombre_decimal, TableHeureServeur
from datetime import datetime, timezone

class TestContratTypesPhysiques(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF, RAISON)
    def test_structures_scalaires_et_table_qualifiee_s01(self):
        r = registre_contrat()
        with sdk_contrat() as sdk:
            t = TableHeureServeur.depuis_document(r['table_heure_serveur'])
            self.assertEqual(t.serveur, sdk.account_info().server)
            symbole = next(iter(r['liaisons'].values()))
            ticks = sdk.copy_ticks_from(symbole, datetime.now(timezone.utc), 10, sdk.COPY_TICKS_ALL)
            self.assertIsNotNone(ticks)
            self.assertGreater(len(ticks), 0, 'tick récent nécessaire à la sonde S01')
            for tick in ticks:
                self.assertGreaterEqual(t.utc_de_serveur(entier_natif(tick['time_msc'])), 0)
                self.assertGreater(nombre_decimal(tick['bid']), 0)
                self.assertGreaterEqual(nombre_decimal(tick['ask']), nombre_decimal(tick['bid']))

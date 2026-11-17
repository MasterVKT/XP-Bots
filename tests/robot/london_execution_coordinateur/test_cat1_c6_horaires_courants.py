"""Catégorie 1, couche 6 : lectures nécessaires aux sorties, sans admission nouvelle."""
from dataclasses import replace
import unittest
from robot.london_execution_coordinateur.test_cat2_c6_coordinateur import ouvert
from robot.outils.coordinateur_execution import bloc_coordinateur, traiter
from robot.outils.execution_partagee import T, cotation
from xpbots.execution.c4_cycle import NatureCommande


class TestRelectureSorties(unittest.TestCase):
    def test_aucune_relecture_superflue_quand_aucune_position_n_est_ouverte(self):
        b = bloc_coordinateur(); b.port.appels.clear()
        lot = traiter(b, T+1)
        self.assertFalse(lot.commandes)
        self.assertFalse(any(a[0] == 'specifications' for a in b.port.appels))

    def test_position_ouverte_relue_sans_nouveau_signal_ni_ordre_d_entree(self):
        b, _, _ = ouvert(); b.port.appels.clear(); t = T+2
        q = replace(cotation(), instant_fournisseur_ms=t, instant_reception_ms=t)
        lot = traiter(b, t, cotations=(q,))
        self.assertEqual(sum(a[:2] == ('specifications', 'EURUSD') for a in b.port.appels), 1)
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in lot.commandes))
        self.assertFalse(lot.preparations)

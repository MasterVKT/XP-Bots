"""Catégorie 2, couche 1c : vraie réservation et nouveau dimensionnement C07."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.cycle_execution import bloc_cycle
from xpbots.execution.c0d_prix import construire_niveaux
from xpbots.execution.c3_dimensionnement import dimensionner,PlanDimensionnement


class TestJonctionTentative(unittest.TestCase):
    def test_nouvelle_cotation_repasse_le_vrai_dimensionnement_sans_double_reserve(self):
        b=bloc_cycle();cle=b.plan.reservation.cle
        b.registre.annuler_tentative(cle,b.registre.etat.version)
        q=replace(b.cotation,bid=b.cotation.bid+D('.00001'),ask=b.cotation.ask+D('.00001'))
        n=construire_niveaux(b.signal,q,b.profil,b.params)
        plan=dimensionner(b.signal,n,b.profil,b.compte,b.registre,b.garde,b.port,b.params,cle.deploiement)
        self.assertIsInstance(plan,PlanDimensionnement)
        e=b.registre.reserver(plan.reservation,b.compte,plan.version_reservations)
        self.assertEqual(len(e.reservations),1);self.assertEqual(e.reservations[0].cle,cle)
        self.assertEqual(b.registre.risque_total(b.compte),plan.risque)

"""Catégorie 2, bloc réel 0–5a : priorité, attente et clôture confirmée."""
from dataclasses import replace
import unittest
from robot.london_execution_coordinateur.test_cat1_c5a_sorties_obligatoires import ouvert, evaluer
from robot.outils.cycle_execution import cloture
from xpbots.execution.c1b_gardes import GardesCompte
from xpbots.execution.c4_cycle import CycleOrdre, NatureCommande
from xpbots.noyau.c1c_domaine import CauseCloture


class TestJonctionSorties(unittest.TestCase):
    def test_duree_sans_cotation_garde_protections_et_risque_jusqu_a_confirmation(self):
        b=ouvert(); t=b.signal.cloture_ms
        demande=evaluer(b,t+7200001).demandes[0]
        e=b.cycle.demander_cloture(t+7200001,demande.cause,priorite=demande.priorite)
        self.assertEqual([c.nature for c in e.commandes],[NatureCommande.MINUTERIE])
        self.assertEqual(e.etat.sl_natif,b.plan.niveaux.stop)
        self.assertEqual(len(b.registre.etat.reservations),1)
        e=b.cycle.sur_reponse(cloture(b,instant_ms=t+7200002,cause=CauseCloture.STOP_LOSS))
        for i in e.issues: b.registre.sur_issue(i)
        self.assertFalse(b.registre.etat.reservations)
        self.assertFalse(evaluer(b,t+7200002).demandes)

    def test_arret_persistant_apres_restauration_ne_devient_pas_neutre(self):
        b=ouvert(); t=b.signal.cloture_ms
        g=GardesCompte(b.params,replace(b.garde.etat,arret_global=True))
        b.cycle=CycleOrdre(b.params,b.signal,b.plan,b.profil,16,b.cycle.etat)
        b.cycle.reprendre(t+2)
        self.assertEqual(evaluer(b,t+2,gardes=g).demandes[0].cause,CauseCloture.ARRET_GLOBAL)

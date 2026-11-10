"""Le vrai cycle et les gardes consomment les réponses et mouvements natifs."""
from decimal import Decimal as D
import unittest
from robot.outils.rejeu import cas_simulateur,cotation_test
from xpbots.execution.c0a_types import EtatIntention
from xpbots.execution.c1b_gardes import GardesCompte,BaseReconstituee
from xpbots.rejeu.c1b_simulateur import PlanExecution


class TestJonctionSimulateur(unittest.TestCase):
    def test_cycle_reel_avec_accuse_fill_et_protection(self):
        b,e,c=cas_simulateur();t=b.signal.cloture_ms
        b.cycle.sur_reponse(e.soumettre((c,))[0]);r=e.sur_tick(cotation_test(b,t+250))[0]
        b.cycle.sur_reponse(r)
        self.assertIs(b.cycle.etat.statut,EtatIntention.OUVERTE)
        self.assertEqual(b.cycle.etat.premier_fill_ms,t+250)

    def test_base_utc_frais_et_garde_reelles_sans_apport(self):
        b,e,c=cas_simulateur();t=b.signal.cloture_ms
        self.assertIsInstance(e.base_utc(),BaseReconstituee)
        e.soumettre((c,));e.sur_tick(cotation_test(b,t+250));e.sur_tick(cotation_test(b,t+251,'1.09','1.0901'))
        base=e.base_utc();self.assertEqual(base.base_neutralisee,D(100));self.assertEqual(base.references_flux,())
        g=GardesCompte(e.configuration.technique.commun);g.observer(e.etat_compte(),base)
        self.assertEqual(g.etat.base_quotidienne,D(100))

    def test_sl_manquant_declenche_le_vrai_cycle_de_securite(self):
        b,_,c=cas_simulateur();b,e,c=cas_simulateur(plans={c.reference:PlanExecution(protections=False)})
        t=b.signal.cloture_ms;b.cycle.sur_reponse(e.soumettre((c,))[0])
        transition=b.cycle.sur_reponse(e.sur_tick(cotation_test(b,t+250))[0])
        self.assertTrue(transition.commandes)
        self.assertIs(b.cycle.etat.statut,EtatIntention.CLOTURE_DEMANDEE)

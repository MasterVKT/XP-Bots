"""Le dimensionnement et le cycle réels consomment le même livre actualisé."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.rejeu import cas_simulateur,cotation_test
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.execution.c0a_types import RefusExecution,EtatIntention
from xpbots.execution.c1b_gardes import GardesCompte
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.execution.c3_dimensionnement import dimensionner
from xpbots.rejeu.c0a_types import TarifCommission


class TestJonctionProfilCourant(unittest.TestCase):
    def test_dimensionnement_refuse_la_fermeture_recue_sans_changer_le_compte(self):
        b,e,_=cas_simulateur();t=e.instant_ms
        g=GardesCompte(b.params);g.observer(e.etat_compte(),e.base_utc())
        h=replace(b.profil.horaires,fermetures=(Intervalle(t,t+60000),))
        p=replace(b.profil,horaires=h,releve_ms=t)
        e.actualiser_profil(p,TarifCommission('ZERO_DECLARE',D(0),D(0),D(0),D(0)),t)
        resultat=dimensionner(b.signal,b.plan.niveaux,p,e.etat_compte(),
                             RegistreReservations(b.params),g,e,b.params,'paper')
        self.assertIsInstance(resultat,RefusExecution)
        self.assertEqual(e.etat_compte().solde,D(100))
        self.assertFalse(e.positions_ouvertes)

    def test_cycle_reel_reste_ouvert_apres_actualisation_du_livre(self):
        b,e,c=cas_simulateur();t=e.instant_ms
        b.cycle.sur_reponse(e.soumettre((c,))[0])
        b.cycle.sur_reponse(e.sur_tick(cotation_test(b,t+250))[0])
        e.actualiser_profil(replace(b.profil,releve_ms=t+250),
                           TarifCommission('ZERO_DECLARE',D(0),D(0),D(0),D(0)),t+250)
        self.assertIs(b.cycle.etat.statut,EtatIntention.OUVERTE)
        self.assertEqual(e.positions_ouvertes,(c.cle,))
        self.assertEqual(len(e.premiers_remplissages),1)

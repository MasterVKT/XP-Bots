"""Catégorie 2 : redémarrage sur partiel, vrais cycles, registres et gardes."""
from decimal import Decimal as D
import unittest
from robot.outils.cycle_execution import bloc_cycle, remplissage, cloture
from robot.london_execution_coordinateur.test_cat1_c5b_reprise_rapprochement import sauvegarde, observation
from xpbots.execution.c4_cycle import ReponseCourtier, NatureReponse, NatureCommande
from xpbots.execution.c5b_reprise import restaurer, rapprocher
from xpbots.noyau.c1c_domaine import CauseCloture, NatureIssue


class TestJonctionReprise(unittest.TestCase):
    def test_partiel_puis_redemarrage_cloture_native_et_annulation(self):
        b=bloc_cycle(); t=b.signal.cloture_ms
        b.cycle.preparer_envoi(t)
        e=b.cycle.sur_reponse(remplissage(b,volume_cumule=D('.2'),volume_position=D('.2'),
            reliquat=b.plan.volume-D('.2'),reliquat_annule=False))
        for i in e.issues: b.registre.sur_issue(i)
        r=restaurer(b.params,sauvegarde(b),16,t+1000)
        self.assertTrue(r.etat.cycles[0].etat.quota_compte)
        self.assertEqual(r.etat.cycles[0].etat.premier_fill_ms,t+1)
        ferme=cloture(b,instant_ms=t+2000,cause=CauseCloture.STOP_LOSS)
        annule=ReponseCourtier(NatureReponse.ANNULATION,b.plan.reservation.cle,'annulation',t+2000,
            dict(ordre='ordre-1',confirmee=True))
        r=rapprocher(b.params,r.etat,16,observation(b,t+2000,reponses=(ferme,annule)))
        self.assertTrue(r.prete); self.assertFalse(r.etat.reservations.reservations)
        self.assertFalse(r.etat.reservations.verrous)
        self.assertEqual([i.nature for i in r.issues],[NatureIssue.CLOTUREE])
        self.assertEqual(r.issues[0].cause,CauseCloture.STOP_LOSS)
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in r.commandes))

    def test_reprise_n_efface_pas_les_tentatives_de_protection(self):
        b=bloc_cycle(); t=b.signal.cloture_ms
        b.cycle.preparer_envoi(t); e=b.cycle.sur_reponse(remplissage(b,tp=None))
        for i in e.issues: b.registre.sur_issue(i)
        b.cycle.sur_minuterie(t+251,negociable=True)
        r=restaurer(b.params,sauvegarde(b),16,t+500)
        self.assertEqual(r.etat.cycles[0].etat.tentatives_protection,1)
        self.assertEqual(r.etat.cycles[0].etat.prochaine_protection_ms,t+1251)

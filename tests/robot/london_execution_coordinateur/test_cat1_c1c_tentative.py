"""Catégorie 1, couche 1c : retirer une tentative non remplie sans terminer l’intention."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.london_execution_coordinateur.test_cat1_c1c_registre_reservations import compte,reservation
from robot.outils.execution_partagee import commun,T,signal
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.noyau.c1c_domaine import Issue,NatureIssue,Motif


class TestAnnulationTentative(unittest.TestCase):
    def preparer(self):
        r=RegistreReservations(commun());a=reservation();r.reserver(a,compte(),0)
        return r,a

    def test_retirer_sans_terminer_puis_reserver_un_nouveau_plan(self):
        r,a=self.preparer();avant=r.etat
        e=r.annuler_tentative(a.cle,avant.version)
        self.assertEqual(e.version,avant.version+1);self.assertEqual(e.reservations,())
        self.assertEqual(e.terminees,());self.assertIs(r.annuler_tentative(a.cle,e.version),e)
        nouveau=replace(a,risque_initial=D('.4'))
        self.assertEqual(r.reserver(nouveau,compte(),e.version).reservations,(nouveau,))

    def test_version_perimee_bool_et_verrou_ne_liberent_aucun_risque(self):
        r,a=self.preparer();avant=r.etat
        for version in (0,True,1.0):
            v=r.annuler_tentative(a.cle,version)
            self.assertEqual(v.detail,'version_reservations');self.assertEqual(r.etat,avant)
        r.verrouiller(a.sous_jacent);avant=r.etat
        v=r.annuler_tentative(a.cle,avant.version)
        self.assertEqual(v.detail,'ETAT_ORDRE_INCONNU');self.assertEqual(r.etat,avant)

    def test_fill_et_cle_deja_terminee_ne_sont_pas_des_tentatives_liberables(self):
        r,a=self.preparer();r.sur_issue(Issue(a.cle,NatureIssue.REMPLIE,T));avant=r.etat
        with self.assertRaises(ValueError):r.annuler_tentative(a.cle,avant.version)
        self.assertEqual(r.etat,avant)
        r,a=self.preparer();r.sur_issue(Issue(a.cle,NatureIssue.REFUSEE,T,Motif.SPREAD_CAP));avant=r.etat
        self.assertEqual(r.annuler_tentative(a.cle,avant.version).detail,'cle_terminee')
        self.assertEqual(r.etat,avant)

    def test_reserve_de_l_autre_methode_preservee(self):
        r,a=self.preparer();b=reservation(signal(symbole='GBPUSD'),risque=D('.4'))
        r.reserver(b,compte(),r.etat.version)
        r.annuler_tentative(a.cle,r.etat.version)
        self.assertEqual(r.etat.reservations,(b,));self.assertEqual(r.risque_total(compte()),D('.4'))

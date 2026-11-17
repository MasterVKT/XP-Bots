"""Jonction 2a/2c : vrais C04, risque, dimensionnement et coordinateur."""
from dataclasses import replace
from decimal import Decimal as D
from tempfile import TemporaryDirectory
import unittest
from robot.outils.qualification_mt5 import T,JOUR,frontiere,exports,octets
from robot.outils.execution_partagee import configuration,signal,cotation
from robot.outils.faux_mt5 import TradePosition,OrderCheckResult
from xpbots.infra.c2c_calculs import CalculsMT5
from xpbots.execution.c0a_types import RefusExecution
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.execution.c1b_gardes import GardesCompte,reconstituer_base_utc
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.execution.c0d_prix import construire_niveaux
from xpbots.execution.c3_dimensionnement import dimensionner,PlanDimensionnement
from xpbots.execution.c4_cycle import NatureCommande,PreuvePersistance
from xpbots.execution.c5b_reprise import ObservationNative
from xpbots.execution.c6_coordinateur import CoordinateurCompte
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.noyau.c1c_domaine import Motif


class TestJonctionCalculs(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.sdk,self.session,self.specs=frontiere(self.temp.name)
        self.addCleanup(self.session.fermer)
        s,f=exports();self.specs.recevoir_exports(T,seances={'EURUSD.micro':octets(s)},fermetures=octets(f))
        self.conf=configuration();self.p=self.specs.instrument('EURUSD',T);self.pc=self.specs.compte(T)
        self.port=CalculsMT5(self.session,self.conf.commun,{'EURUSD':'EURUSD.micro'},T,profil=self.specs.instrument,
            qualification_compte=self.specs.compte,proprietaire=lambda ticket:None,flux_externe=lambda t,solde:False,assiette_stop_out=None)
        self.s=signal(cloture_ms=T);self.q=cotation(instant_fournisseur_ms=T,instant_reception_ms=T)

    def dimensionner(self,p=None):
        p=p or self.p;c=self.port.etat_compte();g=GardesCompte(self.conf.commun)
        base=reconstituer_base_utc(c,(),Intervalle(T//JOUR*JOUR,T+1),aucune_position_minuit=True)
        g.observer(c,base)
        n=construire_niveaux(self.s,self.q,p,self.conf.commun)
        return dimensionner(self.s,n,p,c,RegistreReservations(self.conf.commun),g,self.port,self.conf.commun,'FIXTURE')

    def test_grille_et_risque_all_in_natifs_du_vrai_dimensionnement(self):
        plan=self.dimensionner()
        self.assertIsInstance(plan,PlanDimensionnement)
        self.assertEqual(plan.volume%self.p.volume_pas,0)
        self.assertLessEqual(plan.risque,D(100)*D(str(self.conf.commun.risk_fraction_per_entry)))
        self.assertGreater(plan.reservation.marge_initiale,0)
        self.assertTrue(any(a[0]=='order_calc_profit' for a in self.sdk.appels))
        self.assertTrue(any(a[0]=='order_calc_margin' for a in self.sdk.appels))
        self.assertTrue(any(a[0]=='order_check' for a in self.sdk.appels))

    def test_volume_minimal_ou_frais_au_dela_du_budget_ne_sont_pas_forces(self):
        for p in (replace(self.p,volume_min=D(1),volume_pas=D(1)),
                  replace(self.p,commission_minimum_par_ordre=D(1),commission_nulle_confirmee=False)):
            r=self.dimensionner(p)
            self.assertIsInstance(r,RefusExecution);self.assertEqual(r.motif,Motif.MIN_VOLUME_OR_RISK_REJECT)

    def test_position_externe_et_marge_native_trop_forte_refusent(self):
        self.sdk.positions=[TradePosition(ticket=11,symbol='AUTRE_SYMBOLE',volume=1.)]
        r=self.dimensionner();self.assertEqual(r.motif,Motif.ACCOUNT_RISK_CAP);self.assertEqual(r.detail,'POSITIONS_EXTERNES')
        self.sdk.positions=[]
        self.sdk.scenarios['order_check'].extend([OrderCheckResult(retcode=0,margin=40.,margin_free=60.,equity=100.)]*100)
        r=self.dimensionner();self.assertEqual(r.motif,Motif.MARGIN_REJECT)

    def test_coordinateur_prepare_persiste_et_autorise_sans_envoi_natif_du_port(self):
        c=self.port.etat_compte();base=reconstituer_base_utc(c,(),Intervalle(T//JOUR*JOUR,T+1),aucune_position_minuit=True)
        coord=CoordinateurCompte(self.conf,'FIXTURE',{'EURUSD':self.p},self.pc,self.port,ControleTechniqueNeutre(),T,
            longueur_empreinte=16,mode='REJEU',observation=ObservationNative(c,T//JOUR*JOUR,True),base_utc=base)
        lot=coord.traiter(T,signaux=(self.s,),cotations=(self.q,))
        self.assertEqual(len(lot.preparations),1)
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in lot.commandes))
        preuve=PreuvePersistance(lot.etat.revision,tuple(c.reference for c in lot.preparations))
        envoi=coord.confirmer_persistance(preuve,T)
        self.assertEqual(len([c for c in envoi.commandes if c.nature is NatureCommande.ENTREE]),1)
        self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))

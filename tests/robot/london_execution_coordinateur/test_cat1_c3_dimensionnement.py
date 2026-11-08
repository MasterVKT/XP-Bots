"""Catégorie 1, couche 3 (dimensionnement) : contrat et bornes des sources C04–C09."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.execution_partagee import *
from robot.doublures.calculs_execution import CalculSynthetique
from xpbots.execution.c0a_types import *
from xpbots.execution.c0d_prix import construire_niveaux
from xpbots.execution.c1b_gardes import GardesCompte,reconstituer_base_utc
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.execution.c3_dimensionnement import *
from xpbots.noyau.c0a_temps import instant_vers_datetime,instant_depuis_datetime
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.noyau.c1c_domaine import Issue,NatureIssue,Motif

def preparer(p=None,c=None,*,param=None,port_=None,registre=None):
    p=p or profil();c=c or EtatCompte(T,D(100),D(100),D(0));param=param or commun()
    s=signal(cloture_prix=1.1005,stop_technique=1.09985);q=cotation(bid=D('1.1005'),ask=D('1.1006'))
    n=construire_niveaux(s,q,p,param)
    g=GardesCompte(param)
    minuit=instant_depuis_datetime(instant_vers_datetime(c.instant_ms).replace(hour=0,minute=0,second=0,microsecond=0))
    # Historique explicitement complet : solde courant inchangé depuis minuit pour cette famille de fixtures.
    base=reconstituer_base_utc(c,[],Intervalle(minuit,c.instant_ms+1),aucune_position_minuit=True)
    g.observer(c,base)
    return s,n,p,c,registre or RegistreReservations(param),g,port_ or CalculSynthetique(c,p),param
def calculer(args,**kwargs):return dimensionner(*args,'synthetique',**kwargs)

class TestDimensionnement(unittest.TestCase):
    def test_revalidation_avant_envoi_volume_exact_budget_gele_et_pas_de_double_reserve(self):
        args=preparer();plan=calculer(args);s,n,p,c,r,g,port,param=args
        r.reserver(plan.reservation,c,r.etat.version);initial=r.etat
        nouveau=replace(c,fonds_propres=D(1000),solde=D(1000))
        valide=revalider_avant_envoi(plan,s,p,nouveau,r,g,port,param)
        self.assertIsInstance(valide,PlanDimensionnement)
        self.assertEqual((valide.volume,valide.budget_gele,valide.fonds_propres_reference),(plan.volume,D('.5'),D(100)))
        self.assertEqual(r.etat,initial)
        port.autres_frais=D('.03')
        refus=revalider_avant_envoi(plan,s,p,nouveau,r,g,port,param)
        self.assertEqual(refus.motif,Motif.MIN_VOLUME_OR_RISK_REJECT)
        port.autres_frais=D('.01')
        self.assertEqual(revalider_avant_envoi(plan,s,p,nouveau,r,g,port,param).detail,'couts_avant_ordre')
        self.assertEqual(revalider_avant_envoi(plan,s,replace(p,volume_limite=D('.5')),nouveau,r,g,port,param).detail,'specifications_modifiees')

    def test_revalidation_controle_version_reelle_et_reservation_non_remplie(self):
        args=preparer();plan=calculer(args);s,n,p,c,r,g,port,param=args
        r.reserver(plan.reservation,c,r.etat.version)
        class Port(CalculSynthetique):
            def controler(self,*a,**kw):
                r.verrouiller('GBPUSD');return super().controler(*a,**kw)
        self.assertEqual(revalider_avant_envoi(plan,s,p,c,r,g,Port(),param).detail,'version_reservations')
        r.sur_issue(Issue(plan.reservation.cle,NatureIssue.REMPLIE,T))
        self.assertEqual(revalider_avant_envoi(plan,s,p,c,r,g,port,param).detail,'reservation_avant_ordre')

    def test_L01_minimum_standard_refuse_micro_admis(self):
        standard=profil(taille_contrat=D(100000),volume_min=D('.01'),volume_pas=D('.01'),volume_max=D('.01'))
        self.assertIs(calculer(preparer(standard)).motif,Motif.MIN_VOLUME_OR_RISK_REJECT)
        micro=profil(volume_max=D('.1'));plan=calculer(preparer(micro))
        self.assertEqual((plan.volume,plan.risque,plan.budget_gele),(D('.1'),D('.08'),D('.5')))
    def test_plus_grand_volume_et_budget_exact_inclus(self):
        args=preparer();plan=calculer(args)
        self.assertEqual((plan.volume,plan.risque),(D('.6'),D('.48')))
        c=CalculSynthetique(autres_frais=D('.02'));plan=calculer(preparer(port_=c))
        self.assertEqual((plan.volume,plan.risque),(D('.6'),D('.50')))
    def test_frais_non_monotones_pas_d_hypothese_lineaire(self):
        class P(CalculSynthetique):
            def frais_aller_retour(self,p,s,v): return D('.3') if v==D('.9') else D('.6') if v>=D('.8') else D(0)
        p=profil(taille_contrat=D(100));c=P(profil_=p)
        plan=calculer(preparer(p,port_=c));self.assertEqual(plan.volume,D('.9'))
    def test_plafond_grille_arrondi_bas_sans_epsilon(self):
        p=profil(volume_max=D('.29999999999'),volume_limite=D('.29999999999'))
        plan=calculer(preparer(p));self.assertEqual(plan.volume,D('.2'))
    def test_fraction_marge_P06_chargee_et_borne_exacte(self):
        self.assertEqual(commun().max_margin_fraction_of_equity,1/3)
        plafond=D(str(commun().max_margin_fraction_of_equity))*D(100)
        class P(CalculSynthetique):
            surplus=D(0)
            def controler(self,o,c,remplacement=False):return ControleNatif(True,plafond+self.surplus,D(100),True,'ok')
        p=profil(volume_max=D('.1'));port=P(profil_=p)
        self.assertIsInstance(calculer(preparer(p,port_=port)),PlanDimensionnement)
        port.surplus=D('.0000000000000001')
        r=calculer(preparer(p,port_=port));self.assertEqual((r.motif,r.detail),(Motif.MARGIN_REJECT,'MARGE_TIERS'))
    def test_marge_cumulee_positions_et_reservations_en_attente(self):
        p=profil(volume_max=D('.1'));c=EtatCompte(T,D(100),D(100),D(20))
        port=CalculSynthetique(c,p,marge_unitaire=D(100))
        self.assertIsInstance(calculer(preparer(p,c,port_=port)),PlanDimensionnement)
        r=RegistreReservations(commun());r.reserver(Reservation(cle(signal(symbole='GBPUSD')),'GBPUSD',D('.1'),D(5),D('.1')),c,0)
        v=calculer(preparer(p,c,port_=port,registre=r))
        self.assertEqual((v.motif,v.detail),(Motif.MARGIN_REJECT,'MARGE_TIERS'))
    def test_native_total_stopout_marge_libre_et_erreur(self):
        p=profil(volume_max=D('.1'))
        class P(CalculSynthetique):
            def controler(self,*a,**k): return ControleNatif(True,D(1),D(99),False,'stopout')
        self.assertEqual(calculer(preparer(p,port_=P(profil_=p))).detail,'CONTROLE_NATIF')
        class P(CalculSynthetique):
            def controler(self,*a,**k): return None
        self.assertEqual(calculer(preparer(p,port_=P(profil_=p))).detail,'controler')
    def test_externe_symbole_et_garde_sont_bloquants(self):
        externe=PositionCompte('externe','GBPUSD','GBPUSD',D('.1'),None)
        c=EtatCompte(T,D(100),D(100),D(0),(externe,))
        self.assertEqual(calculer(preparer(c=c)).detail,'POSITIONS_EXTERNES')
        args=preparer();g=args[5];g.observer(replace(args[3],fonds_propres=D(90)))
        self.assertIs(calculer(args).motif,Motif.GLOBAL_DRAWDOWN_HALT)
    def test_reserve_totale_reduit_le_volume_autorise(self):
        c=EtatCompte(T,D(100),D(100),D(0));r=RegistreReservations(commun())
        r.reserver(Reservation(cle(signal(symbole='GBPUSD')),'GBPUSD',D('.9'),D(0),D('.1')),c,0)
        plan=calculer(preparer(registre=r));self.assertEqual((plan.volume,plan.risque),(D('.1'),D('.08')))
    def test_profil_droits_et_frais_inconnus_refuses(self):
        args=list(preparer());args[2]=replace(args[2],commission_nulle_confirmee=False)
        self.assertIs(calculer(args).motif,Motif.ENVIRONMENT_NOT_READY)
        args=list(preparer());args[2]=replace(args[2],mode_negociation='SELL_ONLY')
        self.assertEqual(calculer(args).detail,'mode_negociation')
    def test_mutation_etat_pendant_calcul_interdit_admission_perimee(self):
        r=RegistreReservations(commun())
        class P(CalculSynthetique):
            def controler(self,*a,**kw):
                r.verrouiller('GBPUSD');return super().controler(*a,**kw)
        args=preparer(registre=r,port_=P())
        self.assertEqual(calculer(args).detail,'version_reservations')
    def test_reduction_post_fill_budget_gel_et_sl_fixe(self):
        args=preparer();initial=calculer(args);s,n,p,c,r,g,port,param=args
        r.reserver(initial.reservation,c,initial.version_reservations)
        r.sur_issue(Issue(initial.reservation.cle,NatureIssue.REMPLIE,T))
        position=PositionCompte('p','EURUSD','EURUSD',initial.volume,initial.risque,initial.reservation.cle)
        nouveau=replace(c,fonds_propres=D('99.5'),marge_utilisee=initial.volume,positions=(position,))
        args=(s,n,p,nouveau,r,g,port,param)
        plan=calculer(args,plan_initial=initial,volume_rempli=initial.volume,prix_reel=D('1.101075'),frais_entree_reels=D(0))
        self.assertEqual((plan.volume,plan.risque,plan.budget_gele,plan.fonds_propres_reference),(D('.4'),D('.5'),D('.5'),D(100)))
        self.assertEqual(plan.niveaux.stop,initial.niveaux.stop)
        self.assertTrue(plan.remplacement)
    def test_post_fill_sans_volume_admissible_demande_cloture_future(self):
        args=preparer(profil(volume_max=D('.1')));initial=calculer(args);s,n,p,c,r,g,port,param=args
        r.reserver(initial.reservation,c,r.etat.version);r.sur_issue(Issue(initial.reservation.cle,NatureIssue.REMPLIE,T))
        pos=PositionCompte('p','EURUSD','EURUSD',D('.1'),initial.risque,initial.reservation.cle)
        c=replace(c,positions=(pos,),marge_utilisee=D('.1'))
        v=calculer((s,n,p,c,r,g,port,param),plan_initial=initial,volume_rempli=D('.1'),prix_reel=D('1.101075'),frais_entree_reels=D('.49'))
        self.assertIs(v.motif,Motif.MIN_VOLUME_OR_RISK_REJECT)

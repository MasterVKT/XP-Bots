"""Sept calculs sur le SDK doublé et les vrais profils C04."""
from dataclasses import replace
from decimal import Decimal as D,localcontext,Context
from tempfile import TemporaryDirectory
import unittest
from robot.outils.qualification_mt5 import T,frontiere,exports,octets
from robot.outils.faux_mt5 import TradePosition,OrderCheckResult
from robot.outils.execution_partagee import configuration,signal
from xpbots.infra.c0a_types import ErreurInfra
from xpbots.infra.c2c_calculs import CalculsMT5
from xpbots.execution.c0a_types import PositionCompte,OrdreCalcule,RefusExecution
from xpbots.execution.c1a_calcul import appeler_calcul,CalculCourtier
from xpbots.noyau.c1c_domaine import Sens,CleIntention,Motif


class TestCalculsNatifs(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.sdk,self.session,self.specs=frontiere(self.temp.name)
        self.addCleanup(self.session.fermer)
        s,f=exports();self.specs.recevoir_exports(T,seances={'EURUSD.micro':octets(s)},fermetures=octets(f))
        self.profil=self.specs.instrument('EURUSD',T);self.pc=self.specs.compte(T);self.connues={};self.flux=False
        self.port=self.calculs()
        self.cle=CleIntention('FIXTURE','LONDON_V3','EURUSD',T,Sens.ACHAT)

    def calculs(self,assiette=None):
        return CalculsMT5(self.session,configuration().commun,{'EURUSD':'EURUSD.micro'},T,
            profil=lambda s,t:self.profil,qualification_compte=lambda t:self.pc,proprietaire=self.connues.get,
            flux_externe=lambda t,solde:self.flux,assiette_stop_out=assiette)

    def ordre(self):return OrdreCalcule(self.cle,'EURUSD.micro',D('.1'),D('1.1004'),D('1.0999'),D('1.1014'))

    def test_port_exact_profit_natif_achat_vente_et_marge(self):
        self.assertIsInstance(self.port,CalculCourtier)
        for sens,signe in ((Sens.ACHAT,1),(Sens.VENTE,-1)):
            v=self.port.profit(self.profil,sens,D('.1'),D('1.1'),D('1.101'))
            self.assertAlmostEqual(float(v),signe*.1)
            args=[a[1] for a in self.sdk.appels if a[0]=='order_calc_profit'][-1]
            self.assertEqual(args,(self.sdk.ORDER_TYPE_BUY if signe==1 else self.sdk.ORDER_TYPE_SELL,'EURUSD.micro',.1,1.1,1.101))
        self.assertAlmostEqual(float(self.port.marge(self.profil,Sens.ACHAT,D('.1'),D('1.1'))),1.1)
        self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))

    def test_frais_qualifies_minimum_et_contexte_decimal_independant(self):
        p=replace(self.profil,commission_par_lot_par_cote=D('2.5'),commission_minimum_par_ordre=D('.4'),commission_nulle_confirmee=False)
        with localcontext(Context(prec=3)):
            self.assertEqual(self.port.frais_aller_retour(p,Sens.ACHAT,D('.1')),D('.8'))
            self.assertEqual(self.port.frais_sortie(p,Sens.ACHAT,D('.2')),D('.50'))
        for p in (replace(p,devise_frais='EUR'),replace(self.profil,commission_nulle_confirmee=False)):
            r=appeler_calcul(self.port,'frais_sortie',p,Sens.ACHAT,D('.1'))
            self.assertEqual(r.motif,Motif.ENVIRONMENT_NOT_READY)

    def test_none_non_fini_bool_negative_marge_refusent(self):
        for fonction,v in (('order_calc_profit',None),('order_calc_profit',float('nan')),('order_calc_profit',True),
                            ('order_calc_margin',-1.),('order_calc_margin',None)):
            self.sdk.scenarios[fonction].append(v)
            nom='profit' if fonction=='order_calc_profit' else 'marge'
            args=(self.profil,Sens.ACHAT,D('.1'),D('1.1'))+((D('1.101'),) if nom=='profit' else ())
            r=appeler_calcul(self.port,nom,*args)
            self.assertIsInstance(r,RefusExecution);self.assertEqual(r.motif,Motif.ENVIRONMENT_NOT_READY)
        with self.assertRaises(ValueError):self.port.marge(self.profil,Sens.ACHAT,D('1e-1000'),D(1))

    def test_toutes_positions_externes_et_propriete_uniquement_par_ticket_prouve(self):
        self.sdk.positions=[TradePosition(ticket=11,symbol='EURUSD.micro',volume=.1),TradePosition(ticket=12,symbol='INDICE_EXTERNE',volume=1.)]
        compte=self.port.etat_compte()
        self.assertEqual(len(compte.positions),2);self.assertTrue(all(p.cle is None and p.risque_initial is None for p in compte.positions))
        self.connues['11']=PositionCompte('11','EURUSD','EURUSD',D('.1'),D('.3'),self.cle)
        compte=self.port.etat_compte()
        self.assertEqual(compte.positions[0].cle,self.cle);self.assertIsNone(compte.positions[1].cle)
        self.assertEqual(compte.positions[0].risque_initial,D('.3'))
        self.flux=None
        self.assertIsInstance(appeler_calcul(self.port,'etat_compte'),RefusExecution)
        self.flux=True;self.assertTrue(self.port.etat_compte().flux_externe_non_neutralise)

    def test_compte_natif_modifie_et_releve_non_causal_refusent(self):
        c=self.sdk.compte
        for cle,val in (('currency','EUR'),('margin',None),('equity',float('inf')),('margin_mode',self.sdk.ACCOUNT_MARGIN_MODE_RETAIL_NETTING)):
            self.sdk.compte=c._replace(**{cle:val})
            self.assertIsInstance(appeler_calcul(self.port,'etat_compte'),RefusExecution)
        self.sdk.compte=c;self.port.actualiser_instant(T+1)
        with self.assertRaises(ErreurInfra):self.port.actualiser_instant(T)

    def test_controle_projection_exacte_sans_champ_invente(self):
        compte=self.port.etat_compte();ordre=self.ordre();r=self.port.controler(ordre,compte)
        self.assertTrue(r.admis);self.assertTrue(r.stop_out_respecte);self.assertEqual(r.code,'CHECK_OK')
        requete=[a[1][0] for a in self.sdk.appels if a[0]=='order_check'][-1]
        self.assertEqual(requete,dict(action=self.sdk.TRADE_ACTION_DEAL,symbol='EURUSD.micro',volume=.1,type=self.sdk.ORDER_TYPE_BUY,
            price=1.1004,sl=1.0999,tp=1.1014,type_filling=self.sdk.ORDER_FILLING_IOC,type_time=self.sdk.ORDER_TIME_GTC))
        self.assertFalse({'magic','comment','deviation'}&requete.keys())

    def test_stop_out_pourcent_borne_stricte_marge_zero_et_marge_absente(self):
        compte=self.port.etat_compte();ordre=self.ordre()
        for marge,equity,attendu in ((100.,50.,False),(100.,50.01,True),(0.,0.,True)):
            self.sdk.scenarios['order_check'].append(OrderCheckResult(retcode=0,margin=marge,margin_free=1.,equity=equity))
            self.assertEqual(self.port.controler(ordre,compte).stop_out_respecte,attendu)
        self.sdk.scenarios['order_check'].append(OrderCheckResult(retcode=0,margin=None,margin_free=1.,equity=100.))
        self.assertIsInstance(appeler_calcul(self.port,'controler',ordre,compte),RefusExecution)

    def test_stop_out_money_exige_assiette_et_differe_equity_de_free_margin(self):
        self.pc=replace(self.pc,mode_stop_out='MONEY',niveau_stop_out=D(50))
        self.sdk.compte=self.sdk.compte._replace(margin_so_mode=self.sdk.ACCOUNT_STOPOUT_MODE_MONEY)
        compte=self.port.etat_compte();ordre=self.ordre()
        for assiette,attendu in (('EQUITY',True),('FREE_MARGIN',False),(None,None)):
            p=self.calculs(assiette)
            self.sdk.scenarios['order_check'].append(OrderCheckResult(retcode=0,margin=60.,margin_free=40.,equity=100.))
            r=appeler_calcul(p,'controler',ordre,compte)
            if attendu is None:self.assertIsInstance(r,RefusExecution)
            else:self.assertEqual(r.stop_out_respecte,attendu)

    def test_refus_preliminaire_garde_code_sans_commentaire_libre(self):
        compte=self.port.etat_compte()
        self.sdk.scenarios['order_check'].append(OrderCheckResult(retcode=self.sdk.TRADE_RETCODE_NO_MONEY,margin=0.,margin_free=0.,equity=100.,comment='NE_PAS_JOURNALISER'))
        r=self.port.controler(self.ordre(),compte)
        self.assertFalse(r.admis);self.assertEqual(r.code,'TRADE_RETCODE_NO_MONEY')
        self.assertNotIn('NE_PAS_JOURNALISER',repr(r))

    def test_remplacement_modifie_sltp_sans_nouvelle_marge(self):
        ordre=self.ordre();self.connues['11']=PositionCompte('11','EURUSD','EURUSD',D('.2'),D('.4'),self.cle)
        self.sdk.positions=[TradePosition(ticket=11,symbol='EURUSD.micro',volume=.2,sl=1.0999)]
        self.sdk.compte=self.sdk.compte._replace(margin=12.,margin_free=88.)
        compte=self.port.etat_compte()
        self.sdk.scenarios['order_check'].append(OrderCheckResult(retcode=0,margin=0.,margin_free=0.,equity=0.))
        r=self.port.controler(ordre,compte,remplacement=True)
        self.assertTrue(r.admis);self.assertEqual((r.marge_totale_apres,r.marge_libre_apres),(D(12),D(88)))
        req=[a[1][0] for a in self.sdk.appels if a[0]=='order_check'][-1]
        self.assertEqual(req,dict(action=self.sdk.TRADE_ACTION_SLTP,position=11,sl=1.0999,tp=1.1014))
        self.sdk.positions[0]=self.sdk.positions[0]._replace(sl=0.)
        self.assertIsInstance(appeler_calcul(self.port,'controler',ordre,compte,remplacement=True),RefusExecution)

    def test_solde_reel_du_releve_est_transmis_au_rapprochement_des_flux(self):
        appels=[]
        def flux(t,solde):
            appels.append((t,solde))
            return solde!=D(100)
        p=CalculsMT5(self.session,configuration().commun,{'EURUSD':'EURUSD.micro'},T,
            profil=lambda s,t:self.profil,qualification_compte=lambda t:self.pc,proprietaire=self.connues.get,
            flux_externe=flux,assiette_stop_out=None)
        self.sdk.compte=self.sdk.compte._replace(balance=200.,equity=200.)
        c=p.etat_compte()
        self.assertTrue(c.flux_externe_non_neutralise)
        self.assertEqual(appels,[(T,D(200))]);self.assertEqual(c.solde,D(200))

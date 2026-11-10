"""Sept mesures distinctes, calcul manuel, coûts réconciliés une fois."""
from dataclasses import replace
from datetime import date
from decimal import Decimal as D,Context,localcontext
import unittest
from robot.outils.rejeu import C,T
from robot.london_rejeu.test_cat1_c0a_types import trade
from xpbots.rejeu.c0a_types import ErreurRejeu,PointCompte,JourMarche,FactureIA
from xpbots.rejeu.c0b_protocole import charger_protocole
from xpbots.rejeu.c1c_metriques import (ComptageC09,calculer_mesures,retention,
    reconcilier_factures,drawdown,courbe_economique,panel_journalier,ventiler_trades)

J=date(2026,11,9)


def cas():
    a=trade(profit_brut=D('2.3'))
    b=replace(a,cle=replace(a.cle,cloture_ms=T+20),entree_ms=T+21,sortie_ms=T+30,profit_brut=D('-.7'))
    jours=(JourMarche(J,'validation'),JourMarche(date(2026,11,10),'validation'))
    courbe=(PointCompte(T,D(100),D(100),D(0)),PointCompte(T+5,D(110),D(100),D(1)),
        PointCompte(T+25,D(88),D(102),D(1)),PointCompte(T+30,D(101),D(101),D(0)))
    return (a,b),courbe,jours,ComptageC09(7,4,{'SPREAD_CAP':2},2,{J:2})


class TestMetriques(unittest.TestCase):
    def test_sept_mesures_non_confondues_et_profit_factor_manuel(self):
        ts,c,j,n=cas();b=calculer_mesures(ts,c,j,n)
        self.assertEqual((b.comptage.configurations,b.comptage.signaux,dict(b.comptage.refus),b.comptage.entrees),
            (7,4,{'SPREAD_CAP':2},2))
        self.assertEqual((b.positions_closes,b.resultats_nets,b.drawdown_courtier),(2,(D(2),D(-1)),D('.2')))
        self.assertEqual((b.pnl_courtier,b.esperance,b.profit_factor,b.taux_reussite),(D(1),D('.5'),D(2),D('.5')))
        self.assertEqual((b.jours_marche,b.jours_zero,b.frequence),(2,1,D(1)))
        self.assertEqual(b.r_moyen_net,D(1))

    def test_aucune_perte_pf_non_applicable_et_aucun_trade(self):
        ts,c,j,n=cas();n=ComptageC09(1,1,{},1,{J:1})
        b=calculer_mesures(ts[:1],c,j,n);self.assertIsNone(b.profit_factor);self.assertEqual(b.statut_pf,'SANS_PERTE')
        b=calculer_mesures((),c,j,ComptageC09(0,0,{},0,{}))
        self.assertEqual(b.jours_zero,2);self.assertIsNone(b.esperance);self.assertIsNone(b.taux_reussite)

    def test_entree_encore_ouverte_comptee_sans_trade_clos(self):
        _,c,j,_=cas();b=calculer_mesures((),c,j,ComptageC09(2,1,{},1,{J:1}))
        self.assertEqual((b.comptage.entrees,b.positions_closes,b.jours_zero),(1,0,1))

    def test_retention_absente_nulle_faible_et_exploitable(self):
        s=charger_protocole(C).seuils
        for ref in (None,0):self.assertEqual((retention(5,ref,s).ratio,retention(5,ref,s).statut),(None,'N_A'))
        self.assertEqual((retention(20,25,s).ratio,retention(20,25,s).statut),(D('.8'),'TROP_FAIBLE'))
        self.assertEqual((retention(40,50,s).ratio,retention(40,50,s).statut),(D('.8'),'EXPLOITABLE'))
        self.assertEqual(retention(8,10,s).ratio,D('.8'))  # ratio brut, pas une qualification

    def test_drawdown_sur_flottant_et_fonds_negatifs(self):
        _,c,_,_=cas();self.assertEqual(drawdown(c),D('.2'))
        c=c+(PointCompte(T+31,D(-11),D(101),D(0)),)
        self.assertEqual(drawdown(c),D('1.1'))
        with self.assertRaises(ErreurRejeu):drawdown(tuple(reversed(c)))

    def test_facture_dupliquee_et_recherche_au_bilan_global(self):
        f=FactureIA('evenement',T+1,D('.03'),('LONDON_V3','EMA_V3'),'EVENEMENT')
        r=FactureIA('recherche',T+2,D('.02'),('LONDON_V3',),'RECHERCHE')
        b=reconcilier_factures((f,f,r));self.assertEqual((b.total,b.recherche),(D('.05'),D('.02')))
        self.assertEqual(dict(b.par_methode),{'LONDON_V3':D('.015'),'EMA_V3':D('.015')})
        with self.assertRaises(ErreurRejeu):reconcilier_factures((f,replace(f,montant_usd=D('.04'))))

    def test_cout_ia_une_seule_fois_et_au_temps_sans_tick(self):
        ts,c,j,n=cas();f=FactureIA('consommation',T+15,D('.04'),('LONDON_V3',),'JOURNAL')
        b=calculer_mesures(ts,c,j,n,(f,f))
        self.assertEqual((b.pnl_courtier,b.cout_ia,b.pnl_economique),(D(1),D('.04'),D('.96')))
        econ=courbe_economique(c,(f,));p=next(p for p in econ if p.instant_ms==T+15)
        self.assertEqual(p.fonds_propres,D('109.96'))
        self.assertEqual(b.esperance_economique,D('.48'))
        self.assertEqual(c[-1].fonds_propres,D(101))

    def test_comptages_incoherents_et_positions_dupliquees_refuses(self):
        for args in ((1,2,{},1,{J:1}),(2,1,{},2,{J:2}),(1,1,{},1,{}),(1,1,{'INVENTE':1},0,{})):
            with self.subTest(args=args),self.assertRaises(ErreurRejeu):ComptageC09(*args)
        ts,c,j,n=cas()
        with self.assertRaises(ErreurRejeu):calculer_mesures((ts[0],ts[0]),c,j,n)

    def test_panel_journalier_sortie_et_jours_a_zero(self):
        ts,_,j,_=cas();panel=panel_journalier(ts,j,C.technique.commun)
        self.assertEqual([(v.pnl_net,v.trades_clos) for v in panel],[(D(1),2),(D(0),0)])
        with self.assertRaises(ErreurRejeu):panel_journalier(ts,j[1:],C.technique.commun)

    def test_ventilations_descriptives_n_utilisent_pas_le_score_json(self):
        ts,_,_,_=cas();v=ventiler_trades(ts,C.technique.commun)
        self.assertEqual(v[('symbole','EURUSD')]['taux_reussite'],D('.5'))
        self.assertEqual(v[('methode','LONDON_V3')]['r_moyen_net'],D(1))

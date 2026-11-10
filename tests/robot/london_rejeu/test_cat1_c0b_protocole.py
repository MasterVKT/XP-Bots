"""Catégorie 1, couche 0b : protocole textuel C10 et paramètres effectivement chargés."""
from dataclasses import FrozenInstanceError,replace
from datetime import date,datetime,timedelta
from decimal import Decimal as D
from types import MappingProxyType
import unittest
from robot.outils.orchestration import C
from robot.outils.chemins import RACINE_DEPOT
from xpbots.rejeu.c0b_protocole import (ErreurProtocole,BlocC10,ScenarioExecution,
    ParametresBootstrap,charger_protocole)


class TestProtocole(unittest.TestCase):
    def test_blocs_exactement_chronologiques_et_diagnostic_distinct(self):
        p=charger_protocole(C)
        self.assertEqual([(b.nom,b.debut,b.fin_exclusive) for b in p.blocs],[
            ('INITIALISATION',date(2019,12,2),date(2020,1,1)),
            ('DEVELOPPEMENT',date(2020,1,1),date(2023,1,1)),
            ('VALIDATION',date(2023,1,1),date(2025,1,1)),
            ('RESERVE',date(2025,1,1),date(2026,5,1)),
            ('DIAGNOSTIC',date(2026,5,1),date(2026,11,4))])
        self.assertEqual((p.continu.debut,p.continu.fin_exclusive),(date(2020,1,1),date(2026,11,4)))
        self.assertEqual(p.debut_diagnostic_v3,date(2026,5,11))

    def test_bornes_utc_semi_ouvertes(self):
        p=charger_protocole(C)
        for a,b in zip(p.blocs,p.blocs[1:]):self.assertEqual(a.intervalle_ms.fin_ms,b.intervalle_ms.debut_ms)
        self.assertEqual(p.blocs[-1].intervalle_ms.fin_ms-p.blocs[-1].intervalle_ms.debut_ms,187*86400000)

    def test_scenarios_p11_reference_et_stress(self):
        p=charger_protocole(C);r=p.scenario('REFERENCE');s=p.scenario('STRESS')
        self.assertEqual((r.delai_ms,r.ticks_adverses,r.facteur_spread),(250,1,D(1)))
        self.assertEqual((s.delai_ms,s.ticks_adverses,s.facteur_spread),(1000,2,D('1.25')))
        with self.assertRaises(ErreurProtocole):p.scenario('OPTIMISE')

    def test_seuils_c10_textuels_et_exportes(self):
        p=charger_protocole(C);s=p.seuils
        self.assertEqual((s.min_trades_total,s.min_trades_reserve,s.min_trades_symbole,s.min_reference),(200,100,50,50))
        self.assertEqual((s.profit_factor_reference,s.profit_factor_stress),(D('1.15'),D('1.00')))
        self.assertEqual((s.drawdown_reference,s.drawdown_stress),(D('.1'),D('.15')))
        self.assertEqual(s.retention,D(str(C.technique.commun.trade_count_retention_target)))
        self.assertEqual(s.trades_ia,C.ia.parametres['financial_min_closed_trades_per_strategy'])

    def test_parametres_bootstrap_viennent_de_l_export(self):
        p=charger_protocole(C);v=C.ia.parametres;b=p.bootstrap
        self.assertEqual((b.replications,b.bloc_jours,b.graine),(v['bootstrap_replications'],v['bootstrap_block_market_days'],v['bootstrap_seed']))
        self.assertEqual((b.percentile_bas,b.percentile_haut),(D(str(v['bootstrap_lower_percentile'])),D(str(v['bootstrap_upper_percentile']))))

    def test_variation_des_exports_synthetiques_change_le_protocole(self):
        v=dict(C.ia.parametres);v.update(bootstrap_replications=13,bootstrap_block_market_days=3,bootstrap_seed=42,
            bootstrap_lower_percentile=10,bootstrap_upper_percentile=90,financial_min_market_days=12,financial_min_retention=.7)
        c=replace(C,ia=replace(C.ia,parametres=MappingProxyType(v)),
            technique=replace(C.technique,commun=replace(C.technique.commun,combined_mean_fills_per_trading_day_target=2)))
        p=charger_protocole(c)
        self.assertEqual((p.bootstrap.replications,p.bootstrap.bloc_jours,p.bootstrap.graine),(13,3,42))
        self.assertEqual((p.bootstrap.percentile_bas,p.bootstrap.percentile_haut),(D(10),D(90)))
        self.assertEqual((p.seuils.jours_ia,p.seuils.retention_ia,p.seuils.frequence_forex),(12,D('.7'),D(2)))

    def test_six_perturbations_prescrites_sans_selection(self):
        p=charger_protocole(C)
        self.assertEqual([(c,v) for _,c,v in p.perturbations],[('OBJECTIF',D('.9')),('OBJECTIF',D('1.1')),
            ('BUFFER',D('.9')),('BUFFER',D('1.1')),('DUREE',6480),('DUREE',7920)])
        with self.assertRaises(FrozenInstanceError):p.prospectif_min_trades=1

    def test_prospectif_est_un_protocole_pas_un_deploiement(self):
        p=charger_protocole(C)
        self.assertEqual((p.prospectif.debut,p.prospectif.fin_exclusive,p.prospectif_min_trades),
            (date(2026,11,5),date(2027,2,5),100))

    def test_valeurs_exclusivement_textuelles_presentes_dans_c10(self):
        spec=(RACINE_DEPOT/'livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md').read_text(encoding='utf-8')
        c10=spec.split('## C10 —',1)[1].split('## C11 —',1)[0]
        for texte in ('02/12/2019','01/01/2020','31/12/2022','01/01/2023','31/12/2024',
            '01/01/2025','30/04/2026','01/05/2026','03/11/2026','05/11/2026','04/02/2027',
            '250 ms','1 000 ms','un tick adverse','deux ticks adverses','1,25','1,15','1,00','10 %','15 %','200 trades','100 dans','50 par','<50 trades','×0,9','×1,1','6 480','7 920'):
            with self.subTest(texte=texte):self.assertIn(texte,c10)

    def test_types_bornes_et_doublons_refuses(self):
        p=charger_protocole(C)
        for kw in ({'delai_ms':True},{'ticks_adverses':-1},{'facteur_spread':D('NaN')},{'nom':''}):
            with self.subTest(kw=kw),self.assertRaises(ErreurProtocole):replace(p.scenarios[0],**kw)
        for kw in ({'replications':False},{'bloc_jours':0},{'graine':-1},{'percentile_haut':D(101)},
            {'percentile_bas':D(99),'percentile_haut':D(90)}):
            with self.subTest(kw=kw),self.assertRaises(ErreurProtocole):replace(p.bootstrap,**kw)
        with self.assertRaises(ErreurProtocole):BlocC10('b',datetime(2026,1,1),date(2026,2,1),'x')
        with self.assertRaises(ErreurProtocole):replace(p,scenarios=(p.scenarios[0],p.scenarios[0]))
        with self.assertRaises(ErreurProtocole):replace(p,perturbations=(p.perturbations[0],p.perturbations[0]))

    def test_configuration_manquante_ou_parametre_non_fini_refuse(self):
        with self.assertRaises(ErreurProtocole):charger_protocole(None)
        v=dict(C.ia.parametres);v['financial_min_retention']=float('nan')
        with self.assertRaises(ErreurProtocole):charger_protocole(replace(C,ia=replace(C.ia,parametres=v)))

"""Catégorie 1, couche 1b (gardes_compte) : contrat et bornes des sources C04–C09."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.execution_partagee import *
from xpbots.execution.c0a_types import EtatCompte
from xpbots.execution.c1b_gardes import *
from xpbots.noyau.c0a_temps import instant_depuis_iso as ms
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.noyau.c1c_domaine import Motif

MINUIT=ms('2026-11-06T00:00:00.000Z')
def compte(eq=D(100),instant_=MINUIT,**kw): return EtatCompte(instant_,eq,kw.pop('solde',eq),D(0),**kw)
class TestGardes(unittest.TestCase):
    def test_quotidien_exact_puis_lendemain(self):
        g=GardesCompte(commun());self.assertIsNone(g.observer(compte()))
        self.assertIsNone(g.observer(compte(D('98.00001'),MINUIT+1)))
        self.assertIs(g.observer(compte(D(98),MINUIT+2)).motif,Motif.DAILY_LOSS_LOCK)
        self.assertIs(g.observer(compte(D(101),MINUIT+3)).motif,Motif.DAILY_LOSS_LOCK)
        self.assertIsNone(g.observer(compte(D(101),MINUIT+86400000)))
    def test_pic_global_exact_et_persistant(self):
        g=GardesCompte(commun());g.observer(compte());g.observer(compte(D(120),MINUIT+1))
        self.assertIsNone(g.observer(compte(D('108.00001'),MINUIT+2)))
        self.assertIs(g.observer(compte(D(108),MINUIT+3)).motif,Motif.GLOBAL_DRAWDOWN_HALT)
        self.assertIs(g.observer(compte(D(150),MINUIT+86400000)).motif,Motif.GLOBAL_DRAWDOWN_HALT)
        g.reactiver(compte(D(150),MINUIT+86400001),'decision-deploiement')
        self.assertFalse(g.etat.arret_global);self.assertEqual(g.etat.pic,D(150))
    def test_pas_de_base_premiere_equite_observee(self):
        g=GardesCompte(commun());r=g.observer(compte(D(90),T))
        self.assertEqual((r.motif,r.detail),(Motif.ENVIRONMENT_NOT_READY,'base_quotidienne'));self.assertIsNone(g.etat)
    def test_reconstitution_frais_et_flottant(self):
        c=compte(D(97),T,solde=D(99))
        base=reconstituer_base_utc(c,[MouvementCompte('frais',T,D(-1))],Intervalle(MINUIT,T+1),aucune_position_minuit=True)
        self.assertEqual((base.solde_minuit,base.base_neutralisee,base.pic_solde_neutralise),(D(100),D(100),D(100)))
        self.assertIs(GardesCompte(commun()).observer(c,base).motif,Motif.DAILY_LOSS_LOCK)
    def test_historique_incomplet_position_minuit_et_futur(self):
        c=compte(instant_=T)
        for couverture,preuve in ((Intervalle(MINUIT+1,T+1),True),(Intervalle(MINUIT,T),True),(Intervalle(MINUIT,T+1),False)):
            self.assertIs(reconstituer_base_utc(c,[],couverture,aucune_position_minuit=preuve).motif,Motif.ENVIRONMENT_NOT_READY)
        with self.assertRaises(ValueError): reconstituer_base_utc(c,[MouvementCompte('futur',T+1,D(1))],Intervalle(MINUIT,T+1),aucune_position_minuit=True)
    def test_flux_identifie_ne_fait_pas_un_profit(self):
        c=compte(D(150),T)
        b=reconstituer_base_utc(c,[MouvementCompte('depot',T,D(50),True)],Intervalle(MINUIT,T+1),aucune_position_minuit=True)
        self.assertEqual((b.solde_minuit,b.base_neutralisee,b.pic_solde_neutralise),(D(100),D(150),D(150)))
        g=GardesCompte(commun());g.observer(compte());g.neutraliser_flux(D(50),'depot')
        self.assertEqual(g.etat.base_quotidienne,D(150));g.neutraliser_flux(D(50),'depot');self.assertEqual(g.etat.pic,D(150))
        self.assertIsNone(g.observer(c));self.assertEqual(g.etat.pic,D(150))
    def test_flux_inconnu_et_references_invalides(self):
        g=GardesCompte(commun());g.observer(compte());avant=g.etat
        r=g.observer(compte(D(150),T,flux_externe_non_neutralise=True))
        self.assertEqual(r.detail,'flux_externe');self.assertEqual(g.etat,avant)
        with self.assertRaises(ValueError): g.reactiver(compte(),'')
        with self.assertRaises(ValueError): g.observer(compte(instant_=MINUIT-1))
    def test_retrait_pendant_arret_rebase_aussi_ancien_pic(self):
        g=GardesCompte(commun());g.observer(compte())
        t=T+86400000;c=compte(D(50),t)
        b=reconstituer_base_utc(c,[MouvementCompte('retrait',t,D(-50),True)],Intervalle(MINUIT+86400000,t+1),aucune_position_minuit=True)
        self.assertIsNone(g.observer(c,b))
        self.assertEqual((g.etat.base_quotidienne,g.etat.pic),(D(50),D(50)))
    def test_parametres_modifies_sans_seuil_recopie(self):
        g=GardesCompte(replace(commun(),daily_equity_loss_limit_fraction=.03));g.observer(compte())
        self.assertIsNone(g.observer(compte(D(98),MINUIT+1)))
        self.assertIs(g.observer(compte(D(97),MINUIT+2)).motif,Motif.DAILY_LOSS_LOCK)

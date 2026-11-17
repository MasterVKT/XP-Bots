"""Dépôt, pic de solde intermédiaire et arrêts durables dans la vraie boucle."""
from decimal import Decimal as D
import unittest
from robot.outils.boucle_directe import HarnaisDirect
from robot.outils.faux_mt5 import TradeDeal
from robot.outils.qualification_mt5 import T
from robot.outils.orchestration import C
from xpbots.app.c1e_cli_rapports import rapporter_incident


class TestCompteDansLaBoucle(HarnaisDirect,unittest.TestCase):
    def deal(self,ticket,position,type_,entry,t,profit):
        return TradeDeal(ticket=ticket,order=ticket if position else 0,time_msc=t,type=type_,entry=entry,
            magic=0,position_id=position,reason=self.sdk.DEAL_REASON_CLIENT,volume=.1 if position else 0.,
            price=1. if position else 0.,commission=0.,swap=0.,profit=profit,fee=0.,
            symbol='EURUSD.micro' if position else '',comment='EXTERIEUR_FIXTURE')

    def gardes(self,b):
        return dict(b.moteur.exporter_checkpoint_journal().coordinateurs)['REFERENCE'].reprise.gardes

    def test_flux_neutralise_une_fois_pic_clos_et_arrets_conserves_apres_reprise(self):
        b=self.nouveau('DEMO');b.iterer();sdk=self.sdk
        sdk.transactions=[
            self.deal(7001,0,sdk.DEAL_TYPE_BALANCE,0,T+100,100.),
            self.deal(7002,9001,sdk.DEAL_TYPE_BUY,sdk.DEAL_ENTRY_IN,T+200,0.),
            self.deal(7003,9001,sdk.DEAL_TYPE_SELL,sdk.DEAL_ENTRY_OUT,T+500,-4.)]
        sdk.compte=sdk.compte._replace(balance=196.,equity=196.,margin_free=196.)
        self.avancer(1000);b.iterer();g=self.gardes(b)
        self.assertEqual(g.base_quotidienne,D(200));self.assertTrue(g.verrou_quotidien);self.assertFalse(g.arret_global)
        self.assertEqual(g.references.count('mt5:deal:7001'),1)
        # Deux positions tierces déjà closes : aucun ordre ni adoption par le robot.
        # Le solde final reste 196, mais le vrai livre natif a connu un pic à 220.
        sdk.transactions.extend((
            self.deal(7004,9002,sdk.DEAL_TYPE_BUY,sdk.DEAL_ENTRY_IN,T+1100,0.),
            self.deal(7005,9002,sdk.DEAL_TYPE_SELL,sdk.DEAL_ENTRY_OUT,T+1300,24.),
            self.deal(7006,9003,sdk.DEAL_TYPE_BUY,sdk.DEAL_ENTRY_IN,T+1500,0.),
            self.deal(7007,9003,sdk.DEAL_TYPE_SELL,sdk.DEAL_ENTRY_OUT,T+1900,-24.)))
        self.avancer(1000);b.iterer();g=self.gardes(b)
        self.assertEqual((g.base_quotidienne,g.pic),(D(200),D(220)))
        self.assertTrue(g.verrou_quotidien);self.assertTrue(g.arret_global)
        self.assertTrue(any(n=='GLOBAL' and actif for _,n,actif,_,_ in self.infra.depot.arrets()))
        self.assertTrue(self.infra.fermer(1000))
        b=self.nouveau('DEMO',sdk=sdk);b.iterer();g=self.gardes(b)
        self.assertTrue(g.verrou_quotidien);self.assertTrue(g.arret_global)
        self.assertEqual((g.base_quotidienne,g.pic),(D(200),D(220)))
        self.assertEqual(g.references.count('mt5:deal:7001'),1)
        self.assertEqual(rapporter_incident(C,b.archive_incident())['statut'],'IDENTIQUE')
        self.assertFalse(any(n=='order_send' for n,*_ in sdk.appels))

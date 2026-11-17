"""Transactions reelles du faux terminal, sans doublure des composants C08."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from unittest.mock import patch
from robot.outils.faux_mt5 import TradeDeal,TradePosition,TradeOrder,OrderSendResult
from robot.outils.qualification_mt5 import T,JOUR
from xpbots.execution.c4_cycle import NatureReponse,NatureCommande,CommandeExecution,PreuvePersistance
from xpbots.execution.c1b_gardes import GardesCompte,BaseReconstituee
from xpbots.execution.c0a_types import EtatIntention
from xpbots.noyau.c1c_domaine import CauseCloture
from robot.london_infrastructure.test_cat1_c2d_transport import HarnaisTransport


class TestObservationNative(HarnaisTransport,unittest.TestCase):
    def remplir(self):
        self.autoriser();self.attendre()
        rapport=self.transport.observer()
        self.assertIsNotNone(rapport.observation,rapport.alertes)
        return rapport

    def test_ack_ne_compte_pas_un_fill_mais_deal_natif_le_prouve(self):
        r=self.remplir();o=r.observation
        fills=[v for v in o.reponses if v.nature is NatureReponse.REMPLISSAGE]
        self.assertEqual(len(fills),1);f=fills[0];d=self.commande.donnees
        self.assertEqual((f.donnees['volume_cumule'],f.donnees['prix_moyen'],f.donnees['execution_ms']),
            (d['volume'],d['prix'],T))
        self.assertEqual(o.compte.positions,());self.assertEqual(o.positions[0].sl,d['sl'])
        p=self.transport.proprietaire(o.positions[0].ticket)
        self.assertEqual((p.cle,p.risque_initial),(self.commande.cle,d['risque_initial']))
        self.temps+=1
        repete=self.transport.observer()
        self.assertEqual(repete.observation.reponses,o.reponses)
        self.assertFalse(self.transport.flux_externe(self.temps,D(100)))
        self.assertTrue(self.transport.flux_externe(self.temps,D(200)))

    def test_none_ou_deal_futur_ne_valent_jamais_absence_ni_base(self):
        self.sdk.scenarios['history_deals_get'].append(None)
        r=self.transport.observer();self.assertIsNone(r.observation);self.assertIsNone(r.base_utc)
        self.remplir();self.sdk.transactions[0]=self.sdk.transactions[0]._replace(time_msc=T+1)
        r=self.transport.observer();self.assertIsNone(r.observation)
        self.assertTrue(self.transport.flux_externe(T,D(100)))

    def test_none_apres_emission_et_reprise_ne_donnent_aucune_absence(self):
        self.sdk.scenarios['order_send'].append(None);self.autoriser();self.attendre()
        self.temps+=1000000
        r=self.transport.observer();self.assertEqual(r.observation.absences,())
        reprise=self.nouveau(self.transport.exporter_etat());self.addCleanup(lambda:reprise.fermer(1000))
        self.assertEqual(reprise.observer().observation.absences,())
        self.assertEqual(sum(a[0]=='order_send' for a in self.sdk.appels),1)

    def test_timeout_retourne_avec_envoi_termine_autorise_preuve_positive_seulement(self):
        self.sdk.scenarios['order_send'].append(OrderSendResult(retcode=self.sdk.TRADE_RETCODE_TIMEOUT,order=0))
        self.autoriser();self.attendre();self.temps+=1000000
        r=self.transport.observer();self.assertEqual(len(r.observation.absences),1)
        self.assertTrue(r.observation.absences[0].envoi_termine)
        # Le cycle, non l'adaptateur, decide de la liberation sur preuve positive.

    def test_dates_de_reception_apres_lecture_ne_tronquent_pas_la_preuve_positive(self):
        self.sdk.scenarios['order_send'].append(OrderSendResult(retcode=self.sdk.TRADE_RETCODE_TIMEOUT,order=0))
        self.autoriser();self.attendre()
        compteur=[T]
        def heure():
            compteur[0]+=1
            return compteur[0]*1000000
        with patch('time.time_ns',side_effect=heure):r=self.transport.observer()
        self.assertIsNotNone(r.observation,r.alertes)
        self.assertGreater(r.instant_ms,T)
        self.assertEqual(r.observation.absences[0].fin_ms,r.instant_ms)
        self.assertIsInstance(r.base_utc,BaseReconstituee)

    def test_identifier_est_distinct_du_ticket_et_une_modification_de_ticket_bloque(self):
        self.autoriser();self.attendre()
        self.sdk.positions[0]=self.sdk.positions[0]._replace(identifier=999)
        self.sdk.transactions[0]=self.sdk.transactions[0]._replace(position_id=999)
        r=self.transport.observer();self.assertIsNotNone(r.observation,r.alertes)
        p=r.observation.positions[0]
        self.assertEqual(self.transport.proprietaire(p.ticket).identifiant,p.ticket)
        self.sdk.positions[0]=self.sdk.positions[0]._replace(ticket=888)
        r=self.transport.observer();self.assertIsNone(r.observation)

    def test_fin_future_ordre_historique_ne_prouve_pas_absence(self):
        self.sdk.historique_ordres=[TradeOrder(ticket=99,position_id=0,symbol='TIERS',magic=0,comment='',
            time_setup_msc=T-1,time_done_msc=T+1,state=self.sdk.ORDER_STATE_REJECTED,volume_current=0.)]
        self.assertIsNone(self.transport.observer().observation)

    def test_partiel_reliquat_non_annule_et_frais_corriges_meme_transaction(self):
        self.autoriser();self.attendre();d=self.sdk.transactions[0];p=self.sdk.positions[0];demande=D(str(d.volume));partiel=demande/2
        self.sdk.transactions[0]=d._replace(volume=float(partiel),commission=-.01)
        self.sdk.compte=self.sdk.compte._replace(balance=99.99,equity=99.99)
        self.sdk.positions[0]=p._replace(volume=float(partiel))
        self.sdk.ordres=[TradeOrder(ticket=d.order,position_id=p.identifier,symbol=p.symbol,magic=p.magic,comment=p.comment,
            time_setup_msc=T,state=self.sdk.ORDER_STATE_PARTIAL,volume_current=float(partiel))]
        r=self.transport.observer();self.assertIsNotNone(r.observation,r.alertes)
        fill=next(v for v in r.observation.reponses if v.nature is NatureReponse.REMPLISSAGE)
        self.assertEqual((fill.donnees['reliquat'],fill.donnees['reliquat_annule']),(partiel,False))
        self.sdk.transactions[0]=self.sdk.transactions[0]._replace(commission=-.02)
        self.sdk.compte=self.sdk.compte._replace(balance=99.98,equity=99.98)
        corrige=self.transport.observer();f=next(v for v in corrige.observation.reponses if v.nature is NatureReponse.REMPLISSAGE)
        self.assertEqual((f.donnees['transaction'],f.donnees['frais_entree']),(fill.donnees['transaction'],D('.02')))
        self.assertNotEqual(f.reference,fill.reference)
        self.sdk.historique_ordres=[self.sdk.ordres[0]._replace(state=self.sdk.ORDER_STATE_CANCELED,time_done_msc=T,volume_current=0.)];self.sdk.ordres=[]
        f=next(v for v in self.transport.observer().observation.reponses if v.nature is NatureReponse.REMPLISSAGE)
        self.assertEqual((f.donnees['reliquat'],f.donnees['reliquat_annule']),(D(0),True))

    def test_depot_identifie_neutralise_la_base_et_declenche_verrou_quotidien(self):
        self.sdk.transactions=[TradeDeal(ticket=1,order=0,time_msc=T-1000,type=self.sdk.DEAL_TYPE_BALANCE,entry=0,
            magic=0,position_id=0,reason=self.sdk.DEAL_REASON_CLIENT,volume=0.,price=0.,commission=0.,swap=0.,profit=100.,fee=0.,symbol='',comment='')]
        self.sdk.compte=self.sdk.compte._replace(balance=200.,equity=196.)
        r=self.transport.observer(depuis_flux_ms=T-2000)
        self.assertIsInstance(r.base_utc,BaseReconstituee);self.assertEqual(r.base_utc.base_neutralisee,D(200))
        self.assertEqual(r.base_utc.flux_identifies[0].variation_solde,D(100))
        g=GardesCompte(self.transport_configuration());refus=g.observer(r.observation.compte,r.base_utc)
        self.assertEqual(refus.motif.value,'DAILY_LOSS_LOCK')

    def test_solde_modifie_sans_transaction_identifiee_est_bloquant(self):
        self.assertIsNotNone(self.transport.observer().observation)
        self.sdk.compte=self.sdk.compte._replace(balance=150.,equity=150.)
        r=self.transport.observer()
        self.assertIsNone(r.observation)
        self.assertTrue(self.transport.flux_externe(T,D(150)))

    def transport_configuration(self):
        from robot.outils.execution_partagee import configuration
        return configuration().commun

    def test_position_presente_a_minuit_ne_prouve_pas_base(self):
        self.sdk.positions=[TradePosition(ticket=9,identifier=9,type=self.sdk.POSITION_TYPE_BUY,magic=0,
            time_msc=T-2*JOUR,volume=.1,sl=0.,tp=0.,symbol='AUTRE',comment='tiers')]
        r=self.transport.observer();self.assertIsNotNone(r.observation)
        self.assertNotIsInstance(r.base_utc,BaseReconstituee)
        self.assertTrue(r.observation.compte.flux_externe_non_neutralise)
        self.assertIsNone(self.transport.proprietaire('9'))

    def test_cloture_native_tp_et_fermeture_inconnue_bloquante(self):
        self.remplir();d=self.sdk.transactions[0];self.sdk.positions=[]
        out=d._replace(ticket=d.ticket+1,order=d.order+1,type=self.sdk.DEAL_TYPE_SELL,entry=self.sdk.DEAL_ENTRY_OUT,
            reason=self.sdk.DEAL_REASON_TP,price=d.price+.001,profit=.1)
        self.sdk.transactions.append(out)
        self.sdk.compte=self.sdk.compte._replace(balance=100.1,equity=100.1)
        r=self.transport.observer();self.assertIsNotNone(r.observation,r.alertes)
        close=next(v for v in r.observation.reponses if v.nature is NatureReponse.CLOTURE)
        self.assertEqual((close.donnees['volume_restant'],close.donnees['cause']),(D(0),CauseCloture.TAKE_PROFIT))
        self.sdk.transactions[-1]=out._replace(reason=self.sdk.DEAL_REASON_CLIENT)
        r=self.transport.observer();self.assertIsNone(r.observation)

    def test_pic_de_solde_entre_deux_observations_ne_disparait_pas(self):
        def deal(ticket,position,type_,entry,instant,profit):
            return TradeDeal(ticket=ticket,order=ticket,time_msc=instant,type=type_,entry=entry,
                magic=0,position_id=position,reason=self.sdk.DEAL_REASON_CLIENT,volume=.1,price=1.,commission=0.,swap=0.,profit=profit,fee=0.,symbol='TIERS',comment='')
        self.sdk.transactions=[deal(1,1,self.sdk.DEAL_TYPE_BUY,self.sdk.DEAL_ENTRY_IN,T-4000,0.),
            deal(2,1,self.sdk.DEAL_TYPE_SELL,self.sdk.DEAL_ENTRY_OUT,T-3000,20.),
            deal(3,3,self.sdk.DEAL_TYPE_BUY,self.sdk.DEAL_ENTRY_IN,T-2000,0.),
            deal(4,3,self.sdk.DEAL_TYPE_SELL,self.sdk.DEAL_ENTRY_OUT,T-1000,-12.)]
        self.sdk.compte=self.sdk.compte._replace(balance=108.,equity=108.)
        r=self.transport.observer(depuis_flux_ms=T-5000)
        self.assertIsInstance(r.base_utc,BaseReconstituee)
        self.assertEqual((r.base_utc.base_neutralisee,r.base_utc.pic_solde_neutralise),(D(100),D(120)))
        g=GardesCompte(self.transport_configuration())
        self.assertEqual(g.observer(r.observation.compte,r.base_utc).motif.value,'GLOBAL_DRAWDOWN_HALT')

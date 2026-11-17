"""Jonction du vrai coordinateur, calcul MT5, transport et depot physique."""
from decimal import Decimal as D
from pathlib import Path
from threading import Event
import unittest
from robot.london_infrastructure.test_cat1_c2d_transport import HarnaisTransport
from robot.outils.execution_partagee import configuration,signal,cotation
from robot.outils.qualification_mt5 import T
from xpbots.infra.c2c_calculs import CalculsMT5
from xpbots.infra.c0c_sqlite import DepotSQLite
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.execution.c4_cycle import NatureCommande,PreuvePersistance,NatureReponse
from xpbots.execution.c6_coordinateur import CoordinateurCompte
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur
from robot.outils.faux_mt5 import OrderSendResult,TradeDeal,TradePosition,TradeOrder


class TestJonctionExecution(HarnaisTransport,unittest.TestCase):
    def transmettre(self,coord,lot,t=T):
        suite=coord.confirmer_persistance(PreuvePersistance(lot.etat.revision,tuple(c.reference for c in lot.preparations)),t)
        natif=self.transport.preparer_entrees(suite.commandes,t)
        self.transport.autoriser_entrees(PreuvePersistance(natif.revision,natif.references))
        return suite

    def construire(self):
        conf=configuration();r=self.transport.observer();self.assertIsNotNone(r.observation,r.alertes)
        port=CalculsMT5(self.session,conf.commun,{'EURUSD':'EURUSD.micro'},T,profil=self.specs.instrument,
            qualification_compte=self.specs.compte,proprietaire=self.transport.proprietaire,
            flux_externe=self.transport.flux_externe,assiette_stop_out=None)
        # Scenario de controle du coeur REJEU explicite ; le seul terminal est FauxMT5.
        coord=CoordinateurCompte(conf,'FIXTURE',{'EURUSD':self.p},self.specs.compte(T),port,ControleTechniqueNeutre(),T,
            longueur_empreinte=16,mode='REJEU',observation=r.observation,base_utc=r.base_utc)
        q=cotation(instant_fournisseur_ms=T,instant_reception_ms=T)
        lot=coord.traiter(T,signaux=(signal(cloture_ms=T),),cotations=(q,))
        self.assertEqual(len(lot.preparations),1)
        return coord,port,lot,q

    def test_deux_commits_reels_avant_envoi_et_un_seul_quota_sur_observations_repetees(self):
        coord,port,lot,q=self.construire()
        meta=dict(deploiement='FIXTURE',mode='DEMO',empreintes={'technique':'a'*64,'ia':'b'*64},commit='c'*40)
        path=Path(self.temp.name)/'etat.sqlite'
        with DepotSQLite(path,meta) as depot:
            depot.persister(1,T,serialiser_valeur(lot.etat))
            suite=coord.confirmer_persistance(PreuvePersistance(lot.etat.revision,tuple(c.reference for c in lot.preparations)),T)
            entrees=tuple(c for c in suite.commandes if c.nature is NatureCommande.ENTREE)
            natif=self.transport.preparer_entrees(entrees,T)
            avant=serialiser_valeur(dict(coeur=coord.etat,natif=self.transport.exporter_etat()))
            depot.persister(2,T,avant)
            self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))
            self.assertEqual(depot.charger(),avant)
            self.transport.autoriser_entrees(PreuvePersistance(natif.revision,natif.references))
            ack=self.attendre();self.assertTrue(all(r.nature is NatureReponse.ACCUSE for r in ack.reponses))
            r=self.transport.observer(depuis_flux_ms=T)
            sortie=coord.traiter(T,reponses=ack.reponses,observation=r.observation,base_utc=r.base_utc,cotations=(q,))
            self.assertEqual(sum(i.nature.value=='REMPLIE' for i in sortie.issues),1)
            self.assertTrue(coord.etat.reprise.cycles[0].etat.quota_compte)
            repete=coord.traiter(T,observation=r.observation,base_utc=r.base_utc)
            self.assertFalse(repete.issues)
            depot.persister(3,T,serialiser_valeur(dict(coeur=coord.etat,natif=self.transport.exporter_etat())))
        with DepotSQLite(path,meta) as depot:
            sauve=deserialiser_valeur(depot.charger())
        reprise=self.nouveau(sauve['natif']);self.addCleanup(lambda:reprise.fermer(1000))
        self.assertTrue(reprise.flux_externe(T,D(100)))
        r=reprise.observer(depuis_flux_ms=T);self.assertIsNotNone(r.observation)
        coord2=CoordinateurCompte(configuration(),'FIXTURE',{'EURUSD':self.p},self.specs.compte(T),port,ControleTechniqueNeutre(),T,
            longueur_empreinte=16,mode='REJEU',etat=sauve['coeur'],observation=r.observation,base_utc=r.base_utc)
        self.assertTrue(coord2.etat.reprise.cycles[0].etat.quota_compte)
        self.assertEqual(sum(a[0]=='order_send' for a in self.sdk.appels),1)

    def test_commit_native_en_echec_ne_produit_aucun_envoi(self):
        coord,port,lot,q=self.construire()
        meta=dict(deploiement='FIXTURE',mode='DEMO',empreintes={'technique':'a'*64,'ia':'b'*64},commit='c'*40)
        with DepotSQLite(Path(self.temp.name)/'etat.sqlite',meta) as depot:
            depot.persister(1,T,serialiser_valeur(lot.etat))
            suite=coord.confirmer_persistance(PreuvePersistance(lot.etat.revision,tuple(c.reference for c in lot.preparations)),T)
            self.transport.preparer_entrees(suite.commandes,T)
            with self.assertRaises(ValueError):depot.persister(3,T,serialiser_valeur(coord.etat))
        self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))

    def test_refus_prix_refait_tous_les_controles_avec_nouvelle_reference_et_un_quota(self):
        coord,port,lot,q=self.construire()
        self.sdk.scenarios['order_send'].append(OrderSendResult(retcode=self.sdk.TRADE_RETCODE_REQUOTE,order=0))
        premier=self.transmettre(coord,lot);ack=self.attendre()
        attente=coord.traiter(T,reponses=ack.reponses)
        self.assertFalse(attente.issues)
        self.temps=T+1;port.actualiser_instant(self.temps)
        r=self.transport.observer(depuis_flux_ms=T)
        q=cotation(instant_fournisseur_ms=self.temps,instant_reception_ms=self.temps)
        lot=coord.traiter(self.temps,observation=r.observation,base_utc=r.base_utc,cotations=(q,))
        self.assertEqual(len(lot.preparations),1,[(i.nature,i.motif,i.detail) for i in lot.issues]);self.assertFalse(lot.issues)
        self.sdk.instant_ms=self.temps
        second=self.transmettre(coord,lot,self.temps);self.attendre()
        refs=[c.reference for lot_ in (premier,second) for c in lot_.commandes if c.nature is NatureCommande.ENTREE]
        self.assertEqual(len(set(refs)),2)
        r=self.transport.observer(depuis_flux_ms=T)
        lot=coord.traiter(self.temps,observation=r.observation,base_utc=r.base_utc)
        self.assertEqual(sum(i.nature.value=='REMPLIE' for i in lot.issues),1)
        self.assertEqual(sum(a[0]=='order_send' for a in self.sdk.appels),2)

    def test_partiel_reel_annule_reliquat_sans_complement_et_ne_compte_quune_entree(self):
        coord,port,lot,q=self.construire()
        def partiel(req):
            v=req['volume']/2
            self.sdk.transactions=[TradeDeal(ticket=201,order=202,time_msc=T,type=self.sdk.DEAL_TYPE_BUY,entry=self.sdk.DEAL_ENTRY_IN,
                magic=req['magic'],position_id=203,reason=self.sdk.DEAL_REASON_EXPERT,volume=v,price=req['price'],
                commission=0.,swap=0.,profit=0.,fee=0.,symbol=req['symbol'],comment=req['comment'])]
            self.sdk.positions=[TradePosition(ticket=203,identifier=203,type=self.sdk.POSITION_TYPE_BUY,magic=req['magic'],
                time_msc=T,volume=v,sl=req['sl'],tp=req['tp'],symbol=req['symbol'],comment=req['comment'])]
            self.sdk.ordres=[TradeOrder(ticket=202,position_id=203,time_setup_msc=T,volume_current=v,state=self.sdk.ORDER_STATE_PARTIAL,
                magic=req['magic'],symbol=req['symbol'],comment=req['comment'])]
            return OrderSendResult(retcode=self.sdk.TRADE_RETCODE_DONE_PARTIAL,order=202)
        self.sdk.scenarios['order_send'].append(partiel);self.transmettre(coord,lot);ack=self.attendre()
        r=self.transport.observer(depuis_flux_ms=T)
        lot=coord.traiter(T,reponses=ack.reponses,observation=r.observation,base_utc=r.base_utc,cotations=(q,))
        self.assertEqual(sum(i.nature.value=='REMPLIE' for i in lot.issues),1)
        annulations=tuple(c for c in lot.commandes if c.nature is NatureCommande.ANNULATION)
        self.assertEqual(len(annulations),1)
        historique=self.sdk.ordres[0]._replace(state=self.sdk.ORDER_STATE_CANCELED,time_done_msc=T,volume_current=0.)
        self.transport.soumettre_defenses(annulations,T);self.attendre()
        self.sdk.historique_ordres=[historique]
        r=self.transport.observer(depuis_flux_ms=T)
        lot=coord.traiter(T,observation=r.observation,base_utc=r.base_utc)
        cycle=coord.etat.reprise.cycles[0].etat
        self.assertTrue(cycle.reliquat_annule);self.assertTrue(cycle.quota_compte)
        self.assertFalse(lot.issues)
        self.assertEqual(sum(a[0]=='order_send' and a[1][0]['action']==self.sdk.TRADE_ACTION_DEAL for a in self.sdk.appels),1)

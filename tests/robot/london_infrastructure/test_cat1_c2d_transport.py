"""Premier harnais du transport, avant jonction au decodeur d'observation."""
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch
import unittest
from dataclasses import replace
from decimal import Decimal as D
from robot.outils.qualification_mt5 import T,JOUR,frontiere,exports,octets,iso
from robot.outils.execution_partagee import signal,cotation,configuration
from robot.outils.cycle_execution import bloc_cycle
from robot.outils.faux_mt5 import OrderSendResult,OrderCheckResult
from xpbots.infra.c0a_types import ErreurInfra,TableHeureServeur,SegmentServeur
from xpbots.infra.c0b_horloge import HorlogeSysteme
from xpbots.infra.c2d_execution_mt5 import ExecutionMT5
from xpbots.execution.c4_cycle import NatureCommande,NatureReponse,StatutAccuse,PreuvePersistance,CommandeExecution,identifier_courtier
from xpbots.noyau.c1c_domaine import CauseCloture


class HarnaisTransport:
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.temps=T
        self.horloge=patch('time.time_ns',side_effect=lambda:self.temps*1000000);self.horloge.start();self.addCleanup(self.horloge.stop)
        self.table=TableHeureServeur('SERVEUR_FIXTURE',1,iso(T-1000),('MESURE_SYNTHETIQUE_S01',),
            (SegmentServeur(T-14*JOUR,T+30*JOUR,0),))
        self.sdk,self.session,self.specs=frontiere(self.temp.name,table=self.table,**self.options_frontiere());self.addCleanup(self.session.fermer)
        s,f=exports();self.specs.recevoir_exports(T,seances={'EURUSD.micro':octets(s)},fermetures=octets(f))
        self.p=self.specs.instrument('EURUSD',T)
        bloc=bloc_cycle(signal_=signal(cloture_ms=T),profil_=self.p,cotation_=cotation(instant_fournisseur_ms=T,instant_reception_ms=T))
        self.commande=next(c for c in bloc.cycle.preparer_envoi(T).commandes if c.nature is NatureCommande.ENTREE)
        self.transport=self.nouveau();self.addCleanup(lambda:self.transport.fermer(1000))

    def nouveau(self,etat=None,*,maximum=4,convention_ticks='SERVEUR_S01'):
        return ExecutionMT5(self.session,configuration().commun,self.table,{'EURUSD':'EURUSD.micro'},HorlogeSysteme(),
            profil=self.specs.instrument,preuve=self.specs.preuve,qualification_compte=self.specs.compte,preuve_compte=self.specs.preuve_compte,
            longueur_empreinte=16,max_taches_natives=maximum,depuis_utc_ms=T//86400000*86400000,etat=etat,
            convention_ticks=convention_ticks)

    def options_frontiere(self):return dict(mode='DEMO')

    def autoriser(self):
        lot=self.transport.preparer_entrees((self.commande,),T)
        preuve=PreuvePersistance(lot.revision,lot.references)
        self.transport.autoriser_entrees(preuve)
        return preuve

    def attendre(self):
        for _ in range(2000):
            r=self.transport.collecter()
            if r.reponses:return r
            Event().wait(.001)
        self.fail('reponse du faux SDK non recue')


class TestTransportNatif(HarnaisTransport,unittest.TestCase):
    def position_avec_heure_financiere_serveur_et_tick_sdk_utc(self):
        self.table=TableHeureServeur('SERVEUR_FIXTURE',2,iso(T-1000),('D12_ET_FAITS_COMPTE_PLUS_2H',),
            (SegmentServeur(T-14*JOUR,T+30*JOUR,7200),))
        self.transport=self.nouveau(convention_ticks='UTC');self.addCleanup(lambda:self.transport.fermer(1000))
        self.autoriser();self.attendre()
        # Les faits de compte de cette fixture relèvent de S01 ; ses ticks SDK
        # demeurent UTC. Aucun état interne de l'adaptateur n'est remplacé.
        for nom in ('positions','historique_ordres','transactions'):
            valeurs=getattr(self.sdk,nom)
            for i,n in enumerate(valeurs):
                changements={k:getattr(n,k)+(7200000 if k.endswith('_msc') else 7200)
                             for k in n._fields if k.startswith('time')
                             and isinstance(getattr(n,k),int) and getattr(n,k)>0}
                valeurs[i]=n._replace(**changements)
        o=self.transport.observer()
        self.assertIsNotNone(o.observation,o.alertes)
        self.assertTrue(o.observation.positions)
        ticket=o.observation.positions[0].ticket
        self.assertIsNotNone(self.transport.proprietaire(ticket))
        return CommandeExecution(NatureCommande.CLOTURE,self.commande.cle,'defense-utc',T,
            dict(ticket=ticket,volume=self.commande.donnees['volume'],cause=CauseCloture.FLATTEN,
                 motif=None,detail=None,priorite=0))

    def test_tick_sdk_utc_frais_autorise_defense_meme_si_serveur_d12_decale(self):
        defense=self.position_avec_heure_financiere_serveur_et_tick_sdk_utc()
        self.sdk.ajouter_tick('EURUSD.micro',T,1.1003,1.1004)
        self.transport.soumettre_defenses((defense,),T);r=self.attendre()
        self.assertEqual(r.reponses[0].donnees['statut'],StatutAccuse.ACCEPTE)
        self.assertFalse(self.sdk.positions)
        self.assertEqual(sum(a[0]=='order_send' for a in self.sdk.appels),2)

    def test_tick_sdk_futur_ne_devient_pas_frais_par_decalage_d12(self):
        defense=self.position_avec_heure_financiere_serveur_et_tick_sdk_utc()
        self.sdk.ajouter_tick('EURUSD.micro',T+7200000,1.1003,1.1004)
        self.transport.soumettre_defenses((defense,),T);r=self.attendre()
        self.assertEqual(r.reponses[0].donnees['statut'],StatutAccuse.REFUSE)
        self.assertTrue(self.sdk.positions)
        self.assertEqual(sum(a[0]=='order_send' for a in self.sdk.appels),1)

    def test_aucun_envoi_sans_preuve_native_et_requete_exacte(self):
        lot=self.transport.preparer_entrees((self.commande,),T)
        self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))
        with self.assertRaises(ErreurInfra):self.transport.autoriser_entrees(PreuvePersistance(lot.revision+1,lot.references))
        self.transport.autoriser_entrees(PreuvePersistance(lot.revision,lot.references));r=self.attendre()
        self.assertEqual(r.reponses[0].donnees['statut'],StatutAccuse.ACCEPTE)
        self.assertTrue(all(v.nature is NatureReponse.ACCUSE for v in r.reponses))
        req=[a[1][0] for a in self.sdk.appels if a[0]=='order_send'][0];d=self.commande.donnees
        self.assertEqual(req,dict(action=self.sdk.TRADE_ACTION_DEAL,symbol=d['symbole_courtier'],volume=float(d['volume']),
            type=self.sdk.ORDER_TYPE_BUY,price=float(d['prix']),sl=float(d['sl']),tp=float(d['tp']),deviation=d['deviation_points'],
            type_filling=self.sdk.ORDER_FILLING_IOC,type_time=self.sdk.ORDER_TIME_GTC,magic=d['magic'],comment=d['commentaire']))
        self.assertEqual([a[1][0] for a in self.sdk.appels if a[0]=='order_check'][-1],req)

    def test_precontrole_refuse_ne_fait_pas_order_send(self):
        self.sdk.scenarios['order_check'].append(OrderCheckResult(retcode=self.sdk.TRADE_RETCODE_NO_MONEY))
        self.autoriser();r=self.attendre()
        self.assertEqual((r.reponses[0].donnees['statut'],r.reponses[0].donnees['definitif']),(StatutAccuse.REFUSE,True))
        self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))

    def test_none_garde_etat_inconnu_et_ne_retransmet_jamais(self):
        self.sdk.scenarios['order_send'].append(None)
        preuve=self.autoriser();r=self.attendre()
        self.assertEqual(r.reponses[0].donnees['statut'],StatutAccuse.INCONNU)
        self.transport.autoriser_entrees(preuve)
        self.assertEqual(sum(a[0]=='order_send' for a in self.sdk.appels),1)
        etat=self.transport.exporter_etat()
        self.assertFalse(etat['registre'][0]['envoi_termine'])
        reprise=self.nouveau(etat);self.addCleanup(lambda:reprise.fermer(1000))
        reprise.autoriser_entrees(preuve)
        self.assertEqual(sum(a[0]=='order_send' for a in self.sdk.appels),1)

    def test_refus_prix_est_non_permanent_et_code_inconnu_ne_devient_pas_rejet(self):
        for code,attendu,definitif in ((self.sdk.TRADE_RETCODE_REQUOTE,StatutAccuse.REFUSE,False),(123456,StatutAccuse.INCONNU,False)):
            t=self.nouveau();self.addCleanup(lambda t=t:t.fermer(1000))
            self.sdk.scenarios['order_send'].append(OrderSendResult(retcode=code,order=0,comment='COMMENTAIRE_SECRET'))
            lot=t.preparer_entrees((self.commande,),T);t.autoriser_entrees(PreuvePersistance(lot.revision,lot.references))
            for _ in range(2000):
                r=t.collecter()
                if r.reponses:break
                Event().wait(.001)
            self.assertTrue(r.reponses)
            self.assertEqual((r.reponses[0].donnees['statut'],r.reponses[0].donnees['definitif']),(attendu,definitif))
            self.assertNotIn('COMMENTAIRE_SECRET',repr(t.exporter_etat()))

    def test_preparation_restauree_nest_jamais_transmise(self):
        lot=self.transport.preparer_entrees((self.commande,),T)
        reprise=self.nouveau(self.transport.exporter_etat());self.addCleanup(lambda:reprise.fermer(1000))
        with self.assertRaises(ErreurInfra):reprise.autoriser_entrees(PreuvePersistance(lot.revision,lot.references))
        self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))

    def test_changement_compte_nemet_rien(self):
        lot=self.transport.preparer_entrees((self.commande,),T)
        self.sdk.compte=self.sdk.compte._replace(login=self.sdk.compte.login+1)
        self.transport.autoriser_entrees(PreuvePersistance(lot.revision,lot.references))
        self.assertEqual(self.attendre().reponses[0].donnees['statut'],StatutAccuse.REFUSE)
        self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))

    def test_ttl_expire_avant_emission_nemet_rien(self):
        lot=self.transport.preparer_entrees((self.commande,),T)
        self.temps=self.commande.donnees['expire_ms']
        self.transport.autoriser_entrees(PreuvePersistance(lot.revision,lot.references))
        self.assertEqual(self.attendre().reponses[0].donnees['statut'],StatutAccuse.REFUSE)
        self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))

    def test_ttl_est_recontrole_apres_order_check_bloquant(self):
        def controle(req):
            self.temps=self.commande.donnees['expire_ms']
            return OrderCheckResult(retcode=0)
        self.sdk.scenarios['order_check'].append(controle)
        self.autoriser();self.assertEqual(self.attendre().reponses[0].donnees['statut'],StatutAccuse.REFUSE)
        self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))

    def test_seul_refus_prix_permet_autre_reference_de_la_meme_intention(self):
        self.sdk.scenarios['order_send'].append(OrderSendResult(retcode=self.sdk.TRADE_RETCODE_REQUOTE,order=0))
        self.autoriser();self.attendre()
        autre=replace(self.commande,reference=self.commande.reference+':3')
        lot=self.transport.preparer_entrees((autre,),T)
        self.transport.autoriser_entrees(PreuvePersistance(lot.revision,lot.references));self.attendre()
        self.assertEqual(sum(a[0]=='order_send' for a in self.sdk.appels),2)
        with self.assertRaises(ErreurInfra):self.transport.preparer_entrees((replace(autre,reference=autre.reference+':5'),),T)

    def test_defense_possedee_passe_pendant_un_autre_order_send_bloque(self):
        self.transport=self.nouveau(maximum=2);self.addCleanup(lambda:self.transport.fermer(1000))
        self.autoriser();self.attendre();o=self.transport.observer().observation;ticket=o.positions[0].ticket
        entree_bloquee=Event();liberer=Event();self.addCleanup(liberer.set)
        def bloquer(req):
            entree_bloquee.set();liberer.wait(5)
            return OrderSendResult(retcode=self.sdk.TRADE_RETCODE_TIMEOUT,order=0)
        self.sdk.scenarios['order_send'].append(bloquer)
        cle=replace(self.commande.cle,deploiement='AUTRE_FIXTURE')
        identite=identifier_courtier(cle,16);d=dict(self.commande.donnees,magic=identite.magic,commentaire=identite.commentaire)
        autre=replace(self.commande,cle=cle,reference='autre-entree',donnees=d)
        lot=self.transport.preparer_entrees((autre,),T)
        self.transport.autoriser_entrees(PreuvePersistance(lot.revision,lot.references))
        self.assertTrue(entree_bloquee.wait(1))
        try:
            cle3=replace(cle,deploiement='TROISIEME_FIXTURE');identite3=identifier_courtier(cle3,16)
            troisieme=replace(autre,cle=cle3,reference='troisieme-entree',donnees=dict(d,magic=identite3.magic,commentaire=identite3.commentaire))
            lot=self.transport.preparer_entrees((troisieme,),T)
            self.transport.autoriser_entrees(PreuvePersistance(lot.revision,lot.references))
            refus=self.attendre()
            self.assertEqual(refus.reponses[0].cle,cle3)
            self.assertEqual(refus.reponses[0].donnees['statut'],StatutAccuse.REFUSE)
            defense=CommandeExecution(NatureCommande.CLOTURE,self.commande.cle,'defense',T,
                dict(ticket=ticket,volume=self.commande.donnees['volume'],cause=CauseCloture.FLATTEN,motif=None,detail=None,priorite=0))
            self.sdk.ajouter_tick('EURUSD.micro',T,1.1003,1.1004)
            self.transport.soumettre_defenses((defense,),T)
            r=self.attendre();self.assertEqual(r.reponses[0].cle,self.commande.cle)
            self.assertFalse(self.sdk.positions)
            self.assertFalse(self.transport.fermer(0))
        finally:liberer.set()

    def test_capacite_unique_est_refusee_pour_garder_une_voie_defensive(self):
        with self.assertRaises(ErreurInfra):self.nouveau(maximum=1)

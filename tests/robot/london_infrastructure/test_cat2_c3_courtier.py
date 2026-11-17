"""Jonction DEMO synthetique avec vrais C05, C08, calculs et SQLite."""
from decimal import Decimal as D
from pathlib import Path
from threading import Event
import unittest
from robot.london_infrastructure.test_cat1_c3_courtier import HarnaisCourtier
from robot.outils.qualification_mt5 import T,JOUR,iso,natif,exports
from robot.outils.execution_partagee import configuration,signal
from robot.outils.fondamental import message,calendrier,octets,table_importance
from xpbots.infra.c0c_sqlite import DepotSQLite
from xpbots.infra.c0a_types import TableHeureServeur,SegmentServeur
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.noyau.c1a_marche import Cotation
from xpbots.execution.c6_coordinateur import CoordinateurCompte
from xpbots.execution.c4_cycle import NatureCommande,PreuvePersistance,StatutAccuse
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur


class TestJonctionCourtier(HarnaisCourtier,unittest.TestCase):
    def fondamental(self,decalage_ms=0):
        p=configuration().commun
        fond=PermissionsFondamentales(p,self.courtier.convertir_serveur)
        m=message(issued_at_utc=iso(T),known_at_utc=iso(T),valid_from_utc=iso(T),
            valid_until_utc=iso(T+int(p.fundamental_max_validity_seconds*1000)))
        fond.recevoir_permission('EURUSD',octets(m),T)
        cal=calendrier(export_ms=T,export_serveur=natif(T+decalage_ms),export_gmt=natif(T),
            fenetre_debut_serveur=natif(T//JOUR*JOUR-JOUR+decalage_ms),
            fenetre_fin_serveur=natif(T+decalage_ms+int((p.news_forward_coverage_seconds+p.news_calendar_max_age_seconds+60)*1000)))
        fond.recevoir_calendrier(octets(cal),T,table_importance())
        return fond

    def exercer_convention_qualifiee(self,convention):
        self.assertTrue(self.courtier.fermer(1000));decalage=7200000
        self.table=TableHeureServeur('SERVEUR_FIXTURE',2,iso(T-1000),('S01_D12_ET_FINANCIER_PLUS_2H',),
            (SegmentServeur(T-14*JOUR,T+30*JOUR,7200),))
        self.qualification['convention_ticks']=convention
        # Le temps du faux SDK pilote ses faits financiers, qualifiés serveur
        # selon S01 ; ses ticks ont séparément la convention C04 choisie.
        self.sdk.instant_ms=T+decalage
        self.courtier=self.nouveau()
        s,f=exports();s['export_serveur']=natif(T+decalage)
        self.courtier.recevoir_exports(T,seances={'EURUSD.micro':octets(s)},fermetures=octets(f))
        self.assertEqual(self.courtier.convertir_serveur(natif(T+decalage)),T)
        fond=self.fondamental(decalage)
        self.sdk.ajouter_tick('EURUSD.micro',T+(decalage if convention=='SERVEUR_S01' else 0),1.1003,1.1004)
        marche=self.courtier.lire_marche()
        self.assertFalse(marche.erreurs);self.assertEqual(len(marche.ticks),1)
        q=marche.ticks[0];self.assertEqual(q.instant_fournisseur_ms,T)
        cot=Cotation(q.symbole,D(str(q.bid)),D(str(q.ask)),q.instant_fournisseur_ms,q.instant_reception_ms)
        r=self.courtier.observer();self.assertIsNotNone(r.observation,r.alertes)
        pc=self.courtier.profil_compte(T);p=self.courtier.calculs.specifications('EURUSD')
        coord=CoordinateurCompte(configuration(),'FIXTURE',{'EURUSD':p},pc,self.courtier.calculs,fond,T,
            longueur_empreinte=16,mode='DEMO',observation=r.observation,base_utc=r.base_utc)
        lot=coord.traiter(T,signaux=(signal(cloture_ms=T),),cotations=(cot,))
        self.assertEqual(len(lot.preparations),1)
        meta=dict(deploiement='FIXTURE',mode='DEMO',empreintes={'technique':'a'*64,'ia':'b'*64},commit='c'*40)
        def attendre():
            for _ in range(2000):
                reception=self.courtier.collecter()
                if reception.reponses:return reception
                Event().wait(.001)
            self.fail('reponse native synthetique absente')
        with DepotSQLite(Path(self.temp.name)/'horloge.sqlite',meta) as db:
            db.persister(1,T,serialiser_valeur(dict(coeur=lot.etat,courtier=self.courtier.exporter_etat())))
            suite=coord.confirmer_persistance(PreuvePersistance(lot.etat.revision,tuple(c.reference for c in lot.preparations)),T)
            preparation=self.courtier.preparer_entrees(suite.commandes,T)
            db.persister(2,T,serialiser_valeur(dict(coeur=coord.etat,courtier=self.courtier.exporter_etat())))
            self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))
            self.courtier.autoriser_entrees(PreuvePersistance(preparation.revision,preparation.references))
            ack=attendre();self.assertEqual(ack.reponses[0].donnees['statut'],StatutAccuse.ACCEPTE)
            r=self.courtier.observer(depuis_flux_ms=T);self.assertIsNotNone(r.observation,r.alertes)
            lot=coord.traiter(T,reponses=ack.reponses,observation=r.observation,base_utc=r.base_utc,cotations=(cot,))
            self.assertEqual(sum(i.nature.value=='REMPLIE' for i in lot.issues),1)
            db.persister(3,T,serialiser_valeur(dict(coeur=coord.etat,courtier=self.courtier.exporter_etat())))
            sauve=deserialiser_valeur(db.charger())
        self.assertTrue(self.courtier.fermer(1000));self.temps=T+1;self.sdk.instant_ms=self.temps+decalage
        self.courtier=self.nouveau(sauve['courtier'])
        r=self.courtier.observer(depuis_flux_ms=T);self.assertIsNotNone(r.observation,r.alertes)
        coord=CoordinateurCompte(configuration(),'FIXTURE',{'EURUSD':p},pc,self.courtier.calculs,fond,self.temps,
            longueur_empreinte=16,mode='DEMO',etat=sauve['coeur'],observation=r.observation,base_utc=r.base_utc)
        self.assertFalse(self.courtier.lire_marche().ticks)
        m=message(sequence=2,risk_state='FLATTEN',issued_at_utc=iso(self.temps),known_at_utc=iso(self.temps),
            valid_from_utc=iso(self.temps),valid_until_utc=iso(self.temps+int(configuration().commun.fundamental_max_validity_seconds*1000)))
        fond.recevoir_permission('EURUSD',octets(m),self.temps)
        sortie=coord.traiter(self.temps,cotations=(cot,))
        defenses=tuple(c for c in sortie.commandes if c.nature is NatureCommande.CLOTURE)
        self.assertEqual(len(defenses),1)
        self.courtier.soumettre_defenses(defenses,self.temps)
        ack=attendre();self.assertEqual(ack.reponses[0].donnees['statut'],StatutAccuse.ACCEPTE)
        self.assertFalse(self.sdk.positions)
        self.assertEqual(sum(a[0]=='order_send' for a in self.sdk.appels),2)

    def test_ticks_sdk_utc_distincts_d12_entree_reprise_et_flatten(self):
        self.exercer_convention_qualifiee('UTC')

    def test_ticks_serveur_s01_qualifies_entree_reprise_et_flatten(self):
        self.exercer_convention_qualifiee('SERVEUR_S01')

    def test_tick_c05_commit_remplissage_et_reprise_sur_la_composition_reelle(self):
        self.exports();fond=self.fondamental()
        self.sdk.ajouter_tick('EURUSD.micro',T,1.1003,1.1004)
        marche=self.courtier.lire_marche();q=marche.ticks[0]
        cot=Cotation(q.symbole,D(str(q.bid)),D(str(q.ask)),q.instant_fournisseur_ms,q.instant_reception_ms)
        r=self.courtier.observer();self.assertIsNotNone(r.observation,r.alertes)
        pc=self.courtier.profil_compte(T);p=self.courtier.calculs.specifications('EURUSD')
        coord=CoordinateurCompte(configuration(),'FIXTURE',{'EURUSD':p},pc,self.courtier.calculs,fond,T,
            longueur_empreinte=16,mode='DEMO',observation=r.observation,base_utc=r.base_utc)
        lot=coord.traiter(T,signaux=(signal(cloture_ms=T),),cotations=(cot,))
        self.assertEqual(len(lot.preparations),1)
        meta=dict(deploiement='FIXTURE',mode='DEMO',empreintes={'technique':'a'*64,'ia':'b'*64},commit='c'*40)
        with DepotSQLite(Path(self.temp.name)/'etat.sqlite',meta) as db:
            db.persister(1,T,serialiser_valeur(dict(coeur=lot.etat,courtier=self.courtier.exporter_etat())))
            suite=coord.confirmer_persistance(PreuvePersistance(lot.etat.revision,tuple(c.reference for c in lot.preparations)),T)
            natif=self.courtier.preparer_entrees(suite.commandes,T)
            db.persister(2,T,serialiser_valeur(dict(coeur=coord.etat,courtier=self.courtier.exporter_etat())))
            self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))
            self.courtier.autoriser_entrees(PreuvePersistance(natif.revision,natif.references))
            for _ in range(2000):
                ack=self.courtier.collecter()
                if ack.reponses:break
                Event().wait(.001)
            self.assertTrue(ack.reponses)
            r=self.courtier.observer(depuis_flux_ms=T)
            lot=coord.traiter(T,reponses=ack.reponses,observation=r.observation,base_utc=r.base_utc,cotations=(cot,))
            self.assertEqual(sum(i.nature.value=='REMPLIE' for i in lot.issues),1)
            db.persister(3,T,serialiser_valeur(dict(coeur=coord.etat,courtier=self.courtier.exporter_etat())))
            sauve=deserialiser_valeur(db.charger())
        self.temps=T+1;reprise=self.nouveau(sauve['courtier']);self.addCleanup(lambda:reprise.fermer(1000))
        r=reprise.observer(depuis_flux_ms=T)
        nouveau=CoordinateurCompte(configuration(),'FIXTURE',{'EURUSD':p},pc,reprise.calculs,fond,self.temps,
            longueur_empreinte=16,mode='DEMO',etat=sauve['coeur'],observation=r.observation,base_utc=r.base_utc)
        suite=nouveau.traiter(self.temps)
        self.assertTrue(suite.etat.reprise.cycles[0].etat.quota_compte)
        self.assertFalse(suite.issues)
        self.assertFalse(reprise.lire_marche().ticks)
        self.assertEqual(sum(a[0]=='order_send' for a in self.sdk.appels),1)

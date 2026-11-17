"""Coquille physique avec vrais C05/C08, commit, journal et reprise native."""
from decimal import Decimal as D
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import json,sqlite3,unittest
from robot.london_infrastructure.test_cat1_c4_assemblage import HarnaisInfrastructure,META
from robot.outils.assemblage_mt5 import parametres,installer_controles
from robot.outils.execution_partagee import configuration,signal
from robot.outils.qualification_mt5 import T
from robot.outils.fondamental import table_importance
from robot.outils.faux_mt5 import FauxMT5,OrderSendResult
from xpbots.infra.c0a_types import ErreurInfra
from xpbots.execution.c4_cycle import PreuvePersistance,NatureCommande,NatureReponse
from xpbots.execution.c6_coordinateur import CoordinateurCompte
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.noyau.c1a_marche import Cotation
from xpbots.noyau.c1c_domaine import CauseCloture
from xpbots.noyau.c2_journal import Enveloppe,enregistrement,serialiser
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur


class TestJonctionAssemblage(HarnaisInfrastructure,unittest.TestCase):
    def configurer(self):
        i,sdk=self.nouveau();table,q,options=parametres(sdk);c=i.initialiser_courtier(table,q,options)
        with self.assertRaises(ErreurInfra):i.initialiser_courtier(table,q,options)
        installer_controles(i.session.etat.common_files)
        receptions=i.lire_controles();c.recevoir_exports(T,seances={sdk.symboles['EURUSD.micro'].name:v.octets for v in receptions if v.nature=='SEANCES'},
            fermetures=next(v.octets for v in receptions if v.nature=='FERMETURES'))
        fond=PermissionsFondamentales(configuration().commun,c.convertir_serveur)
        for v in receptions:
            if v.nature=='PERMISSION':fond.recevoir_permission(v.symbole,v.octets,v.instant_ms)
            elif v.nature=='CALENDRIER':fond.recevoir_calendrier(v.octets,v.instant_ms,table_importance())
        sdk.ajouter_tick('EURUSD.micro',T,1.1003,1.1004)
        tick=c.lire_marche().ticks[0];cot=Cotation(tick.symbole,D(str(tick.bid)),D(str(tick.ask)),tick.instant_fournisseur_ms,tick.instant_reception_ms)
        r=c.observer();p=c.calculs.specifications('EURUSD')
        coord=CoordinateurCompte(configuration(),'FIXTURE',{'EURUSD':p},c.profil_compte(T),c.calculs,fond,T,
            longueur_empreinte=16,mode='DEMO',observation=r.observation,base_utc=r.base_utc)
        lot=coord.traiter(T,signaux=(signal(cloture_ms=T),),cotations=(cot,))
        self.assertEqual(len(lot.preparations),1)
        i.depot.persister(1,T,serialiser_valeur(dict(coeur=coord.etat,courtier=c.exporter_etat())))
        return SimpleNamespace(i=i,sdk=sdk,c=c,coord=coord,fond=fond,lot=lot,cotation=cot,table=table,q=q,options=options)

    def transmettre(self,b):
        lot=b.lot
        suite=b.coord.confirmer_persistance(PreuvePersistance(lot.etat.revision,tuple(c.reference for c in lot.preparations)),T)
        natif=b.c.preparer_entrees(suite.commandes,T)
        b.i.depot.persister(2,T,serialiser_valeur(dict(coeur=b.coord.etat,courtier=b.c.exporter_etat())))
        b.c.autoriser_entrees(PreuvePersistance(natif.revision,natif.references))

    def attendre(self,c):
        for _ in range(2000):
            r=c.collecter()
            if r.reponses:return r
            Event().wait(.001)
        self.fail('faux SDK sans resultat')

    def test_stockage_indisponible_n_empeche_pas_la_cloture_fondamentale_possedee(self):
        b=self.configurer();self.transmettre(b);ack=self.attendre(b.c);r=b.c.observer(depuis_flux_ms=T)
        lot=b.coord.traiter(T,reponses=ack.reponses,observation=r.observation,base_utc=r.base_utc,cotations=(b.cotation,))
        self.assertTrue(b.sdk.positions)
        b.i.depot.persister(3,T,serialiser_valeur(dict(coeur=b.coord.etat,courtier=b.c.exporter_etat())))
        b.i.depot.fermer()
        with self.assertRaises(sqlite3.ProgrammingError):b.i.depot.persister(4,T,b'{}')
        self.temps=T+1;b.sdk.instant_ms=self.temps;b.sdk.ajouter_tick('EURUSD.micro',self.temps,1.1003,1.1004)
        installer_controles(b.i.session.etat.common_files,t=self.temps,sequence=2,risque='FLATTEN')
        for v in b.i.lire_controles():
            if v.nature=='PERMISSION':b.fond.recevoir_permission(v.symbole,v.octets,v.instant_ms)
        r=b.c.observer(depuis_flux_ms=T)
        lot=b.coord.traiter(self.temps,observation=r.observation,base_utc=r.base_utc)
        defenses=tuple(c for c in lot.commandes if c.nature is NatureCommande.CLOTURE)
        self.assertTrue(defenses);self.assertEqual(defenses[0].donnees['cause'],CauseCloture.FLATTEN)
        b.c.soumettre_defenses(lot.commandes,self.temps);self.attendre(b.c)
        self.assertFalse(b.sdk.positions)
        r=b.c.observer(depuis_flux_ms=T)
        closes=tuple(v for v in r.observation.reponses if v.nature is NatureReponse.CLOTURE)
        self.assertEqual(closes[-1].donnees['cause'],CauseCloture.FLATTEN)
        self.assertTrue(b.i.fermer(1000))

    def test_arret_borne_conserve_verrou_base_et_session_jusqu_au_retour_natif(self):
        b=self.configurer();entree=Event();liberer=Event();self.addCleanup(liberer.set)
        def bloquer(req):
            entree.set();liberer.wait(5)
            return OrderSendResult(retcode=b.sdk.TRADE_RETCODE_TIMEOUT,order=0)
        b.sdk.scenarios['order_send'].append(bloquer);self.transmettre(b)
        self.assertTrue(entree.wait(1))
        try:
            self.assertFalse(b.i.fermer(0));self.assertTrue(b.sdk.attache);self.assertIsNotNone(b.i.depot.charger())
            autre=FauxMT5(self.commun,instant_ms=T)
            with self.assertRaises(ErreurInfra):self.nouveau(meta=dict(META,deploiement='AUTRE'),sdk=autre)
            self.assertFalse(autre.attache)
        finally:liberer.set()
        self.attendre(b.c);self.assertTrue(b.i.fermer(1000))
        reprise,_=self.nouveau();sauve=deserialiser_valeur(reprise.depot.charger())
        c=reprise.initialiser_courtier(b.table,b.q,b.options,etat=sauve['courtier'])
        self.assertEqual(c.execution.exporter_etat()['registre'][0]['statut'],'INCONNUE')
        self.assertFalse(any(a[0]=='order_send' for a in reprise.session.sdk.appels))

    def test_jsonl_corrompu_repare_depuis_le_vrai_depot_au_redemarrage(self):
        i,_=self.nouveau();e=Enveloppe('FIXTURE','REFERENCE','DEMO',1,T,META['empreintes'])
        decision=serialiser(enregistrement('ALERTE',e,{'code':'INCIDENT_SYNTHETIQUE'})).encode('utf-8')
        entree=json.dumps(dict(numero=1,instant_reception_utc_ms=T,type_evenement='MINUTERIE',contenu=None),sort_keys=True,separators=(',',':')).encode()
        i.depot.persister(1,T,b'{}',decisions=(decision,),entrees=((1,entree),))
        i.journal.ajouter(i.depot.evenements());f=i.journal.dossier/'decisions_2026-11-10.jsonl';attendu=f.read_bytes()
        f.write_bytes(attendu+b'{partiel');i.fermer(0)
        reprise,_=self.nouveau()
        self.assertEqual(f.read_bytes(),attendu);self.assertEqual(reprise.depot.entrees(),(entree,))
        self.assertEqual(len(reprise.depot.evenements()),1)

"""Livre PAPER, profils C04, calculs natifs, coordinateur et SQLite réels."""
from decimal import Decimal as D
from pathlib import Path
import unittest

from robot.london_infrastructure.test_cat1_c3_courtier import HarnaisCourtier
from robot.points_entree.test_cat1_c1a_livre_papier import reprendre
from robot.outils.orchestration import C
from robot.outils.qualification_mt5 import T,JOUR,iso,natif
from robot.outils.execution_partagee import signal
from robot.outils.fondamental import message,calendrier,octets,table_importance
from xpbots.app.c1a_livre_papier import LivrePapier
from xpbots.noyau.c1a_marche import Cotation
from xpbots.noyau.c1c_domaine import Sens
from xpbots.execution.c0a_types import RefusExecution
from xpbots.execution.c4_cycle import PreuvePersistance,NatureCommande
from xpbots.execution.c6_coordinateur import CoordinateurCompte
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.infra.c0c_sqlite import DepotSQLite
from xpbots.orchestration.c3_codec import serialiser_valeur
from xpbots.rejeu.c0a_types import ConditionContrat,TarifCommission


class TestJonctionLivrePapier(HarnaisCourtier,unittest.TestCase):
    def livre_et_fondamental(self):
        self.exports();profil=self.courtier.calculs.specifications('EURUSD')
        creation=T//JOUR*JOUR
        tarif=TarifCommission('PREUVE_C04_FIXTURE',profil.commission_par_lot_par_cote,
            profil.commission_minimum_par_ordre,profil.commission_par_lot_par_cote,profil.commission_minimum_par_ordre)
        p=LivrePapier(C,(ConditionContrat(creation,T+JOUR,T,profil,tarif),),creation)
        p.avancer_au(T)
        fond=PermissionsFondamentales(C.technique.commun,self.courtier.convertir_serveur)
        m=message(issued_at_utc=iso(T),known_at_utc=iso(T),valid_from_utc=iso(T),
            valid_until_utc=iso(T+int(C.technique.commun.fundamental_max_validity_seconds*1000)))
        fond.recevoir_permission('EURUSD',octets(m),T)
        cal=calendrier(export_ms=T,export_serveur=natif(T),export_gmt=natif(T),
            fenetre_debut_serveur=natif(creation-JOUR),
            fenetre_fin_serveur=natif(T+int((C.technique.commun.news_forward_coverage_seconds+
                C.technique.commun.news_calendar_max_age_seconds+60)*1000)))
        fond.recevoir_calendrier(octets(cal),T,table_importance())
        return p,profil,fond

    def coordinateur(self,p,profil,fond,t,etat=None):
        return CoordinateurCompte(C.technique,'FIXTURE',{'EURUSD':profil},p.profil_compte,p,fond,t,
            longueur_empreinte=16,mode='PAPER',observation=p.observation(),base_utc=p.base_utc(),etat=etat)

    def test_admission_remplissage_reprise_et_quota_sans_ordre_natif(self):
        p,profil,fond=self.livre_et_fondamental()
        p.fixer_disponibilite('EURUSD',True,T)
        coord=self.coordinateur(p,profil,fond,T)
        cot=Cotation('EURUSD',D('1.1003'),D('1.1004'),T,T)
        lot=coord.traiter(T,signaux=(signal(cloture_ms=T),),cotations=(cot,))
        self.assertEqual(len(lot.preparations),1)
        with DepotSQLite(Path(self.temp.name)/'papier.sqlite',{'fixture':'livre-papier'}) as db:
            db.persister(1,T,serialiser_valeur(lot.etat))
            suite=coord.confirmer_persistance(PreuvePersistance(lot.etat.revision,
                tuple(c.reference for c in lot.preparations)),T)
            commandes=tuple(c for c in suite.commandes if c.nature is NatureCommande.ENTREE)
            ack=p.soumettre(commandes);coord.traiter(T,reponses=ack)
            self.temps=T+250;self.sdk.ajouter_tick('EURUSD.micro',self.temps,1.1003,1.1004)
            marche=self.courtier.lire_marche();self.assertEqual(len(marche.ticks),1)
            fill=p.sur_tick(marche.ticks[0])
            lot=coord.traiter(self.temps,reponses=fill,observation=p.observation(),base_utc=p.base_utc())
            db.persister(2,self.temps,serialiser_valeur(lot.etat))
        self.assertEqual(sum(i.nature.value=='REMPLIE' for i in lot.issues),1)
        q=reprendre(p);reprise=self.coordinateur(q,profil,fond,self.temps,coord.etat)
        suite=reprise.traiter(self.temps)
        self.assertFalse(suite.issues)
        self.assertTrue(suite.etat.reprise.cycles[0].etat.quota_compte)
        self.assertEqual(q.premiers_remplissages,p.premiers_remplissages)
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))

    def test_profit_c10_confronte_aux_vrais_adaptateurs_du_faux_sdk(self):
        p,profil,_=self.livre_et_fondamental()
        for sens in (Sens.ACHAT,Sens.VENTE):
            papier=p.profit(profil,sens,D('.2'),D('1.1003'),D('1.1013'))
            natif_calc=self.courtier.calculs.profit(profil,sens,D('.2'),D('1.1003'),D('1.1013'))
            self.assertAlmostEqual(papier,natif_calc,places=9)
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))

    def test_indisponibilite_du_flux_refuse_le_vrai_coordinateur(self):
        p,profil,fond=self.livre_et_fondamental()
        coord=self.coordinateur(p,profil,fond,T)
        lot=coord.traiter(T,signaux=(signal(cloture_ms=T),),
                          cotations=(Cotation('EURUSD',D('1.1003'),D('1.1004'),T,T),))
        self.assertFalse(lot.preparations)
        self.assertFalse(p.positions_ouvertes)
        self.assertTrue(any(i.motif.value=='ENVIRONMENT_NOT_READY' for i in lot.issues))

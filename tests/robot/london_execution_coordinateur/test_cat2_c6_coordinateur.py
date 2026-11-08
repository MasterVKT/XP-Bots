"""Catégorie 2 : vrai moteur London, compte partagé, reprise et clôtures natives."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from robot.outils.coordinateur_execution import (bloc_coordinateur,traiter,confirmer,bloc_remplissage,positionner)
from robot.outils.execution_partagee import T,signal,cotation
from robot.outils.cycle_execution import remplissage,cloture
from robot.outils.london import parametres,bougie
from robot.moteur_london.test_cat1_c2_moteur_london import amorcer
from xpbots.execution.c0a_types import adapter_signal_ema
from xpbots.execution.c4_cycle import NatureCommande,identifier_courtier
from xpbots.execution.c5b_reprise import ObservationNative,PositionNative
from xpbots.london.c2_moteur import MoteurLondon
from xpbots.noyau.decisions import Signal as SignalEMA,Sens as SensEMA
from xpbots.noyau.c1c_domaine import CauseCloture,NatureIssue,Motif,SignalTechnique


def ouvert():
    b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
    v=bloc_remplissage(b,lot); confirmer(b,lot)
    positionner(b,v,T+1)
    lot=traiter(b,T+1,reponses=(remplissage(v),))
    return b,v,lot


class TestJonctionCoordinateur(unittest.TestCase):
    def test_signal_london_reel_prime_ema_et_seul_fill_applique_le_quota(self):
        p=parametres(); m=MoteurLondon(p,'EURUSD',D('.00001'))
        amorcer(m,p,haut=1.10000,bas=1.09800,atr_h1=.00080)
        s=m.sur_bougie(bougie(o=1.09995,h=1.10055,l=1.09990,c=1.10050,a=.00050,tr=.00065))
        self.assertIsInstance(s,SignalTechnique); t=s.cloture_ms
        ema=adapter_signal_ema(SignalEMA('EMA_V3','EURUSD',t,SensEMA.ACHAT,D('1.1005'),.0005,1.09985,1.5))
        b=bloc_coordinateur(t=t)
        q=cotation(bid=D('1.1005'),ask=D('1.1006'),instant_fournisseur_ms=t,instant_reception_ms=t)
        lot=traiter(b,t,signaux=(ema,s),cotations=(q,))
        self.assertEqual([c.cle.strategie for c in lot.preparations],['LONDON_V3'])
        self.assertEqual(lot.issues[0].motif,Motif.SYMBOL_BUSY)
        self.assertFalse(m.etat_quotas.remplissages)
        v=bloc_remplissage(b,lot); envoi=confirmer(b,lot,t)
        self.assertEqual(envoi.commandes[0].donnees['sl'],v.plan.niveaux.stop)
        positionner(b,v,t+1)
        lot=traiter(b,t+1,reponses=(remplissage(v),))
        for i in lot.issues: m.sur_issue(i)
        self.assertEqual(len(m.etat_quotas.remplissages),1)
        self.assertTrue(m.position_ouverte)

    def test_sl_natif_connu_au_meme_instant_que_duree_prime_la_cloture_marche(self):
        b,v,lot=ouvert(); t=T+7200001
        initial=lot.etat.reprise.reservations.reservations[0].risque_initial
        self.assertEqual(initial,v.plan.risque)
        b.port.compte=replace(b.port.compte,positions=(),marge_utilisee=D(0))
        q=replace(cotation(),instant_fournisseur_ms=t,instant_reception_ms=t)
        lot=traiter(b,t,reponses=(cloture(v,instant_ms=t,cause=CauseCloture.STOP_LOSS),),cotations=(q,))
        self.assertEqual([i.nature for i in lot.issues],[NatureIssue.CLOTUREE])
        self.assertEqual(lot.issues[0].cause,CauseCloture.STOP_LOSS)
        self.assertFalse(any(c.nature is NatureCommande.CLOTURE for c in lot.commandes))
        self.assertFalse(lot.etat.reprise.reservations.reservations)
        self.assertIsNone(b.coordinateur.prochaine_echeance_ms)

    def test_redemarrage_inconnu_puis_faits_positifs_restaurent_risque_et_quota_sans_renvoi(self):
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        v=bloc_remplissage(b,lot); confirmer(b,lot)
        lot=traiter(b,T+5000)
        reprise=bloc_coordinateur(t=T+6000,etat=lot.etat,observation=None)
        traiter(reprise,T+6000)
        positionner(reprise,v,T+6001)
        identite=identifier_courtier(v.plan.reservation.cle,16)
        n=PositionNative('position-1',v.profil.symbole_courtier,v.plan.volume,identite.magic,identite.commentaire,
            sl=v.plan.niveaux.stop,tp=v.plan.niveaux.objectif)
        o=ObservationNative(replace(reprise.port.compte,positions=()),T,True,(n,),reponses=(remplissage(v),))
        q=replace(cotation(),instant_fournisseur_ms=T+6001,instant_reception_ms=T+6001)
        lot=traiter(reprise,T+6001,observation=o,cotations=(q,))
        self.assertEqual([i.nature for i in lot.issues],[NatureIssue.REMPLIE])
        self.assertEqual(lot.issues[0].instant_ms,T+1)
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in lot.commandes))
        self.assertEqual(lot.etat.reprise.reservations.reservations[0].risque_initial,v.plan.risque)
        self.assertFalse(lot.etat.reprise.reservations.verrous)

    def test_arret_global_restore_reste_bloquant_meme_apres_retablissement_equite(self):
        b,v,_=ouvert()
        b.port.compte=replace(b.port.compte,fonds_propres=D(90),solde=D(90))
        q=replace(cotation(),instant_fournisseur_ms=T+2,instant_reception_ms=T+2)
        lot=traiter(b,T+2,cotations=(q,))
        self.assertTrue(lot.etat.reprise.gardes.arret_global)
        self.assertEqual(next(c for c in lot.commandes if c.nature is NatureCommande.CLOTURE).donnees['cause'],CauseCloture.ARRET_GLOBAL)
        reprise=bloc_coordinateur(t=T+3,etat=lot.etat,observation=None)
        positionner(reprise,v,T+3)
        identite=identifier_courtier(v.plan.reservation.cle,16)
        n=PositionNative('position-1',v.profil.symbole_courtier,v.plan.volume,identite.magic,identite.commentaire,
            sl=v.plan.niveaux.stop,tp=v.plan.niveaux.objectif)
        o=ObservationNative(replace(reprise.port.compte,positions=()),T,True,(n,))
        lot=traiter(reprise,T+3,observation=o,signaux=(signal(symbole='GBPUSD'),),
            cotations=(replace(cotation(symbole='GBPUSD'),instant_fournisseur_ms=T+3,instant_reception_ms=T+3),))
        self.assertTrue(lot.etat.reprise.gardes.arret_global)
        self.assertEqual(lot.issues[0].motif,Motif.GLOBAL_DRAWDOWN_HALT)
        self.assertFalse(lot.preparations)

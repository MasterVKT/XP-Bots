"""Catégorie 2, couche 3 (dimensionnement) : contrat et bornes des sources C04–C09."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.execution_partagee import *
from robot.doublures.calculs_execution import CalculSynthetique
from xpbots.execution.c0a_types import EtatCompte,RefusExecution,adapter_signal_ema
from xpbots.execution.c0d_prix import construire_niveaux
from xpbots.execution.c1b_gardes import GardesCompte,reconstituer_base_utc
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.execution.c2b_arbitrage import candidats_admission
from xpbots.execution.c3_dimensionnement import dimensionner,PlanDimensionnement
from xpbots.noyau.c0a_temps import instant_vers_datetime,instant_depuis_datetime
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.noyau.decisions import Signal as SignalEMA,Sens as SensEMA
from xpbots.noyau.c1c_domaine import Motif

class TestJonctionDimensionnement(unittest.TestCase):
    def test_arbitrage_vrai_compte_commun_et_risque_restant(self):
        c=EtatCompte(T,D(100),D(100),D(0));r=RegistreReservations(commun());g=GardesCompte(commun())
        borne=instant_depuis_datetime(instant_vers_datetime(T).replace(hour=0,minute=0,second=0,microsecond=0))
        g.observer(c,reconstituer_base_utc(c,[],Intervalle(borne,T+1),aucune_position_minuit=True))
        ema=adapter_signal_ema(SignalEMA('EMA_V3','EURUSD',T,SensEMA.ACHAT,D('1.1003'),.0005,1.0998,1.5))
        decisions=[]
        for candidat in candidats_admission([ema,signal(symbole='GBPUSD'),signal()],commun(),r):
            s=candidat.signal;p=profil(symbole=s.symbole,symbole_courtier=s.symbole+'synth',sous_jacent=s.symbole)
            q=cotation(symbole=s.symbole);n=construire_niveaux(s,q,p,commun())
            plan=dimensionner(s,n,p,c,r,g,CalculSynthetique(c,p),commun(),'synthetique')
            if isinstance(plan,PlanDimensionnement):
                self.assertEqual(plan.version_reservations,candidat.etat_reservations.version)
                r.reserver(plan.reservation,c,plan.version_reservations)
            decisions.append((s.strategie,s.symbole,getattr(plan,'motif',None)))
        self.assertEqual(decisions,[('LONDON_V3','EURUSD',None),('LONDON_V3','GBPUSD',None),('EMA_V3','EURUSD',Motif.SYMBOL_BUSY)])
        self.assertLessEqual(r.risque_total(c),D(1));self.assertEqual(len(r.etat.reservations),2)
    def test_plan_perime_ne_peut_pas_reserver_deux_fois_le_budget(self):
        # Deux propositions calculées avant la première transition ; CAS impose une réévaluation.
        from robot.london_execution_coordinateur.test_cat1_c3_dimensionnement import preparer,calculer
        args=preparer();a=calculer(args);s,n,p,c,r,g,port,param=args
        s2=signal(symbole='GBPUSD');p2=profil(symbole='GBPUSD',sous_jacent='GBPUSD');q2=cotation(symbole='GBPUSD')
        b=dimensionner(s2,construire_niveaux(s2,q2,p2,commun()),p2,c,r,g,CalculSynthetique(c,p2),commun(),'synthetique')
        r.reserver(a.reservation,c,a.version_reservations)
        refus=r.reserver(b.reservation,c,b.version_reservations)
        self.assertEqual(refus.detail,'version_reservations');self.assertEqual(len(r.etat.reservations),1)

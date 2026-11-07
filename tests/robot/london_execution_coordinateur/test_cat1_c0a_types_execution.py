"""Catégorie 1, couche 0a (types_execution) : contrat et bornes des sources C04–C09."""
from dataclasses import FrozenInstanceError,replace
from datetime import date
from decimal import Decimal as D
import unittest
from xpbots.execution.c0a_types import *
from xpbots.noyau.c1c_domaine import CleIntention,Sens
from xpbots.noyau.decisions import Signal,Sens as SensEMA,CleIntention as CleEMA
from xpbots.noyau.marche import Tick
from xpbots.noyau.temps import Instant

class TestTypesExecution(unittest.TestCase):
    def setUp(self): self.cle=CleIntention('test','EMA_V3','EURUSD',1000,Sens.ACHAT)
    def test_adaptation_signal_reel_et_cle(self):
        for sens in SensEMA:
            s=Signal('EMA_V3','EURUSD',1000,sens,D('1.1'),.001,1.099 if sens>0 else 1.101,1.5,{'mesure':D('.1')})
            a=adapter_signal_ema(s)
            self.assertEqual((a.strategie,a.symbole,a.cloture_ms,a.sens.signe,a.cloture_prix,a.atr_reference,a.stop_technique,a.multiple_objectif),('EMA_V3','EURUSD',1000,int(sens),1.1,.001,s.b_sl,1.5))
            self.assertEqual(a.contexte['etat_detecteur']['mesure'],'0.1')
            self.assertEqual(adapter_cle_ema(CleEMA.du_signal('test',s)),CleIntention('test',s.strategie,s.symbole,s.cloture_ms,a.sens))
    def test_adaptation_tick_conserve_decimaux_et_temps(self):
        t=Tick('EURUSD','synth',Instant(1000,7),D('1.10001'),D('1.10003'))
        q=adapter_cotation_ema(t,1002)
        self.assertEqual((q.bid,q.ask,q.instant_fournisseur_ms,q.instant_reception_ms),(t.bid,t.ask,1000,1002))
        with self.assertRaises(ValueError): adapter_cotation_ema(t,True)
    def test_adaptateurs_refusent_types_et_conversion_perdante(self):
        for f,args in ((adapter_signal_ema,(None,)),(adapter_cotation_ema,(None,0)),(adapter_cle_ema,(None,))):
            with self.assertRaises(ValueError): f(*args)
        s=Signal('EMA_V3','EURUSD',1000,SensEMA.ACHAT,D('1.10000000000000001'),.001,1.099,1.5)
        with self.assertRaises(ValueError): adapter_signal_ema(s)
    def test_etat_compte_copie_positions_et_distingue_externe(self):
        ps=[PositionCompte('p','EURUSD','EURUSD',D('.1'),None)]
        e=EtatCompte(0,D(100),D(100),D(1),ps)
        ps.clear(); self.assertEqual(len(e.positions),1); self.assertIsNone(e.positions[0].cle)
        with self.assertRaises(FrozenInstanceError): e.solde=D(9)
    def test_nombres_booleens_et_positions_invalides(self):
        for v in (100,True,D('NaN'),D('Infinity')):
            with self.subTest(v=v),self.assertRaises(ValueError): EtatCompte(0,v,D(100),D(0))
        p=PositionCompte('p','EURUSD','EURUSD',D('.1'),D('.1'),self.cle)
        with self.assertRaises(ValueError): EtatCompte(0,D(100),D(100),D(0),(p,p))
        with self.assertRaises(ValueError): replace(p,symbole='GBPUSD')
    def test_reservation_et_restauration_controlees(self):
        r=Reservation(self.cle,'EURUSD',D('.3'),D(1),D('.1'))
        self.assertEqual(EtatReservations(1,[r]).reservations,(r,))
        for changes in ({'risque_initial':D(-1)},{'volume':D(0)},{'remplie':1}):
            with self.assertRaises(ValueError): replace(r,**changes)
        for args in ((True,), (0,(r,r)),(0,(r,),(),(self.cle,))):
            with self.assertRaises(ValueError): EtatReservations(*args)
    def test_risque_nul_C07_et_collections_mal_formees(self):
        r=Reservation(self.cle,'EURUSD',D(0),D(0),D('.1'))
        self.assertEqual(EtatReservations(reservations=(r,)).reservations,(r,))
        for kw in ({'terminees':([{}],)},{'verrous':([{}],)},{'reservations':None},{'verrous':'EURUSD'}):
            with self.subTest(kw=kw),self.assertRaises(ValueError): EtatReservations(**kw)
        with self.assertRaises(ValueError): EtatGardes(date(2026,11,6),D(100),D(100),False,False,0,([{}],))
        with self.assertRaises(ValueError): EtatCompte(0,D(100),D(100),D(0),None)
    def test_etats_gardes_et_ordres_invalides(self):
        e=EtatGardes(date(2026,11,6),D(100),D(100),False,True,0,['decision'])
        self.assertEqual(e.references,('decision',))
        with self.assertRaises(ValueError): replace(e,arret_global=1)
        with self.assertRaises(ValueError): OrdreCalcule(self.cle,'synth',D(1),D(100),D(101),D(102))
        with self.assertRaises(ValueError): ControleNatif(True,D(-1),D(0),True,'ok')
    def test_refus_suit_les_details_du_noyau(self):
        from xpbots.noyau.c1c_domaine import Motif
        self.assertEqual(RefusExecution(Motif.ACCOUNT_RISK_CAP,'RESERVE_TOTALE').detail,'RESERVE_TOTALE')
        with self.assertRaises(ValueError): RefusExecution(Motif.ACCOUNT_RISK_CAP,'invente')

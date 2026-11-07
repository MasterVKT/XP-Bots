"""Catégorie 2, couche 2b (arbitrage) : contrat et bornes des sources C04–C09."""
from decimal import Decimal as D
import unittest
from robot.outils.execution_partagee import *
from xpbots.noyau.decisions import Signal as SignalEMA,Sens as SensEMA
from xpbots.noyau.c1c_domaine import Motif
from xpbots.execution.c0a_types import Reservation,EtatCompte,adapter_signal_ema
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.execution.c2b_arbitrage import candidats_admission

class TestJonctionArbitrage(unittest.TestCase):
    def test_EMA_reel_adapte_et_London_meme_compte_sans_couverture(self):
        ema=adapter_signal_ema(SignalEMA('EMA_V3','EURUSD',T,SensEMA.VENTE,D('1.1003'),.0005,1.1008,1.5))
        r=RegistreReservations(commun());c=EtatCompte(T,D(100),D(100),D(0));resultats=[]
        for candidat in candidats_admission([ema,signal()],commun(),r):
            s=candidat.signal
            v=r.reserver(Reservation(cle(s),s.symbole,D('.5'),D(1),D('.1')),c,candidat.etat_reservations.version)
            resultats.append((s.strategie,getattr(v,'motif',None)))
        self.assertEqual(resultats,[('LONDON_V3',None),('EMA_V3',Motif.SYMBOL_BUSY)])
        self.assertEqual(r.risque_total(c),D('.5'));self.assertEqual(len(r.etat.reservations),1)
    def test_reserve_risque_nul_occupe_toujours_une_place(self):
        r=RegistreReservations(commun());c=EtatCompte(T,D(100),D(100),D(0))
        for s in (signal(),signal(symbole='GBPUSD')): r.reserver(Reservation(cle(s),s.symbole,D(0),D(0),D('.1')),c,r.etat.version)
        refus=r.reserver(Reservation(cle(signal(symbole='XAUUSD')),'XAUUSD',D(0),D(0),D('.1')),c,r.etat.version)
        self.assertEqual((refus.motif,refus.detail),(Motif.ACCOUNT_RISK_CAP,'NOMBRE_POSITIONS'))

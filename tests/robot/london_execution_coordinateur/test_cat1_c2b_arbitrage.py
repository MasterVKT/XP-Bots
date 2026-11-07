"""Catégorie 1, couche 2b (arbitrage) : contrat et bornes des sources C04–C09."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.execution_partagee import *
from xpbots.execution.c0a_types import Reservation,EtatCompte
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.execution.c2b_arbitrage import *

class TestArbitrage(unittest.TestCase):
    def test_priorites_exactes_des_deux_listes(self):
        signaux=[signal(symbole=s,strategie=m) for m in reversed(commun().simultaneous_strategy_priority) for s in reversed(commun().universe_priority)]
        attendu=[(m,s) for m in commun().simultaneous_strategy_priority for s in commun().universe_priority]
        self.assertEqual([(s.strategie,s.symbole) for s in ordonner_signaux(signaux,commun())],attendu)
    def test_parametres_priorite_modifies_effectifs(self):
        p=replace(commun(),simultaneous_strategy_priority=('EMA_V3','LONDON_V3'),universe_priority=('GBPUSD','EURUSD','XAUUSD'))
        suite=[signal(symbole=s,strategie=m) for m in ('LONDON_V3','EMA_V3') for s in ('EURUSD','GBPUSD')]
        self.assertEqual([(s.strategie,s.symbole) for s in ordonner_signaux(suite,p)],[('EMA_V3','GBPUSD'),('EMA_V3','EURUSD'),('LONDON_V3','GBPUSD'),('LONDON_V3','EURUSD')])
    def test_doublon_et_clotures_distinctes_refuses(self):
        for suite in ([signal(),signal()],[signal(),signal(symbole='GBPUSD',cloture_ms=T+1)],[None]):
            with self.assertRaises(ValueError): ordonner_signaux(suite,commun())
        self.assertEqual(ordonner_signaux([],commun()),())
    def test_instantane_relu_apres_reservation(self):
        r=RegistreReservations(commun());c=EtatCompte(T,D(100),D(100),D(0))
        it=candidats_admission([signal(),signal(symbole='GBPUSD')],commun(),r)
        a=next(it);self.assertEqual(a.etat_reservations.version,0)
        r.reserver(Reservation(cle(a.signal),'EURUSD',D('.5'),D(1),D('.1')),c,0)
        b=next(it);self.assertEqual(b.etat_reservations.version,1);self.assertEqual(b.etat_reservations,r.etat)

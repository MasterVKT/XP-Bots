"""Catégorie 2, couche 1c (registre_reservations) : contrat et bornes des sources C04–C09."""
from decimal import Decimal as D
import unittest
from robot.outils.execution_partagee import *
from xpbots.execution.c0a_types import EtatCompte,Reservation
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.noyau.c1c_domaine import Motif

class TestJonctionReservations(unittest.TestCase):
    def test_deux_methodes_meme_registre_reprise_et_alias(self):
        c=EtatCompte(T,D(100),D(100),D(0));r=RegistreReservations(commun())
        a=Reservation(cle(signal(strategie='LONDON_V3')),'EURUSD',D('.5'),D(1),D('.1'))
        r.reserver(a,c,0);reprise=RegistreReservations(commun(),r.etat)
        b=Reservation(cle(signal(strategie='EMA_V3')),'EURUSD',D('.5'),D(1),D('.1'))
        self.assertIs(reprise.reserver(b,c,reprise.etat.version).motif,Motif.SYMBOL_BUSY)
        self.assertEqual(reprise.risque_total(c),D('.5'))

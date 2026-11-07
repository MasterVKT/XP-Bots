"""Catégorie 2, couche 1b (gardes_compte) : contrat et bornes des sources C04–C09."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.execution_partagee import commun,T
from xpbots.execution.c0a_types import EtatCompte
from xpbots.execution.c1b_gardes import GardesCompte,reconstituer_base_utc
from xpbots.noyau.c0a_temps import instant_depuis_iso as ms
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.noyau.c1c_domaine import Motif

class TestJonctionGardes(unittest.TestCase):
    def test_reprise_etat_ne_leve_pas_arret(self):
        t=ms('2026-11-06T00:00:00.000Z');g=GardesCompte(commun())
        g.observer(EtatCompte(t,D(100),D(100),D(0)));g.observer(EtatCompte(t+1,D(90),D(100),D(0)))
        reprise=GardesCompte(commun(),g.etat)
        self.assertIs(reprise.refus().motif,Motif.GLOBAL_DRAWDOWN_HALT)
        reprise.observer(EtatCompte(t+2,D(100),D(100),D(0)))
        self.assertTrue(reprise.etat.arret_global)
    def test_jour_utc_independant_du_jour_londres_ete(self):
        t=ms('2026-07-06T23:30:00.000Z');c=EtatCompte(t,D(100),D(100),D(0))
        b=reconstituer_base_utc(c,[],Intervalle(ms('2026-07-06T00:00:00.000Z'),t+1),aucune_position_minuit=True)
        g=GardesCompte(commun());g.observer(c,b)
        self.assertEqual(g.etat.jour_utc.isoformat(),'2026-07-06')
        with self.assertRaises(ValueError): GardesCompte(commun(),replace(g.etat,jour_utc=b.jour_utc.replace(day=7)))

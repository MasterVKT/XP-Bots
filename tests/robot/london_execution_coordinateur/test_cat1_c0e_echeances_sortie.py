"""Catégorie 1, couche 0e (echeances_sortie) : contrat et bornes des sources C04–C09."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.execution_partagee import *
from xpbots.execution.c0e_echeances import *
from xpbots.noyau.c0a_temps import instant_depuis_iso as ms
from xpbots.noyau.c1b_instrument import HorairesCotation,Intervalle
from xpbots.noyau.c1c_domaine import CauseCloture,Motif

class TestEcheances(unittest.TestCase):
    def h(self,t,fin=None): return HorairesCotation((Intervalle(t-86400000,fin or t+86400000),),(),t-86400000,t+172800000)
    def test_duree_depuis_premier_fill_non_aligne(self):
        t=T+1234;r=premiere_echeance(t,'LONDON_V3',configuration(),self.h(t))
        self.assertEqual((r.instant_ms,r.causes),(t+commun().max_position_wallclock_seconds*1000,(CauseCloture.DUREE_MAXIMALE,)))
    def test_sortie_locale_ete_et_hiver(self):
        for text,want in (('2026-07-06T10:30:00.000Z','2026-07-06T11:00:00.000Z'),('2026-11-06T11:30:00.000Z','2026-11-06T12:00:00.000Z')):
            t=ms(text);r=premiere_echeance(t,'LONDON_V3',configuration(),self.h(t))
            self.assertEqual(r.instant_ms,ms(want));self.assertIn(CauseCloture.HEURE_SORTIE,r.causes)
    def test_pause_native_et_horaires_inconnus(self):
        r=premiere_echeance(T,'LONDON_V3',configuration(),self.h(T,T+120000))
        self.assertEqual((r.instant_ms,r.causes),(T+60000,(CauseCloture.FERMETURE_NATIVE,)))
        h=HorairesCotation((Intervalle(T,T+10000),),(),T,T+10000)
        self.assertIs(premiere_echeance(T,'LONDON_V3',configuration(),h).motif,Motif.ENVIRONMENT_NOT_READY)
    def test_blackout_et_methode_configuree(self):
        conf=configuration()
        conf=replace(conf,london={**conf.london,'force_exit_local':'23:59:00'})
        t=ms('2026-11-06T20:30:00.000Z')
        r=premiere_echeance(t,'LONDON_V3',conf,self.h(t))
        self.assertEqual((r.instant_ms,r.causes),(ms('2026-11-06T21:00:00.000Z'),(CauseCloture.BLACKOUT,)))
        r=premiere_echeance(ms('2026-11-06T21:30:00.000Z'),'LONDON_V3',conf,self.h(t))
        self.assertEqual(r.instant_ms,ms('2026-11-06T21:00:00.000Z'))
        self.assertIsNotNone(premiere_echeance(T,'EMA_V3',configuration(),self.h(T)).instant_ms)

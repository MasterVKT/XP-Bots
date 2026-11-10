"""Jonction avec les valeurs, horaires et calendriers réels du noyau."""
from dataclasses import replace
from datetime import datetime,date,timezone
import unittest
from robot.outils.rejeu import C,lot_csv
from xpbots.noyau.c0a_temps import instant_depuis_datetime
from xpbots.noyau.c1b_instrument import Intervalle,HorairesCotation
from xpbots.rejeu.c0a_types import ErreurRejeu
from xpbots.rejeu.c1a_ticks import analyser_lignes_ticks,jours_marche


class TestJonctionTicks(unittest.TestCase):
    def test_jours_sans_tick_retenus_apres_changement_heure(self):
        a=instant_depuis_datetime(datetime(2026,10,23,tzinfo=timezone.utc))
        b=instant_depuis_datetime(datetime(2026,10,28,tzinfo=timezone.utc))
        l,m=lot_csv(debut=a,fin=b)
        # Séances uniquement 07:30-08:00 UTC : Londres 08:30 le vendredi, 07:30 le lundi.
        vendredi=Intervalle(a+27000000,a+28800000)
        lundi=Intervalle(a+3*86400000+27000000,a+3*86400000+28800000)
        mardi=Intervalle(a+4*86400000+28800000,a+4*86400000+30600000)
        h=HorairesCotation((vendredi,lundi,mardi),(),a,b)
        m=replace(m,horaires={'EURUSD':h},couverture=(),trous=(m.intervalle,))
        jours=jours_marche(m,'test',{'EURUSD':('08:00:00','11:00:00')},C.technique.commun)
        self.assertEqual([j.jour for j in jours],[date(2026,10,23),date(2026,10,27)])
        self.assertEqual(len(jours),2)  # Aucun prix n'est nécessaire au dénominateur.

    def test_fermeture_exceptionnelle_et_horaire_inconnu(self):
        a=instant_depuis_datetime(datetime(2026,11,9,tzinfo=timezone.utc));b=a+86400000
        _,m=lot_csv(debut=a,fin=b)
        h=HorairesCotation((m.intervalle,),(Intervalle(a+28800000,a+39600000),),a,b)
        self.assertEqual(jours_marche(replace(m,horaires={'EURUSD':h}),'x',{'EURUSD':('08:00','11:00')},C.technique.commun),())
        h=HorairesCotation((m.intervalle,),(),a,a+28800000)
        with self.assertRaises(ErreurRejeu):jours_marche(replace(m,horaires={'EURUSD':h}),'x',{'EURUSD':('08:00','11:00')},C.technique.commun)

    def test_couverture_transmise_sans_combler_le_trou(self):
        l,m=lot_csv();h=analyser_lignes_ticks(l,m)
        self.assertIs(h.manifeste,m);self.assertEqual(h.manifeste.couverture,m.couverture)

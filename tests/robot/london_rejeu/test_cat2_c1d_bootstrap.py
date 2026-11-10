"""Jonction valeurs/protocole réels ; panel comprenant les journées sans trade."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.rejeu import C
from robot.london_rejeu.test_cat1_c1d_bootstrap import panel
from xpbots.rejeu.c0a_types import ValeurJour
from xpbots.rejeu.c0b_protocole import charger_protocole
from xpbots.rejeu.c1d_bootstrap import bootstrap_apparie


class TestJonctionBootstrap(unittest.TestCase):
    def test_parametres_charges_et_meme_panel_multi_methodes(self):
        p=charger_protocole(C).bootstrap
        j=panel();a=tuple(ValeurJour(v.jour,v.periode,D(1),2 if i%2 else 0) for i,v in enumerate(j))
        b=tuple(replace(v,pnl_net=v.pnl_net+D('.1')) for v in a)
        r=bootstrap_apparie(a,b,replace(p,replications=5),D(C.technique.commun.initial_equity_usd))
        self.assertEqual((r.nombre_jours,r.parametres.graine,r.parametres.bloc_jours),(8,p.graine,p.bloc_jours))
        self.assertEqual(r.gain_incremental.valeurs,(D('.8'),)*5)
        self.assertEqual(r.esperance_candidat.invalides,0)

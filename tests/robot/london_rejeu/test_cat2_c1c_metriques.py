"""Jonction des types réels, coûts originaux et calendrier de sortie Londres."""
from dataclasses import replace
from datetime import date,datetime,timezone
from decimal import Decimal as D
import unittest
from robot.outils.rejeu import C
from robot.london_rejeu.test_cat1_c0a_types import trade
from xpbots.noyau.c0a_temps import instant_depuis_datetime
from xpbots.rejeu.c0a_types import JourMarche,FactureIA
from xpbots.rejeu.c1c_metriques import panel_journalier


class TestJonctionMetriques(unittest.TestCase):
    def test_sortie_ete_23h30_utc_affectee_au_lendemain_londres(self):
        t=instant_depuis_datetime(datetime(2026,6,8,23,30,tzinfo=timezone.utc))
        a=trade();a=replace(a,cle=replace(a.cle,cloture_ms=t-2),entree_ms=t-1,sortie_ms=t)
        j=(JourMarche(date(2026,6,8),'validation'),JourMarche(date(2026,6,9),'validation'))
        f=FactureIA('f',t,D('.1'),('LONDON_V3','EMA_V3'),'EVENEMENT')
        v=panel_journalier((a,),j,C.technique.commun,(f,),methode='LONDON_V3')
        self.assertEqual((v[0].pnl_net,v[0].trades_clos),(D(0),0))
        self.assertEqual((v[1].pnl_net,v[1].trades_clos),(D('1.65'),1))

    def test_facture_sans_trade_reste_dans_le_panel_et_frontiere(self):
        t=instant_depuis_datetime(datetime(2026,11,9,12,tzinfo=timezone.utc))
        jours=(JourMarche(date(2026,11,9),'a'),JourMarche(date(2026,11,10),'b'))
        f=FactureIA('f',t,D('.02'),('LONDON_V3',),'BRIEFING')
        v=panel_journalier((),jours,C.technique.commun,(f,f))
        self.assertEqual([(x.periode,x.pnl_net,x.trades_clos) for x in v],[('a',D('-.02'),0),('b',D(0),0)])

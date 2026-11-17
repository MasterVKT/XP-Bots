"""Catégorie 2, couche 2 : vrais bras London A/B et rejeu des faits de marché."""
import unittest
from robot.outils.orchestration import ticks_courts
from robot.outils.pilote_orchestration import duo
from robot.orchestration.test_cat1_c2_marche import paquet
from xpbots.orchestration.c0_contrats import ReceptionExterne, EntreeMoteur


class TestJonctionMarche(unittest.TestCase):
    def test_memes_faits_de_marche_ab_et_rejeu_sans_courtier(self):
        ticks=ticks_courts();m,ports,_,_,_=duo(ticks);sorties=[]
        for i,tick in enumerate(ticks):
            for p in ports.values():p.sur_tick(tick)
            entree=EntreeMoteur(tick.instant_reception_ms,i+1,'TICKS',(tick,),receptions=(
                ReceptionExterne('MARCHE',paquet(tick.instant_reception_ms,i+1),'EURUSD'),))
            sorties.append(m.traiter(entree))
        r,ports2,_,_,_=duo(ticks)
        def interdit(*a,**kw):raise AssertionError('backend au rejeu de MARCHE')
        for p in ports2.values():
            for n in ('profit','frais_aller_retour','frais_sortie','marge','controler','specifications','etat_compte'):
                setattr(p,n,interdit)
        for j,s in zip(m.entrees,sorties):self.assertEqual(r.rejouer(j),s)
        self.assertEqual(r.exporter_checkpoint(),m.exporter_checkpoint())

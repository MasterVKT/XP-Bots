"""Catégorie 2, couche 2 : checkpoint sur les vrais bras London A/B."""
import unittest
from robot.outils.orchestration import ticks_courts
from robot.outils.pilote_orchestration import duo,piloter


class TestCheckpointJonction(unittest.TestCase):
    def test_checkpoint_etat_et_rejeu_sur_les_deux_bras_reels(self):
        ticks=ticks_courts();m,ports,_,_,_=duo(ticks);sorties,_=piloter(ticks,m,ports)
        cp=m.exporter_checkpoint();etat=m.etat
        self.assertEqual(cp.numero_entrees,len(m.entrees));self.assertEqual(cp.flux,etat.flux)
        self.assertEqual(cp.bras,etat.bras);self.assertEqual(cp.fondamental,etat.fondamental);self.assertEqual(cp.ia,etat.ia)
        r,p2,_,_,_=duo(ticks)
        def interdit(*a,**kw):raise AssertionError('backend consulte au rejeu')
        for p in p2.values():
            for n in ('profit','frais_aller_retour','frais_sortie','marge','controler','specifications','etat_compte'):setattr(p,n,interdit)
        for j,s in zip(m.entrees,sorties):self.assertEqual(r.rejouer(j),s)
        self.assertEqual(r.exporter_checkpoint(),cp)

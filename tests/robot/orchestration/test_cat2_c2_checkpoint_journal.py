"""Reconstitution A/B par le journal réel et comparaison de l'état courant."""
import unittest
from robot.outils.orchestration import ticks_courts
from robot.outils.pilote_orchestration import duo,piloter


class TestJonctionCheckpointJournal(unittest.TestCase):
    def test_historiques_c05_et_ia_complets_reconstitues_depuis_les_engagements(self):
        from robot.outils.checkpoints_controles import controles_repetes,composition_controles
        m,_,sorties=controles_repetes(100);r,ports,_,_,_=composition_controles()
        def interdit(*a,**k):raise AssertionError('BACKEND_INTERDIT')
        for p in ports.values():
            for n in ('profit','frais_aller_retour','frais_sortie','marge','controler','specifications','etat_compte'):
                setattr(p,n,interdit)
        cp=m.exporter_checkpoint_journal()
        for j,s in zip(m.entrees,sorties):self.assertEqual(r.rejouer(j),s)
        self.assertEqual(r.exporter_checkpoint_journal(),cp)
        self.assertEqual(r.exporter_checkpoint(),m.exporter_checkpoint())
        self.assertEqual(len(r.exporter_checkpoint().ia.scelles),100)

    def test_journal_rejoue_et_sorties_identiques_sur_les_deux_bras(self):
        ticks=ticks_courts();m,ports,_,_,_=duo(ticks);sorties,_=piloter(ticks,m,ports)
        r,p2,_,_,_=duo(ticks)
        def interdit(*a,**kw):raise AssertionError('BACKEND_INTERDIT')
        for p in p2.values():
            for n in ('profit','frais_aller_retour','frais_sortie','marge','controler','specifications','etat_compte'):
                setattr(p,n,interdit)
        for entree,sortie in zip(m.entrees,sorties):self.assertEqual(r.rejouer(entree),sortie)
        self.assertEqual(r.exporter_checkpoint_journal(),m.exporter_checkpoint_journal())
        self.assertEqual(r.exporter_checkpoint(),m.exporter_checkpoint())

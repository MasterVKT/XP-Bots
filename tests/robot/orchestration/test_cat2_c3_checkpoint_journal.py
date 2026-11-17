"""Checkpoint et entrées réels désérialisés puis rejoués sur backend interdit."""
import unittest
from robot.outils.orchestration import ticks_courts
from robot.outils.pilote_orchestration import duo,piloter
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur


class TestJonctionCodecCheckpointJournal(unittest.TestCase):
    def test_controles_courants_et_historiques_complets_apres_codec_et_rejeu(self):
        from robot.outils.checkpoints_controles import controles_repetes,composition_controles
        m,_,sorties=controles_repetes(100)
        cp=deserialiser_valeur(serialiser_valeur(m.exporter_checkpoint_journal()))
        complet=deserialiser_valeur(serialiser_valeur(m.exporter_checkpoint()))
        entrees=deserialiser_valeur(serialiser_valeur(m.entrees))
        attendues=deserialiser_valeur(serialiser_valeur(sorties))
        r,ports,_,_,_=composition_controles()
        def interdit(*a,**k):raise AssertionError('BACKEND_INTERDIT')
        for p in ports.values():
            for n in ('profit','frais_aller_retour','frais_sortie','marge','controler','specifications','etat_compte'):
                setattr(p,n,interdit)
        for entree,sortie in zip(entrees,attendues):
            self.assertEqual(r.rejouer(entree),sortie)
        self.assertEqual(r.exporter_checkpoint_journal(),cp)
        self.assertEqual(r.exporter_checkpoint(),complet)
        self.assertEqual(len(complet.ia.scelles),100)

    def test_deux_bras_reconstitues_et_checkpoint_compact_identique(self):
        ticks=ticks_courts();m,ports,_,_,_=duo(ticks);piloter(ticks,m,ports)
        cp=deserialiser_valeur(serialiser_valeur(m.exporter_checkpoint_journal()))
        entrees=deserialiser_valeur(serialiser_valeur(m.entrees));r,p2,_,_,_=duo(ticks)
        def interdit(*a,**k):raise AssertionError('BACKEND_INTERDIT')
        for p in p2.values():
            for n in ('profit','frais_aller_retour','frais_sortie','marge','controler','specifications','etat_compte'):
                setattr(p,n,interdit)
        for j in entrees:r.rejouer(j)
        self.assertEqual(r.exporter_checkpoint_journal(),cp)

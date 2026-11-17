"""Catégorie 2 : vraies valeurs London, reprise et rejeu du journal décodé."""
from dataclasses import replace
import json
import unittest
from robot.outils.orchestration import ticks_courts
from robot.outils.pilote_orchestration import duo, piloter
from xpbots.orchestration.c0_contrats import ErreurOrchestration
from xpbots.orchestration.c3_codec import serialiser_valeur, deserialiser_valeur
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle


class TestCodecJonction(unittest.TestCase):
    def test_etat_complet_et_checkpoint_du_vrai_moteur_ab(self):
        ticks = ticks_courts(); m, ports, _, _, _ = duo(ticks); piloter(ticks, m, ports)
        for v in (m.etat, m.exporter_checkpoint(), m.entrees):
            b = serialiser_valeur(v)
            self.assertEqual(deserialiser_valeur(b), v)
            self.assertEqual(serialiser_valeur(deserialiser_valeur(b)), b)

    def test_rejeu_du_journal_decode_sans_backend(self):
        ticks = ticks_courts(); m, ports, _, _, _ = duo(ticks); sorties, _ = piloter(ticks, m, ports)
        journal = deserialiser_valeur(serialiser_valeur(m.entrees))
        r, p2, _, _, _ = duo(ticks)
        def interdit(*a, **kw): raise AssertionError('backend physique au rejeu')
        for p in p2.values():
            for n in ('profit', 'frais_aller_retour', 'frais_sortie', 'marge', 'controler', 'specifications', 'etat_compte'):
                setattr(p, n, interdit)
        for j, sortie in zip(journal, sorties): self.assertEqual(r.rejouer(j), sortie)
        self.assertEqual(r.exporter_checkpoint(), m.exporter_checkpoint())

    def test_sceau_corrompu_refuse_avant_restauration(self):
        ticks = ticks_courts(); m, ports, _, _, _ = duo(ticks); piloter(ticks, m, ports)
        for v in (m.etat, m.exporter_checkpoint()):
            b = serialiser_valeur(replace(v, empreinte='0'*64))
            with self.assertRaises(ErreurOrchestration): deserialiser_valeur(b)

    def test_horaires_reconstruisent_leurs_intervalles_effectifs(self):
        v = HorairesCotation((Intervalle(100, 1000),), (Intervalle(300, 400),), 100, 1000)
        r = deserialiser_valeur(serialiser_valeur(v))
        self.assertEqual(r, v)
        self.assertEqual(r.ouvert_a(350), v.ouvert_a(350))

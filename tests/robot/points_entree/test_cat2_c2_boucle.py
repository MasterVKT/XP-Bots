"""Vraie boucle, adaptateurs, livres et journaux, sans SDK réel."""
import unittest
from robot.outils.boucle_directe import HarnaisDirect
from robot.outils.orchestration import C
from xpbots.app.c1e_cli_rapports import rapporter_incident
from xpbots.noyau.c2_journal import serialiser
from xpbots.orchestration.c3_codec import deserialiser_valeur
from xpbots.app.c1a_livre_papier import TYPES_PAPIER
from xpbots.app.c1f_composition_moteur import rejouer_incident


class TestJonctionBoucle(HarnaisDirect,unittest.TestCase):
    def test_rejeu_des_sorties_exactes_et_reprise_physique_sans_retro_entree(self):
        b=self.nouveau();sorties=[]
        for n in range(3):
            self.sdk.ajouter_tick('EURUSD.micro',self.temps,1.1003,1.1004)
            sorties.extend(b.iterer());self.avancer(1000)
        archive=b.archive_incident();rapport=rapporter_incident(C,archive)
        self.assertEqual(rapport['statut'],'IDENTIQUE')
        d=deserialiser_valeur(archive,types_supplementaires=TYPES_PAPIER);s=d['session']
        i=deserialiser_valeur(s['initialisation'],types_supplementaires=TYPES_PAPIER)
        m,ss=rejouer_incident(C,i['composition'],dict(i['appels_initialisation']),s['entrees'],s['checkpoint'])
        self.assertEqual(tuple(ss),tuple(sorties))
        self.assertEqual(m.exporter_checkpoint(),b.moteur.exporter_checkpoint())
        self.assertEqual(tuple(serialiser(e).encode() for x in sorties for e in x.enregistrements),d['decisions'])
        self.infra.fermer(1000)
        nouveau=self.nouveau(sdk=self.sdk)
        self.assertEqual(nouveau.moteur.entrees,b.moteur.entrees)
        self.assertEqual(nouveau.livres['REFERENCE'].checkpoint,b.livres['REFERENCE'].checkpoint)
        nouveau.iterer()
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))

    def test_deux_comptes_ab_durables_et_rejoues_sans_ordre_natif(self):
        b=self.nouveau('PAPER_AB');b.iterer()
        self.assertIsNot(b.livres['REFERENCE'],b.livres['IA'])
        rapport=rapporter_incident(C,b.archive_incident())
        self.assertEqual(set(rapport['livres_verifies']),{'REFERENCE','IA'})
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))

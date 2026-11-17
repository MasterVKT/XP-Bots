"""Séance London complète par le vrai direct et les fichiers physiques."""
import unittest
from robot.outils.boucle_directe import HarnaisDirect
from robot.outils.scenario_london_direct import ScenarioLondonDirect
from robot.outils.orchestration import C
from xpbots.app.c1a_livre_papier import TYPES_PAPIER
from xpbots.app.c1e_cli_rapports import rapporter_incident
from xpbots.app.c1f_composition_moteur import rejouer_incident
from xpbots.noyau.c2_journal import serialiser
from xpbots.orchestration.c3_codec import deserialiser_valeur


class TestSeanceLondonPhysique(HarnaisDirect,unittest.TestCase):
    def test_seance_complete_paper_journaux_et_rejeu_c11_14_exacts(self):
        s=ScenarioLondonDirect(self)
        s.jusqua(s.jour+17*3600000+1000)
        b=s.boucle;p=b.livres['REFERENCE']
        self.assertTrue(p.premiers_remplissages);self.assertTrue(p.trades)
        self.assertFalse(p.positions_ouvertes)
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))
        archive=b.archive_incident();a=deserialiser_valeur(archive,types_supplementaires=TYPES_PAPIER)
        session=a['session'];i=deserialiser_valeur(session['initialisation'],types_supplementaires=TYPES_PAPIER)
        m,sorties=rejouer_incident(C,i['composition'],dict(i['appels_initialisation']),session['entrees'],session['checkpoint'])
        self.assertEqual(sorties,tuple(s.sorties))
        self.assertEqual(m.exporter_checkpoint(),b.moteur.exporter_checkpoint())
        self.assertEqual(a['decisions'],tuple(serialiser(e).encode() for sortie in s.sorties for e in sortie.enregistrements))
        decisions=b''.join(f.read_bytes() for f in sorted(self.infra.journal.dossier.glob('decisions_*.jsonl')))
        self.assertEqual(decisions,b''.join(x+b'\n' for x in a['decisions']))
        entrees=b''.join(f.read_bytes() for f in sorted(self.infra.journal.dossier.glob('entrees_*.jsonl')))
        self.assertEqual(entrees,b''.join(x+b'\n' for x in self.infra.depot.entrees()))
        rapport=rapporter_incident(C,archive)
        self.assertEqual(rapport['statut'],'IDENTIQUE')
        self.assertEqual(rapport['validation_financiere'],'NON_EVALUEE')
        self.assertEqual(set(rapport['livres_verifies']),{'REFERENCE'})

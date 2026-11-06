"""Segment S6 : journal canonique du noyau écrit par l'infrastructure (fichier temporaire puis remplacement)."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from robot.outils.configuration import configuration_figee
from xpbots.infra.squelette import NOM_JOURNAL_SQUELETTE, ecrire_journal, lire_configuration
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c2_journal import serialiser
from xpbots.london.squelette import fabriquer_strategie
from xpbots.orchestration.squelette import fabriquer_moteur_minimal
from xpbots.rejeu.squelette import hypotheses_marche_squelette
from robot.outils.chemins import RACINE_DEPOT
from robot.outils.configuration import octets_exports


class TestJournalDuSquelette(unittest.TestCase):
    def test_lignes_canoniques_ecrites_puis_relues(self):
        configuration = configuration_figee()
        duree = configuration.technique.commun.timeframe_seconds * 1000
        ticks = [Tick('EURUSD', 'EURUSD', i * duree, i * duree, i, 1.1, 1.1001) for i in range(3)]
        horaires, periodes = hypotheses_marche_squelette(ticks, configuration)
        moteur = fabriquer_moteur_minimal(fabriquer_strategie(configuration), configuration, 'REJEU',
                                          horaires=horaires, periodes_couvertes=periodes)
        enregistrements = [e for t in ticks for e in moteur.traiter_tick(t).enregistrements]
        with tempfile.TemporaryDirectory() as dossier:
            chemin = ecrire_journal(dossier, (serialiser(e) for e in enregistrements))
            lignes = Path(chemin).read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(lignes), 2)
        for ligne in lignes:
            self.assertEqual(json.dumps(json.loads(ligne), ensure_ascii=False, sort_keys=True, separators=(',', ':')), ligne)

    def test_ecriture_et_remplacement(self):
        with tempfile.TemporaryDirectory() as racine:
            dossier = str(Path(racine) / 'sortie' / 'jour')
            chemin = ecrire_journal(dossier, ['{"a":1}', '{"a":2}'])
            self.assertEqual(Path(chemin).name, NOM_JOURNAL_SQUELETTE)
            self.assertEqual(Path(chemin).read_bytes(), b'{"a":1}\n{"a":2}\n')
            ecrire_journal(dossier, ['{"b":1}'])
            self.assertEqual(Path(chemin).read_text(encoding='utf-8'), '{"b":1}\n')
            self.assertEqual(sorted(os.listdir(dossier)), [NOM_JOURNAL_SQUELETTE])

    def test_ligne_invalide_sans_fichier_partiel(self):
        with tempfile.TemporaryDirectory() as dossier:
            ecrire_journal(dossier, ['{"ancien":1}'])
            with self.assertRaises(ValueError):
                ecrire_journal(dossier, ['{"a":1}', 'deux\nlignes'])
            self.assertEqual(sorted(os.listdir(dossier)), [NOM_JOURNAL_SQUELETTE])
            self.assertEqual((Path(dossier) / NOM_JOURNAL_SQUELETTE).read_text(encoding='utf-8'), '{"ancien":1}\n')

    def test_lecture_de_la_configuration_du_depot(self):
        self.assertEqual(lire_configuration(str(RACINE_DEPOT)), octets_exports())


if __name__ == '__main__':
    unittest.main()

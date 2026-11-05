"""Segment S6 : forme canonique des enregistrements (noyau) et écriture atomique du journal (infrastructure)."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from xpbots.infra.squelette import NOM_JOURNAL_SQUELETTE, ecrire_journal
from xpbots.noyau.squelette import ErreurDonnees, serialiser_enregistrement


class TestFormeCanonique(unittest.TestCase):
    def test_cles_triees_sans_espace_utf8(self):
        ligne = serialiser_enregistrement({'z': 1, 'a': {'é': 'Londres', 'b': [1.5, None]}})
        self.assertEqual(ligne, '{"a":{"b":[1.5,null],"é":"Londres"},"z":1}')
        self.assertEqual(serialiser_enregistrement(json.loads(ligne)), ligne)

    def test_nombres_non_finis_refuses(self):
        for valeur in (float('nan'), float('inf'), -float('inf')):
            with self.subTest(valeur=valeur), self.assertRaises(ErreurDonnees):
                serialiser_enregistrement({'x': valeur})


class TestEcritureJournal(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()

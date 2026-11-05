"""Segment S1 : lecture des lignes (infrastructure) et analyse des ticks (rejeu)."""
from pathlib import Path
import tempfile
import unittest

from robot.outils.fabrique_ticks import BougieVoulue, ecrire_csv, lignes_csv, ticks_de_bougies
from xpbots.infra.squelette import lire_lignes, lire_octets
from xpbots.noyau.squelette import ErreurDonnees, Tick
from xpbots.rejeu.squelette import analyser_lignes_ticks

ENTETE = 'canonical_symbol,broker_symbol,time_utc_ms,sequence,bid,ask'


class TestAnalyseTicks(unittest.TestCase):
    def test_lignes_valides(self):
        ticks = list(analyser_lignes_ticks([ENTETE, 'EURUSD,EURUSDm,1000,1,1.10000,1.10010',
                                            'EURUSD,EURUSDm,1000,2,1.10001,1.10011']))
        self.assertEqual(ticks, [Tick('EURUSD', 'EURUSDm', 1000, 1, 1.1, 1.1001),
                                 Tick('EURUSD', 'EURUSDm', 1000, 2, 1.10001, 1.10011)])

    def test_refus(self):
        cas = {
            'fichier vide': [],
            'en-tête': ['symbol,time,bid,ask'],
            'champs': [ENTETE, 'EURUSD,EURUSD,1000,1,1.1'],
            'symbole vide': [ENTETE, ',EURUSD,1000,1,1.1,1.2'],
            'instant négatif': [ENTETE, 'EURUSD,EURUSD,-1,1,1.1,1.2'],
            'instant décimal': [ENTETE, 'EURUSD,EURUSD,1.5,1,1.1,1.2'],
            'prix illisible': [ENTETE, 'EURUSD,EURUSD,1000,1,abc,1.2'],
            'prix non fini': [ENTETE, 'EURUSD,EURUSD,1000,1,nan,1.2'],
            'prix infini': [ENTETE, 'EURUSD,EURUSD,1000,1,1.1,inf'],
            'prix nul': [ENTETE, 'EURUSD,EURUSD,1000,1,0,1.2'],
            'ordre': [ENTETE, 'EURUSD,EURUSD,2000,1,1.1,1.2', 'EURUSD,EURUSD,1000,2,1.1,1.2'],
            'séquence répétée': [ENTETE, 'EURUSD,EURUSD,1000,3,1.1,1.2', 'EURUSD,EURUSD,1000,3,1.1,1.2'],
            'ligne vide': [ENTETE, ''],
        }
        for nom, lignes in cas.items():
            with self.subTest(cas=nom), self.assertRaises(ErreurDonnees):
                list(analyser_lignes_ticks(lignes))


class TestLectureFichiers(unittest.TestCase):
    def test_aller_retour_fabrique(self):
        ticks = ticks_de_bougies('EURUSD', [BougieVoulue(0, '1.10000', '1.10020', '1.09990', '1.10010')])
        with tempfile.TemporaryDirectory() as dossier:
            chemin = ecrire_csv(Path(dossier) / 'ticks.csv', ticks)
            self.assertEqual(list(lire_lignes(str(chemin))), lignes_csv(ticks))
            self.assertEqual(lire_octets(str(chemin)), chemin.read_bytes())
            lus = list(analyser_lignes_ticks(lire_lignes(str(chemin))))
        self.assertEqual([t.bid for t in lus], [float(t.bid) for t in ticks])

    def test_fins_de_ligne_crlf(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / 'ticks.csv'
            chemin.write_bytes(f'{ENTETE}\r\nEURUSD,EURUSD,0,1,1.1,1.2\r\n'.encode('utf-8'))
            self.assertEqual(len(list(analyser_lignes_ticks(lire_lignes(str(chemin))))), 1)


if __name__ == '__main__':
    unittest.main()

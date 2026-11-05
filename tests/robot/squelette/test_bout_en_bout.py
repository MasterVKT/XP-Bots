"""Test de bout en bout du squelette composite (document 04, phase 1, étape 4).

Une journée Londres synthétique d'EURUSD est écrite dans un dossier temporaire au format canonique, puis
rejouée par la vraie commande `python -m xpbots.app.rejeu_squelette`, `PYTHONPATH` désignant `src`. Attendus :
code de sortie nul ; un enregistrement par bougie M15 close, dans l'ordre ; forme canonique ; motif admis par
C09 (P-07) ; OHLC identiques aux bougies voulues ; durée et identifiant de stratégie venant de la
configuration figée. Ce test fait partie de la régression intégrale de chaque gate du plan.
"""
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from robot.outils.chemins import CONFIGURATION_TECHNIQUE, RACINE_DEPOT, SOURCES
from robot.outils.fabrique_ticks import bornes_journee_londres, ecrire_csv, journee_londres
from robot.outils.specification import configuration_technique, motifs_admis
from xpbots.noyau.squelette import serialiser_enregistrement

CONFIGURATION = configuration_technique()
DUREE_MS = CONFIGURATION['common']['timeframe_seconds'] * 1000


def rejouer_journee(jour, dossier):
    bougies, ticks = journee_londres(jour, duree_ms=DUREE_MS)
    fichier = ecrire_csv(dossier / f'EURUSD_{jour.isoformat()}.csv', ticks)
    environnement = {**os.environ, 'PYTHONPATH': str(SOURCES)}
    execution = subprocess.run(
        [sys.executable, '-B', '-m', 'xpbots.app.rejeu_squelette', '--configuration', str(CONFIGURATION_TECHNIQUE),
         '--ticks', str(fichier), '--sortie', str(dossier / 'sortie')],
        cwd=RACINE_DEPOT, env=environnement, capture_output=True, text=True, timeout=120)
    return bougies, ticks, execution


class TestBoutEnBout(unittest.TestCase):
    def test_journee_londres_eurusd(self):
        for jour in (date(2026, 7, 15), date(2026, 1, 14)):
            with self.subTest(jour=jour), tempfile.TemporaryDirectory() as racine:
                dossier = Path(racine)
                bougies, ticks, execution = rejouer_journee(jour, dossier)
                self.assertEqual(execution.returncode, 0, execution.stderr)
                self.assertEqual(execution.stderr, '')
                resume = json.loads(execution.stdout)
                lignes = (dossier / 'sortie' / 'decisions.jsonl').read_text(encoding='utf-8').splitlines()
                self.assertEqual(resume, {'statut': 'OK', 'ticks': len(ticks), 'enregistrements': len(bougies),
                                          'journal': str(dossier / 'sortie' / 'decisions.jsonl')})
                self.assertEqual(len(lignes), len(bougies))
                self.assertEqual(len(lignes), 24 * 3_600_000 // DUREE_MS)
                enregistrements = [json.loads(ligne) for ligne in lignes]
                for ligne, enregistrement in zip(lignes, enregistrements):
                    self.assertEqual(serialiser_enregistrement(enregistrement), ligne)
                self.assertEqual(enregistrements[0]['bougie']['debut_utc_ms'], bornes_journee_londres(jour)[0])
                for numero, (voulue, enregistrement) in enumerate(zip(bougies, enregistrements), start=1):
                    bougie = enregistrement['bougie']
                    self.assertEqual(enregistrement['numero'], numero)
                    self.assertEqual((bougie['debut_utc_ms'], bougie['fin_utc_ms']),
                                     (voulue.debut_ms, voulue.debut_ms + DUREE_MS))
                    self.assertEqual(enregistrement['instant_utc_ms'], voulue.debut_ms + DUREE_MS,
                                     'clôture par le tick de frontière')
                    self.assertEqual((bougie['ouverture'], bougie['haut'], bougie['bas'], bougie['cloture']),
                                     tuple(float(v) for v in (voulue.ouverture, voulue.haut, voulue.bas,
                                                              voulue.cloture)))
                    self.assertEqual((enregistrement['type'], enregistrement['mode'], enregistrement['symbole'],
                                      enregistrement['strategie'], enregistrement['signal']),
                                     ('CLOTURE', 'REJEU', 'EURUSD', CONFIGURATION['london']['strategy_id'], None))
                    self.assertIn(enregistrement['motif'], motifs_admis())
                    self.assertEqual((enregistrement['motif'], enregistrement['detail']),
                                     ('NO_SETUP', 'SEGMENT_MINIMAL_S3'))


if __name__ == '__main__':
    unittest.main()

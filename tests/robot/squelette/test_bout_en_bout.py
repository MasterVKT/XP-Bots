"""Test de bout en bout du squelette composite (document 04, phase 1, étape 4).

Quatorze jours de préchargement puis une journée Londres synthétique d'EURUSD sont écrits au format canonique, puis
le tout est rejoué par la vraie commande `python -m xpbots.app.rejeu_squelette`, `PYTHONPATH` désignant `src`. Attendus :
code de sortie nul ; un enregistrement par bougie M15 close, dans l'ordre ; forme canonique ; motif admis par
C09 (P-07) ; OHLC identiques aux bougies voulues ; durée et identifiant de stratégie venant de la
configuration figée chargée avec contrôle des empreintes. Ce test fait partie de la régression intégrale de chaque gate du plan.
"""
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from robot.outils.chemins import RACINE_DEPOT, SOURCES
from robot.outils.configuration import configuration_figee
from robot.outils.fabrique_ticks import bornes_journee_londres, ecrire_csv
from robot.outils.fabrique_journees_london import journee_london_prechargee
from robot.outils.specification import configuration_technique, motifs_admis

CONFIGURATION = configuration_technique()
DUREE_MS = CONFIGURATION['common']['timeframe_seconds'] * 1000
FIGEE = configuration_figee()
EMPREINTES = {'technique': FIGEE.technique.empreinte_canonique, 'ia': FIGEE.ia.empreinte_canonique}


def rejouer_journee(jour, dossier):
    bougies, ticks = journee_london_prechargee(jour, FIGEE.technique)
    fichier = ecrire_csv(dossier / f'EURUSD_{jour.isoformat()}.csv', ticks)
    environnement = {**os.environ, 'PYTHONPATH': str(SOURCES)}
    execution = subprocess.run(
        [sys.executable, '-B', '-m', 'xpbots.app.rejeu_squelette', '--racine-depot', str(RACINE_DEPOT),
         '--ticks', str(fichier), '--sortie', str(dossier / 'sortie'), '--tick-size', 'EURUSD=0.00001'],
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
                self.assertEqual(resume, {'statut': 'OK', 'ticks': len(ticks), 'enregistrements': len(lignes),
                                          'journal': str(dossier / 'sortie' / 'decisions.jsonl')})
                enregistrements = [json.loads(ligne) for ligne in lignes]
                clotures = [e for e in enregistrements if e['type'] == 'CLOTURE']
                intentions = [e for e in enregistrements if e['type'] == 'INTENTION']
                self.assertEqual(len(clotures), len(bougies))
                self.assertGreaterEqual(len(clotures), CONFIGURATION['common']['warmup_closed_m15_bars'])
                self.assertTrue(intentions, 'S3 doit produire au moins un vrai signal London après préchargement')
                self.assertEqual(len(intentions), sum(e['signal'] is not None for e in clotures))
                self.assertEqual(len(lignes), len(clotures)+len(intentions))
                self.assertTrue(all(e['issue']['nature'] == 'REFUSEE' and e['motif'] == 'ENVIRONMENT_NOT_READY'
                                    and e['detail'] == 'SEGMENT_MINIMAL_S4' for e in intentions))
                self.assertEqual([e['numero'] for e in enregistrements], list(range(1, len(lignes)+1)))
                debut, fin = bornes_journee_londres(jour)
                self.assertEqual(sum(debut <= e['bougie']['debut_utc_ms'] < fin for e in clotures),
                                 (fin-debut)//DUREE_MS)
                for ligne, enregistrement in zip(lignes, enregistrements):
                    self.assertEqual(json.dumps(enregistrement, ensure_ascii=False, sort_keys=True,
                                                separators=(',', ':')), ligne)
                self.assertEqual(clotures[0]['bougie']['debut_utc_ms'], bougies[0].debut_ms)
                for voulue, enregistrement in zip(bougies, clotures):
                    bougie = enregistrement['bougie']
                    self.assertEqual((bougie['debut_utc_ms'], bougie['fin_utc_ms']),
                                     (voulue.debut_ms, voulue.debut_ms + DUREE_MS))
                    self.assertEqual(enregistrement['instant_utc_ms'], voulue.debut_ms + DUREE_MS,
                                     'clôture par le tick de frontière')
                    self.assertEqual((bougie['ouverture'], bougie['haut'], bougie['bas'], bougie['cloture']),
                                     tuple(float(v) for v in (voulue.ouverture, voulue.haut, voulue.bas,
                                                              voulue.cloture)))
                    self.assertEqual((enregistrement['type'], enregistrement['version_schema'], enregistrement['mode'],
                                      enregistrement['bras'], enregistrement['symbole'], enregistrement['strategie']),
                                     ('CLOTURE', 'xp-journal-v1', 'REJEU', 'REFERENCE', 'EURUSD',
                                      CONFIGURATION['london']['strategy_id']))
                    self.assertEqual(enregistrement['empreinte_regles'], EMPREINTES)
                    if enregistrement['signal'] is None:
                        self.assertIn(enregistrement['motif'], motifs_admis())
                        self.assertNotEqual(enregistrement['detail'], 'SEGMENT_MINIMAL_S3')
                    else:
                        self.assertEqual((enregistrement['motif'], enregistrement['detail']), (None, None))
                        self.assertEqual(enregistrement['signal']['multiple_objectif'],
                                         CONFIGURATION['london']['take_profit_gross_price_r'])
                        for cle in ('range_haut', 'range_bas', 'largeur_range', 'atr_h1',
                                    'rapport_range_atr_h1', 'gel_disponible_ms', 'fraction_corps',
                                    'fraction_cloture', 'composantes_stop'):
                            self.assertIn(cle, enregistrement['contexte'])


if __name__ == '__main__':
    unittest.main()

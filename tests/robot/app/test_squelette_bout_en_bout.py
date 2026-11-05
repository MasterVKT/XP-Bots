"""Squelette de bout en bout : fixture → M15 → stratégie neutre → refus → exécution papier → journal C09."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from robot.fixtures import generateur_ticks
from robot.outils import FIXTURE_MANIFESTE, FIXTURE_TICKS, FIXTURES, RACINE, SRC
from xpbots.app.rejeu import SEGMENTS_MINIMAUX, executer_rejeu, main
from xpbots.noyau.journal_schema import valider_enregistrement
from xpbots.noyau.temps import ms_depuis_iso

H09 = generateur_ticks.DEBUT_MS + 3_600_000  # 09:00:00.000 UTC


def lire(chemin):
    return [json.loads(ligne) for ligne in Path(chemin).read_text(encoding='utf-8').splitlines()]


def jusqua(lignes, limite_ms):
    return [l for l in lignes if l['type'] != 'INITIALISATION' and ms_depuis_iso(l['instant_utc']) <= limite_ms]


class TestSqueletteBoutEnBout(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dossier = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def rejouer(self, nom='journal.jsonl', ticks=FIXTURE_TICKS, manifeste=FIXTURE_MANIFESTE, **options):
        chemin = self.dossier / nom
        return executer_rejeu(ticks, manifeste, chemin, **options), chemin

    def test_journal_complet_et_conforme(self):
        resume, chemin = self.rejouer()
        self.assertEqual(resume, {'ticks': 933, 'enregistrements': 20, 'clotures': {'DATA_GAP': 2, 'WARMUP': 14},
                                  'intentions': {}, 'donnees': {'REINITIALISATION': 1, 'TROU': 2}})
        lignes = lire(chemin)
        self.assertEqual([l['sequence'] for l in lignes], list(range(1, 21)))
        self.assertTrue(all(valider_enregistrement(l) == [] for l in lignes))
        self.assertEqual(lignes[0]['type'], 'INITIALISATION')
        self.assertEqual(lignes[0]['segments_minimaux'], list(SEGMENTS_MINIMAUX))
        cles = [(ms_depuis_iso(l['instant_utc']), ['EURUSD', 'GBPUSD'].index(l['symbole'])) for l in lignes[1:]]
        self.assertEqual(cles, sorted(cles))
        clotures = [l for l in lignes if l['type'] == 'CLOTURE_BOUGIE']
        trous = [(l['symbole'], l['cloture_utc']) for l in clotures if l['motif'] == 'DATA_GAP']
        self.assertEqual(trous, [('GBPUSD', '2026-11-04T08:45:00.000Z'), ('GBPUSD', '2026-11-04T09:00:00.000Z')])
        self.assertTrue(all(l['valide'] is (l['motif'] == 'WARMUP') for l in clotures))
        self.assertTrue(all(l['jour_londres'] == '2026-11-04' and 'tr' in l['indicateurs'] or l['motif'] == 'DATA_GAP'
                            for l in clotures))
        donnees = [(l['evenement'], l['debut_utc'], l['details']['motif']) for l in lignes if l['type'] == 'DONNEES']
        self.assertEqual(donnees, [('TROU', '2026-11-04T08:30:00.000Z', 'COUVERTURE'),
                                   ('TROU', '2026-11-04T08:45:00.000Z', 'COUVERTURE'),
                                   ('REINITIALISATION', '2026-11-04T08:30:00.000Z', 'RECUPERATION_INDISPONIBLE')])

    def test_rejeu_deterministe_octet_pour_octet(self):
        _, premier = self.rejouer('a.jsonl')
        _, second = self.rejouer('b.jsonl')
        self.assertEqual(premier.read_bytes(), second.read_bytes())

    def test_point_d_entree_module(self):
        _, attendu = self.rejouer('fonction.jsonl')
        sortie = self.dossier / 'cli.jsonl'
        env = dict(os.environ, PYTHONPATH=str(SRC), PYTHONDONTWRITEBYTECODE='1')
        commande = [sys.executable, '-m', 'xpbots.app.rejeu', '--ticks', str(FIXTURE_TICKS), '--manifeste',
                    str(FIXTURE_MANIFESTE), '--journal', str(sortie)]
        resultat = subprocess.run(commande, cwd=RACINE, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertEqual(json.loads(resultat.stdout)['clotures'], {'DATA_GAP': 2, 'WARMUP': 14})
        self.assertEqual(sortie.read_bytes(), attendu.read_bytes())
        repetition = subprocess.run(commande, cwd=RACINE, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(repetition.returncode, 2)  # un journal existant n'est jamais écrasé
        self.assertIn('existe déjà', repetition.stderr)

    def test_main_erreur_de_donnees(self):
        absent = self.dossier / 'absent.json'
        erreurs = io.StringIO()
        with contextlib.redirect_stderr(erreurs):
            code = main(['--ticks', str(FIXTURE_TICKS), '--manifeste', str(absent),
                         '--journal', str(self.dossier / 'x.jsonl')])
        self.assertEqual(code, 2)
        self.assertIn('absent.json', erreurs.getvalue())
        self.assertFalse((self.dossier / 'x.jsonl').exists())

    def test_fixture_regeneree_a_l_identique(self):
        ticks, manifeste = generateur_ticks.ecrire(self.dossier / 'regen')
        self.assertEqual(ticks.read_bytes(), (FIXTURES / generateur_ticks.NOM_TICKS).read_bytes())
        self.assertEqual(manifeste.read_bytes(), (FIXTURES / generateur_ticks.NOM_MANIFESTE).read_bytes())

    def _fixture_derivee(self, transformer, fin_ms=None):
        lignes = FIXTURE_TICKS.read_text(encoding='utf-8').splitlines()
        entete, corps = lignes[0], [transformer(l.split(',')) for l in lignes[1:]]
        ticks = self.dossier / 'derive.csv'
        ticks.write_text('\n'.join([entete] + [','.join(c) for c in corps if c]) + '\n', encoding='utf-8')
        manifeste = json.loads(FIXTURE_MANIFESTE.read_text(encoding='utf-8'))
        if fin_ms is not None:
            manifeste['fin_donnees_ms'] = fin_ms
            for decl in manifeste['symboles'].values():
                for cle in ('couverture', 'seances'):
                    decl[cle] = [[a, min(b, fin_ms)] for a, b in decl[cle] if a < fin_ms]
        chemin_manifeste = self.dossier / 'derive.json'
        chemin_manifeste.write_text(json.dumps(manifeste), encoding='utf-8')
        return ticks, chemin_manifeste

    def test_causalite_ticks_futurs_retires(self):
        # C11.1 sur le squelette : retirer les ticks postérieurs à 09:00 ne change aucune clôture antérieure.
        _, complet = self.rejouer('complet.jsonl')
        ticks, manifeste = self._fixture_derivee(lambda c: c if int(c[2]) < H09 else None, fin_ms=H09)
        _, prefixe = self.rejouer('prefixe.jsonl', ticks, manifeste)
        attendu = jusqua(lire(complet), H09)
        self.assertEqual(len(attendu), 11)  # 8 clôtures, 2 trous et la réinitialisation GBPUSD de 09:00
        self.assertEqual(jusqua(lire(prefixe), H09), attendu)

    def test_causalite_ticks_futurs_modifies(self):
        _, complet = self.rejouer('complet.jsonl')

        def decaler(c):
            if int(c[2]) >= H09:
                c[4], c[5] = '2.00000', '2.00010'
            return c

        ticks, manifeste = self._fixture_derivee(decaler)
        _, modifie = self.rejouer('modifie.jsonl', ticks, manifeste)
        self.assertEqual(jusqua(lire(modifie), H09), jusqua(lire(complet), H09))
        self.assertNotEqual(lire(modifie)[-1]['ohlc'], lire(complet)[-1]['ohlc'])


if __name__ == '__main__':
    unittest.main()

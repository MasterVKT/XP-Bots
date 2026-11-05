"""Règles transverses du plan maître (section 4.2) vérifiées sur tout `src/` : aucune valeur normative
recopiée, aucune horloge ni bibliothèque de frontière hors infrastructure, lanceur de tests fiable."""
import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path

from robot.outils import RACINE, SRC

# Valeurs autorisées malgré une égalité fortuite avec une valeur de config/, avec leur justification.
NOMBRES_AUTORISES = {
    0: 'neutre arithmétique', 1: 'unité, départ de numérotation', -1: 'sens de vente',
}
NOMBRES_AUTORISES_PAR_FICHIER = {
    ('noyau/temps.py', 1000): 'conversions d\'unités ms/s et µs/ms, seules constantes temporelles du code',
    ('app/rejeu.py', 2): 'code de sortie d\'usage invalide (convention argparse)',
}
TEXTES_AUTORISES = {
    'PAPER': 'nom du mode (code) ; la valeur par défaut reste lue dans common.default_mode',
    'UTC': 'fuseau déclaré par un manifeste de fixture',
}
APPELS_D_HORLOGE = {('datetime', 'now'), ('datetime', 'utcnow'), ('datetime', 'today'), ('date', 'today'),
                    ('time', 'time'), ('time', 'time_ns'), ('time', 'monotonic'), ('time', 'monotonic_ns'),
                    ('time', 'perf_counter'), ('time', 'perf_counter_ns')}
BIBLIOTHEQUES_DE_FRONTIERE = {'MetaTrader5', 'sqlite3', 'urllib', 'http', 'ssl', 'socket', 'time'}
INFRASTRUCTURE = SRC / 'xpbots' / 'infrastructure'


def feuilles(valeur):
    if isinstance(valeur, dict):
        for element in valeur.values():
            yield from feuilles(element)
    elif isinstance(valeur, list):
        for element in valeur:
            yield from feuilles(element)
    else:
        yield valeur


def valeurs_normatives():
    nombres, textes = set(), set()
    for nom in ('parametres_figes_v3.json', 'parametres_IA_integration_v1.json'):
        for valeur in feuilles(json.loads((RACINE / 'config' / nom).read_text(encoding='utf-8'))):
            if type(valeur) in (int, float):
                nombres.add(valeur)
            elif type(valeur) is str:
                textes.add(valeur)
    return nombres, textes


def fichiers_source():
    return sorted(p for p in (SRC / 'xpbots').rglob('*.py') if '__pycache__' not in p.parts)


class TestReglesTransverses(unittest.TestCase):
    def test_aucune_valeur_normative_recopiee(self):
        nombres, textes = valeurs_normatives()
        violations = []
        for chemin in fichiers_source():
            relatif = chemin.relative_to(SRC / 'xpbots').as_posix()
            for noeud in ast.walk(ast.parse(chemin.read_text(encoding='utf-8'))):
                if not isinstance(noeud, ast.Constant) or type(noeud.value) is bool:
                    continue
                v = noeud.value
                if type(v) in (int, float) and v in nombres and v not in NOMBRES_AUTORISES \
                        and (relatif, v) not in NOMBRES_AUTORISES_PAR_FICHIER:
                    violations.append(f'{relatif}:{noeud.lineno} nombre {v!r}')
                if type(v) is str and v in textes and v not in TEXTES_AUTORISES:
                    violations.append(f'{relatif}:{noeud.lineno} texte {v!r}')
        self.assertEqual(violations, [], 'valeurs de config/ recopiées dans le code')

    def test_aucune_horloge_hors_infrastructure(self):
        violations = []
        for chemin in fichiers_source():
            if INFRASTRUCTURE / 'horloge' in chemin.parents:
                continue
            for noeud in ast.walk(ast.parse(chemin.read_text(encoding='utf-8'))):
                if isinstance(noeud, ast.Attribute):
                    base = noeud.value.attr if isinstance(noeud.value, ast.Attribute) else getattr(noeud.value, 'id', None)
                    if (base, noeud.attr) in APPELS_D_HORLOGE:
                        violations.append(f'{chemin.relative_to(RACINE)}:{noeud.lineno} {base}.{noeud.attr}')
        self.assertEqual(violations, [])

    def test_bibliotheques_de_frontiere_confinees_a_l_infrastructure(self):
        violations = []
        for chemin in fichiers_source():
            if INFRASTRUCTURE in chemin.parents:
                continue
            for noeud in ast.walk(ast.parse(chemin.read_text(encoding='utf-8'))):
                noms = []
                if isinstance(noeud, ast.Import):
                    noms = [alias.name for alias in noeud.names]
                elif isinstance(noeud, ast.ImportFrom) and noeud.level == 0:
                    noms = [noeud.module or '']
                for nom in noms:
                    if nom.split('.')[0] in BIBLIOTHEQUES_DE_FRONTIERE:
                        violations.append(f'{chemin.relative_to(RACINE)}:{noeud.lineno} import {nom}')
        self.assertEqual(violations, [])


class TestLanceur(unittest.TestCase):
    def lancer(self, *arguments):
        return subprocess.run([sys.executable, str(RACINE / 'tools' / 'run_robot_tests.py'), *arguments],
                              cwd=RACINE, capture_output=True, text=True, timeout=120)

    def test_filtre_sans_test_signale_par_le_code_5(self):
        resultat = self.lancer('--artefact', 'noyau', '--couche', '9z', '--categorie', '1')
        self.assertEqual(resultat.returncode, 5, resultat.stderr)

    def test_artefact_inconnu(self):
        self.assertEqual(self.lancer('--artefact', 'inexistant').returncode, 2)

    def test_motif_des_fichiers(self):
        sys.path.insert(0, str(RACINE / 'tools'))
        try:
            from run_robot_tests import motif_fichiers
        finally:
            sys.path.remove(str(RACINE / 'tools'))
        self.assertEqual(motif_fichiers(None, None), 'test_*.py')
        self.assertEqual(motif_fichiers('2', '1'), 'test_c2_cat1_*.py')
        self.assertEqual(motif_fichiers('1a', None), 'test_c1a_cat*_*.py')
        self.assertEqual(motif_fichiers(None, '2'), 'test_c*_cat2_*.py')


if __name__ == '__main__':
    unittest.main()

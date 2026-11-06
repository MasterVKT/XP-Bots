"""Lanceur des tests du robot London XP-Bots (bibliothèque standard, `unittest`).

Le robot 1 a son propre lanceur, `tools/run_robot_tests.py` (convention de nommage `test_c<couche>_cat<k>_*.py`, code 5 pour une
sélection vide) ; les deux lanceurs découvrent la suite intégrale sous `tests/robot/`. Celui-ci suit la convention du London
(`test_cat<k>_c<couche>_<thème>.py`, code 1 pour une sélection vide).

Usage (depuis n'importe quel dossier) :
    python tools/run_london_tests.py [--artefact NOM] [--couche ID] [--categorie 1|2]
                                    [--racine-tests DOSSIER] [--rapport FICHIER] [--verbeux]

Le lanceur ajoute `src/` et la racine du dépôt au chemin d'import, découvre les fichiers `test_*.py` sous
`tests/robot/` (ou sous `--racine-tests`, qui sert au test du lanceur lui-même), puis exécute la sélection :
- `--artefact` restreint au dossier de l'artefact (`london-donnees-temps` → `tests/robot/london_donnees_temps/`) ;
- `--couche` et `--categorie` ne retiennent que les fichiers `test_cat<1|2>_c<couche>_<theme>.py`
  (document 03, §2) ; `--couche` exige `--artefact`.
Il écrit un résumé JSON (par défaut `.local/reports/robot_tests.json`, ignoré par Git) et rend 0 si tous les
tests sélectionnés passent, 1 en cas d'échec, d'erreur, de fichier non importable ou de sélection vide, 2 en cas
d'usage invalide.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
RACINE_TESTS = ROOT / 'tests' / 'robot'
RAPPORT = ROOT / '.local' / 'reports' / 'robot_tests.json'
FICHIER_CATEGORISE = re.compile(r'^test_cat(?P<categorie>[12])_c(?P<couche>\d+[a-z]?)_[a-z0-9_]+\.py$')


def _aplatir(suite: unittest.TestSuite):
    for element in suite:
        if isinstance(element, unittest.TestSuite):
            yield from _aplatir(element)
        else:
            yield element


def _fichier_du_test(test: unittest.TestCase) -> str | None:
    module = sys.modules.get(type(test).__module__)
    chemin = getattr(module, '__file__', None)
    return Path(chemin).name if chemin else None


def _retenu(test: unittest.TestCase, couche: str | None, categorie: str | None) -> bool:
    if couche is None and categorie is None:
        return True
    if type(test).__module__ == 'unittest.loader':
        return True  # fichier non importable : toujours signalé comme erreur
    nom = _fichier_du_test(test)
    trouve = FICHIER_CATEGORISE.match(nom or '')
    if not trouve:
        return False
    return ((couche is None or trouve['couche'] == couche)
            and (categorie is None or trouve['categorie'] == categorie))


def _ecrire_rapport(chemin: Path, rapport: dict) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(rapport, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(prog='python tools/run_london_tests.py',
                                        description='Exécute les tests du robot XP-Bots.')
    analyseur.add_argument('--artefact', help='nom de l\'artefact MCL, par exemple london-donnees-temps')
    analyseur.add_argument('--couche', help='identifiant de couche, par exemple 0a (exige --artefact)')
    analyseur.add_argument('--categorie', choices=('1', '2'), help='catégorie de tests MCL')
    analyseur.add_argument('--racine-tests', help='dossier racine des tests (paquet Python)')
    analyseur.add_argument('--rapport', help='chemin du résumé JSON')
    analyseur.add_argument('--verbeux', action='store_true', help='afficher chaque test')
    arguments = analyseur.parse_args(argv)
    if arguments.couche and not arguments.artefact:
        analyseur.error('--couche exige --artefact')
    if arguments.couche and not re.fullmatch(r'\d+[a-z]?', arguments.couche):
        analyseur.error('--couche attend un identifiant comme 0, 1a ou 2b')

    racine = Path(arguments.racine_tests).resolve() if arguments.racine_tests else RACINE_TESTS
    if not (racine / '__init__.py').is_file():
        analyseur.error(f'racine de tests sans __init__.py : {racine}')
    depart = racine
    if arguments.artefact:
        depart = racine / arguments.artefact.replace('-', '_')
        if not (depart / '__init__.py').is_file():
            analyseur.error(f'aucun dossier de tests pour l\'artefact : {depart}')
    rapport_chemin = Path(arguments.rapport).resolve() if arguments.rapport else RAPPORT

    sys.dont_write_bytecode = True
    for chemin in (ROOT, ROOT / 'src'):
        if str(chemin) not in sys.path:
            sys.path.insert(0, str(chemin))
    suite = unittest.TestLoader().discover(str(depart), pattern='test_*.py', top_level_dir=str(racine.parent))
    tests = [test for test in _aplatir(suite) if _retenu(test, arguments.couche, arguments.categorie)]
    selection = {'artefact': arguments.artefact, 'couche': arguments.couche, 'categorie': arguments.categorie,
                 'racine': str(racine)}
    if not tests:
        rapport = {'statut': 'ECHEC', 'motif': 'aucun test sélectionné', 'selection': selection,
                   'tests': 0, 'echecs': 0, 'erreurs': 0, 'ignores': 0}
        _ecrire_rapport(rapport_chemin, rapport)
        print(json.dumps(rapport, ensure_ascii=False, sort_keys=True))
        return 1

    debut = time.monotonic()
    resultat = unittest.TextTestRunner(verbosity=2 if arguments.verbeux else 1, stream=sys.stderr).run(
        unittest.TestSuite(tests))
    rapport = {
        'statut': 'PASS' if resultat.wasSuccessful() else 'ECHEC',
        'selection': selection,
        'tests': resultat.testsRun,
        'echecs': len(resultat.failures),
        'erreurs': len(resultat.errors),
        'ignores': len(resultat.skipped),
        'succes_inattendus': len(resultat.unexpectedSuccesses),
        'duree_s': round(time.monotonic() - debut, 3),
        'en_defaut': sorted(test.id() for test, _ in resultat.failures + resultat.errors),
    }
    _ecrire_rapport(rapport_chemin, rapport)
    print(json.dumps({cle: rapport[cle] for cle in ('statut', 'tests', 'echecs', 'erreurs', 'ignores')}
                     | {'rapport': str(rapport_chemin)}, ensure_ascii=False, sort_keys=True))
    return 0 if resultat.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())

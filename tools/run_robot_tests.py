"""Lanceur de la suite du robot (unittest, bibliothèque standard) ; aucun ordre ni appel réseau.

Exemples : `python tools/run_robot_tests.py` (suite intégrale) ;
`python tools/run_robot_tests.py --artefact moteur_ema --couche 2 --categorie 1` (gate MCL d'une couche).
Codes de sortie : 0 succès, 1 échec, 2 usage invalide, 5 aucun test ne correspond au filtre.
"""
from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_TESTS = RACINE / 'tests'
SUITE_ROBOT = DOSSIER_TESTS / 'robot'
AUCUN_TEST = 5


def motif_fichiers(couche: str | None, categorie: str | None) -> str:
    """Motif des fichiers de test : `test_c<couche>_cat<catégorie>_*.py`, ou tous les `test_*.py`."""
    if couche is None and categorie is None:
        return 'test_*.py'
    return f"test_c{couche or '*'}_cat{categorie or '*'}_*.py"


def main(argv=None) -> int:
    parseur = argparse.ArgumentParser(description='Suite de tests du robot XP-Bots.')
    parseur.add_argument('--artefact', help='paquet testé, par exemple moteur_ema (dossier tests/robot/<paquet>)')
    parseur.add_argument('--couche', help='identifiant MCL de la couche, par exemple 0, 1a, 2')
    parseur.add_argument('--categorie', choices=['1', '2'], help='catégorie MCL : 1 contrat propre, 2 jonction')
    parseur.add_argument('-v', '--verbeux', action='store_true')
    args = parseur.parse_args(argv)

    sys.dont_write_bytecode = True  # l'arbre reste propre : l'empreinte des gates MCL ne bouge pas
    for chemin in (RACINE, DOSSIER_TESTS, RACINE / 'src'):
        if str(chemin) not in sys.path:
            sys.path.insert(0, str(chemin))
    depart = SUITE_ROBOT / args.artefact if args.artefact else SUITE_ROBOT
    if not depart.is_dir():
        print(f'dossier de tests introuvable : {depart.relative_to(RACINE)}', file=sys.stderr)
        return 2
    suite = unittest.defaultTestLoader.discover(str(depart), pattern=motif_fichiers(args.couche, args.categorie),
                                                top_level_dir=str(DOSSIER_TESTS))
    if suite.countTestCases() == 0:
        print('aucun test ne correspond au filtre', file=sys.stderr)
        return AUCUN_TEST
    resultat = unittest.TextTestRunner(verbosity=2 if args.verbeux else 1).run(suite)
    return 0 if resultat.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())

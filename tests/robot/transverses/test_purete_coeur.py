"""Garde de pureté du cœur (document 03, §8 ; document 01, principe 2 ; A03).

Le test parcourt les paquets du cœur et refuse, par analyse de l'arbre syntaxique : les modules d'horloge, de
fichiers, de réseau, de base de données, de fils d'exécution, de processus, `MetaTrader5`, `reference` et le
chargement dynamique de modules ; les appels `open`, `__import__`, `datetime.now`, `datetime.utcnow`,
`date.today` et équivalents ; la lecture ou l'écriture de fichiers par `pathlib`. Le hasard (`random`) n'est
admis que dans `journal-rejeu` (bootstrap, document 02, §8). Ce contrôle complète la carte MCL : il couvre aussi
un fichier qui n'appartiendrait à aucune couche. Des cas négatifs prouvent que chaque règle détecte sa violation.
"""
import ast
import unittest

from robot.outils.chemins import SOURCES

PAQUETS_COEUR = ('noyau', 'donnees', 'london', 'london_v1', 'execution', 'fondamental', 'contexte_ia',
                 'orchestration', 'rejeu')
PAQUETS_AVEC_HASARD = ('rejeu',)
MODULES_INTERDITS = frozenset({'time', 'os', 'pathlib', 'io', 'shutil', 'tempfile', 'glob', 'gzip', 'socket',
                               'ssl', 'http', 'urllib', 'sqlite3', 'threading', 'concurrent', 'queue',
                               'subprocess', 'multiprocessing', 'importlib', 'MetaTrader5', 'reference'})
MODULES_HASARD = frozenset({'random', 'secrets'})
APPELS_HORLOGE = frozenset({'now', 'utcnow', 'today'})
APPELS_FICHIERS = frozenset({'read_text', 'read_bytes', 'write_text', 'write_bytes'})


def violations(source: str, chemin: str, hasard_admis: bool) -> list[str]:
    """Liste des violations de pureté d'un fichier source."""
    interdits = MODULES_INTERDITS if hasard_admis else MODULES_INTERDITS | MODULES_HASARD
    trouvees = []
    for noeud in ast.walk(ast.parse(source, filename=chemin)):
        if isinstance(noeud, ast.Import):
            modules = [alias.name for alias in noeud.names]
        elif isinstance(noeud, ast.ImportFrom):
            modules = [noeud.module or ''] if noeud.level == 0 else []
        else:
            modules = []
        for module in modules:
            if module.split('.')[0] in interdits:
                trouvees.append(f'{chemin}:{noeud.lineno} import interdit {module}')
        if isinstance(noeud, ast.Call):
            fonction = noeud.func
            if isinstance(fonction, ast.Name) and fonction.id in ('open', '__import__'):
                trouvees.append(f'{chemin}:{noeud.lineno} appel interdit {fonction.id}()')
            elif isinstance(fonction, ast.Attribute) and fonction.attr in APPELS_HORLOGE | APPELS_FICHIERS:
                trouvees.append(f'{chemin}:{noeud.lineno} appel interdit .{fonction.attr}()')
    return trouvees


class TestPureteDuCoeur(unittest.TestCase):
    def test_paquets_du_coeur(self):
        fichiers = [(paquet, chemin) for paquet in PAQUETS_COEUR
                    for chemin in sorted((SOURCES / 'xpbots' / paquet).rglob('*.py'))]
        self.assertTrue(fichiers, 'aucun fichier du cœur trouvé')
        trouvees = [v for paquet, chemin in fichiers
                    for v in violations(chemin.read_text(encoding='utf-8'), str(chemin.relative_to(SOURCES)),
                                        paquet in PAQUETS_AVEC_HASARD)]
        self.assertEqual(trouvees, [])

    def test_chaque_regle_detecte_sa_violation(self):
        cas = {
            'horloge importée': 'import time',
            'horloge par from': 'from time import monotonic',
            'fichiers': 'import os.path',
            'pathlib': 'from pathlib import Path',
            'réseau': 'import urllib.request',
            'base': 'import sqlite3',
            'fils': 'import threading',
            'processus': 'import subprocess',
            'plateforme': 'import MetaTrader5',
            'oracle': 'from reference.technical import wilder',
            'chargement dynamique': 'import importlib',
            'appel open': 'open("x")',
            'appel __import__': '__import__("time")',
            'datetime.now': 'import datetime\ndatetime.datetime.now()',
            'utcnow': 'from datetime import datetime\ndatetime.utcnow()',
            'date.today': 'from datetime import date\ndate.today()',
            'lecture pathlib': 'chemin.read_text()',
            'écriture pathlib': 'chemin.write_bytes(b"")',
            'hasard hors rejeu': 'import random',
        }
        for nom, source in cas.items():
            with self.subTest(cas=nom):
                self.assertTrue(violations(source, nom, hasard_admis=False), nom)
        self.assertEqual(violations('import random', 'rejeu', hasard_admis=True), [])
        self.assertEqual(violations('from datetime import datetime, timezone\nfrom decimal import Decimal\n'
                                    'import json, math\nfrom .voisin import x\n', 'sain', False), [])


if __name__ == '__main__':
    unittest.main()

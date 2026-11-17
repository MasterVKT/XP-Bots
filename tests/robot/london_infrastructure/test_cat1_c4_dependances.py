"""Les dépendances de poste respectent les versions et le marqueur Windows."""
from pathlib import Path
import unittest
from robot.outils import RACINE


def versions(texte):
    resultat={}
    for ligne in texte.splitlines():
        ligne=ligne.split('#',1)[0].strip()
        if not ligne:continue
        nom,version=ligne.split('==',1)
        paquet,_,marqueur=version.partition(';')
        resultat[nom.strip().lower()]=(paquet.strip(),marqueur.strip())
    return resultat


class TestDependancesPoste(unittest.TestCase):
    def test_versions_numpy_tzdata_identiques_et_sdk_limite_windows(self):
        dev=versions((RACINE/'requirements-dev.txt').read_text(encoding='utf-8'))
        poste=versions((RACINE/'requirements-windows.txt').read_text(encoding='utf-8'))
        for paquet in ('numpy','tzdata'):
            self.assertEqual(poste[paquet],dev[paquet])
        self.assertEqual(poste['metatrader5'],('5.0.6231','sys_platform == "win32"'))

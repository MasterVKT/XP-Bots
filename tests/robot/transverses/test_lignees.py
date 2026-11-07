"""Garde de coexistence des deux lignées de construction (robot 1 EMA_V3, robot London) : voir
docs/architecture/COEXISTENCE_ROBOT1_LONDON.md.

Trois contrôles : aucun fichier n'est déclaré propriétaire des deux lignées ; le code du London n'importe aucun module du
robot 1 ; le code du robot 1 n'importe aucun module du London. Les modules partagés (`xpbots`, `xpbots.app`, `xpbots.noyau`
pour leurs `__init__.py`) ne portent aucune logique et ne sont pas concernés. Des cas négatifs prouvent la détection.
"""
import ast
from pathlib import Path
import unittest

from robot.outils.chemins import RACINE_DEPOT, SOURCES
from robot.outils.lignees import COMMUN, LONDON, ROBOT1, appartient

# Modules (préfixes de noms pointés) propres à chaque lignée, miroir des registres de `robot.outils.lignees`.
MODULES_ROBOT1 = ('xpbots.donnees_temps', 'xpbots.moteur_ema', 'xpbots.noyau.config', 'xpbots.noyau.decisions',
                  'xpbots.noyau.journal_schema', 'xpbots.noyau.json_canonique', 'xpbots.noyau.marche',
                  'xpbots.noyau.ports', 'xpbots.noyau.temps', 'xpbots.app.rejeu', 'xpbots.app.segments_minimaux')
MODULES_LONDON = ('xpbots.donnees', 'xpbots.london', 'xpbots.orchestration', 'xpbots.rejeu', 'xpbots.infra',
                  'xpbots.execution.squelette', 'xpbots.app.rejeu_squelette')
SOUS_PAQUETS_NOYAU_LONDON = ('c0a_temps', 'c0b_nombres', 'c0c_configuration', 'c1a_marche', 'c1b_instrument',
                             'c1c_domaine', 'c2_journal')


def _est_sous(nom: str, prefixes) -> bool:
    return any(nom == p or nom.startswith(p + '.') for p in prefixes)


def modules_importes(source: str) -> set[str]:
    """Noms pointés absolus importés par un fichier (`from a import b` compte `a` et `a.b`)."""
    noms = set()
    for noeud in ast.walk(ast.parse(source)):
        if isinstance(noeud, ast.Import):
            noms.update(alias.name for alias in noeud.names)
        elif isinstance(noeud, ast.ImportFrom) and noeud.level == 0 and noeud.module:
            noms.add(noeud.module)
            noms.update(f'{noeud.module}.{alias.name}' for alias in noeud.names)
    return noms


def importe_la_lignee(source: str, lignee_interdite: str) -> list[str]:
    """Imports du fichier qui visent l'autre lignée (`robot1` ou `london`)."""
    interdits = {'robot1': MODULES_ROBOT1,
                 'london': MODULES_LONDON + tuple(f'xpbots.noyau.{s}' for s in SOUS_PAQUETS_NOYAU_LONDON)}[lignee_interdite]
    return sorted(nom for nom in modules_importes(source) if _est_sous(nom, interdits))


def fichiers(registre) -> list[Path]:
    return sorted(p for p in (SOURCES / 'xpbots').rglob('*.py')
                  if '__pycache__' not in p.parts and appartient(p.relative_to(RACINE_DEPOT).as_posix(), registre))


class TestLignees(unittest.TestCase):
    def test_aucun_fichier_dans_les_deux_registres(self):
        communs = [p.relative_to(RACINE_DEPOT).as_posix() for p in fichiers(ROBOT1) if p in set(fichiers(LONDON))]
        communs += [p.relative_to(RACINE_DEPOT).as_posix() for p in fichiers(COMMUN)
                    if p in set(fichiers(ROBOT1)) | set(fichiers(LONDON))]
        self.assertEqual(communs, [])

    def test_coordinateur_commun_adaptateurs_bornes(self):
        partages = fichiers(COMMUN)
        self.assertTrue(partages)
        trouves=[]
        for p in partages:
            # R4/R5 : les importations de types EMA sont limitées à la frontière commune 0a.
            if p.parent.name == 'c0a_types':
                continue
            trouves += importe_la_lignee(p.read_text(encoding='utf-8'),'robot1')
        self.assertEqual(trouves,[])

    def test_les_deux_registres_ne_sont_pas_vides(self):
        self.assertTrue(fichiers(ROBOT1))
        self.assertTrue(fichiers(LONDON))

    def test_le_london_n_importe_rien_du_robot_1(self):
        trouvees = [f'{p.relative_to(RACINE_DEPOT)} -> {nom}' for p in fichiers(LONDON)
                    for nom in importe_la_lignee(p.read_text(encoding='utf-8'), 'robot1')]
        self.assertEqual(trouvees, [])

    def test_le_robot_1_n_importe_rien_du_london(self):
        trouvees = [f'{p.relative_to(RACINE_DEPOT)} -> {nom}' for p in fichiers(ROBOT1)
                    for nom in importe_la_lignee(p.read_text(encoding='utf-8'), 'london')]
        self.assertEqual(trouvees, [])

    def test_cas_negatifs(self):
        self.assertEqual(importe_la_lignee('from xpbots.noyau import temps', 'robot1'), ['xpbots.noyau.temps'])
        self.assertEqual(importe_la_lignee('import xpbots.moteur_ema.c3_moteur', 'robot1'),
                         ['xpbots.moteur_ema.c3_moteur'])
        self.assertEqual(importe_la_lignee('from xpbots.noyau.c0a_temps import Instant', 'london'),
                         ['xpbots.noyau.c0a_temps', 'xpbots.noyau.c0a_temps.Instant'])
        self.assertEqual(importe_la_lignee('from xpbots.donnees import c3_flux', 'london'),
                         ['xpbots.donnees', 'xpbots.donnees.c3_flux'])
        self.assertEqual(importe_la_lignee('import decimal\nfrom xpbots.noyau import decisions', 'london'), [])


if __name__ == '__main__':
    unittest.main()

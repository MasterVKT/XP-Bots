"""Chemins du dépôt utilisés par les tests du robot."""
from pathlib import Path

RACINE_DEPOT = Path(__file__).resolve().parents[3]
SOURCES = RACINE_DEPOT / 'src'
CONFIGURATION_TECHNIQUE = RACINE_DEPOT / 'config' / 'parametres_figes_v3.json'
SPECIFICATION_LONDON = (RACINE_DEPOT / 'livrables' / 'strategies_m15'
                        / '02_London_Breakout_M15_Specification_IA.md')
OUTIL_MCL = RACINE_DEPOT / '.agents' / 'skills' / 'mcl-matryoshka-construction-layers' / 'scripts' / 'mcl.py'
LANCEUR = RACINE_DEPOT / 'tools' / 'run_robot_tests.py'

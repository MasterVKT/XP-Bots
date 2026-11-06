"""Chemins du dépôt utilisés par les tests du robot."""
from pathlib import Path

RACINE_DEPOT = Path(__file__).resolve().parents[3]
SOURCES = RACINE_DEPOT / 'src'
CONFIGURATION_TECHNIQUE = RACINE_DEPOT / 'config' / 'parametres_figes_v3.json'
CONFIGURATION_IA = RACINE_DEPOT / 'config' / 'parametres_IA_integration_v1.json'
PREUVE_CONSERVATION = RACINE_DEPOT / 'docs' / 'validation' / 'conservation_ressources.json'
DIAGNOSTIC_FAISABILITE = RACINE_DEPOT / 'docs' / 'validation' / 'diagnostic_faisabilite_v3.json'
DOCUMENT_ARCHITECTURE = RACINE_DEPOT / 'docs' / 'architecture' / 'robot_london_v3' / '01_architecture.md'
DOCUMENT_CONTRATS = RACINE_DEPOT / 'docs' / 'architecture' / 'robot_london_v3' / '08_contrats_frontieres.md'
SPECIFICATION_LONDON = (RACINE_DEPOT / 'livrables' / 'strategies_m15'
                        / '02_London_Breakout_M15_Specification_IA.md')
OUTIL_MCL = RACINE_DEPOT / '.agents' / 'skills' / 'mcl-matryoshka-construction-layers' / 'scripts' / 'mcl.py'
LANCEUR = RACINE_DEPOT / 'tools' / 'run_london_tests.py'

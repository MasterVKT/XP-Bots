"""Outils de test : fabriques synthétiques et doublures des seules frontières externes (robot London), et aides du squelette
du robot 1 réexportées ici pour que `from robot.outils import ...` reste valable (module `squelette_ema`)."""
from robot.outils.squelette_ema import (FIXTURE_MANIFESTE, FIXTURE_TICKS, FIXTURES, RACINE, SPECIFICATION_EMA, SRC,
                                        empreinte_bundle_de_la_specification, motifs_c09_de_la_specification,
                                        signal_valide, texte_specification)

__all__ = ['FIXTURE_MANIFESTE', 'FIXTURE_TICKS', 'FIXTURES', 'RACINE', 'SPECIFICATION_EMA', 'SRC',
           'empreinte_bundle_de_la_specification', 'motifs_c09_de_la_specification', 'signal_valide',
           'texte_specification']

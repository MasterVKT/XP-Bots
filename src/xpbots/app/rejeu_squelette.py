"""Segment minimal S7 du squelette : rejeu de bout en bout d'un fichier de ticks.

Segment minimal du squelette, remplacé en phase 11 par l'artefact `points-entree`. Contrat de la couture :
mcl/squelette/COUTURES.md. Point de composition : il lit la configuration figée et les ticks par
l'infrastructure, injecte la stratégie dans le moteur minimal (D-18), rejoue, puis écrit le journal.

Usage (depuis la racine du dépôt, `PYTHONPATH` désignant `src`) :
    python -m xpbots.app.rejeu_squelette --configuration config/parametres_figes_v3.json \
        --ticks <fichier.csv> --sortie <dossier>
Codes de sortie : 0 rejeu complet ; 1 donnée ou fichier refusé ; 2 usage invalide.
"""
from __future__ import annotations

import argparse
import json
import sys

from xpbots.infra.squelette import ecrire_journal, lire_lignes, lire_octets
from xpbots.london.squelette import fabriquer_strategie
from xpbots.noyau.squelette import ErreurDonnees, lire_configuration_squelette, serialiser_enregistrement
from xpbots.orchestration.squelette import fabriquer_moteur_minimal
from xpbots.rejeu.squelette import ExecutionPapierMinimale, analyser_lignes_ticks, rejouer

MODE_REJEU = 'REJEU'


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(prog='python -m xpbots.app.rejeu_squelette',
                                        description='Rejeu de bout en bout du squelette composite.')
    analyseur.add_argument('--configuration', required=True, help='config/parametres_figes_v3.json')
    analyseur.add_argument('--ticks', required=True, help='fichier CSV de ticks au format canonique')
    analyseur.add_argument('--sortie', required=True, help='dossier où écrire decisions.jsonl')
    arguments = analyseur.parse_args(argv)
    try:
        configuration = lire_configuration_squelette(lire_octets(arguments.configuration))
        moteur = fabriquer_moteur_minimal(fabriquer_strategie(configuration), configuration, MODE_REJEU)
        resultat = rejouer(analyser_lignes_ticks(lire_lignes(arguments.ticks)), moteur,
                           ExecutionPapierMinimale())
        chemin = ecrire_journal(arguments.sortie,
                                (serialiser_enregistrement(e) for e in resultat.enregistrements))
    except (ErreurDonnees, OSError, UnicodeDecodeError) as erreur:
        print(f'rejeu_squelette : {erreur}', file=sys.stderr)
        return 1
    print(json.dumps({'statut': 'OK', 'ticks': resultat.nombre_ticks,
                      'enregistrements': len(resultat.enregistrements), 'journal': chemin},
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

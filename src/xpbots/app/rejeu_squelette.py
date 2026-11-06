"""Segment minimal S7 du squelette : rejeu de bout en bout d'un fichier de ticks.

Segment minimal du squelette, remplacé en phase 11 par l'artefact `points-entree`. Contrat de la couture :
mcl/squelette/COUTURES.md. Point de composition : il charge la configuration figée par le chargeur de production
du noyau (empreintes contrôlées contre la preuve de conservation), lit les ticks par l'infrastructure, en déduit
l'hypothèse de marché du squelette (horaires et couverture sur l'étendue du fichier, `xpbots.rejeu.squelette`),
injecte la stratégie dans le moteur minimal (D-18), rejoue, puis écrit le journal canonique du noyau.

Usage (depuis la racine du dépôt, `PYTHONPATH` désignant `src`) :
    python -m xpbots.app.rejeu_squelette --ticks <fichier.csv> --sortie <dossier> --tick-size EURUSD=0.00001 [--racine-depot <dossier>]
Répéter --tick-size pour chaque symbole synthétique présent ; les tailles ne sont jamais déduites des prix.
Codes de sortie : 0 rejeu complet ; 1 donnée, configuration ou fichier refusés ; 2 usage invalide.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import json
import sys

from xpbots.infra.squelette import ecrire_journal, lire_configuration, lire_lignes
from xpbots.london.c2_moteur import fabriquer_strategie
from xpbots.noyau.c0c_configuration import charger_configuration_figee
from xpbots.noyau.c2_journal import serialiser
from xpbots.orchestration.squelette import fabriquer_moteur_minimal
from xpbots.rejeu.squelette import (ExecutionPapierMinimale, analyser_lignes_ticks, hypotheses_marche_squelette,
                                    rejouer)

MODE_REJEU = 'REJEU'


def _tailles_tick(arguments, symboles):
    """Hypothèse explicite du squelette, remplacée par le profil C04 en phase 11."""
    tailles = {}
    for argument in arguments:
        symbole, separateur, valeur = argument.partition('=')
        if not separateur or not symbole or symbole in tailles:
            raise ValueError('--tick-size attend une seule valeur SYMBOLE=DECIMAL par symbole')
        try:
            tailles[symbole] = Decimal(valeur)
        except InvalidOperation as erreur:
            raise ValueError('--tick-size : décimal illisible') from erreur
    if set(tailles) != symboles:
        raise ValueError('--tick-size requis exactement pour chaque symbole du fichier de ticks')
    return tailles


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(prog='python -m xpbots.app.rejeu_squelette',
                                        description='Rejeu de bout en bout du squelette composite.')
    analyseur.add_argument('--ticks', required=True, help='fichier CSV de ticks au format canonique')
    analyseur.add_argument('--sortie', required=True, help='dossier où écrire decisions.jsonl')
    analyseur.add_argument('--racine-depot', default='.', help='racine du dépôt (exports figés et preuve)')
    analyseur.add_argument('--tick-size', action='append', default=[], metavar='SYMBOLE=DECIMAL',
                          help='taille de tick explicite, une fois par symbole du fichier ; hypothèse du squelette')
    arguments = analyseur.parse_args(argv)
    try:
        configuration = charger_configuration_figee(*lire_configuration(arguments.racine_depot))
        ticks = list(analyser_lignes_ticks(lire_lignes(arguments.ticks)))
        tailles = _tailles_tick(arguments.tick_size, {tick.symbole for tick in ticks})
        horaires, periodes = hypotheses_marche_squelette(ticks, configuration)
        moteur = fabriquer_moteur_minimal(fabriquer_strategie(configuration, tailles), configuration, MODE_REJEU,
                                          horaires=horaires, periodes_couvertes=periodes)
        resultat = rejouer(ticks, moteur, ExecutionPapierMinimale())
        chemin = ecrire_journal(arguments.sortie, (serialiser(e) for e in resultat.enregistrements))
    except (ValueError, OSError) as erreur:
        print(f'rejeu_squelette : {erreur}', file=sys.stderr)
        return 1
    print(json.dumps({'statut': 'OK', 'ticks': resultat.nombre_ticks,
                      'enregistrements': len(resultat.enregistrements), 'journal': chemin},
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

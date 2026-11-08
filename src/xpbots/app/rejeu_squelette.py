"""Segment minimal S7 du squelette : rejeu de bout en bout d'un fichier de ticks.

Segment minimal du squelette, remplacé en phase 11 par l'artefact `points-entree`. Contrat de la couture :
mcl/squelette/COUTURES.md. Point de composition : il charge la configuration figée par le chargeur de production
du noyau (empreintes contrôlées contre la preuve de conservation), lit les ticks par l'infrastructure, en déduit
l'hypothèse de marché du squelette (horaires et couverture sur l'étendue du fichier, `xpbots.rejeu.squelette`),
injecte la stratégie dans le moteur minimal (D-18), rejoue, puis écrit le journal canonique du noyau.

Usage (depuis la racine du dépôt, `PYTHONPATH` désignant `src`) :
    python -m xpbots.app.rejeu_squelette --ticks <fichier.csv> --sortie <dossier> --tick-size EURUSD=0.00001 --contrat-papier EURUSD=1000,0.1,1,0.1 --scenario TECHNICAL_CONTROL_NEUTRAL [--racine-depot <dossier>]
Répéter --tick-size et --contrat-papier pour chaque symbole synthétique. Modèle S5 sans frais ; aucun profil réel ne se déduit des prix.
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
from xpbots.orchestration.squelette import fabriquer_moteur_minimal, composer_coordinateur_neutre, SCENARIO_TECHNIQUE
from xpbots.rejeu.squelette import (ContratPapier, ExecutionPapierMinimale, StockageMemoirePapier,
    analyser_lignes_ticks, hypotheses_marche_squelette, profils_papier, rejouer)

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


def _contrats_papier(arguments,symboles):
    contrats={}
    for argument in arguments:
        symbole,separateur,valeurs=argument.partition('=')
        if not separateur or not symbole or symbole in contrats:
            raise ValueError('--contrat-papier attend une seule valeur SYMBOLE=TAILLE,MIN,MAX,PAS')
        try:
            champs=tuple(Decimal(v) for v in valeurs.split(','))
            if len(champs)!=4: raise ValueError('quatre valeurs requises')
            contrats[symbole]=ContratPapier(*champs)
        except (InvalidOperation,ValueError,TypeError) as erreur:
            raise ValueError('--contrat-papier : contrat synthétique invalide') from erreur
    if set(contrats)!=symboles:
        raise ValueError('--contrat-papier requis exactement pour chaque symbole du fichier')
    return contrats


def composer_rejeu_papier(configuration,ticks,tailles,contrats,*,strategie=None,deploiement='squelette'):
    """Composition synthétique déclarée ; aucun terminal ou compte réel."""
    if not ticks: raise ValueError('aucun tick dans le fichier')
    horaires,periodes=hypotheses_marche_squelette(ticks,configuration)
    profils=profils_papier(ticks,tailles,contrats,horaires,configuration)
    premier=ticks[0].instant_reception_ms
    creation=premier//86_400_000*86_400_000
    execution=ExecutionPapierMinimale(configuration,profils,creation)
    execution.avancer_au(premier)
    coordinateur=composer_coordinateur_neutre(configuration,deploiement,profils,execution,premier,
        observation=execution.observation(),base_utc=execution.base_utc())
    strategie=strategie if strategie is not None else fabriquer_strategie(configuration,tailles)
    moteur=fabriquer_moteur_minimal(strategie,configuration,MODE_REJEU,deploiement,
        horaires=horaires,periodes_couvertes=periodes,coordinateur=coordinateur,profils=profils,
        profil_compte=execution.profil_compte,scenario_fondamental=SCENARIO_TECHNIQUE)
    return moteur,execution,StockageMemoirePapier()


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(prog='python -m xpbots.app.rejeu_squelette',
                                        description='Rejeu de bout en bout du squelette composite.')
    analyseur.add_argument('--ticks', required=True, help='fichier CSV de ticks au format canonique')
    analyseur.add_argument('--sortie', required=True, help='dossier où écrire decisions.jsonl')
    analyseur.add_argument('--racine-depot', default='.', help='racine du dépôt (exports figés et preuve)')
    analyseur.add_argument('--tick-size', action='append', default=[], metavar='SYMBOLE=DECIMAL',
                          help='taille de tick explicite, une fois par symbole du fichier ; hypothèse du squelette')
    analyseur.add_argument('--contrat-papier',action='append',default=[],metavar='SYMBOLE=TAILLE,MIN,MAX,PAS',
        help='contrat et grille de volume synthétiques explicites, une fois par symbole ; frais nuls du modèle S5')
    analyseur.add_argument('--scenario',required=True,choices=(SCENARIO_TECHNIQUE,),
        help='scénario technique neutre explicite, sans permissions fondamentales historiques')
    arguments = analyseur.parse_args(argv)
    try:
        configuration = charger_configuration_figee(*lire_configuration(arguments.racine_depot))
        ticks = list(analyser_lignes_ticks(lire_lignes(arguments.ticks)))
        tailles = _tailles_tick(arguments.tick_size, {tick.symbole for tick in ticks})
        contrats=_contrats_papier(arguments.contrat_papier,{t.symbole for t in ticks})
        moteur,execution,stockage=composer_rejeu_papier(configuration,ticks,tailles,contrats)
        resultat = rejouer(ticks,moteur,execution,stockage)
        chemin = ecrire_journal(arguments.sortie, (serialiser(e) for e in resultat.enregistrements))
    except (ValueError, OSError) as erreur:
        print(f'rejeu_squelette : {erreur}', file=sys.stderr)
        return 1
    print(json.dumps({'statut': 'OK', 'ticks': resultat.nombre_ticks,
                      'enregistrements': len(resultat.enregistrements), 'journal': chemin,
                       'scenario':arguments.scenario,'entrees_remplies':sum(r.nature.value=='REMPLISSAGE' for r in resultat.reponses),
                       'positions_closes':sum(r.nature.value=='CLOTURE' and r.donnees['volume_restant']==0 for r in resultat.reponses),
                      'positions_ouvertes':len(execution.positions_ouvertes)},
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

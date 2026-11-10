"""Segment minimal S7 du squelette : rejeu de bout en bout d'un fichier de ticks.

Segment minimal du squelette, remplacé en phase 11 par l'artefact `points-entree`. Contrat de la couture :
mcl/squelette/COUTURES.md. Point de composition : il charge la configuration figée par le chargeur de production
du noyau (empreintes contrôlées contre la preuve de conservation), lit les ticks par l'infrastructure, en déduit
l'hypothèse de marché du squelette (horaires et couverture sur l'étendue du fichier, `xpbots.rejeu.squelette`),
injecte la stratégie dans le moteur minimal (D-18), rejoue, puis écrit le journal canonique du noyau.

Usage (depuis la racine du dépôt, `PYTHONPATH` désignant `src`) :
    python -m xpbots.app.rejeu_squelette --ticks <fichier.csv> --sortie <dossier> --tick-size EURUSD=0.00001 --contrat-papier EURUSD=1000,0.1,1,0.1 --scenario TECHNICAL_CONTROL_NEUTRAL [--racine-depot <dossier>]
Répéter --tick-size et --contrat-papier pour chaque symbole synthétique. Commissions nulles déclarées,
délais/glissement/spread C10 (--couts REFERENCE ou STRESS) ; aucun profil réel ne se déduit des prix.
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
from xpbots.orchestration.squelette import (fabriquer_moteur_minimal,composer_coordinateur,
    SCENARIO_TECHNIQUE,LONGUEUR_EMPREINTE_SQUELETTE)
from xpbots.orchestration.c0_contrats import Deploiement,FabriqueStrategie
from xpbots.orchestration.c1_bras import construire_bras
from xpbots.orchestration.c2_moteur import MoteurDecision
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.contexte_ia.c0_types import charger_parametres,PolitiqueVeto
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.rejeu.squelette import (ContratPapier, ExecutionPapierMinimale, StockageMemoirePapier,
    analyser_lignes_ticks, hypotheses_marche_squelette, profils_papier, rejouer,rejouer_ab)
from xpbots.rejeu.c0b_protocole import charger_protocole,ScenarioExecution
from xpbots.rejeu.c3_rapports import rapporter_papier,serialiser_rapport

MODE_REJEU = 'REJEU'


def _scenario_couts(configuration,nom):
    if nom=='SYNTHETIQUE_S5':return ScenarioExecution(nom,0,0,Decimal(1))
    return charger_protocole(configuration).scenario(nom)


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


def composer_rejeu_papier(configuration,ticks,tailles,contrats,*,strategie=None,deploiement='squelette',
                         controle_fondamental=None,source_fondamentale=None,scenario=None,lecteur_ia=None,source_ia=None,
                         modele_couts='REFERENCE'):
    """Composition synthétique déclarée ; aucun terminal ou compte réel."""
    if not ticks: raise ValueError('aucun tick dans le fichier')
    horaires,periodes=hypotheses_marche_squelette(ticks,configuration)
    profils=profils_papier(ticks,tailles,contrats,horaires,configuration)
    premier=ticks[0].instant_reception_ms
    creation=premier//86_400_000*86_400_000
    execution=ExecutionPapierMinimale(configuration,profils,creation,_scenario_couts(configuration,modele_couts))
    execution.avancer_au(premier)
    if source_fondamentale is not None and (source_fondamentale.controle is not controle_fondamental
            or (source_fondamentale.prochaine_reception_ms is not None
                and source_fondamentale.prochaine_reception_ms<premier)):
        raise ValueError('source C05 liée au contrôle et bornée au rejeu requise')
    if source_ia is not None and (source_ia.lecteur is not lecteur_ia
            or (source_ia.prochaine_reception_ms is not None and source_ia.prochaine_reception_ms<premier)):
        raise ValueError('source IA liée au lecteur et bornée au rejeu requise')
    coordinateur=composer_coordinateur(configuration,deploiement,profils,execution,premier,
        observation=execution.observation(),base_utc=execution.base_utc(),
        controle_fondamental=controle_fondamental,scenario=scenario,lecteur_ia=lecteur_ia)
    fabriques=None if strategie is not None else (FabriqueStrategie(configuration.technique.london['strategy_id'],fabriquer_strategie),)
    moteur=fabriquer_moteur_minimal(strategie,configuration,MODE_REJEU,deploiement,
        horaires=horaires,periodes_couvertes=periodes,coordinateur=coordinateur,profils=profils,
        profil_compte=execution.profil_compte,scenario_fondamental=scenario,
        controle_fondamental=controle_fondamental,source_fondamentale=source_fondamentale,lecteur_ia=lecteur_ia,source_ia=source_ia,
        fabriques=fabriques)
    return moteur,execution,StockageMemoirePapier()


def composer_rejeu_papier_ab(configuration,ticks,tailles,contrats,*,deploiement='squelette',
        controle_fondamental=None,source_fondamentale=None,scenario=None,lecteur_ia=None,source_ia=None,
        fabriques=None,modele_couts='REFERENCE'):
    """Mode A/B initial : mêmes données, stratégies et comptes propres à chaque bras."""
    if not ticks:raise ValueError('aucun tick dans le fichier')
    h,c=hypotheses_marche_squelette(ticks,configuration)
    profils=profils_papier(ticks,tailles,contrats,h,configuration)
    premier=ticks[0].instant_reception_ms
    if scenario==SCENARIO_TECHNIQUE and controle_fondamental is None:f=ControleTechniqueNeutre()
    elif scenario is None and isinstance(controle_fondamental,PermissionsFondamentales):f=controle_fondamental
    else:raise ValueError('C05 réel ou scénario technique explicite requis')
    ia=lecteur_ia if lecteur_ia is not None else LecteurContexte(charger_parametres(configuration),PolitiqueVeto(True))
    if not ia.politique.bras_ia:raise ValueError('politique du bras IA requise')
    for s in (source_fondamentale,source_ia):
        if s is not None and s.prochaine_reception_ms is not None and s.prochaine_reception_ms<premier:raise ValueError('réception antérieure au rejeu')
    d=Deploiement(deploiement,configuration.ia.parametres['default_evaluation_mode'],
        tuple(fabriques) if fabriques is not None else (FabriqueStrategie(configuration.technique.london['strategy_id'],fabriquer_strategie),),tailles,LONGUEUR_EMPREINTE_SQUELETTE)
    bras=[];executions={};stockages={}
    for nom in ('REFERENCE','IA'):
        p=ExecutionPapierMinimale(configuration,profils,premier//86400000*86400000,
            _scenario_couts(configuration,modele_couts));p.avancer_au(premier)
        executions[nom]=p;stockages[nom]=StockageMemoirePapier()
        bras.append(construire_bras(configuration,d,nom,profils,p,f,premier,observation=p.observation(),
            base_utc=p.base_utc(),lecteur_ia=ia if nom=='IA' else None))
    moteur=MoteurDecision(configuration,bras,h,c,controle_fondamental=controle_fondamental,lecteur_ia=ia,
        source_fondamentale=source_fondamentale,source_ia=source_ia,scenario_fondamental=scenario)
    return moteur,executions,stockages


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
    analyseur.add_argument('--mode',choices=('REJEU','PAPER_AB'),default=MODE_REJEU,
        help='mode simple ou comparaison de deux comptes papier indépendants')
    analyseur.add_argument('--couts',choices=('REFERENCE','STRESS'),default='REFERENCE',
        help='hypotheses de couts et delais C10, sans mesure reelle du courtier')
    arguments = analyseur.parse_args(argv)
    try:
        configuration = charger_configuration_figee(*lire_configuration(arguments.racine_depot))
        ticks = list(analyser_lignes_ticks(lire_lignes(arguments.ticks)))
        tailles = _tailles_tick(arguments.tick_size, {tick.symbole for tick in ticks})
        contrats=_contrats_papier(arguments.contrat_papier,{t.symbole for t in ticks})
        ab=arguments.mode==configuration.ia.parametres['default_evaluation_mode']
        moteur,execution,stockage=(composer_rejeu_papier_ab if ab else composer_rejeu_papier)(configuration,ticks,tailles,contrats,
            scenario=arguments.scenario,modele_couts=arguments.couts)
        resultat = (rejouer_ab if ab else rejouer)(ticks,moteur,execution,stockage)
        chemin = ecrire_journal(arguments.sortie, (serialiser(e) for e in resultat.enregistrements))
    except (ValueError, OSError) as erreur:
        print(f'rejeu_squelette : {erreur}', file=sys.stderr)
        return 1
    reponses=tuple(r for v in resultat.reponses.values() for r in v) if ab else resultat.reponses
    positions=sum(len(p.positions_ouvertes) for p in execution.values()) if ab else len(execution.positions_ouvertes)
    ports=execution if ab else {next(iter(moteur.moteur.bras)):execution}
    rapport=rapporter_papier(resultat.nombre_ticks,resultat.enregistrements,
        {n:dict(trades=p.trades,courbe=p.courbe,premiers_remplissages=p.premiers_remplissages,
            positions_ouvertes=len(p.positions_ouvertes),scenario=p.scenario.nom) for n,p in ports.items()},configuration)
    print(serialiser_rapport({'statut': 'OK', 'ticks': resultat.nombre_ticks,
                      'enregistrements': len(resultat.enregistrements), 'journal': chemin,
                       'scenario':arguments.scenario,'entrees_remplies':sum(r.nature.value=='REMPLISSAGE' for r in reponses),
                       'positions_closes':sum(r.nature.value=='CLOTURE' and r.donnees['volume_restant']==0 for r in reponses),
                      'positions_ouvertes':positions,'rapport':rapport}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

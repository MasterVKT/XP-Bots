"""Point d'entrée du rejeu : `python -m xpbots.app.rejeu --ticks <csv> --manifeste <json> --journal <jsonl>`.

Phase 1 : chemin minimal du squelette (ticks → bougie M15 → stratégie neutre → coordinateur de refus →
exécution papier → journal C09). Aucun ordre, aucun appel réseau.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Callable, Sequence

from xpbots.app.segments_minimaux import (SCENARIO_TECHNICAL_CONTROL_NEUTRAL, AgregateurM15Minimal,
                                          ContexteIANeutre, CoordinateurRefus, EcrivainJournalJSONL,
                                          ErreurDonneesFixture, ErreurJournal, ExecutionPapierMinimale,
                                          FondamentalAbsent, LecteurFixtureCSV, StrategieNeutre)
from xpbots.noyau.config import BundleTechnique, ConfigurationInvalide, charger_bundle_technique
from xpbots.noyau.journal_schema import ConstructeurEnregistrements, EnregistrementInvalide, Mode
from xpbots.noyau.json_canonique import serialiser
from xpbots.noyau.ports import Strategie

DEPLOYMENT_ID_PAR_DEFAUT = 'rejeu-squelette'
CODE_ERREUR = 2  # convention argparse : usage ou données invalides
SEGMENTS_MINIMAUX = ('lecteur_fixture_csv', 'ecrivain_journal_jsonl', 'agregateur_m15_minimal', 'strategie_neutre',
                     'fondamental_absent', 'contexte_ia_neutre', 'execution_papier_minimale', 'coordinateur_refus')


class _JournalCompte:
    """Compte les enregistrements écrits pour le résumé, sans rien modifier."""

    def __init__(self, journal):
        self._journal = journal
        self.motifs_clotures = Counter()
        self.motifs_intentions = Counter()

    def ajouter(self, enregistrement):
        self._journal.ajouter(enregistrement)
        if enregistrement['type'] == 'CLOTURE_BOUGIE':
            self.motifs_clotures[enregistrement['motif'] or 'SIGNAL'] += 1
        elif enregistrement['type'] == 'INTENTION':
            self.motifs_intentions[enregistrement['motif'] or 'ADMISSION'] += 1


def _symboles_ordonnes(source, priorite: Sequence[str]) -> list[str]:
    inconnus = [s for s in source.symboles() if s not in priorite]
    if inconnus:
        raise ErreurDonneesFixture(f'symboles hors univers de config/ : {inconnus}')
    return [s for s in priorite if s in source.symboles()]


def executer_rejeu(chemin_ticks: Path, chemin_manifeste: Path, chemin_journal: Path, *,
                   deployment_id: str = DEPLOYMENT_ID_PAR_DEFAUT, scenario_fondamental: str | None = None,
                   fabrique_strategies: Callable[[BundleTechnique], Sequence[Strategie]] | None = None,
                   racine: Path | None = None) -> dict:
    """Rejoue une fixture de ticks et écrit le journal C09 ; renvoie un résumé des comptes."""
    bundle = charger_bundle_technique(racine)
    source = LecteurFixtureCSV(chemin_ticks, chemin_manifeste)
    symboles = _symboles_ordonnes(source, bundle.valeur('common', 'universe_priority'))
    mode = Mode(bundle.valeur('common', 'default_mode'))
    strategies = (list(fabrique_strategies(bundle)) if fabrique_strategies
                  else [StrategieNeutre(bundle.valeur('ema', 'strategy_id'))])
    constructeur = ConstructeurEnregistrements(deployment_id, mode, bundle)
    agregateur = AgregateurM15Minimal(symboles, {s: source.couverture(s) for s in symboles},
                                      bundle.valeur('common', 'timeframe_seconds'))
    debuts = [source.couverture(s)[0][0] for s in symboles if source.couverture(s)]
    if not debuts:
        raise ErreurDonneesFixture('manifeste : aucune couverture déclarée')
    debut = min(debuts)
    nb_ticks = 0
    with EcrivainJournalJSONL(chemin_journal) as fichier:
        journal = _JournalCompte(fichier)
        empreintes = source.empreintes()
        journal.ajouter(constructeur.initialisation(
            debut, symboles, {'fichier': Path(chemin_ticks).name, 'sha256': empreintes['ticks'],
                              'manifeste': Path(chemin_manifeste).name, 'manifeste_sha256': empreintes['manifeste']},
            SEGMENTS_MINIMAUX, scenario_fondamental))
        coordinateur = CoordinateurRefus(deployment_id, strategies, FondamentalAbsent(mode, scenario_fondamental),
                                         ContexteIANeutre(), ExecutionPapierMinimale(), journal, constructeur)
        for tick in source.ticks():
            for bougie in agregateur.avancer(tick.instant.ms):
                coordinateur.sur_bougie(bougie)
            agregateur.ajouter(tick)
            nb_ticks += 1
        for bougie in agregateur.terminer(source.fin_donnees_ms()):
            coordinateur.sur_bougie(bougie)
    return {'ticks': nb_ticks, 'enregistrements': constructeur.derniere_sequence,
            'clotures': dict(sorted(journal.motifs_clotures.items())),
            'intentions': dict(sorted(journal.motifs_intentions.items())),
            'bougies_incompletes': agregateur.bougies_incompletes}


def main(argv: Sequence[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description='Rejeu du squelette du robot 1 EMA_V3 (aucun ordre).')
    parseur.add_argument('--ticks', required=True, type=Path, help='CSV au format du cahier de données §2')
    parseur.add_argument('--manifeste', required=True, type=Path, help='manifeste JSON de couverture')
    parseur.add_argument('--journal', required=True, type=Path, help='journal JSONL à créer (jamais écrasé)')
    parseur.add_argument('--deployment-id', default=DEPLOYMENT_ID_PAR_DEFAUT)
    parseur.add_argument('--scenario-fondamental', choices=[SCENARIO_TECHNICAL_CONTROL_NEUTRAL], default=None,
                         help='contrôle technique isolé explicitement nommé (C05)')
    args = parseur.parse_args(argv)
    try:
        resume = executer_rejeu(args.ticks, args.manifeste, args.journal, deployment_id=args.deployment_id,
                                scenario_fondamental=args.scenario_fondamental)
    except (ConfigurationInvalide, ErreurDonneesFixture, ErreurJournal, EnregistrementInvalide, ValueError) as erreur:
        print(f'erreur : {erreur}', file=sys.stderr)
        return CODE_ERREUR
    print(serialiser(resume))
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""Point d'entrée du rejeu : `python -m xpbots.app.rejeu --ticks <csv> --manifeste <json> --journal <jsonl>`.

Phase 3 : ticks → `donnees-temps` (bougies M15 enrichies, trous, préchargement) → `moteur-ema` (méthode S01) →
coordinateur de refus → exécution papier → journal C09. Aucun ordre, aucun appel réseau.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Callable, Iterator, Sequence

from xpbots.app.segments_minimaux import (SCENARIO_TECHNICAL_CONTROL_NEUTRAL, ContexteIANeutre, CoordinateurRefus,
                                          EcrivainJournalJSONL, ErreurDonneesFixture, ErreurJournal,
                                          ExecutionPapierMinimale, FondamentalAbsent, LecteurFixtureCSV,
                                          StockageMemoire)
from xpbots.donnees_temps.c0_parametres_seances import CalendrierSeances, charger_parametres_techniques
from xpbots.donnees_temps.c1a_sessions import SessionsLondres
from xpbots.donnees_temps.c2_etat_indicateurs import SpecIndicateurs
from xpbots.donnees_temps.c3_pipeline import PipelineMarche
from xpbots.moteur_ema.c0_parametres import charger_parametres_ema
from xpbots.moteur_ema.c3_moteur import MoteurEMA
from xpbots.noyau.config import BundleTechnique, ConfigurationInvalide, charger_bundle_technique
from xpbots.noyau.journal_schema import ConstructeurEnregistrements, EnregistrementInvalide, Mode
from xpbots.noyau.json_canonique import serialiser
from xpbots.noyau.marche import BougieEnrichie, EvenementDonnees
from xpbots.noyau.ports import SourceTicksHistoriques, Strategie

DEPLOYMENT_ID_PAR_DEFAUT = 'rejeu-squelette'
CODE_ERREUR = 2  # convention argparse : usage ou données invalides
SEGMENTS_MINIMAUX = ('lecteur_fixture_csv', 'ecrivain_journal_jsonl', 'stockage_memoire', 'fondamental_absent',
                     'contexte_ia_neutre', 'execution_papier_minimale', 'coordinateur_refus')
Fabrique = Callable[[BundleTechnique, SourceTicksHistoriques, Sequence[str]], Sequence[Strategie]]


def strategies_par_defaut(bundle: BundleTechnique, source: SourceTicksHistoriques,
                          symboles: Sequence[str]) -> list[Strategie]:
    """Méthode S01 `EMA_V3` sur les symboles rejoués, tick_size déclaré par la source, état en mémoire."""
    sessions = SessionsLondres(charger_parametres_techniques(bundle))
    return [MoteurEMA(charger_parametres_ema(bundle), sessions, {s: source.tick_size(s) for s in symboles},
                      StockageMemoire())]


def spec_indicateurs_ema(bundle: BundleTechnique) -> SpecIndicateurs:
    """Indicateurs de la méthode S01 lus dans `config/` : EMA, RSI, ATR, EMA lente de t−k, préchauffage M15."""
    periodes = tuple(bundle.valeur('ema', 'ema_periods'))
    return SpecIndicateurs(periodes, bundle.valeur('ema', 'rsi_period'), bundle.valeur('common', 'atr_period'),
                           ((max(periodes), bundle.valeur('ema', 'slow_ema_slope_lookback_bars')),),
                           bundle.valeur('common', 'warmup_closed_m15_bars'))


def _instant(sortie) -> int:
    return sortie.bougie.cloture_ms if isinstance(sortie, BougieEnrichie) else sortie.instant_ms


class MarcheRejoue:
    """Un pipeline `donnees-temps` par symbole ; ticks et transitions de couverture fusionnés dans l'ordre.

    À instant égal, les transitions de couverture précèdent les ticks ; les sorties de plusieurs symboles sont
    ordonnées par instant puis par priorité de l'univers de `config/`.
    """

    def __init__(self, source: SourceTicksHistoriques, symboles: Sequence[str], bundle: BundleTechnique):
        parametres = charger_parametres_techniques(bundle)
        sessions = SessionsLondres(parametres)
        spec = spec_indicateurs_ema(bundle)
        self._source = source
        self._fin = source.fin_donnees_ms()
        self._rang = {s: rang for rang, s in enumerate(symboles)}
        self._pipelines, self._debuts, transitions = {}, {}, []
        for s in symboles:
            couverture = source.couverture(s)
            if not couverture:
                raise ErreurDonneesFixture(f'{s} : aucune couverture déclarée dans le manifeste')
            debut = couverture[0][0]
            seances = tuple((max(a, debut), min(b, self._fin)) for a, b in source.seances(s)
                            if b > debut and a < self._fin)
            self._pipelines[s] = PipelineMarche(s, parametres.periode_m15_s,
                                                CalendrierSeances(s, seances, debut, self._fin), sessions, spec, debut)
            self._debuts[s] = debut
            for a, b in couverture:
                transitions.append((a, self._rang[s], s, True))
                if b < self._fin:
                    transitions.append((b, self._rang[s], s, False))
        self._transitions = sorted(transitions)
        self.debut_ms = min(self._debuts.values())
        self.nb_ticks = 0

    def _ordonner(self, paires) -> list:
        return [sortie for _, _, sortie in sorted(paires, key=lambda p: (p[0], p[1]))]

    def _avancer(self, instant_ms: int) -> list:
        paires = []
        for s, pipeline in self._pipelines.items():
            if instant_ms >= self._debuts[s]:
                paires += [(_instant(sortie), self._rang[s], sortie) for sortie in pipeline.sur_horloge(instant_ms)]
        return self._ordonner(paires)

    def _transitions_jusqua(self, instant_ms: int) -> Iterator:
        while self._transitions and self._transitions[0][0] <= instant_ms:
            instant, _, symbole, etablie = self._transitions.pop(0)
            yield from self._avancer(instant)
            yield from self._pipelines[symbole].sur_couverture(instant, etablie)

    def sorties(self) -> Iterator[BougieEnrichie | EvenementDonnees]:
        self.nb_ticks = 0
        for tick in self._source.ticks():
            if tick.instant.ms < self._debuts[tick.symbole]:
                raise ErreurDonneesFixture(f'{tick.symbole} : tick antérieur à la couverture déclarée')
            yield from self._transitions_jusqua(tick.instant.ms)
            yield from self._avancer(tick.instant.ms)
            yield from self._pipelines[tick.symbole].sur_tick(tick)
            self.nb_ticks += 1
        yield from self._transitions_jusqua(self._fin - 1)
        paires = []
        for s, pipeline in self._pipelines.items():
            paires += [(_instant(sortie), self._rang[s], sortie) for sortie in pipeline.terminer(self._fin)]
        yield from self._ordonner(paires)


class _JournalCompte:
    """Compte les enregistrements écrits pour le résumé, sans rien modifier."""

    def __init__(self, journal):
        self._journal = journal
        self.motifs_clotures = Counter()
        self.motifs_intentions = Counter()
        self.evenements_donnees = Counter()

    def ajouter(self, enregistrement):
        self._journal.ajouter(enregistrement)
        if enregistrement['type'] == 'CLOTURE_BOUGIE':
            self.motifs_clotures[enregistrement['motif'] or 'SIGNAL'] += 1
        elif enregistrement['type'] == 'INTENTION':
            self.motifs_intentions[enregistrement['motif'] or 'ADMISSION'] += 1
        elif enregistrement['type'] == 'DONNEES':
            self.evenements_donnees[enregistrement['evenement']] += 1


def _symboles_ordonnes(source, priorite: Sequence[str]) -> list[str]:
    inconnus = [s for s in source.symboles() if s not in priorite]
    if inconnus:
        raise ErreurDonneesFixture(f'symboles hors univers de config/ : {inconnus}')
    return [s for s in priorite if s in source.symboles()]


def executer_rejeu(chemin_ticks: Path, chemin_manifeste: Path, chemin_journal: Path, *,
                   deployment_id: str = DEPLOYMENT_ID_PAR_DEFAUT, scenario_fondamental: str | None = None,
                   fabrique_strategies: Fabrique = strategies_par_defaut,
                   racine: Path | None = None) -> dict:
    """Rejoue une fixture de ticks et écrit le journal C09 ; renvoie un résumé des comptes."""
    bundle = charger_bundle_technique(racine)
    source = LecteurFixtureCSV(chemin_ticks, chemin_manifeste)
    symboles = _symboles_ordonnes(source, bundle.valeur('common', 'universe_priority'))
    mode = Mode(bundle.valeur('common', 'default_mode'))
    strategies = list(fabrique_strategies(bundle, source, symboles))
    constructeur = ConstructeurEnregistrements(deployment_id, mode, bundle)
    marche = MarcheRejoue(source, symboles, bundle)
    with EcrivainJournalJSONL(chemin_journal) as fichier:
        journal = _JournalCompte(fichier)
        empreintes = source.empreintes()
        journal.ajouter(constructeur.initialisation(
            marche.debut_ms, symboles, {'fichier': Path(chemin_ticks).name, 'sha256': empreintes['ticks'],
                                        'manifeste': Path(chemin_manifeste).name,
                                        'manifeste_sha256': empreintes['manifeste']},
            SEGMENTS_MINIMAUX, scenario_fondamental))
        coordinateur = CoordinateurRefus(deployment_id, strategies, FondamentalAbsent(mode, scenario_fondamental),
                                         ContexteIANeutre(), ExecutionPapierMinimale(), journal, constructeur)
        for sortie in marche.sorties():
            if isinstance(sortie, BougieEnrichie):
                coordinateur.sur_bougie(sortie)
            else:
                coordinateur.sur_evenement_donnees(sortie)
    return {'ticks': marche.nb_ticks, 'enregistrements': constructeur.derniere_sequence,
            'clotures': dict(sorted(journal.motifs_clotures.items())),
            'intentions': dict(sorted(journal.motifs_intentions.items())),
            'donnees': dict(sorted(journal.evenements_donnees.items()))}


def main(argv: Sequence[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description='Rejeu du squelette du robot 1 EMA_V3 (aucun ordre).')
    parseur.add_argument('--ticks', required=True, type=Path, help='CSV au format du cahier de données §2')
    parseur.add_argument('--manifeste', required=True, type=Path, help='manifeste JSON (couverture et séances)')
    parseur.add_argument('--journal', required=True, type=Path, help='journal JSONL à créer (jamais écrasé)')
    parseur.add_argument('--deployment-id', default=DEPLOYMENT_ID_PAR_DEFAUT)
    parseur.add_argument('--scenario-fondamental', choices=[SCENARIO_TECHNICAL_CONTROL_NEUTRAL], default=None,
                         help='contrôle technique isolé explicitement nommé (C05)')
    args = parseur.parse_args(argv)
    try:
        resume = executer_rejeu(args.ticks, args.manifeste, args.journal, deployment_id=args.deployment_id,
                                scenario_fondamental=args.scenario_fondamental)
    except (ConfigurationInvalide, ErreurDonneesFixture, ErreurJournal, EnregistrementInvalide, ValueError,
            LookupError) as erreur:
        print(f'erreur : {erreur}', file=sys.stderr)
        return CODE_ERREUR
    print(serialiser(resume))
    return 0


if __name__ == '__main__':
    sys.exit(main())

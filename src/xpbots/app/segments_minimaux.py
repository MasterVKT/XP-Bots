"""Segments minimaux du squelette composite, chacun remplacé plus tard par un artefact de chair.

Chaque segment respecte la spécification sur son périmètre réduit (voir `mcl/robot-ema-v3/COUTURES.md`) :
fondamental absent = refus, contexte IA absent = NEUTRAL, aucun ordre n'est jamais émis.
"""
from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Mapping, Sequence

from xpbots.noyau.config import ConfigurationInvalide, lire_json_strict
from xpbots.noyau.decisions import (CleIntention, DecisionContexteIA, DecisionFondamentale, EtatContexteIA,
                                    IssueSignal, MotifRefus, Refuse, ResultatTechnique, Sens, Signal)
from xpbots.noyau.journal_schema import (ConstructeurEnregistrements, Decision, EnregistrementInvalide, Mode,
                                         valider_enregistrement)
from xpbots.noyau.json_canonique import serialiser
from xpbots.noyau.marche import Bougie, BougieEnrichie, StatutBougie, Tick
from xpbots.noyau.ports import ContexteIA, ControleFondamental, Journal, Strategie
from xpbots.noyau.temps import MS_PAR_SECONDE, Instant

# Nom du scénario de contrôle technique isolé défini par C05 (jamais un remplacement implicite).
SCENARIO_TECHNICAL_CONTROL_NEUTRAL = 'TECHNICAL_CONTROL_NEUTRAL'

ENTETE_TICKS = ('canonical_symbol', 'broker_symbol', 'time_utc_ms', 'sequence', 'bid', 'ask')
SCHEMA_MANIFESTE = 'xp-fixture-manifeste-v1'
CLES_MANIFESTE = frozenset({'schema', 'origine', 'fuseau', 'description', 'fin_donnees_ms', 'symboles'})
FUSEAU_MANIFESTE = 'UTC'
_ENTIER = re.compile(r'-?\d+')
_DECIMAL = re.compile(r'\d+\.\d+')


class ErreurDonneesFixture(ValueError):
    """Fichier de ticks ou manifeste de fixture non conforme."""


class ErreurJournal(OSError):
    """Journal impossible à créer ou à écrire."""


class IssueInattendue(RuntimeError):
    """Issue reçue par une méthode qui n'a émis aucun signal correspondant."""


def _sha256_fichier(chemin: Path) -> str:
    return hashlib.sha256(Path(chemin).read_bytes()).hexdigest()


def _entier_manifeste(valeur, contexte):
    if type(valeur) is not int:
        raise ErreurDonneesFixture(f'{contexte} : entier attendu, reçu {valeur!r}')
    return valeur


class LecteurFixtureCSV:
    """Ticks d'un CSV au format du cahier de données (§2) et couverture déclarée par un manifeste JSON."""

    def __init__(self, chemin_ticks: Path, chemin_manifeste: Path):
        self._chemin_ticks = Path(chemin_ticks)
        self._chemin_manifeste = Path(chemin_manifeste)
        try:
            manifeste = lire_json_strict(self._chemin_manifeste)
        except ConfigurationInvalide as erreur:
            raise ErreurDonneesFixture(str(erreur)) from erreur
        self._symboles, self._courtier, self._couverture, self._fin = self._valider_manifeste(manifeste)

    def _valider_manifeste(self, m):
        if type(m) is not dict or set(m) != CLES_MANIFESTE:
            raise ErreurDonneesFixture(f'manifeste : clés attendues {sorted(CLES_MANIFESTE)}')
        if m['schema'] != SCHEMA_MANIFESTE or m['fuseau'] != FUSEAU_MANIFESTE:
            raise ErreurDonneesFixture('manifeste : schéma ou fuseau inattendu')
        if type(m['symboles']) is not dict or not m['symboles']:
            raise ErreurDonneesFixture('manifeste : au moins un symbole attendu')
        fin = _entier_manifeste(m['fin_donnees_ms'], 'fin_donnees_ms')
        courtier, couverture = {}, {}
        for symbole, decl in m['symboles'].items():
            if type(decl) is not dict or set(decl) != {'symbole_courtier', 'couverture'}:
                raise ErreurDonneesFixture(f'manifeste : déclaration de {symbole} invalide')
            if type(decl['symbole_courtier']) is not str or not decl['symbole_courtier']:
                raise ErreurDonneesFixture(f'manifeste : symbole courtier de {symbole} invalide')
            intervalles, precedente_fin = [], None
            for intervalle in decl['couverture']:
                try:
                    debut, fin_i = intervalle
                except (TypeError, ValueError) as erreur:
                    raise ErreurDonneesFixture(f'manifeste : intervalle de {symbole} invalide') from erreur
                debut = _entier_manifeste(debut, f'couverture de {symbole}')
                fin_i = _entier_manifeste(fin_i, f'couverture de {symbole}')
                if not debut < fin_i <= fin or (precedente_fin is not None and debut < precedente_fin):
                    raise ErreurDonneesFixture(f'manifeste : couverture de {symbole} non ordonnée ou hors données')
                intervalles.append((debut, fin_i))
                precedente_fin = fin_i
            courtier[symbole] = decl['symbole_courtier']
            couverture[symbole] = tuple(intervalles)
        return tuple(m['symboles']), courtier, couverture, fin

    def symboles(self) -> tuple[str, ...]:
        return self._symboles

    def couverture(self, symbole: str) -> tuple[tuple[int, int], ...]:
        return self._couverture[symbole]

    def fin_donnees_ms(self) -> int:
        return self._fin

    def empreintes(self) -> Mapping[str, str]:
        return {'ticks': _sha256_fichier(self._chemin_ticks), 'manifeste': _sha256_fichier(self._chemin_manifeste)}

    def ticks(self) -> Iterator[Tick]:
        precedent = None
        try:
            fichier = self._chemin_ticks.open(encoding='utf-8', newline='')
        except OSError as erreur:
            raise ErreurDonneesFixture(f'{self._chemin_ticks} : {erreur}') from erreur
        with fichier:
            lecteur = csv.reader(fichier)
            if tuple(next(lecteur, ())) != ENTETE_TICKS:
                raise ErreurDonneesFixture(f'en-tête attendu : {",".join(ENTETE_TICKS)}')
            for numero, ligne in enumerate(lecteur, start=lecteur.line_num + 1):
                tick = self._tick(ligne, numero)
                if precedent is not None and not tick.instant > precedent:
                    raise ErreurDonneesFixture(f'ligne {numero} : ordre (ms, séquence) non strictement croissant')
                if tick.instant.ms >= self._fin:
                    raise ErreurDonneesFixture(f'ligne {numero} : tick au-delà de fin_donnees_ms')
                precedent = tick.instant
                yield tick

    def _tick(self, ligne, numero) -> Tick:
        if len(ligne) != len(ENTETE_TICKS):
            raise ErreurDonneesFixture(f'ligne {numero} : {len(ENTETE_TICKS)} colonnes attendues')
        symbole, courtier, temps, sequence, bid, ask = ligne
        if symbole not in self._courtier or courtier != self._courtier[symbole]:
            raise ErreurDonneesFixture(f'ligne {numero} : symbole absent du manifeste')
        if not (_ENTIER.fullmatch(temps) and _ENTIER.fullmatch(sequence)
                and _DECIMAL.fullmatch(bid) and _DECIMAL.fullmatch(ask)):
            raise ErreurDonneesFixture(f'ligne {numero} : nombre mal formé')
        try:
            return Tick(symbole, courtier, Instant(int(temps), int(sequence)), Decimal(bid), Decimal(ask))
        except ValueError as erreur:
            raise ErreurDonneesFixture(f'ligne {numero} : {erreur}') from erreur


class EcrivainJournalJSONL:
    """Journal C09 en JSONL canonique, ajout seul ; refuse d'écraser un journal existant."""

    def __init__(self, chemin: Path):
        self._chemin = Path(chemin)
        try:
            self._chemin.parent.mkdir(parents=True, exist_ok=True)
            self._fichier = self._chemin.open('x', encoding='utf-8', newline='\n')
        except FileExistsError as erreur:
            raise ErreurJournal(f'le journal existe déjà : {self._chemin}') from erreur
        except OSError as erreur:
            raise ErreurJournal(f'journal impossible à créer : {erreur}') from erreur

    def ajouter(self, enregistrement: Mapping[str, object]) -> None:
        erreurs = valider_enregistrement(enregistrement)
        if erreurs:
            raise EnregistrementInvalide(' ; '.join(erreurs))
        self._fichier.write(serialiser(enregistrement) + '\n')
        self._fichier.flush()

    def fermer(self) -> None:
        self._fichier.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.fermer()
        return False


@dataclass
class _BougieEnCours:
    ouverture_ms: int
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741 (notation OHLC de la spécification)
    c: Decimal
    nb_ticks: int


class AgregateurM15Minimal:
    """Bougies Bid [T, T+période) alignées UTC, closes quand l'horloge de rejeu atteint T+période.

    Validité = intervalle entièrement couvert par le manifeste. Aucune gestion de trou au-delà (artefact
    `donnees-temps`) ; un intervalle sans tick ne produit pas de bougie.
    """

    def __init__(self, symboles_ordonnes: Sequence[str], couverture: Mapping[str, Sequence[tuple[int, int]]],
                 periode_s: int):
        if type(periode_s) is not int or periode_s <= 0:
            raise ValueError('période invalide')
        self._rang = {symbole: rang for rang, symbole in enumerate(symboles_ordonnes)}
        self._couverture = {s: tuple(couverture[s]) for s in symboles_ordonnes}
        self._periode_s = periode_s
        self._periode_ms = periode_s * MS_PAR_SECONDE
        self._en_cours: dict[str, _BougieEnCours] = {}
        self.bougies_incompletes = 0

    def _couverte(self, symbole, debut, fin) -> bool:
        return any(a <= debut and fin <= b for a, b in self._couverture[symbole])

    def _clore(self, symbole, etat: _BougieEnCours) -> BougieEnrichie:
        valide = self._couverte(symbole, etat.ouverture_ms, etat.ouverture_ms + self._periode_ms)
        bougie = Bougie(symbole, self._periode_s, etat.ouverture_ms, etat.o, etat.h, etat.l, etat.c,
                        etat.nb_ticks, valide)
        return BougieEnrichie(bougie, StatutBougie.OK if valide else StatutBougie.DATA_GAP)

    def avancer(self, instant_ms: int) -> list[BougieEnrichie]:
        """Clôt toutes les bougies dont la fin est <= instant, par instant de clôture puis rang du symbole."""
        closes = []
        for symbole in list(self._en_cours):
            etat = self._en_cours[symbole]
            if etat.ouverture_ms + self._periode_ms <= instant_ms:
                closes.append(self._clore(symbole, etat))
                del self._en_cours[symbole]
        return sorted(closes, key=lambda be: (be.bougie.cloture_ms, self._rang[be.bougie.symbole]))

    def ajouter(self, tick: Tick) -> None:
        """Ajoute un tick à sa bougie ; l'horloge doit avoir été avancée à l'instant du tick."""
        if tick.symbole not in self._rang:
            raise ValueError(f'symbole non géré : {tick.symbole}')
        t = tick.instant.ms
        ouverture = t - t % self._periode_ms
        etat = self._en_cours.get(tick.symbole)
        if etat is None:
            self._en_cours[tick.symbole] = _BougieEnCours(ouverture, tick.bid, tick.bid, tick.bid, tick.bid, 1)
            return
        if etat.ouverture_ms != ouverture:
            raise RuntimeError('horloge non avancée avant un tick d\'une nouvelle bougie')
        etat.h = max(etat.h, tick.bid)
        etat.l = min(etat.l, tick.bid)
        etat.c = tick.bid
        etat.nb_ticks += 1

    def terminer(self, fin_ms: int) -> list[BougieEnrichie]:
        """Avance jusqu'à la fin des données ; une bougie non terminée n'est jamais close (causalité)."""
        closes = self.avancer(fin_ms)
        self.bougies_incompletes += len(self._en_cours)
        self._en_cours.clear()
        return closes


class StrategieNeutre:
    """Méthode neutre : jamais de signal ; motif NO_SETUP, ou le motif du statut de la bougie."""

    _MOTIFS = {StatutBougie.OK: MotifRefus.NO_SETUP, StatutBougie.WARMUP: MotifRefus.WARMUP,
               StatutBougie.DATA_GAP: MotifRefus.DATA_GAP}

    def __init__(self, strategie_id: str):
        self.strategie_id = strategie_id

    def sur_cloture(self, bougie: BougieEnrichie) -> ResultatTechnique:
        return ResultatTechnique(None, self._MOTIFS[bougie.statut], {'segment': 'strategie_neutre'})

    def appliquer_issue(self, cle: CleIntention, issue: IssueSignal) -> None:
        raise IssueInattendue(f'la stratégie neutre n\'émet aucun signal : {cle.texte()}')


class FondamentalAbsent:
    """Aucun fournisseur fondamental : refus FUNDAMENTAL_INVALID, sauf scénario C05 explicitement nommé."""

    def __init__(self, mode: Mode, scenario: str | None = None):
        if scenario not in (None, SCENARIO_TECHNICAL_CONTROL_NEUTRAL):
            raise ValueError(f'scénario fondamental inconnu : {scenario!r}')
        if scenario is not None and Mode(mode) is Mode.DEMO:
            raise ValueError('le scénario TECHNICAL_CONTROL_NEUTRAL est interdit en DEMO (C05)')
        self.scenario = scenario

    def autoriser(self, symbole: str, sens: Sens, instant_ms: int) -> DecisionFondamentale:
        if self.scenario is None:
            return DecisionFondamentale(False, MotifRefus.FUNDAMENTAL_INVALID)
        return DecisionFondamentale(True, None, {'direction': 'ANY', 'risk_state': 'ALLOW'}, self.scenario)


class ContexteIANeutre:
    """Aucun service IA : NEUTRAL, c'est-à-dire aucun veto supplémentaire (A12), jamais une autorisation."""

    def decision(self, symbole: str, instant_ms: int) -> DecisionContexteIA:
        return DecisionContexteIA(EtatContexteIA.NEUTRAL)


class ExecutionPapierMinimale:
    """Exécution papier du squelette : n'envoie jamais d'ordre, transforme un refus en issue définitive."""

    def traiter_refus(self, motif: MotifRefus, instant_ms: int) -> Refuse:
        return Refuse(motif, instant_ms)


class CoordinateurRefus:
    """Coordinateur minimal : journalise chaque clôture et refuse explicitement tout signal (ordre C08 réduit).

    Ordre : méthode → fondamental → contexte IA → environnement d'exécution, absent dans le squelette
    (ENVIRONMENT_NOT_READY). Le premier refus rencontré est retenu.
    """

    def __init__(self, deployment_id: str, strategies: Sequence[Strategie], fondamental: ControleFondamental,
                 contexte_ia: ContexteIA, execution: ExecutionPapierMinimale, journal: Journal,
                 constructeur: ConstructeurEnregistrements):
        self._deployment_id = deployment_id
        self._strategies = tuple(strategies)
        self._fondamental = fondamental
        self._contexte_ia = contexte_ia
        self._execution = execution
        self._journal = journal
        self._constructeur = constructeur

    def sur_bougie(self, bougie: BougieEnrichie) -> None:
        for strategie in self._strategies:
            resultat = strategie.sur_cloture(bougie)
            self._journal.ajouter(self._constructeur.cloture_bougie(strategie.strategie_id, bougie, resultat))
            if resultat.signal is not None:
                self._traiter_signal(strategie, resultat.signal)

    def _traiter_signal(self, strategie: Strategie, signal: Signal) -> None:
        if signal.strategie != strategie.strategie_id:
            raise ValueError('un signal porte l\'identifiant de la méthode qui l\'émet')
        cle = CleIntention.du_signal(self._deployment_id, signal)
        instant = signal.cloture_ms
        fondamental = self._fondamental.autoriser(signal.symbole, signal.sens, instant)
        contexte = None
        if not fondamental.autorise:
            motif = fondamental.motif
        else:
            contexte = self._contexte_ia.decision(signal.symbole, instant)
            motif = (MotifRefus.AI_CONTEXT_VETO if contexte.etat is EtatContexteIA.BLOCK
                     else MotifRefus.ENVIRONMENT_NOT_READY)
        issue = self._execution.traiter_refus(motif, instant)
        self._journal.ajouter(self._constructeur.intention(
            instant, cle, signal, fondamental, contexte, Decision.REFUS, motif, ordre_envoye=False))
        strategie.appliquer_issue(cle, issue)

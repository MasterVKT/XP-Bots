"""Segments minimaux S1 (analyse des lignes de ticks) et S5 (exécution papier) et boucle de rejeu du squelette.

Segments minimaux du squelette, remplacés en phase 10 par l'artefact `journal-rejeu` (analyse des ticks et
simulateur C10). Contrat des coutures : mcl/squelette/COUTURES.md. Cœur pur : les lignes sont lues par
l'infrastructure. Types du noyau : `Tick` (`c1a_marche`), `Sens` (`c1c_domaine`), `Enregistrement` (`c2_journal`).

Format des lignes : CSV UTF-8 à en-tête `canonical_symbol,broker_symbol,time_utc_ms,sequence,bid,ask` (format
canonique du document 08, §6.1, ici sans compression). Exécution papier minimale : entrée remplie au premier
tick suivant la soumission (achat à l'Ask, vente au Bid), sans coût ; protections natives contrôlées à partir du
tick suivant le remplissage, achat sur Bid et vente sur Ask, au prix du tick qui les déclenche ; clôture au
premier tick suivant du symbole. Limites assumées : aucun délai, aucun tick adverse, aucun remplissage partiel,
aucun coût (simulateur C10 en phase 10).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
import math
from typing import Iterable, Iterator, Protocol

from xpbots.execution.squelette import CommandeCloture, CommandeEntree
from xpbots.noyau.c1a_marche import ErreurMarche, Tick
from xpbots.noyau.c1c_domaine import Sens
from xpbots.noyau.c2_journal import Enregistrement
from xpbots.orchestration.squelette import SortieMoteur

COLONNES_TICKS = ('canonical_symbol', 'broker_symbol', 'time_utc_ms', 'sequence', 'bid', 'ask')


class ErreurDonnees(ValueError):
    """Fichier de ticks refusé : format, ordre ou valeur invalide."""


def _entier(texte: str, nom: str, ligne: int) -> int:
    if not texte.isascii() or not texte.isdigit():
        raise ErreurDonnees(f'ligne {ligne} : {nom} doit être un entier positif ou nul')
    return int(texte)


def _prix(texte: str, nom: str, ligne: int) -> float:
    try:
        valeur = float(texte)
    except ValueError as erreur:
        raise ErreurDonnees(f'ligne {ligne} : {nom} illisible') from erreur
    if not math.isfinite(valeur) or valeur <= 0:
        raise ErreurDonnees(f'ligne {ligne} : {nom} doit être un nombre fini strictement positif')
    return valeur


def analyser_lignes_ticks(lignes: Iterable[str]) -> Iterator[Tick]:
    """Convertir les lignes d'un fichier de ticks en ticks ordonnés ; toute anomalie lève `ErreurDonnees`."""
    iterateur = iter(lignes)
    entete = next(iterateur, None)
    if entete is None:
        raise ErreurDonnees('fichier de ticks vide')
    if tuple(entete.split(',')) != COLONNES_TICKS:
        raise ErreurDonnees(f'en-tête inattendu : {entete!r}')
    precedent: tuple[int, int] | None = None
    for numero, ligne in enumerate(iterateur, start=2):
        champs = ligne.split(',')
        if len(champs) != len(COLONNES_TICKS):
            raise ErreurDonnees(f'ligne {numero} : {len(COLONNES_TICKS)} champs attendus')
        symbole, symbole_courtier, instant, sequence, bid, ask = champs
        if not symbole or not symbole_courtier:
            raise ErreurDonnees(f'ligne {numero} : symbole vide')
        instant_ms = _entier(instant, 'time_utc_ms', numero)
        try:  # en rejeu, l'heure de réception est l'heure fournisseur (P-04)
            tick = Tick(symbole, symbole_courtier, instant_ms, instant_ms, _entier(sequence, 'sequence', numero),
                        _prix(bid, 'bid', numero), _prix(ask, 'ask', numero))
        except ErreurMarche as erreur:
            raise ErreurDonnees(f'ligne {numero} : {erreur}') from erreur
        cle = (tick.instant_fournisseur_ms, tick.numero)
        if precedent is not None and cle <= precedent:
            raise ErreurDonnees(f'ligne {numero} : ticks non strictement ordonnés par instant puis séquence')
        precedent = cle
        yield tick


@dataclass(frozen=True)
class Remplissage:
    cle: str
    symbole: str
    sens: Sens
    volume: Decimal
    prix: float
    instant_ms: int


@dataclass(frozen=True)
class SortieProtection:
    cle: str
    cause: str
    prix: float
    instant_ms: int


@dataclass(frozen=True)
class ClotureExecutee:
    cle: str
    prix: float
    instant_ms: int


@dataclass(frozen=True)
class RefusCommande:
    cle: str
    raison: str


Reponse = Remplissage | SortieProtection | ClotureExecutee | RefusCommande


@dataclass
class _Position:
    symbole: str
    sens: Sens
    volume: Decimal
    sl: float
    tp: float


class ExecutionPapierMinimale:
    """Exécute au marché les commandes du moteur sur les ticks suivants, sans coût."""

    def __init__(self) -> None:
        self._en_attente: list[CommandeEntree | CommandeCloture] = []
        self._positions: dict[str, _Position] = {}

    @property
    def positions_ouvertes(self) -> tuple[str, ...]:
        return tuple(self._positions)

    def soumettre(self, commandes: Iterable[CommandeEntree | CommandeCloture]) -> None:
        for commande in commandes:
            if not isinstance(commande, (CommandeEntree, CommandeCloture)):
                raise TypeError(f'commande inconnue : {commande!r}')
            self._en_attente.append(commande)

    def sur_tick(self, tick: Tick) -> tuple[Reponse, ...]:
        reponses: list[Reponse] = []
        for cle, position in list(self._positions.items()):
            if position.symbole != tick.symbole:
                continue
            if position.sens is Sens.ACHAT:
                prix = tick.bid
                cause = 'SL' if prix <= position.sl else 'TP' if prix >= position.tp else None
            else:
                prix = tick.ask
                cause = 'SL' if prix >= position.sl else 'TP' if prix <= position.tp else None
            if cause is not None:
                del self._positions[cle]
                reponses.append(SortieProtection(cle, cause, prix, tick.instant_reception_ms))
        restantes: list[CommandeEntree | CommandeCloture] = []
        for commande in self._en_attente:
            if isinstance(commande, CommandeCloture):
                position = self._positions.get(commande.cle)
                if position is None:
                    reponses.append(RefusCommande(commande.cle, 'POSITION_INCONNUE'))
                elif position.symbole != tick.symbole:
                    restantes.append(commande)
                else:
                    del self._positions[commande.cle]
                    prix = tick.bid if position.sens is Sens.ACHAT else tick.ask
                    reponses.append(ClotureExecutee(commande.cle, prix, tick.instant_reception_ms))
            elif commande.symbole != tick.symbole:
                restantes.append(commande)
            elif commande.cle in self._positions:
                reponses.append(RefusCommande(commande.cle, 'CLE_DEJA_OUVERTE'))
            else:
                prix = tick.ask if commande.sens is Sens.ACHAT else tick.bid
                self._positions[commande.cle] = _Position(commande.symbole, commande.sens, commande.volume,
                                                          commande.sl, commande.tp)
                reponses.append(Remplissage(commande.cle, commande.symbole, commande.sens, commande.volume,
                                            prix, tick.instant_reception_ms))
        self._en_attente = restantes
        return tuple(reponses)


class Moteur(Protocol):
    def traiter_tick(self, tick: Tick) -> SortieMoteur:
        ...


@dataclass(frozen=True)
class ResultatRejeu:
    nombre_ticks: int
    enregistrements: tuple[Enregistrement, ...]
    reponses: tuple[Reponse, ...] = field(default=())


def rejouer(ticks: Iterable[Tick], moteur: Moteur, execution: ExecutionPapierMinimale) -> ResultatRejeu:
    """Pour chaque tick : réponses de l'exécution d'abord (C08), puis moteur, puis soumission des commandes."""
    nombre = 0
    enregistrements: list[Enregistrement] = []
    reponses: list[Reponse] = []
    for tick in ticks:
        nombre += 1
        reponses.extend(execution.sur_tick(tick))
        sortie = moteur.traiter_tick(tick)
        enregistrements.extend(sortie.enregistrements)
        execution.soumettre(sortie.commandes)
    return ResultatRejeu(nombre, tuple(enregistrements), tuple(reponses))

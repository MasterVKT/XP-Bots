"""Ports du squelette : interfaces que les segments minimaux puis les artefacts de chair implémentent.

Ports disponibles depuis la phase 1 : `SourceTicksHistoriques`, `Journal`, `Strategie`, `ControleFondamental`,
`ContexteIA` ; depuis la phase 2 : `Stockage`. Les autres ports (flux de ticks réel, horloge, courtier, calculs
courtier, sources fondamentales, lecteur de snapshot, transport HTTP) arrivent avec leur premier consommateur
(`mcl/robot-ema-v3/COUTURES.md`).
"""
from __future__ import annotations

from typing import Iterator, Mapping, Protocol, runtime_checkable

from xpbots.noyau.decisions import (CleIntention, DecisionContexteIA, DecisionFondamentale, IssueSignal,
                                    ResultatTechnique, Sens)
from xpbots.noyau.marche import BougieEnrichie, Tick


@runtime_checkable
class SourceTicksHistoriques(Protocol):
    """Ticks rejoués dans l'ordre strict (ms, séquence) et couverture déclarée par leur manifeste."""

    def symboles(self) -> tuple[str, ...]:
        """Symboles canoniques déclarés par le manifeste."""

    def ticks(self) -> Iterator[Tick]:
        """Ticks ordonnés ; lève une erreur au premier tick hors ordre ou hors manifeste."""

    def couverture(self, symbole: str) -> tuple[tuple[int, int], ...]:
        """Intervalles UTC [début, fin) en ms où le flux du symbole est établi (aucun seuil inventé, R5)."""

    def seances(self, symbole: str) -> tuple[tuple[int, int], ...]:
        """Séances de cotation natives UTC [début, fin) en ms déclarées pour le symbole (C04)."""

    def fin_donnees_ms(self) -> int:
        """Instant jusqu'auquel l'horloge de rejeu peut avancer après le dernier tick."""

    def empreintes(self) -> Mapping[str, str]:
        """SHA-256 des fichiers de données, pour le journal d'initialisation."""


@runtime_checkable
class Stockage(Protocol):
    """État durable clé → octets ; une écriture remplace atomiquement la valeur de sa clé."""

    def lire(self, cle: str) -> bytes | None:
        """Valeur enregistrée, ou None si la clé n'existe pas."""

    def ecrire(self, cle: str, valeur: bytes) -> None:
        """Enregistre la valeur ; elle survit au redémarrage du robot (adaptateur réel)."""


@runtime_checkable
class Journal(Protocol):
    """Destination en ajout seul des enregistrements C09 déjà validés."""

    def ajouter(self, enregistrement: Mapping[str, object]) -> None:
        """Ajoute un enregistrement ; refuse un enregistrement non conforme."""


@runtime_checkable
class Strategie(Protocol):
    """Méthode indépendante appelée à chaque clôture ; le tick size et le profil sont fournis à la construction."""

    strategie_id: str

    def sur_cloture(self, bougie: BougieEnrichie) -> ResultatTechnique:
        """Signal ou motif technique pour cette bougie clôturée."""

    def appliquer_issue(self, cle: CleIntention, issue: IssueSignal) -> None:
        """Issue définitive d'un signal émis par cette méthode (fill ou refus)."""


@runtime_checkable
class ControleFondamental(Protocol):
    """Contrôle C05 obligatoire au signal et juste avant l'ordre."""

    def autoriser(self, symbole: str, sens: Sens, instant_ms: int) -> DecisionFondamentale:
        """Autorisation ou refus avec les seules informations connues à cet instant."""


@runtime_checkable
class ContexteIA(Protocol):
    """Contexte IA lu en mémoire, BLOCK ou NEUTRAL ; le bras A/B est porté par l'instance."""

    def decision(self, symbole: str, instant_ms: int) -> DecisionContexteIA:
        """Décision sans attente réseau ni appel de modèle."""

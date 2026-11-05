"""Enchaînement minimal du squelette (segment S4) : tick → bougies closes → stratégie → coordinateur → journal.

Segment minimal du squelette, remplacé en phase 9 par le moteur de décision de l'artefact `orchestration`.
Contrat de la couture : mcl/squelette/COUTURES.md. Cœur pur : il reçoit des ticks et rend des enregistrements du
journal du noyau (`xpbots.noyau.c2_journal`) et des commandes, sans horloge ni fichier. La stratégie est injectée
(D-18) : ce module n'importe aucun moteur. Chaque bougie close donne un enregistrement `CLOTURE` ; chaque signal
présenté au coordinateur donne en plus un enregistrement `INTENTION` refusé.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from xpbots.donnees.squelette import AgregateurM15
from xpbots.execution.squelette import CommandeCloture, CommandeEntree, CoordinateurMinimal
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1a_marche import Bougie, Tick
from xpbots.noyau.c1c_domaine import CleIntention, Issue, NatureIssue, ResultatTechnique, SignalTechnique
from xpbots.noyau.c2_journal import (Enregistrement, Enveloppe, empreintes_regles, enregistrement_cloture,
                                     enregistrement_intention)

BRAS_UNIQUE = 'REFERENCE'
LONGUEUR_EMPREINTE_SQUELETTE = 16  # provisoire : la longueur du commentaire est qualifiée par la sonde S-05 (D-08)


class Strategie(Protocol):
    """Contrat structurel d'une stratégie injectée."""

    identifiant: str

    def sur_cloture(self, bougie: Bougie) -> ResultatTechnique:
        ...


@dataclass(frozen=True)
class SortieMoteur:
    """Ce que rend le moteur pour un événement : enregistrements du journal et commandes."""

    enregistrements: tuple[Enregistrement, ...]
    commandes: tuple[CommandeEntree | CommandeCloture, ...]


class MoteurMinimal:
    """Moteur minimal : un agrégateur par symbole, une stratégie, le coordinateur minimal."""

    def __init__(self, strategie: Strategie, configuration: ConfigurationFigee, mode: str, deploiement: str) -> None:
        self._strategie = strategie
        self._duree_ms = configuration.technique.commun.timeframe_seconds * 1000
        self._empreintes = empreintes_regles(configuration)
        self._mode = mode
        self._deploiement = deploiement
        self._coordinateur = CoordinateurMinimal()
        self._agregateurs: dict[str, AgregateurM15] = {}
        self._numero = 0

    def _enveloppe(self, instant_ms: int) -> Enveloppe:
        self._numero += 1
        return Enveloppe(self._deploiement, BRAS_UNIQUE, self._mode, self._numero, instant_ms, self._empreintes)

    def traiter_tick(self, tick: Tick) -> SortieMoteur:
        agregateur = self._agregateurs.get(tick.symbole)
        if agregateur is None:
            agregateur = AgregateurM15(tick.symbole, self._duree_ms)
            self._agregateurs[tick.symbole] = agregateur
        enregistrements: list[Enregistrement] = []
        commandes: list[CommandeEntree | CommandeCloture] = []
        for bougie in agregateur.ajouter(tick):
            resultat = self._strategie.sur_cloture(bougie)
            enregistrements.append(enregistrement_cloture(
                self._enveloppe(tick.instant_reception_ms), bougie=bougie, resultat=resultat, profil=None,
                indicateurs={}, etat_strategie={}, permission=None, version_calendrier=None, snapshot_ia=None))
            if isinstance(resultat, SignalTechnique):
                decision = self._coordinateur.decider(resultat)
                cle = CleIntention(self._deploiement, resultat.strategie, resultat.symbole, resultat.cloture_ms,
                                   resultat.sens)
                issue = Issue(cle, NatureIssue.REFUSEE, tick.instant_reception_ms, decision.motif, decision.detail)
                enregistrements.append(enregistrement_intention(
                    self._enveloppe(tick.instant_reception_ms), cle=cle,
                    longueur_empreinte=LONGUEUR_EMPREINTE_SQUELETTE, tentatives=[], issue=issue, cout_ia_usd=None))
                commandes.extend(decision.commandes)
        return SortieMoteur(tuple(enregistrements), tuple(commandes))


def fabriquer_moteur_minimal(strategie: Strategie, configuration: ConfigurationFigee, mode: str,
                             deploiement: str = 'squelette') -> MoteurMinimal:
    """Point de composition du moteur minimal, appelé par la coquille."""
    return MoteurMinimal(strategie, configuration, mode, deploiement)

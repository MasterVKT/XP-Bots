"""Enchaînement minimal du squelette (segment S4) : tick → bougies enrichies → stratégie → coordinateur → journal.

Segment minimal du squelette, remplacé en phase 9 par le moteur de décision de l'artefact `orchestration`.
Contrat de la couture : mcl/squelette/COUTURES.md. Cœur pur : il reçoit des ticks et rend des enregistrements du
journal du noyau (`xpbots.noyau.c2_journal`) et des commandes, sans horloge ni fichier. Les bougies viennent de
l'artefact `donnees-temps` (`xpbots.donnees.c3_flux.FluxBougies`, un flux par symbole, construit sur les horaires
et les périodes couvertes fournies par la coquille). La stratégie est injectée (D-18) : ce module n'importe aucun
moteur. Chaque M15 close donne un enregistrement `CLOTURE` ; chaque signal présenté au coordinateur donne en plus
un enregistrement `INTENTION` refusé ; chaque changement d'état de trou ou anomalie de données donne un
enregistrement `ALERTE`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from xpbots.donnees.c0a_types import AnomalieDonnees, BougieEnrichie, ChangementTrou, UniteTemps
from xpbots.donnees.c1c_couverture import RegistreCouverture
from xpbots.donnees.c3_flux import FluxBougies
from xpbots.execution.squelette import CommandeCloture, CommandeEntree, CoordinateurMinimal
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle
from xpbots.noyau.c1c_domaine import CleIntention, Issue, NatureIssue, ResultatTechnique, SignalTechnique
from xpbots.noyau.c2_journal import (Enregistrement, Enveloppe, TypeEnregistrement, empreintes_regles,
                                     enregistrement, enregistrement_cloture, enregistrement_intention)

BRAS_UNIQUE = 'REFERENCE'
LONGUEUR_EMPREINTE_SQUELETTE = 16  # provisoire : la longueur du commentaire est qualifiée par la sonde S-05 (D-08)


class Strategie(Protocol):
    """Contrat structurel d'une stratégie injectée."""

    identifiant: str

    def sur_bougie(self, bougie: BougieEnrichie) -> ResultatTechnique | None:
        """Un résultat pour chaque M15 close, rien pour une H1."""
        ...


@dataclass(frozen=True)
class SortieMoteur:
    """Ce que rend le moteur pour un événement : enregistrements du journal et commandes."""

    enregistrements: tuple[Enregistrement, ...]
    commandes: tuple[CommandeEntree | CommandeCloture, ...]


class MoteurMinimal:
    """Moteur minimal : un flux de bougies par symbole, une stratégie, le coordinateur minimal."""

    def __init__(self, strategie: Strategie, configuration: ConfigurationFigee, mode: str, deploiement: str,
                 horaires: Mapping[str, HorairesCotation], periodes_couvertes: Mapping[str, Sequence[Intervalle]]) -> None:
        if set(horaires) != set(periodes_couvertes):
            raise ValueError('horaires et périodes couvertes attendus pour les mêmes symboles')
        self._strategie = strategie
        self._empreintes = empreintes_regles(configuration)
        self._mode = mode
        self._deploiement = deploiement
        self._coordinateur = CoordinateurMinimal()
        self._flux = {symbole: FluxBougies(symbole, configuration.technique, horaires[symbole],
                                           RegistreCouverture(periodes_couvertes[symbole])) for symbole in horaires}
        self._numero = 0

    def _enveloppe(self, instant_ms: int) -> Enveloppe:
        self._numero += 1
        return Enveloppe(self._deploiement, BRAS_UNIQUE, self._mode, self._numero, instant_ms, self._empreintes)

    def _alerte(self, evenement: ChangementTrou | AnomalieDonnees, instant_ms: int) -> Enregistrement:
        if isinstance(evenement, ChangementTrou):
            contenu = {'alerte': 'DATA_GAP', 'symbole': evenement.symbole, 'nature': evenement.nature.value,
                       'intervalle_utc_ms': evenement.intervalle_ms, 'connu_utc_ms': evenement.instant_ms}
        else:
            contenu = {'alerte': evenement.raison, 'symbole': evenement.symbole, 'connu_utc_ms': evenement.instant_ms}
        return enregistrement(TypeEnregistrement.ALERTE, self._enveloppe(instant_ms), contenu)

    def traiter_tick(self, tick: Tick) -> SortieMoteur:
        flux = self._flux.get(tick.symbole)
        if flux is None:
            raise ValueError(f'symbole sans horaires ni couverture : {tick.symbole!r}')
        instant = tick.instant_reception_ms
        enregistrements: list[Enregistrement] = []
        commandes: list[CommandeEntree | CommandeCloture] = []
        for evenement in flux.sur_tick(tick):
            if not isinstance(evenement, BougieEnrichie):
                enregistrements.append(self._alerte(evenement, instant))
                continue
            resultat = self._strategie.sur_bougie(evenement)
            if evenement.unite is not UniteTemps.M15:
                if resultat is not None:
                    raise ValueError('la stratégie ne rend rien pour une H1')
                continue
            if not isinstance(resultat, ResultatTechnique):
                raise ValueError('la stratégie rend un résultat technique pour chaque M15 close')
            indicateurs = {} if evenement.indicateurs is None else {
                'tr': evenement.indicateurs.tr, 'atr': evenement.indicateurs.atr, 'a': evenement.indicateurs.a,
                'rang': evenement.indicateurs.rang}
            enregistrements.append(enregistrement_cloture(
                self._enveloppe(instant), bougie=evenement.bougie, resultat=resultat, profil=None,
                indicateurs=indicateurs, etat_strategie={}, permission=None, version_calendrier=None, snapshot_ia=None))
            if isinstance(resultat, SignalTechnique):
                decision = self._coordinateur.decider(resultat)
                cle = CleIntention(self._deploiement, resultat.strategie, resultat.symbole, resultat.cloture_ms,
                                   resultat.sens)
                issue = Issue(cle, NatureIssue.REFUSEE, instant, decision.motif, decision.detail)
                enregistrements.append(enregistrement_intention(
                    self._enveloppe(instant), cle=cle, longueur_empreinte=LONGUEUR_EMPREINTE_SQUELETTE, tentatives=[],
                    issue=issue, cout_ia_usd=None))
                commandes.extend(decision.commandes)
        return SortieMoteur(tuple(enregistrements), tuple(commandes))


def fabriquer_moteur_minimal(strategie: Strategie, configuration: ConfigurationFigee, mode: str,
                             deploiement: str = 'squelette', *, horaires: Mapping[str, HorairesCotation],
                             periodes_couvertes: Mapping[str, Sequence[Intervalle]]) -> MoteurMinimal:
    """Point de composition du moteur minimal, appelé par la coquille."""
    return MoteurMinimal(strategie, configuration, mode, deploiement, horaires, periodes_couvertes)

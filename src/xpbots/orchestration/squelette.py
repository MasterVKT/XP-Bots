"""Enchaînement minimal du squelette (segment S4) : tick → bougies enrichies → stratégie → coordinateur → journal.

Segment minimal du squelette, remplacé en phase 9 par le moteur de décision de l'artefact `orchestration`.
Contrat de la couture : mcl/squelette/COUTURES.md. Cœur pur : il reçoit des ticks et rend des enregistrements du
journal du noyau (`xpbots.noyau.c2_journal`) et des commandes, sans horloge ni fichier. Les bougies viennent de
l'artefact `london-donnees-temps` (`xpbots.donnees.c3_flux.FluxBougies`, un flux par symbole, construit sur les horaires
et les périodes couvertes fournies par la coquille). La stratégie est injectée (D-18) : ce module n'importe aucun
moteur. Chaque M15 close donne un enregistrement `CLOTURE` ; chaque signal présenté au coordinateur donne en plus
des mises à jour `INTENTION` pour la même clé persistante ; chaque changement d'état de trou ou anomalie de données donne un
enregistrement `ALERTE`.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Mapping, Protocol, Sequence, runtime_checkable

from xpbots.donnees.c0a_types import AnomalieDonnees, BougieEnrichie, ChangementTrou, UniteTemps
from xpbots.donnees.c1c_couverture import RegistreCouverture
from xpbots.donnees.c3_flux import FluxBougies
from xpbots.execution.c4_cycle import CommandeExecution
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.execution.c6_coordinateur import CoordinateurCompte, LotCoordinateur
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1a_marche import Tick, Cotation
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle
from xpbots.noyau.c1c_domaine import CleIntention, Issue, NatureIssue, ResultatTechnique, SignalTechnique
from xpbots.noyau.c2_journal import (Enregistrement, Enveloppe, TypeEnregistrement, empreintes_regles,
                                     enregistrement, enregistrement_cloture)

BRAS_UNIQUE = 'REFERENCE'
LONGUEUR_EMPREINTE_SQUELETTE = 16  # provisoire : la longueur du commentaire est qualifiée par la sonde S-05 (D-08)
SCENARIO_TECHNIQUE = ControleTechniqueNeutre.scenario


def composer_coordinateur_neutre(configuration,deploiement,profils,port,instant_ms,*,observation,base_utc):
    """Composition pure du coordinateur réel pour le seul rejeu technique synthétique."""
    return CoordinateurCompte(configuration.technique,deploiement,profils,port.profil_compte,
        port,ControleTechniqueNeutre(),instant_ms,longueur_empreinte=LONGUEUR_EMPREINTE_SQUELETTE,
        mode='REJEU',observation=observation,base_utc=base_utc)


@runtime_checkable
class Strategie(Protocol):
    """Contrat structurel d'une stratégie injectée."""

    identifiant: str

    def sur_bougie(self, bougie: BougieEnrichie) -> ResultatTechnique | None:
        """Un résultat pour chaque M15 close, rien pour une H1."""
        ...

    def sur_issue(self, issue: Issue) -> None:
        """Applique l'issue confirmée sans produire de commande ni de signal rétroactif."""
        ...


@dataclass(frozen=True)
class SortieMoteur:
    """Ce que rend le moteur pour un événement : enregistrements du journal et commandes."""

    enregistrements: tuple[Enregistrement, ...]
    commandes: tuple[CommandeExecution, ...]
    lot: LotCoordinateur | None = None


def _journal(valeur):
    """Adapter les valeurs pures aux contenus du journal canonique du noyau."""
    if isinstance(valeur,(date,datetime)): return valeur.isoformat()
    if is_dataclass(valeur): return {f.name:_journal(getattr(valeur,f.name)) for f in fields(valeur)}
    if isinstance(valeur,Mapping): return {k:_journal(v) for k,v in valeur.items()}
    if isinstance(valeur,(set,frozenset)): return tuple(_journal(v) for v in sorted(valeur))
    if isinstance(valeur,(tuple,list)): return tuple(_journal(v) for v in valeur)
    return valeur


def _issue(issue):
    if issue is None: return None
    return dict(nature=issue.nature.value,instant_utc_ms=issue.instant_ms,
        motif=issue.motif.value if issue.motif is not None else None,detail=issue.detail,
        cause=issue.cause.value if issue.cause is not None else None)


class MoteurMinimal:
    """Moteur minimal : un flux de bougies par symbole, une stratégie injectée, le coordinateur commun réel."""

    def __init__(self, strategie: Strategie, configuration: ConfigurationFigee, mode: str, deploiement: str,
                 horaires: Mapping[str, HorairesCotation], periodes_couvertes: Mapping[str, Sequence[Intervalle]],
                 coordinateur:CoordinateurCompte,profils:Mapping,profil_compte=None,scenario_fondamental=None) -> None:
        if not isinstance(strategie, Strategie):
            raise ValueError('stratégie injectée avec identifiant, sur_bougie et sur_issue attendue')
        if set(horaires) != set(periodes_couvertes):
            raise ValueError('horaires et périodes couvertes attendus pour les mêmes symboles')
        if not isinstance(coordinateur,CoordinateurCompte) or set(profils)!=set(horaires):
            raise ValueError('coordinateur réel et profils explicites requis')
        self._strategie = strategie
        self._empreintes = empreintes_regles(configuration)
        self._mode = mode
        self._deploiement = deploiement
        self._coordinateur = coordinateur
        self._profils=dict(profils);self._profil_compte=profil_compte;self._scenario=scenario_fondamental
        self._intentions_journalisees={}
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

    def alerte(self,code,instant_ms):
        return enregistrement(TypeEnregistrement.ALERTE,self._enveloppe(instant_ms),{'alerte':code})

    @property
    def prochaine_echeance_ms(self): return self._coordinateur.prochaine_echeance_ms

    def _consommer(self,lot,instant):
        lignes=[]
        for issue in lot.issues:
            if issue.cle.strategie==self._strategie.identifiant: self._strategie.sur_issue(issue)
        for trace in lot.traces:
            lignes.append(enregistrement(trace.type,self._enveloppe(instant),dict(trace.donnees)))
        cycles={c.etat.cle:c for c in lot.etat.reprise.cycles}
        for d in lot.etat.intentions:
            if self._intentions_journalisees.get(d.cle)==d: continue
            self._intentions_journalisees[d.cle]=d
            nouvelles=tuple(i for i in lot.issues if i.cle==d.cle)
            i=nouvelles[-1] if nouvelles else None
            cycle=cycles.get(d.cle);plan=cycle.plan if cycle is not None else None
            motif=d.issue.motif if d.issue is not None else None
            contenu=dict(cle=d.cle.texte(),empreinte_cle=d.cle.empreinte(LONGUEUR_EMPREINTE_SQUELETTE),
                strategie=d.cle.strategie,symbole=d.cle.symbole,sens=d.cle.sens.value,
                tentatives=_journal(d.tentatives),issue=_issue(i),issues_nouvelles=tuple(_issue(v) for v in nouvelles),
                derniere_issue=_issue(d.issue),motif=motif.value if motif is not None else None,
                detail=d.issue.detail if d.issue is not None else None,cout_ia_usd=None,
                etat_intention=d.statut.value,signal=_journal(d.signal),
                instrument=_journal(cycle.profil if cycle is not None else self._profils.get(d.cle.symbole)),
                courtier=_journal(self._profil_compte),compte=_journal(lot.compte),
                permission={'scenario':self._scenario},version_calendrier=None,snapshot_ia=None,
                risque_initial=plan.risque if plan is not None else None,
                budget_gele=plan.budget_gele if plan is not None else None,
                fonds_propres_reference=plan.fonds_propres_reference if plan is not None else None,
                frais_calcules=plan.mesure_risque.frais if plan is not None else None,
                marge_calculee=plan.marge_totale_consideree if plan is not None else None,
                reservations=_journal(lot.etat.reprise.reservations),gardes=_journal(lot.etat.reprise.gardes))
            lignes.append(enregistrement(TypeEnregistrement.INTENTION,self._enveloppe(instant),contenu))
        return lignes

    def traiter_evenement(self,instant_ms,*,reponses=(),observation=None,base_utc=None):
        lot=self._coordinateur.traiter(instant_ms,reponses=reponses,observation=observation,base_utc=base_utc)
        return SortieMoteur(tuple(self._consommer(lot,instant_ms)),lot.commandes,lot)

    def confirmer_persistance(self,preuve,instant_ms):
        lot=self._coordinateur.confirmer_persistance(preuve,instant_ms)
        return SortieMoteur(tuple(self._consommer(lot,instant_ms)),lot.commandes,lot)

    def traiter_tick(self,tick:Tick,**kwargs)->SortieMoteur:
        return self.traiter_ticks((tick,),**kwargs)

    def traiter_ticks(self,ticks,*,reponses=(),observation=None,base_utc=None)->SortieMoteur:
        ticks=tuple(ticks)
        if not ticks or any(not isinstance(t,Tick) or t.symbole not in self._flux for t in ticks):
            raise ValueError('ticks de symboles configurés requis')
        if len({t.instant_reception_ms for t in ticks})!=1: raise ValueError('un instant de réception par groupe requis')
        instant=ticks[0].instant_reception_ms
        cotations={t.symbole:Cotation(t.symbole,Decimal(str(t.bid)),Decimal(str(t.ask)),
            t.instant_fournisseur_ms,t.instant_reception_ms) for t in ticks}
        lot=self._coordinateur.traiter(instant,cotations=tuple(cotations.values()),reponses=reponses,
            observation=observation,base_utc=base_utc)
        enregistrements=self._consommer(lot,instant);commandes=list(lot.commandes);signaux=[]
        for tick in ticks:
            for evenement in self._flux[tick.symbole].sur_tick(tick):
                if not isinstance(evenement,BougieEnrichie):
                    enregistrements.append(self._alerte(evenement,instant));continue
                resultat=self._strategie.sur_bougie(evenement)
                if evenement.unite is not UniteTemps.M15:
                    if resultat is not None: raise ValueError('la stratégie ne rend rien pour une H1')
                    continue
                if not isinstance(resultat,ResultatTechnique): raise ValueError('résultat technique requis pour chaque M15')
                indicateurs={} if evenement.indicateurs is None else dict(tr=evenement.indicateurs.tr,
                    atr=evenement.indicateurs.atr,a=evenement.indicateurs.a,rang=evenement.indicateurs.rang)
                record=enregistrement_cloture(self._enveloppe(instant),bougie=evenement.bougie,resultat=resultat,
                    profil=self._profils[tick.symbole],indicateurs=indicateurs,etat_strategie={},
                    permission={'scenario':self._scenario},version_calendrier=None,snapshot_ia=None)
                enregistrements.append(enregistrement(record.type,record.enveloppe,
                    {**record.contenu,'compte':_journal(lot.compte),'courtier':_journal(self._profil_compte)}))
                if isinstance(resultat,SignalTechnique): signaux.append(resultat)
        if signaux:
            lot=self._coordinateur.traiter(instant,signaux=tuple(signaux),base_utc=base_utc)
            enregistrements.extend(self._consommer(lot,instant));commandes.extend(lot.commandes)
        return SortieMoteur(tuple(enregistrements),tuple(commandes),lot)


def fabriquer_moteur_minimal(strategie: Strategie, configuration: ConfigurationFigee, mode: str,
                             deploiement: str = 'squelette', *, horaires: Mapping[str, HorairesCotation],
                             periodes_couvertes: Mapping[str, Sequence[Intervalle]],coordinateur:CoordinateurCompte,
                             profils:Mapping,profil_compte=None,scenario_fondamental=None) -> MoteurMinimal:
    """Point de composition du moteur minimal, appelé par la coquille."""
    return MoteurMinimal(strategie,configuration,mode,deploiement,horaires,periodes_couvertes,
        coordinateur,profils,profil_compte,scenario_fondamental)

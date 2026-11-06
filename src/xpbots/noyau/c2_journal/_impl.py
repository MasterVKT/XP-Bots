"""Implémentation de la couche 2 (journal). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
import json
import math
import re
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from xpbots.noyau.c0a_temps import ErreurInstant, verifier_instant
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1a_marche import Bougie
from xpbots.noyau.c1b_instrument import ProfilInstrument
from xpbots.noyau.c1c_domaine import (AbsenceDeSignal, CleIntention, ErreurDomaine, Issue, ResultatTechnique,
                                      SignalTechnique, verifier_motif)

VERSION_SCHEMA = 'xp-journal-v1'
MODES = frozenset({'REJEU', 'PAPER', 'PAPER_AB', 'DEMO', 'REEL'})
BRAS = frozenset({'REFERENCE', 'IA'})
_RESERVEES = frozenset({'type', 'version_schema', 'deploiement', 'bras', 'mode', 'numero', 'instant_utc_ms',
                        'empreinte_regles'})
_EMPREINTE = re.compile(r'[0-9a-f]{64}')


class ErreurJournal(ValueError):
    """Enregistrement ou sérialisation refusés."""


class TypeEnregistrement(StrEnum):
    CLOTURE = 'CLOTURE'
    INTENTION = 'INTENTION'
    ORDRE = 'ORDRE'
    REPONSE = 'REPONSE'
    EXECUTION = 'EXECUTION'
    PROTECTION = 'PROTECTION'
    CLOTURE_POSITION = 'CLOTURE_POSITION'
    COMPTE = 'COMPTE'
    ALERTE = 'ALERTE'
    DEMARRAGE = 'DEMARRAGE'
    ARRET = 'ARRET'
    RAPPROCHEMENT = 'RAPPROCHEMENT'


CHAMPS_OBLIGATOIRES: Mapping[TypeEnregistrement, frozenset[str]] = MappingProxyType({
    **{t: frozenset() for t in TypeEnregistrement},
    TypeEnregistrement.CLOTURE: frozenset({'strategie', 'symbole', 'instrument', 'bougie', 'indicateurs',
                                           'etat_strategie', 'signal', 'motif', 'detail', 'permission',
                                           'version_calendrier', 'snapshot_ia'}),
    TypeEnregistrement.INTENTION: frozenset({'cle', 'empreinte_cle', 'strategie', 'symbole', 'sens', 'tentatives',
                                             'issue', 'motif', 'detail', 'cout_ia_usd'}),
})


def empreintes_regles(configuration: ConfigurationFigee) -> Mapping[str, str]:
    if not isinstance(configuration, ConfigurationFigee):
        raise ErreurJournal('configuration figée attendue')
    return MappingProxyType({'technique': configuration.technique.empreinte_canonique,
                             'ia': configuration.ia.empreinte_canonique})


@dataclass(frozen=True)
class Enveloppe:
    deploiement: str
    bras: str
    mode: str
    numero: int
    instant_utc_ms: int
    empreinte_regles: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.deploiement, str) or not self.deploiement:
            raise ErreurJournal('deploiement : texte non vide attendu')
        if self.bras not in BRAS:
            raise ErreurJournal(f'bras inconnu : {self.bras!r}')
        if self.mode not in MODES:
            raise ErreurJournal(f'mode inconnu : {self.mode!r}')
        if isinstance(self.numero, bool) or not isinstance(self.numero, int) or self.numero < 1:
            raise ErreurJournal('numero : entier ≥ 1 attendu')
        try:
            verifier_instant(self.instant_utc_ms)
        except ErreurInstant as erreur:
            raise ErreurJournal(f'instant_utc_ms : {erreur}') from erreur
        empreintes = self.empreinte_regles
        if (not isinstance(empreintes, Mapping) or set(empreintes) != {'technique', 'ia'}
                or not all(isinstance(v, str) and _EMPREINTE.fullmatch(v) for v in empreintes.values())):
            raise ErreurJournal('empreinte_regles : {technique, ia} en SHA-256 hexadécimal attendu')
        object.__setattr__(self, 'empreinte_regles', MappingProxyType(dict(empreintes)))


def _figer(valeur: Any, chemin: str) -> Any:
    if isinstance(valeur, Mapping):
        if not all(isinstance(cle, str) for cle in valeur):
            raise ErreurJournal(f'{chemin} : clés textuelles attendues')
        return MappingProxyType({cle: _figer(v, f'{chemin}.{cle}') for cle, v in valeur.items()})
    if isinstance(valeur, (list, tuple)):
        return tuple(_figer(v, chemin) for v in valeur)
    if isinstance(valeur, Decimal):
        if not valeur.is_finite():
            raise ErreurJournal(f'{chemin} : décimal non fini')
        return valeur
    if isinstance(valeur, float):
        if not math.isfinite(valeur):
            raise ErreurJournal(f'{chemin} : nombre non fini')
        return valeur
    if valeur is None or isinstance(valeur, (str, bool, int)):
        return valeur
    raise ErreurJournal(f'{chemin} : valeur non sérialisable {type(valeur).__name__}')


@dataclass(frozen=True)
class Enregistrement:
    type: TypeEnregistrement
    enveloppe: Enveloppe
    contenu: Mapping[str, Any]

    def __post_init__(self) -> None:
        try:
            type_ = TypeEnregistrement(self.type)
        except ValueError as erreur:
            raise ErreurJournal(f'type d\'enregistrement inconnu : {self.type!r}') from erreur
        object.__setattr__(self, 'type', type_)
        if not isinstance(self.enveloppe, Enveloppe):
            raise ErreurJournal('enveloppe attendue')
        if not isinstance(self.contenu, Mapping):
            raise ErreurJournal('contenu : correspondance attendue')
        reservees = sorted(_RESERVEES & set(self.contenu))
        if reservees:
            raise ErreurJournal(f'contenu : clés réservées à l\'enveloppe {reservees}')
        manquants = sorted(CHAMPS_OBLIGATOIRES[type_] - set(self.contenu))
        if manquants:
            raise ErreurJournal(f'{type_} : champs obligatoires absents {manquants}')
        if self.contenu.get('motif') is not None:
            try:
                verifier_motif(self.contenu['motif'], self.contenu.get('detail'))
            except ErreurDomaine as erreur:
                raise ErreurJournal(str(erreur)) from erreur
        object.__setattr__(self, 'contenu', _figer(self.contenu, 'contenu'))

    def vers_dict(self) -> dict[str, Any]:
        enveloppe = self.enveloppe
        return {'type': self.type, 'version_schema': VERSION_SCHEMA, 'deploiement': enveloppe.deploiement,
                'bras': enveloppe.bras, 'mode': enveloppe.mode, 'numero': enveloppe.numero,
                'instant_utc_ms': enveloppe.instant_utc_ms, 'empreinte_regles': enveloppe.empreinte_regles,
                **self.contenu}


def enregistrement(type_: TypeEnregistrement | str, enveloppe: Enveloppe, contenu: Mapping[str, Any]) -> Enregistrement:
    return Enregistrement(type_, enveloppe, contenu)


def _bougie(bougie: Bougie) -> dict[str, Any]:
    return {'debut_utc_ms': bougie.debut_ms, 'fin_utc_ms': bougie.fin_ms, 'duree_ms': bougie.duree_ms,
            'ouverture': bougie.ouverture, 'haut': bougie.haut, 'bas': bougie.bas, 'cloture': bougie.cloture,
            'evenements': bougie.nombre_evenements, 'valide': bougie.valide,
            'motif_invalidite': bougie.motif_invalidite, 'disponible_utc_ms': bougie.instant_disponibilite_ms}


def enregistrement_cloture(enveloppe: Enveloppe, *, bougie: Bougie, resultat: ResultatTechnique,
                           profil: ProfilInstrument | None, indicateurs: Mapping[str, Any],
                           etat_strategie: Mapping[str, Any], permission: Mapping[str, Any] | None,
                           version_calendrier: str | None, snapshot_ia: str | None) -> Enregistrement:
    if not isinstance(bougie, Bougie) or not isinstance(resultat, (SignalTechnique, AbsenceDeSignal)):
        raise ErreurJournal('bougie et résultat technique attendus')
    if resultat.symbole != bougie.symbole or resultat.cloture_ms != bougie.fin_ms:
        raise ErreurJournal('résultat et bougie incohérents (symbole ou clôture)')
    if profil is not None and (not isinstance(profil, ProfilInstrument) or profil.symbole != bougie.symbole):
        raise ErreurJournal('profil d\'instrument incohérent avec la bougie')
    if isinstance(resultat, SignalTechnique):
        signal = {'sens': resultat.sens, 'cloture_prix': resultat.cloture_prix,
                  'atr_reference': resultat.atr_reference, 'stop_technique': resultat.stop_technique,
                  'multiple_objectif': resultat.multiple_objectif}
        motif, detail = None, None
    else:
        signal, motif, detail = None, resultat.motif, resultat.detail
    instrument = None if profil is None else {
        'symbole_courtier': profil.symbole_courtier, 'taille_contrat': profil.taille_contrat,
        'tick_size': profil.tick_size, 'volume_min': profil.volume_min, 'volume_pas': profil.volume_pas}
    return Enregistrement(TypeEnregistrement.CLOTURE, enveloppe, {
        'strategie': resultat.strategie, 'symbole': bougie.symbole, 'instrument': instrument,
        'bougie': _bougie(bougie), 'indicateurs': indicateurs, 'etat_strategie': etat_strategie,
        'signal': signal, 'motif': motif, 'detail': detail, 'contexte': resultat.contexte,
        'permission': permission, 'version_calendrier': version_calendrier, 'snapshot_ia': snapshot_ia})


def enregistrement_intention(enveloppe: Enveloppe, *, cle: CleIntention, longueur_empreinte: int,
                             tentatives: Sequence[Mapping[str, Any]], issue: Issue, cout_ia_usd: Decimal | None,
                             details: Mapping[str, Any] | None = None) -> Enregistrement:
    if not isinstance(cle, CleIntention) or not isinstance(issue, Issue) or issue.cle != cle:
        raise ErreurJournal('clé d\'intention et issue de cette intention attendues')
    if cout_ia_usd is not None and (not isinstance(cout_ia_usd, Decimal) or cout_ia_usd < 0):
        raise ErreurJournal('cout_ia_usd : décimal ≥ 0 ou None attendu')
    try:
        empreinte = cle.empreinte(longueur_empreinte)
    except ErreurDomaine as erreur:
        raise ErreurJournal(str(erreur)) from erreur
    return Enregistrement(TypeEnregistrement.INTENTION, enveloppe, {
        'cle': cle.texte(), 'empreinte_cle': empreinte, 'strategie': cle.strategie, 'symbole': cle.symbole,
        'sens': cle.sens, 'cloture_utc_ms': cle.cloture_ms, 'tentatives': list(tentatives),
        'issue': {'nature': issue.nature, 'instant_utc_ms': issue.instant_ms, 'cause': issue.cause},
        'motif': issue.motif, 'detail': issue.detail, 'cout_ia_usd': cout_ia_usd, 'details': details})


def _json(valeur: Any) -> Any:
    if isinstance(valeur, Mapping):
        return {cle: _json(v) for cle, v in valeur.items()}
    if isinstance(valeur, (list, tuple)):
        return [_json(v) for v in valeur]
    if isinstance(valeur, Decimal):
        return format(valeur, 'f')
    if isinstance(valeur, StrEnum):
        return valeur.value
    return valeur


def serialiser(enregistrement_: Enregistrement) -> str:
    if not isinstance(enregistrement_, Enregistrement):
        raise ErreurJournal('enregistrement attendu')
    try:
        return json.dumps(_json(enregistrement_.vers_dict()), ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError) as erreur:
        raise ErreurJournal(f'sérialisation impossible : {erreur}') from erreur

"""Enregistrements du journal C09 : schéma fermé par type, validation et construction numérotée.

Types disponibles depuis la phase 1 : INITIALISATION, CLOTURE_BOUGIE, INTENTION. Les autres types (ordres,
exécutions, protections, sorties, gardes, alertes, rapprochements) s'ajoutent par extension additive avec leur
premier producteur.
"""
from __future__ import annotations

import copy
import math
import re
from datetime import date
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Mapping

from xpbots.noyau.config import BundleTechnique
from xpbots.noyau.decisions import (CleIntention, DecisionContexteIA, DecisionFondamentale, MotifRefus,
                                    ResultatTechnique, Signal)
from xpbots.noyau.json_canonique import JSONInvalide, serialiser
from xpbots.noyau.marche import BougieEnrichie, StatutBougie
from xpbots.noyau.temps import InstantInvalide, iso_depuis_ms, ms_depuis_iso


class EnregistrementInvalide(ValueError):
    """Enregistrement C09 incomplet, avec une clé en trop ou une valeur hors contrat."""


class TypeEnregistrement(StrEnum):
    INITIALISATION = 'INITIALISATION'
    CLOTURE_BOUGIE = 'CLOTURE_BOUGIE'
    INTENTION = 'INTENTION'


class Mode(StrEnum):
    """Mode d'exécution du robot : exécution simulée sur données réelles ou rejouées, ou compte démo."""

    PAPER = 'PAPER'
    DEMO = 'DEMO'


class Decision(StrEnum):
    ADMISSION = 'ADMISSION'
    REFUS = 'REFUS'


CLES_COMMUNES = frozenset({'type', 'sequence', 'instant_utc', 'deployment_id', 'mode', 'regles'})
CLES_SPECIFIQUES = {
    TypeEnregistrement.INITIALISATION: frozenset({
        'symboles', 'source_ticks', 'segments_minimaux', 'scenario_fondamental'}),
    TypeEnregistrement.CLOTURE_BOUGIE: frozenset({
        'strategie', 'symbole', 'ouverture_utc', 'cloture_utc', 'jour_londres', 'ohlc', 'nb_ticks', 'valide',
        'statut', 'indicateurs', 'a_t', 'etat_detecteur', 'signal_emis', 'motif'}),
    TypeEnregistrement.INTENTION: frozenset({
        'cle', 'signal', 'fondamental', 'calendrier', 'contexte_ia', 'bras_ab', 'cout_api_alloue_usd', 'courtier',
        'cotation', 'frais', 'risque', 'volume', 'decision', 'motif', 'ordre_envoye'}),
}
_EMPREINTE = re.compile(r'[0-9a-f]{64}')


def en_json(valeur):
    """Conversion explicite vers des types JSON : Decimal en texte exact, énumérations par valeur."""
    if valeur is None or type(valeur) in (bool, str):
        return valeur
    if isinstance(valeur, Enum):
        return valeur.value
    if type(valeur) is int:
        return valeur
    if type(valeur) is float:
        if not math.isfinite(valeur):
            raise EnregistrementInvalide(f'nombre non fini : {valeur!r}')
        return valeur
    if type(valeur) is Decimal:
        if not valeur.is_finite():
            raise EnregistrementInvalide(f'décimal non fini : {valeur!r}')
        return str(valeur)
    if type(valeur) is date:
        return valeur.isoformat()
    if isinstance(valeur, Mapping):
        if any(type(cle) is not str for cle in valeur):
            raise EnregistrementInvalide('les clés JSON doivent être des textes')
        return {cle: en_json(element) for cle, element in valeur.items()}
    if isinstance(valeur, (list, tuple)):
        return [en_json(element) for element in valeur]
    raise EnregistrementInvalide(f'type non journalisable : {type(valeur).__name__}')


def _iso_valide(valeur):
    try:
        ms_depuis_iso(valeur)
        return True
    except InstantInvalide:
        return False


def _verifier_specifique(type_, enr, erreurs):
    if type_ is TypeEnregistrement.INITIALISATION:
        if not isinstance(enr['symboles'], list) or not enr['symboles'] \
                or any(type(s) is not str for s in enr['symboles']):
            erreurs.append('symboles : liste non vide de textes attendue')
        if not isinstance(enr['segments_minimaux'], list) or any(type(s) is not str for s in enr['segments_minimaux']):
            erreurs.append('segments_minimaux : liste de textes attendue')
        if enr['scenario_fondamental'] is not None and type(enr['scenario_fondamental']) is not str:
            erreurs.append('scenario_fondamental : texte ou null attendu')
    elif type_ is TypeEnregistrement.CLOTURE_BOUGIE:
        if type(enr['signal_emis']) is not bool:
            erreurs.append('signal_emis : booléen attendu')
        elif (enr['motif'] is None) != enr['signal_emis']:
            erreurs.append('une clôture porte soit un signal émis, soit un motif')
        if enr['statut'] not in {s.value for s in StatutBougie}:
            erreurs.append(f"statut inconnu : {enr['statut']!r}")
        for cle in ('ouverture_utc', 'cloture_utc'):
            if not _iso_valide(enr[cle]):
                erreurs.append(f'{cle} : instant UTC mal formé')
    elif type_ is TypeEnregistrement.INTENTION:
        if enr['decision'] not in {d.value for d in Decision}:
            erreurs.append(f"decision inconnue : {enr['decision']!r}")
        elif (enr['motif'] is None) != (enr['decision'] == Decision.ADMISSION):
            erreurs.append('une admission n\'a pas de motif ; un refus en a un')
        if type(enr['ordre_envoye']) is not bool:
            erreurs.append('ordre_envoye : booléen attendu')
        elif enr['decision'] == Decision.REFUS and enr['ordre_envoye']:
            erreurs.append('un refus n\'envoie aucun ordre')


def valider_enregistrement(enr: Mapping) -> list[str]:
    """Liste des violations du schéma C09 d'un enregistrement (vide si conforme)."""
    if not isinstance(enr, Mapping):
        return ['un enregistrement est un objet JSON']
    try:
        type_ = TypeEnregistrement(enr.get('type'))
    except ValueError:
        return [f"type d'enregistrement inconnu : {enr.get('type')!r}"]
    attendues = CLES_COMMUNES | CLES_SPECIFIQUES[type_]
    erreurs = []
    if set(enr) != attendues:
        manquantes, en_trop = sorted(attendues - set(enr)), sorted(set(enr) - attendues)
        return [f'clés manquantes {manquantes}, clés en trop {en_trop}']
    if type(enr['sequence']) is not int or enr['sequence'] < 1:
        erreurs.append('sequence : entier >= 1 attendu')
    if not _iso_valide(enr['instant_utc']):
        erreurs.append('instant_utc : instant UTC mal formé')
    if type(enr['deployment_id']) is not str or not enr['deployment_id'].strip():
        erreurs.append('deployment_id : texte non vide attendu')
    if enr['mode'] not in {m.value for m in Mode}:
        erreurs.append(f"mode inconnu : {enr['mode']!r}")
    regles = enr['regles']
    if not isinstance(regles, Mapping) or set(regles) != {'version_technique', 'empreinte'} \
            or type(regles.get('version_technique')) is not str \
            or not _EMPREINTE.fullmatch(str(regles.get('empreinte'))):
        erreurs.append('regles : {version_technique, empreinte SHA-256} attendu')
    if 'motif' in enr and enr['motif'] is not None and enr['motif'] not in {m.value for m in MotifRefus}:
        erreurs.append(f"motif inconnu : {enr['motif']!r}")
    _verifier_specifique(type_, enr, erreurs)
    try:
        serialiser(enr)
    except JSONInvalide as erreur:
        erreurs.append(str(erreur))
    return erreurs


class ConstructeurEnregistrements:
    """Construit des enregistrements C09 conformes, numérotés sans trou à partir de 1."""

    def __init__(self, deployment_id: str, mode: Mode, bundle: BundleTechnique):
        if type(deployment_id) is not str or not deployment_id.strip():
            raise EnregistrementInvalide('deployment_id : texte non vide attendu')
        self._commun = {'deployment_id': deployment_id, 'mode': Mode(mode).value,
                        'regles': {'version_technique': bundle.valeur('common', 'version'),
                                   'empreinte': bundle.empreinte}}
        self._sequence = 0

    @property
    def derniere_sequence(self) -> int:
        return self._sequence

    def _finaliser(self, type_: TypeEnregistrement, instant_ms: int, specifique: dict) -> dict:
        enr = {'type': type_.value, 'sequence': self._sequence + 1, 'instant_utc': iso_depuis_ms(instant_ms),
               **copy.deepcopy(self._commun), **en_json(specifique)}
        erreurs = valider_enregistrement(enr)
        if erreurs:
            raise EnregistrementInvalide(f'{type_.value} : ' + ' ; '.join(erreurs))
        self._sequence += 1
        return enr

    def initialisation(self, instant_ms: int, symboles, source_ticks: Mapping, segments_minimaux,
                       scenario_fondamental: str | None) -> dict:
        return self._finaliser(TypeEnregistrement.INITIALISATION, instant_ms, {
            'symboles': list(symboles), 'source_ticks': source_ticks,
            'segments_minimaux': list(segments_minimaux), 'scenario_fondamental': scenario_fondamental})

    def cloture_bougie(self, strategie: str, bougie: BougieEnrichie, resultat: ResultatTechnique) -> dict:
        b = bougie.bougie
        return self._finaliser(TypeEnregistrement.CLOTURE_BOUGIE, b.cloture_ms, {
            'strategie': strategie, 'symbole': b.symbole, 'ouverture_utc': iso_depuis_ms(b.ouverture_ms),
            'cloture_utc': iso_depuis_ms(b.cloture_ms), 'jour_londres': bougie.jour_londres,
            'ohlc': {'o': b.o, 'h': b.h, 'l': b.l, 'c': b.c}, 'nb_ticks': b.nb_ticks, 'valide': b.valide,
            'statut': bougie.statut, 'indicateurs': bougie.indicateurs, 'a_t': bougie.a_t,
            'etat_detecteur': resultat.etat_detecteur, 'signal_emis': resultat.signal is not None,
            'motif': resultat.motif})

    def intention(self, instant_ms: int, cle: CleIntention, signal: Signal,
                  fondamental: DecisionFondamentale | None, contexte_ia: DecisionContexteIA | None,
                  decision: Decision, motif: MotifRefus | None, ordre_envoye: bool, *, calendrier=None,
                  bras_ab=None, cout_api_alloue_usd=None, courtier=None, cotation=None, frais=None, risque=None,
                  volume=None) -> dict:
        return self._finaliser(TypeEnregistrement.INTENTION, instant_ms, {
            'cle': cle.en_json(),
            'signal': {'sens': signal.sens, 'cloture_bid': signal.cloture_bid, 'a_t': signal.a_t,
                       'b_sl': signal.b_sl, 'multiple_objectif': signal.multiple_objectif,
                       'etat_detecteur': signal.etat_detecteur},
            'fondamental': None if fondamental is None else {
                'autorise': fondamental.autorise, 'motif': fondamental.motif,
                'permission': fondamental.permission, 'scenario': fondamental.scenario},
            'contexte_ia': None if contexte_ia is None else {
                'etat': contexte_ia.etat, 'sequence_snapshot': contexte_ia.sequence_snapshot,
                'evenements': contexte_ia.evenements},
            'calendrier': calendrier, 'bras_ab': bras_ab, 'cout_api_alloue_usd': cout_api_alloue_usd,
            'courtier': courtier, 'cotation': cotation, 'frais': frais, 'risque': risque, 'volume': volume,
            'decision': decision, 'motif': motif, 'ordre_envoye': ordre_envoye})

"""Couche 2 de `donnees-temps` : états récursifs des indicateurs d'un symbole, préchargement et persistance.

Contrat : `mcl/donnees-temps/contrats/couche-2.md`. Sources : C03 points 7 à 11.
"""
from __future__ import annotations

import hashlib
import math
from collections import deque
from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from xpbots.donnees_temps.c1c_indicateurs import (CLE_TR, EtatATR, EtatEMA, EtatRSI, ValeurInvalide, cle_atr,
                                                  cle_ema, cle_ema_decalee, cle_rsi)
from xpbots.noyau.json_canonique import JSONInvalide, charger_strict, serialiser
from xpbots.noyau.marche import Bougie
from xpbots.noyau.ports import Stockage

SCHEMA_ETAT = 'xp-etat-indicateurs-v1'


class PrechargementInsuffisant(ValueError):
    """Moins de bougies valides que le préchauffage demandé (C03 point 7)."""


class EtatIncompatible(ValueError):
    """État restauré ou importé qui ne correspond pas à la spécification ou à l'empreinte attendues."""


def _entier_positif(valeur, nom):
    if type(valeur) is not int or valeur <= 0:
        raise ValueError(f'{nom} doit être un entier strictement positif, reçu {valeur!r}')


@dataclass(frozen=True)
class SpecIndicateurs:
    """Indicateurs à calculer, lus dans `config/` par l'appelant."""

    periodes_ema: tuple[int, ...]
    periode_rsi: int
    periode_atr: int
    decalages_ema: tuple[tuple[int, int], ...]
    prechauffage: int

    def __post_init__(self):
        object.__setattr__(self, 'periodes_ema', tuple(self.periodes_ema))
        object.__setattr__(self, 'decalages_ema', tuple(tuple(d) for d in self.decalages_ema))
        if not self.periodes_ema or len(set(self.periodes_ema)) != len(self.periodes_ema):
            raise ValueError('périodes EMA distinctes attendues')
        for n in self.periodes_ema:
            _entier_positif(n, 'période EMA')
        _entier_positif(self.periode_rsi, 'période RSI')
        _entier_positif(self.periode_atr, 'période ATR')
        _entier_positif(self.prechauffage, 'préchauffage')
        disponibilite = [max(self.periodes_ema), self.periode_rsi + 1, self.periode_atr + 1]
        for decalage in self.decalages_ema:
            try:
                periode, k = decalage
            except ValueError as erreur:
                raise ValueError('décalage EMA : couple (période calculée, décalage) attendu') from erreur
            if periode not in self.periodes_ema:
                raise ValueError('décalage EMA d\'une période non calculée')
            _entier_positif(k, 'décalage EMA')
            disponibilite.append(periode + k)
        if self.prechauffage < max(disponibilite):
            raise ValueError('préchauffage trop court : un indicateur serait indisponible à la première décision')

    def en_json(self) -> dict:
        return {'periodes_ema': list(self.periodes_ema), 'periode_rsi': self.periode_rsi,
                'periode_atr': self.periode_atr, 'decalages_ema': [list(d) for d in self.decalages_ema],
                'prechauffage': self.prechauffage}


@dataclass(frozen=True)
class EmpreintePrechargement:
    premiere_ouverture_ms: int
    derniere_cloture_ms: int
    nombre: int
    sha256: str

    def en_json(self) -> dict:
        return {'premiere_ouverture_ms': self.premiere_ouverture_ms, 'derniere_cloture_ms': self.derniere_cloture_ms,
                'nombre': self.nombre, 'sha256': self.sha256}


@dataclass(frozen=True)
class Indicateurs:
    """Indicateurs disponibles après une bougie, `a_t` (ATR de t−1 strictement positif) et compte de bougies."""

    valeurs: Mapping[str, float]
    a_t: float | None
    compte: int


def _ligne_prechargement(bougie: Bougie) -> str:
    return serialiser([bougie.ouverture_ms, bougie.cloture_ms, str(bougie.o), str(bougie.h), str(bougie.l),
                       str(bougie.c)])


class EtatIndicateursSymbole:
    """États récursifs EMA, RSI et ATR d'un symbole, appliqués aux seules bougies valides."""

    def __init__(self, spec: SpecIndicateurs):
        if type(spec) is not SpecIndicateurs:
            raise ValueError('SpecIndicateurs attendue')
        self.spec = spec
        self.reinitialiser()

    def reinitialiser(self) -> None:
        """Nouvelle initialisation : tout état récursif repart de zéro (C03 point 7)."""
        s = self.spec
        self._emas = {n: EtatEMA(n) for n in s.periodes_ema}
        self._historiques = {d: deque(maxlen=d[1] + 1) for d in s.decalages_ema}
        self._rsi = EtatRSI(s.periode_rsi)
        self._atr = EtatATR(s.periode_atr)
        self.compte = 0
        self.derniere_cloture_ms: int | None = None
        self._lignes: list[str] = []
        self._premiere_ouverture: int | None = None
        self.empreinte_prechargement: EmpreintePrechargement | None = None

    @property
    def pret(self) -> bool:
        return self.compte >= self.spec.prechauffage

    def appliquer(self, bougie: Bougie) -> Indicateurs:
        if type(bougie) is not Bougie or not bougie.valide:
            raise ValeurInvalide('seule une bougie valide met à jour les indicateurs')
        if self.derniere_cloture_ms is not None and bougie.cloture_ms <= self.derniere_cloture_ms:
            raise ValeurInvalide('bougie non postérieure à la précédente')
        h, l, c = float(bougie.h), float(bougie.l), float(bougie.c)  # noqa: E741
        valeurs = {}
        for n, ema in self._emas.items():
            v = ema.maj(c)
            if v is not None:
                valeurs[cle_ema(n)] = v
        for (n, k), historique in self._historiques.items():
            if cle_ema(n) in valeurs:
                historique.append(valeurs[cle_ema(n)])
                if len(historique) == k + 1:
                    valeurs[cle_ema_decalee(n, k)] = historique[0]
        rsi = self._rsi.maj(c)
        if rsi is not None:
            valeurs[cle_rsi(self.spec.periode_rsi)] = rsi
        mesure = self._atr.maj(h, l, c)
        valeurs[CLE_TR] = mesure.tr
        if mesure.atr is not None:
            valeurs[cle_atr(self.spec.periode_atr)] = mesure.atr
        self.compte += 1
        self.derniere_cloture_ms = bougie.cloture_ms
        if self.empreinte_prechargement is None:
            if self._premiere_ouverture is None:
                self._premiere_ouverture = bougie.ouverture_ms
            self._lignes.append(_ligne_prechargement(bougie))
            if self.compte == self.spec.prechauffage:
                self.empreinte_prechargement = EmpreintePrechargement(
                    self._premiere_ouverture, bougie.cloture_ms, self.compte,
                    hashlib.sha256('\n'.join(self._lignes).encode('utf-8')).hexdigest())
                self._lignes = []
        a_t = mesure.a_t if mesure.a_t is not None and mesure.a_t > 0 else None
        return Indicateurs(MappingProxyType(valeurs), a_t, self.compte)

    def precharger(self, bougies: Iterable[Bougie]) -> EmpreintePrechargement:
        """Applique un préchargement complet sur un état vierge et rend son empreinte."""
        if self.compte:
            raise EtatIncompatible('préchargement sur un état déjà initialisé')
        for bougie in bougies:
            self.appliquer(bougie)
        if self.empreinte_prechargement is None:
            raise PrechargementInsuffisant(f'{self.compte} bougies pour un préchauffage de {self.spec.prechauffage}')
        return self.empreinte_prechargement

    def exporter(self) -> dict:
        return {
            'schema': SCHEMA_ETAT, 'spec': self.spec.en_json(), 'compte': self.compte,
            'derniere_cloture_ms': self.derniere_cloture_ms,
            'ema': [self._emas[n].exporter() for n in self.spec.periodes_ema],
            'historiques': [list(self._historiques[d]) for d in self.spec.decalages_ema],
            'rsi': self._rsi.exporter(), 'atr': self._atr.exporter(),
            'prechargement': {'premiere_ouverture_ms': self._premiere_ouverture, 'lignes': list(self._lignes)},
            'empreinte': None if self.empreinte_prechargement is None else self.empreinte_prechargement.en_json(),
        }

    @classmethod
    def importer(cls, spec: SpecIndicateurs, etat: Mapping) -> EtatIndicateursSymbole:
        cles = {'schema', 'spec', 'compte', 'derniere_cloture_ms', 'ema', 'historiques', 'rsi', 'atr',
                'prechargement', 'empreinte'}
        if not isinstance(etat, Mapping) or set(etat) != cles or etat['schema'] != SCHEMA_ETAT:
            raise EtatIncompatible('état d\'indicateurs illisible')
        if etat['spec'] != spec.en_json():
            raise EtatIncompatible('état d\'indicateurs d\'une autre spécification')
        nouveau = cls(spec)
        try:
            nouveau._emas = {n: EtatEMA.importer(e) for n, e in zip(spec.periodes_ema, etat['ema'], strict=True)}
            nouveau._historiques = {d: deque(valeurs, maxlen=d[1] + 1)
                                    for d, valeurs in zip(spec.decalages_ema, etat['historiques'], strict=True)}
            nouveau._rsi = EtatRSI.importer(etat['rsi'])
            nouveau._atr = EtatATR.importer(etat['atr'])
            nouveau.compte = etat['compte']
            nouveau.derniere_cloture_ms = etat['derniere_cloture_ms']
            nouveau._premiere_ouverture = etat['prechargement']['premiere_ouverture_ms']
            nouveau._lignes = list(etat['prechargement']['lignes'])
            e = etat['empreinte']
            nouveau.empreinte_prechargement = None if e is None else EmpreintePrechargement(
                e['premiere_ouverture_ms'], e['derniere_cloture_ms'], e['nombre'], e['sha256'])
        except (KeyError, TypeError, ValueError) as erreur:
            raise EtatIncompatible(f'état d\'indicateurs incohérent : {erreur}') from erreur
        if type(nouveau.compte) is not int or nouveau.compte < 0:
            raise EtatIncompatible('compte de bougies incohérent')
        if nouveau.derniere_cloture_ms is not None and type(nouveau.derniere_cloture_ms) is not int:
            raise EtatIncompatible('dernière clôture incohérente')
        if any(type(v) is not float or not math.isfinite(v) for h in nouveau._historiques.values() for v in h):
            raise EtatIncompatible('historique d\'EMA incohérent')
        return nouveau

    def sauvegarder(self, stockage: Stockage, cle: str) -> None:
        stockage.ecrire(cle, serialiser(self.exporter()).encode('utf-8'))

    @classmethod
    def restaurer(cls, spec: SpecIndicateurs, stockage: Stockage, cle: str,
                  empreinte_attendue: str | None = None) -> EtatIndicateursSymbole | None:
        """État persisté, ou None s'il n'existe pas ; une empreinte différente est une autre initialisation."""
        brut = stockage.lire(cle)
        if brut is None:
            return None
        try:
            contenu = charger_strict(brut)
        except JSONInvalide as erreur:
            raise EtatIncompatible(f'état persisté illisible : {erreur}') from erreur
        etat = cls.importer(spec, contenu)
        if empreinte_attendue is not None and (etat.empreinte_prechargement is None
                                               or etat.empreinte_prechargement.sha256 != empreinte_attendue):
            raise EtatIncompatible('empreinte de préchargement différente : nouvelle initialisation à journaliser')
        return etat

"""Implémentation de la couche 2b (etat_indicateurs). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Mapping

from xpbots.donnees.c0a_types import ErreurDonneesTemps, IdentitePrechargement, IndicateursBougie
from xpbots.donnees.c1b_indicateurs import EtatIndicateurs, avancer, etat_initial
from xpbots.noyau.c1a_marche import Bougie

SCHEMA_ETAT = 'xp-etat-indicateurs-v1'
_ZERO = '0' * 64
_EMPREINTE = re.compile(r'[0-9a-f]{64}')
_CLES = {'schema', 'empreinte_configuration', 'periode', 'duree_ms', 'cloture_precedente', 'tr_initiaux', 'atr',
         'nombre_valides', 'premiere_ms', 'empreinte_chaine', 'dernier_debut_ms'}


def _empreinte(valeur: object, nom: str) -> str:
    if not isinstance(valeur, str) or not _EMPREINTE.fullmatch(valeur):
        raise ErreurDonneesTemps(f'{nom} : SHA-256 hexadécimal attendu')
    return valeur


class ChaineIndicateurs:
    """Chaîne TR/ATR/A sur les seules bougies valides d'un symbole et d'une durée."""

    def __init__(self, periode: int) -> None:
        self._etat: EtatIndicateurs = etat_initial(periode)
        self._duree: int | None = None
        self._dernier_debut: int | None = None
        self._nombre = 0
        self._premiere: int | None = None
        self._chaine = _ZERO

    @property
    def nombre_valides(self) -> int:
        return self._nombre

    @property
    def identite(self) -> IdentitePrechargement:
        return IdentitePrechargement(self._premiere, self._nombre, self._chaine)

    def ajouter(self, bougie: Bougie) -> IndicateursBougie | None:
        if not isinstance(bougie, Bougie):
            raise ErreurDonneesTemps('bougie du noyau attendue')
        if self._duree is not None and bougie.duree_ms != self._duree:
            raise ErreurDonneesTemps('bougie d\'une autre durée')
        if self._dernier_debut is not None and bougie.debut_ms <= self._dernier_debut:
            raise ErreurDonneesTemps('bougie hors ordre')
        self._duree, self._dernier_debut = bougie.duree_ms, bougie.debut_ms
        if not bougie.valide:
            return None
        resultat = avancer(self._etat, bougie.haut, bougie.bas, bougie.cloture)
        indicateurs = IndicateursBougie(resultat.tr, resultat.atr, resultat.a, self._nombre)
        self._etat = resultat.etat
        texte = (f'{self._chaine}|{bougie.debut_ms}|{bougie.duree_ms}|{bougie.ouverture!r}|{bougie.haut!r}|'
                 f'{bougie.bas!r}|{bougie.cloture!r}')
        self._chaine = hashlib.sha256(texte.encode('utf-8')).hexdigest()
        if self._premiere is None:
            self._premiere = bougie.debut_ms
        self._nombre += 1
        return indicateurs

    def exporter(self, empreinte_configuration: str) -> dict[str, Any]:
        return {'schema': SCHEMA_ETAT, 'empreinte_configuration': _empreinte(empreinte_configuration, 'empreinte_configuration'),
                'periode': self._etat.periode, 'duree_ms': self._duree, 'cloture_precedente': self._etat.cloture_precedente,
                'tr_initiaux': list(self._etat.tr_initiaux), 'atr': self._etat.atr, 'nombre_valides': self._nombre,
                'premiere_ms': self._premiere, 'empreinte_chaine': self._chaine, 'dernier_debut_ms': self._dernier_debut}

    @classmethod
    def importer(cls, donnees: Mapping[str, Any], empreinte_configuration: str) -> 'ChaineIndicateurs':
        if not isinstance(donnees, Mapping) or set(donnees) != _CLES:
            raise ErreurDonneesTemps('état exporté incomplet ou inconnu')
        if donnees['schema'] != SCHEMA_ETAT:
            raise ErreurDonneesTemps(f'schéma d\'état inattendu : {donnees["schema"]!r}')
        if _empreinte(donnees['empreinte_configuration'], 'empreinte_configuration') != \
                _empreinte(empreinte_configuration, 'empreinte_configuration'):
            raise ErreurDonneesTemps('état exporté sous une autre configuration')

        def flottant(valeur, nom, optionnel=True):
            if optionnel and valeur is None:
                return None
            if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur):
                raise ErreurDonneesTemps(f'{nom} : nombre fini attendu')
            return float(valeur)

        def entier(valeur, nom, optionnel=True):
            if optionnel and valeur is None:
                return None
            if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 0:
                raise ErreurDonneesTemps(f'{nom} : entier ≥ 0 attendu')
            return valeur

        if not isinstance(donnees['tr_initiaux'], list):
            raise ErreurDonneesTemps('tr_initiaux : liste attendue')
        chaine = cls(entier(donnees['periode'], 'periode', optionnel=False))
        chaine._etat = EtatIndicateurs(chaine._etat.periode, flottant(donnees['cloture_precedente'], 'cloture_precedente'),
                                       tuple(flottant(v, 'tr_initiaux', False) for v in donnees['tr_initiaux']),
                                       flottant(donnees['atr'], 'atr'))
        chaine._duree = entier(donnees['duree_ms'], 'duree_ms')
        chaine._dernier_debut = entier(donnees['dernier_debut_ms'], 'dernier_debut_ms')
        chaine._nombre = entier(donnees['nombre_valides'], 'nombre_valides', optionnel=False)
        chaine._premiere = entier(donnees['premiere_ms'], 'premiere_ms')
        chaine._chaine = _empreinte(donnees['empreinte_chaine'], 'empreinte_chaine')
        chaine._verifier_coherence()
        return chaine

    def _verifier_coherence(self) -> None:
        n, etat = self._nombre, self._etat
        attendus = (len(etat.tr_initiaux) == n and etat.atr is None) if n < etat.periode else \
            (not etat.tr_initiaux and etat.atr is not None)
        vide = n == 0
        if not attendus or (etat.cloture_precedente is None) != vide or (self._premiere is None) != vide \
                or (self._chaine == _ZERO) != vide or (self._duree is None) != (self._dernier_debut is None) \
                or (not vide and (self._dernier_debut is None or self._premiere > self._dernier_debut)) \
                or (self._duree is not None and self._duree == 0):
            raise ErreurDonneesTemps('état exporté incohérent')

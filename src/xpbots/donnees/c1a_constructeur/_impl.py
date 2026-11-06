"""Implémentation de la couche 1a (constructeur_bougies). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping

from xpbots.donnees.c0a_types import AnomalieDonnees, ErreurDonneesTemps
from xpbots.noyau.c0a_temps import ErreurInstant, aligner
from xpbots.noyau.c1a_marche import Tick

SCHEMA_CONSTRUCTEUR = 'xp-constructeur-bougies-v1'
_CLES = {'schema', 'symbole', 'duree_ms', 'derniere_fin_ms', 'ouverte'}
_CLES_OUVERTE = {'debut_ms', 'ouverture', 'haut', 'bas', 'cloture', 'nombre'}


@dataclass(frozen=True)
class BougieBrute:
    symbole: str
    debut_ms: int
    duree_ms: int
    ouverture: float | None
    haut: float | None
    bas: float | None
    cloture: float | None
    nombre_evenements: int
    instant_disponibilite_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.symbole, str) or not self.symbole:
            raise ErreurDonneesTemps('symbole : texte non vide attendu')
        try:
            if aligner(self.debut_ms, self.duree_ms) != self.debut_ms:
                raise ErreurDonneesTemps('debut_ms non aligné')
        except ErreurInstant as erreur:
            raise ErreurDonneesTemps(str(erreur)) from erreur
        if isinstance(self.nombre_evenements, bool) or not isinstance(self.nombre_evenements, int) or self.nombre_evenements < 0:
            raise ErreurDonneesTemps('nombre_evenements : entier ≥ 0 attendu')
        prix = (self.ouverture, self.haut, self.bas, self.cloture)
        if self.nombre_evenements == 0:
            if any(p is not None for p in prix):
                raise ErreurDonneesTemps('une bougie vide n\'a pas de prix')
        else:
            if not all(isinstance(p, float) and math.isfinite(p) for p in prix):
                raise ErreurDonneesTemps('prix flottants finis attendus')
            if not self.bas <= min(self.ouverture, self.cloture) <= max(self.ouverture, self.cloture) <= self.haut:
                raise ErreurDonneesTemps('OHLC incohérents')
        if isinstance(self.instant_disponibilite_ms, bool) or not isinstance(self.instant_disponibilite_ms, int) \
                or self.instant_disponibilite_ms < self.fin_ms:
            raise ErreurDonneesTemps('disponibilité antérieure à la fin de la bougie')

    @property
    def fin_ms(self) -> int:
        return self.debut_ms + self.duree_ms

    @property
    def vide(self) -> bool:
        return self.nombre_evenements == 0


@dataclass(frozen=True)
class SortieConstructeur:
    bougies: tuple[BougieBrute, ...]
    anomalie: AnomalieDonnees | None = None


@dataclass
class _Ouverte:
    debut_ms: int
    ouverture: float
    haut: float
    bas: float
    cloture: float
    nombre: int


class ConstructeurBougies:
    """Bougies brutes Bid d'un symbole et d'une durée, closes par le tick de frontière."""

    def __init__(self, symbole: str, duree_ms: int, debut_ms: int | None = None) -> None:
        if not isinstance(symbole, str) or not symbole:
            raise ErreurDonneesTemps('symbole : texte non vide attendu')
        try:
            if debut_ms is not None and aligner(debut_ms, duree_ms) != debut_ms:
                raise ErreurDonneesTemps('debut_ms non aligné sur la durée')
            aligner(0, duree_ms)
        except ErreurInstant as erreur:
            raise ErreurDonneesTemps(str(erreur)) from erreur
        self.symbole = symbole
        self.duree_ms = duree_ms
        self._ouverte: _Ouverte | None = None
        self._derniere_fin = debut_ms

    @property
    def derniere_fin_ms(self) -> int | None:
        return self._derniere_fin

    def _vides(self, depuis: int, jusqua: int, disponibilite: int) -> list[BougieBrute]:
        return [BougieBrute(self.symbole, debut, self.duree_ms, None, None, None, None, 0,
                            max(disponibilite, debut + self.duree_ms))
                for debut in range(depuis, jusqua, self.duree_ms)]

    def ajouter(self, tick: Tick) -> SortieConstructeur:
        if not isinstance(tick, Tick) or tick.symbole != self.symbole:
            raise ErreurDonneesTemps(f'tick du symbole {self.symbole} attendu')
        instant = tick.instant_fournisseur_ms
        limite = self._ouverte.debut_ms if self._ouverte is not None else self._derniere_fin
        if limite is not None and instant < limite:
            return SortieConstructeur((), AnomalieDonnees(self.symbole, 'TICK_ANTERIEUR', tick.instant_reception_ms))
        debut = aligner(instant, self.duree_ms)
        emises: list[BougieBrute] = []
        ouverte = self._ouverte
        if ouverte is not None and debut != ouverte.debut_ms:
            fin = ouverte.debut_ms + self.duree_ms
            emises.append(BougieBrute(self.symbole, ouverte.debut_ms, self.duree_ms, ouverte.ouverture, ouverte.haut,
                                      ouverte.bas, ouverte.cloture, ouverte.nombre,
                                      max(tick.instant_reception_ms, fin)))
            emises.extend(self._vides(fin, debut, tick.instant_reception_ms))
            ouverte = None
        elif ouverte is None and self._derniere_fin is not None:
            emises.extend(self._vides(self._derniere_fin, debut, tick.instant_reception_ms))
        if emises:
            self._derniere_fin = debut
        if ouverte is None:
            self._ouverte = _Ouverte(debut, tick.bid, tick.bid, tick.bid, tick.bid, 1)
        else:
            ouverte.haut = max(ouverte.haut, tick.bid)
            ouverte.bas = min(ouverte.bas, tick.bid)
            ouverte.cloture = tick.bid
            ouverte.nombre += 1
        return SortieConstructeur(tuple(emises))

    def exporter(self) -> dict[str, Any]:
        """État complet, bougie ouverte comprise, en dictionnaire JSON strict."""
        return {'schema': SCHEMA_CONSTRUCTEUR, 'symbole': self.symbole, 'duree_ms': self.duree_ms,
                'derniere_fin_ms': self._derniere_fin,
                'ouverte': None if self._ouverte is None else asdict(self._ouverte)}

    @classmethod
    def importer(cls, donnees: Mapping[str, Any]) -> 'ConstructeurBougies':
        if not isinstance(donnees, Mapping) or set(donnees) != _CLES or donnees['schema'] != SCHEMA_CONSTRUCTEUR:
            raise ErreurDonneesTemps('état de constructeur incomplet, inconnu ou d\'un autre schéma')
        derniere = donnees['derniere_fin_ms']
        if derniere is not None and (isinstance(derniere, bool) or not isinstance(derniere, int)):
            raise ErreurDonneesTemps('derniere_fin_ms : entier attendu')
        constructeur = cls(donnees['symbole'], donnees['duree_ms'], derniere)
        ouverte = donnees['ouverte']
        if ouverte is not None:
            if not isinstance(ouverte, Mapping) or set(ouverte) != _CLES_OUVERTE:
                raise ErreurDonneesTemps('bougie ouverte incomplète ou inconnue')
            nombre = ouverte['nombre']
            if isinstance(nombre, bool) or not isinstance(nombre, int) or nombre < 1:
                raise ErreurDonneesTemps('bougie ouverte : au moins un événement attendu')
            prix = [ouverte[c] for c in ('ouverture', 'haut', 'bas', 'cloture')]
            if not all(not isinstance(p, bool) and isinstance(p, (int, float)) and math.isfinite(p) for p in prix):
                raise ErreurDonneesTemps('bougie ouverte : prix finis attendus')
            debut = ouverte['debut_ms']
            try:
                aligne = not isinstance(debut, bool) and isinstance(debut, int) \
                    and aligner(debut, constructeur.duree_ms) == debut
            except ErreurInstant:
                aligne = False
            if not aligne or (derniere is not None and debut < derniere):
                raise ErreurDonneesTemps('bougie ouverte : début aligné, non antérieur à la dernière fin, attendu')
            o, h, b, c = (float(p) for p in prix)
            if not b <= min(o, c) <= max(o, c) <= h:
                raise ErreurDonneesTemps('bougie ouverte : OHLC incohérents')
            constructeur._ouverte = _Ouverte(debut, o, h, b, c, nombre)
        return constructeur

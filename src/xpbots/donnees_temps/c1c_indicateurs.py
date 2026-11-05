"""Couche 1c de `donnees-temps` : EMA à graine SMA, Wilder, RSI, TR et ATR incrémentaux (C03 points 8 à 12).

Contrat : `mcl/donnees-temps/contrats/couche-1c.md`. Flottants 64 bits ; ordre exact des récurrences ; graine =
moyenne exactement arrondie (`math.fsum`) des n premières valeurs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

CLE_TR = 'tr'
RSI_NEUTRE = 50.0       # C03 point 9 : hausse et baisse moyennes nulles
RSI_MAXIMUM = 100.0     # C03 point 9 : baisse moyenne seule nulle
RSI_MINIMUM = 0.0       # C03 point 9 : hausse moyenne seule nulle


def cle_ema(n: int) -> str:
    return f'ema_{n}'


def cle_ema_decalee(n: int, k: int) -> str:
    return f'ema_{n}_t_moins_{k}'


def cle_rsi(n: int) -> str:
    return f'rsi_{n}'


def cle_atr(n: int) -> str:
    return f'atr_{n}'


class ValeurInvalide(ValueError):
    """Entrée non finie, période invalide ou état importé incohérent."""


def _fini(valeur, nom='valeur') -> float:
    if type(valeur) is not float or not math.isfinite(valeur):
        raise ValeurInvalide(f'{nom} doit être un flottant fini, reçu {valeur!r}')
    return valeur


def _periode(n) -> int:
    if type(n) is not int or n <= 0:
        raise ValeurInvalide(f'période entière strictement positive attendue, reçu {n!r}')
    return n


def _optionnel(valeur, nom):
    return None if valeur is None else _fini(valeur, nom)


class _AvecGraine:
    """Moyenne exacte des n premières valeurs, puis récurrence propre à l'indicateur."""

    def __init__(self, n: int):
        self.n = _periode(n)
        self._graine: list[float] = []
        self.valeur: float | None = None

    def _ajouter(self, x: float) -> float | None:
        if self.valeur is None:
            self._graine.append(x)
            if len(self._graine) == self.n:
                self.valeur = math.fsum(self._graine) / self.n
                self._graine = []
            return self.valeur
        self.valeur = self._recurrence(self.valeur, x)
        return self.valeur

    def _recurrence(self, precedente: float, x: float) -> float:
        raise NotImplementedError

    def exporter(self) -> dict:
        return {'n': self.n, 'graine': list(self._graine), 'valeur': self.valeur}

    def _importer(self, etat: dict):
        if type(etat) is not dict or set(etat) != {'n', 'graine', 'valeur'} or etat['n'] != self.n:
            raise ValeurInvalide('état importé incohérent')
        graine = [_fini(x, 'graine') for x in etat['graine']]
        valeur = _optionnel(etat['valeur'], 'valeur')
        coherent = (valeur is None and len(graine) < self.n) or (valeur is not None and not graine)
        if not coherent:
            raise ValeurInvalide('état importé incohérent : graine et valeur')
        self._graine, self.valeur = graine, valeur
        return self


class EtatEMA(_AvecGraine):
    """EMA(n) : graine SMA des n premières clôtures, puis EMA_t = EMA_(t−1) + 2/(n+1) × (C_t − EMA_(t−1))."""

    def maj(self, cloture: float) -> float | None:
        return self._ajouter(_fini(cloture, 'clôture'))

    def _recurrence(self, precedente, x):
        return precedente + 2 / (self.n + 1) * (x - precedente)

    @classmethod
    def importer(cls, etat: dict) -> EtatEMA:
        return cls(etat.get('n') if type(etat) is dict else None)._importer(etat)


class EtatWilder(_AvecGraine):
    """Lissage de Wilder : graine = moyenne des n premières valeurs, puis ((n−1) M_(t−1) + x_t)/n."""

    def maj(self, x: float) -> float | None:
        return self._ajouter(_fini(x))

    def _recurrence(self, precedente, x):
        return ((self.n - 1) * precedente + x) / self.n

    @classmethod
    def importer(cls, etat: dict) -> EtatWilder:
        return cls(etat.get('n') if type(etat) is dict else None)._importer(etat)


class EtatRSI:
    """RSI(n) de Wilder sur les variations entre clôtures, avec les cas nuls de C03 point 9."""

    def __init__(self, n: int):
        self.n = _periode(n)
        self._precedente: float | None = None
        self._hausses = EtatWilder(n)
        self._baisses = EtatWilder(n)
        self.valeur: float | None = None

    def maj(self, cloture: float) -> float | None:
        cloture = _fini(cloture, 'clôture')
        if self._precedente is None:
            self._precedente = cloture
            return None
        variation = cloture - self._precedente
        self._precedente = cloture
        hausse = self._hausses.maj(max(variation, 0.0))
        baisse = self._baisses.maj(max(-variation, 0.0))
        if hausse is None:
            return None
        if hausse == 0 and baisse == 0:
            self.valeur = RSI_NEUTRE
        elif baisse == 0:
            self.valeur = RSI_MAXIMUM
        elif hausse == 0:
            self.valeur = RSI_MINIMUM
        else:
            self.valeur = RSI_MAXIMUM - RSI_MAXIMUM / (1 + hausse / baisse)
        return self.valeur

    def exporter(self) -> dict:
        return {'n': self.n, 'precedente': self._precedente, 'hausses': self._hausses.exporter(),
                'baisses': self._baisses.exporter(), 'valeur': self.valeur}

    @classmethod
    def importer(cls, etat: dict) -> EtatRSI:
        if type(etat) is not dict or set(etat) != {'n', 'precedente', 'hausses', 'baisses', 'valeur'}:
            raise ValeurInvalide('état RSI importé incohérent')
        rsi = cls(etat['n'])
        rsi._precedente = _optionnel(etat['precedente'], 'precedente')
        rsi._hausses = EtatWilder.importer(etat['hausses'])
        rsi._baisses = EtatWilder.importer(etat['baisses'])
        rsi.valeur = _optionnel(etat['valeur'], 'valeur')
        if rsi._hausses.n != rsi.n or rsi._baisses.n != rsi.n:
            raise ValeurInvalide('état RSI importé incohérent : périodes')
        return rsi


@dataclass(frozen=True)
class MesureATR:
    """TR de la bougie, ATR après elle et `a_t` = ATR de la bougie précédente (C03 point 11)."""

    tr: float
    atr: float | None
    a_t: float | None


class EtatATR:
    """TR et ATR(n) de Wilder ; le TR de la première bougie vaut H − L."""

    def __init__(self, n: int):
        self.n = _periode(n)
        self._precedente: float | None = None
        self._wilder = EtatWilder(n)

    @property
    def valeur(self) -> float | None:
        return self._wilder.valeur

    def maj(self, h: float, l: float, c: float) -> MesureATR:  # noqa: E741
        h, l, c = _fini(h, 'H'), _fini(l, 'L'), _fini(c, 'C')
        if not l <= c <= h:
            raise ValeurInvalide('OHLC incohérent : L <= C <= H attendu')
        tr = h - l if self._precedente is None else max(h - l, abs(h - self._precedente), abs(l - self._precedente))
        a_t = self._wilder.valeur
        atr = self._wilder.maj(tr)
        self._precedente = c
        return MesureATR(tr, atr, a_t)

    def exporter(self) -> dict:
        return {'n': self.n, 'precedente': self._precedente, 'wilder': self._wilder.exporter()}

    @classmethod
    def importer(cls, etat: dict) -> EtatATR:
        if type(etat) is not dict or set(etat) != {'n', 'precedente', 'wilder'}:
            raise ValeurInvalide('état ATR importé incohérent')
        atr = cls(etat['n'])
        atr._precedente = _optionnel(etat['precedente'], 'precedente')
        atr._wilder = EtatWilder.importer(etat['wilder'])
        if atr._wilder.n != atr.n:
            raise ValeurInvalide('état ATR importé incohérent : période')
        return atr

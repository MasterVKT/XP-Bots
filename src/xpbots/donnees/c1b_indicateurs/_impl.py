"""Implémentation de la couche 1b (indicateurs). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from dataclasses import dataclass
import math

from xpbots.donnees.c0a_types import ErreurDonneesTemps


@dataclass(frozen=True)
class EtatIndicateurs:
    periode: int
    cloture_precedente: float | None
    tr_initiaux: tuple[float, ...]
    atr: float | None

    def __post_init__(self) -> None:
        if isinstance(self.periode, bool) or not isinstance(self.periode, int) or self.periode < 1:
            raise ErreurDonneesTemps('periode : entier ≥ 1 attendu')
        if self.atr is None and len(self.tr_initiaux) >= self.periode:
            raise ErreurDonneesTemps('état incohérent : ATR absent malgré assez de TR')
        if self.atr is not None and self.tr_initiaux:
            raise ErreurDonneesTemps('état incohérent : TR initiaux conservés après l\'ATR initial')


@dataclass(frozen=True)
class ResultatIndicateurs:
    tr: float
    atr: float | None
    a: float | None
    etat: EtatIndicateurs


def etat_initial(periode: int) -> EtatIndicateurs:
    return EtatIndicateurs(periode, None, (), None)


def _fini(valeur, nom):
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur):
        raise ErreurDonneesTemps(f'{nom} : nombre fini attendu')
    return float(valeur)


def avancer(etat: EtatIndicateurs, haut: float, bas: float, cloture: float) -> ResultatIndicateurs:
    if not isinstance(etat, EtatIndicateurs):
        raise ErreurDonneesTemps('état d\'indicateurs attendu')
    haut, bas, cloture = _fini(haut, 'haut'), _fini(bas, 'bas'), _fini(cloture, 'cloture')
    if not bas <= cloture <= haut:
        raise ErreurDonneesTemps('bougie incohérente : bas ≤ clôture ≤ haut exigé')
    if etat.cloture_precedente is None:
        tr = haut - bas
    else:
        precedente = etat.cloture_precedente
        tr = max(haut - bas, abs(haut - precedente), abs(bas - precedente))
    n = etat.periode
    if etat.atr is None:
        initiaux = etat.tr_initiaux + (tr,)
        if len(initiaux) == n:
            somme = 0.0
            for valeur in initiaux:
                somme += valeur
            atr, initiaux = somme / n, ()
        else:
            atr = None
    else:
        atr, initiaux = ((n - 1) * etat.atr + tr) / n, ()
    return ResultatIndicateurs(tr, atr, etat.atr, EtatIndicateurs(n, cloture, initiaux, atr))

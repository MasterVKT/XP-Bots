"""Couche 1a de `donnees-temps` : jours et fenêtres en heure de Londres, jour UTC, blackout de rollover.

Contrat : `mcl/donnees-temps/contrats/couche-1a.md`. Sources : C03 point 3, S01.1, C08.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from xpbots.donnees_temps.c0_parametres_seances import ParametresTechniques, analyser_heure

_EPOQUE = datetime(1970, 1, 1, tzinfo=timezone.utc)


class HeureLocaleInvalide(ValueError):
    """Heure locale inexistante (passage à l'heure d'été) ou ambiguë (retour à l'heure d'hiver) ce jour-là."""


def _utc(instant_ms: int) -> datetime:
    if type(instant_ms) is not int:
        raise ValueError('instant en millisecondes entières attendu')
    return _EPOQUE + timedelta(milliseconds=instant_ms)


def _ms(moment: datetime) -> int:
    return (moment - _EPOQUE) // timedelta(milliseconds=1)


class SessionsLondres:
    """Calendrier civil des méthodes : fuseau `session_timezone`, jours actifs, blackout UTC de rollover."""

    def __init__(self, parametres: ParametresTechniques):
        self._fuseau = ZoneInfo(parametres.fuseau_sessions)
        self._jours = parametres.jours_actifs
        self._blackout = (parametres.blackout_debut, parametres.blackout_fin)

    def local(self, instant_ms: int) -> datetime:
        return _utc(instant_ms).astimezone(self._fuseau)

    def jour_londres(self, instant_ms: int) -> date:
        return self.local(instant_ms).date()

    def jour_utc(self, instant_ms: int) -> date:
        return _utc(instant_ms).date()

    def jour_actif(self, jour: date) -> bool:
        return jour.weekday() in self._jours

    def dans_fenetre(self, ouverture_ms: int, cloture_ms: int, debut: str, fin_exclue: str) -> bool:
        """Bougie [ouverture, clôture) admissible pour une fenêtre locale [début, fin) d'un jour actif."""
        if not ouverture_ms < cloture_ms:
            raise ValueError('l\'ouverture doit précéder strictement la clôture')
        lo, lc = self.local(ouverture_ms), self.local(cloture_ms)
        return (lo.date() == lc.date() and self.jour_actif(lc.date())
                and lo.time() >= analyser_heure(debut) and lc.time() < analyser_heure(fin_exclue))

    def instant_local(self, jour: date, heure: str) -> int:
        """Instant UTC (ms) d'une heure locale d'un jour, refusée si inexistante ou ambiguë."""
        naif = datetime.combine(jour, analyser_heure(heure))
        avant, apres = naif.replace(tzinfo=self._fuseau, fold=0), naif.replace(tzinfo=self._fuseau, fold=1)
        if avant.utcoffset() != apres.utcoffset():
            raise HeureLocaleInvalide(f'{heure} n\'existe pas ou est ambiguë le {jour.isoformat()}')
        return _ms(avant)

    def dans_blackout(self, instant_ms: int) -> bool:
        """Heure UTC dans [début, fin) du blackout de rollover (intervalle éventuellement à cheval sur minuit)."""
        heure: time = _utc(instant_ms).time()
        debut, fin = self._blackout
        return debut <= heure < fin if debut <= fin else (heure >= debut or heure < fin)

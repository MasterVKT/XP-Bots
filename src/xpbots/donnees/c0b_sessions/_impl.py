"""Implémentation de la couche 0b (sessions_londres). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from xpbots.noyau.c0a_temps import ErreurInstant, aligner, instant_depuis_datetime, instant_vers_datetime
from xpbots.noyau.c0c_configuration import ParametresCommuns

_JOUR = timedelta(days=1)


class ErreurSessions(ValueError):
    """Fuseau, heure locale, fenêtre ou instant refusés."""


def _secondes(heure: time) -> int:
    return heure.hour * 3600 + heure.minute * 60 + heure.second


class CalendrierLondres:
    """Repères de Londres et du jour UTC, fondés sur la base IANA, jamais sur un décalage constant."""

    def __init__(self, fuseau: str, jours_actifs: tuple[int, ...], blackout_debut: time, blackout_fin: time) -> None:
        try:
            self._zone = ZoneInfo(fuseau)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as erreur:
            raise ErreurSessions(f'fuseau inconnu : {fuseau!r}') from erreur
        jours = tuple(jours_actifs)
        if not jours or not all(not isinstance(j, bool) and isinstance(j, int) and 0 <= j <= 6 for j in jours):
            raise ErreurSessions('jours actifs de 0 à 6 attendus')
        if not isinstance(blackout_debut, time) or not isinstance(blackout_fin, time) or blackout_debut == blackout_fin:
            raise ErreurSessions('blackout de durée non nulle attendu')
        self.fuseau = fuseau
        self.jours_actifs = frozenset(jours)
        self.blackout_debut = blackout_debut
        self.blackout_fin = blackout_fin

    @classmethod
    def depuis_parametres(cls, commun: ParametresCommuns) -> 'CalendrierLondres':
        return cls(commun.session_timezone, commun.active_weekdays_local, commun.rollover_blackout_utc_start,
                   commun.rollover_blackout_utc_end)

    def _utc(self, instant_ms: int) -> datetime:
        try:
            return instant_vers_datetime(instant_ms)
        except ErreurInstant as erreur:
            raise ErreurSessions(str(erreur)) from erreur

    def datetime_local(self, instant_ms: int) -> datetime:
        return self._utc(instant_ms).astimezone(self._zone)

    def jour_local(self, instant_ms: int) -> date:
        return self.datetime_local(instant_ms).date()

    def jour_actif(self, jour: date) -> bool:
        return jour.weekday() in self.jours_actifs

    def instant_local(self, jour: date, heure: time) -> int:
        if not isinstance(jour, date) or isinstance(jour, datetime) or not isinstance(heure, time):
            raise ErreurSessions('date et heure locales attendues')
        naif = datetime.combine(jour, heure)
        avant, apres = naif.replace(tzinfo=self._zone, fold=0), naif.replace(tzinfo=self._zone, fold=1)
        if avant.utcoffset() != apres.utcoffset():
            raise ErreurSessions(f'heure locale inexistante ou ambiguë : {jour} {heure}')
        return instant_depuis_datetime(avant)

    def ouvertures(self, jour: date, debut: time, fin_exclue: time, duree_ms: int) -> tuple[int, ...]:
        premier, fin = self.instant_local(jour, debut), self.instant_local(jour, fin_exclue)
        try:
            aligne = aligner(premier, duree_ms) == premier
        except ErreurInstant as erreur:
            raise ErreurSessions(str(erreur)) from erreur
        if fin <= premier or (fin - premier) % duree_ms or not aligne:
            raise ErreurSessions('bornes non alignées ou non multiples de la durée')
        return tuple(range(premier, fin, duree_ms))

    def decision_dans_fenetre(self, ouverture_ms: int, cloture_ms: int, debut: time, fin_exclue: time) -> bool:
        ouverture, cloture = self.datetime_local(ouverture_ms), self.datetime_local(cloture_ms)
        return (ouverture.date() == cloture.date() and cloture.weekday() in self.jours_actifs
                and ouverture.time().replace(microsecond=0) >= debut
                and cloture.time().replace(microsecond=0) < fin_exclue)

    def jour_utc(self, instant_ms: int) -> date:
        return self._utc(instant_ms).date()

    def dans_blackout(self, instant_ms: int) -> bool:
        moment = self._utc(instant_ms)
        secondes = _secondes(moment.time()) + moment.microsecond / 1e6
        debut, fin = _secondes(self.blackout_debut), _secondes(self.blackout_fin)
        if debut < fin:
            return debut <= secondes < fin
        return secondes >= debut or secondes < fin

    def prochain_debut_blackout(self, instant_ms: int) -> int:
        moment = self._utc(instant_ms)
        candidat = datetime.combine(moment.date(), self.blackout_debut, tzinfo=timezone.utc)
        if candidat < moment:
            candidat += _JOUR
        return instant_depuis_datetime(candidat)

"""Implémentation de la couche 1e (quotas_london). Révisable à comportement constant sous harnais complet."""
from datetime import date

from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.london.c0a_parametres import ParametresLondon
from xpbots.london.c0b_types import ErreurLondon, EtatQuotas, RefusLondon
from xpbots.noyau.c1c_domaine import Issue, Motif, NatureIssue, Sens


class QuotasLondon:
    def __init__(self, parametres: ParametresLondon, symbole: str, etat: EtatQuotas | None = None):
        if not isinstance(parametres, ParametresLondon) or not isinstance(symbole, str) or not symbole:
            raise ErreurLondon('paramètres London et symbole non vide attendus')
        if etat is not None and not isinstance(etat, EtatQuotas):
            raise ErreurLondon('état de quotas attendu')
        self._parametres, self._symbole = parametres, symbole
        self._calendrier = CalendrierLondres.depuis_parametres(parametres.commun)
        self._etat = etat or EtatQuotas()
        for cle in self._etat.remplissages:
            self._verifier_cle(cle)

    def _verifier_cle(self, cle):
        if cle.symbole != self._symbole or cle.strategie != self._parametres.strategy_id:
            raise ErreurLondon('issue ou état d’une autre stratégie ou d’un autre symbole')

    @property
    def etat(self) -> EtatQuotas:
        return self._etat

    @property
    def total(self) -> int:
        return len(self._etat.remplissages)

    def par_sens(self, sens: Sens) -> int:
        if not isinstance(sens, Sens):
            raise ErreurLondon('sens typé attendu')
        return sum(cle.sens is sens for cle in self._etat.remplissages)

    def changer_jour(self, jour: date) -> None:
        if type(jour) is not date or self._etat.jour is not None and jour < self._etat.jour:
            raise ErreurLondon('jour invalide ou antérieur au jour courant')
        if jour != self._etat.jour:
            self._etat = EtatQuotas(jour)

    def sur_issue(self, issue: Issue) -> None:
        if not isinstance(issue, Issue):
            raise ErreurLondon('issue du noyau attendue')
        self._verifier_cle(issue.cle)
        if issue.nature is not NatureIssue.REMPLIE:
            return
        jour = self._calendrier.jour_local(issue.instant_ms)
        if self._etat.jour is None or jour > self._etat.jour:
            self.changer_jour(jour)
        if jour == self._etat.jour and issue.cle not in self._etat.remplissages:
            self._etat = EtatQuotas(jour, (*self._etat.remplissages, issue.cle))

    def refus(self, sens: Sens) -> RefusLondon | None:
        compte = self.par_sens(sens)
        if self.total >= self._parametres.max_filled_entries_per_symbol_local_day:
            return RefusLondon(Motif.DAILY_ENTRY_CAP, 'MAXIMUM_JOURNALIER')
        if compte >= self._parametres.max_filled_entries_per_direction_local_day:
            return RefusLondon(Motif.DAILY_ENTRY_CAP, 'SENS_DEJA_REMPLI')
        return None

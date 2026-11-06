"""Implémentation de la couche 2 (moteur_london). Révisable à comportement constant sous harnais complet."""
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from xpbots.donnees.c0a_types import BougieEnrichie, UniteTemps
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.london.c0a_parametres import ParametresLondon, charger_parametres_london
from xpbots.london.c0b_types import ErreurLondon, RefusLondon, tick_flottant, verifier_bougie
from xpbots.london.c1a_range import construire_range
from xpbots.london.c1b_gel_atr_h1 import construire_gel
from xpbots.london.c1c_cassure import evaluer_cassure
from xpbots.london.c1d_stop import calculer_stop
from xpbots.london.c1e_quotas import QuotasLondon
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1c_domaine import AbsenceDeSignal, Issue, Motif, NatureIssue, Sens, SignalTechnique


class MoteurLondon:
    """État d'un symbole et d'un bras ; aucune relation avec le coordinateur de compte."""

    def __init__(self, parametres: ParametresLondon, symbole: str, tick_size: Decimal):
        if (not isinstance(parametres, ParametresLondon) or not isinstance(symbole, str)
                or symbole not in parametres.commun.universe_priority):
            raise ErreurLondon('paramètres London et symbole canonique configuré attendus')
        tick_flottant(tick_size)
        self._p, self._symbole, self._tick_size = parametres, symbole, tick_size
        self.identifiant = parametres.strategy_id
        self._calendrier = CalendrierLondres.depuis_parametres(parametres.commun)
        self._quotas = QuotasLondon(parametres, symbole)
        self._jour = None
        self._range = self._gel = None
        self._m15_range = {}
        self._h1 = {}
        self._ouvertures = ()
        self._dernier_m15 = None
        self._en_trou = False
        self._positions = set()
        self._cloturees = set()

    @property
    def etat_quotas(self):
        return self._quotas.etat

    @property
    def position_ouverte(self) -> bool:
        return bool(self._positions)

    @property
    def range(self):
        return self._range

    @property
    def gel(self):
        return self._gel

    def _adopter_jour(self, jour) -> None:
        if self._jour is None or jour > self._jour:
            self._jour = jour
            self._range = self._gel = None
            self._m15_range, self._h1 = {}, {}
            self._quotas.changer_jour(jour)
            self._ouvertures = self._calendrier.ouvertures(jour, self._p.range_start_local,
                                                         self._p.range_end_local_exclusive,
                                                         self._p.commun.timeframe_seconds * 1000)

    def sur_issue(self, issue: Issue) -> None:
        if not isinstance(issue, Issue) or issue.cle.symbole != self._symbole or issue.cle.strategie != self.identifiant:
            raise ErreurLondon('issue de ce moteur attendue')
        self._adopter_jour(self._calendrier.jour_local(issue.instant_ms))
        self._quotas.sur_issue(issue)
        if issue.nature is NatureIssue.REMPLIE and issue.cle not in self._cloturees:
            self._positions.add(issue.cle)
        elif issue.nature is NatureIssue.CLOTUREE:
            self._positions.discard(issue.cle)
            self._cloturees.add(issue.cle)

    def _essayer_gel(self, fin_ms) -> None:
        borne = self._calendrier.instant_local(self._jour, self._p.range_h1_atr_frozen_local)
        if self._gel is None and fin_ms >= borne and self._calendrier.jour_actif(self._jour):
            self._gel = construire_gel(self._jour, self._h1.values(), self._p)

    def _contexte(self, fin_ms):
        contexte = {'jour_londres': self._jour.isoformat(), 'trou_actif': self._en_trou,
                    'quota_total': self._quotas.total, 'quota_achat': self._quotas.par_sens(Sens.ACHAT),
                    'quota_vente': self._quotas.par_sens(Sens.VENTE), 'position_ouverte': self.position_ouverte,
                    'tick_size': str(self._tick_size)}
        if self._range is not None and self._range.disponible_ms <= fin_ms:
            contexte.update(range_haut=self._range.haut, range_bas=self._range.bas,
                            largeur_range=self._range.largeur, range_disponible_ms=self._range.disponible_ms)
        if self._gel is not None:
            contexte['gel_disponible_ms'] = self._gel.disponible_ms
            if self._gel.disponible_ms <= fin_ms:
                contexte.update(atr_h1=self._gel.atr, gel_fin_h1_ms=self._gel.fin_h1_ms)
                if 'largeur_range' in contexte:
                    contexte['rapport_range_atr_h1'] = contexte['largeur_range'] / self._gel.atr
        return contexte

    def sur_bougie(self, enrichie: BougieEnrichie):
        if not isinstance(enrichie, BougieEnrichie):
            raise ErreurLondon('bougie enrichie attendue')
        b = enrichie.bougie
        verifier_bougie(enrichie, enrichie.unite, enrichie.unite.duree_ms(self._p.commun), self._symbole)
        if (enrichie.jour_londres != self._calendrier.jour_local(b.debut_ms)
                or enrichie.ouverture_locale != self._calendrier.datetime_local(b.debut_ms)
                or enrichie.cloture_locale != self._calendrier.datetime_local(b.fin_ms)):
            raise ErreurLondon('repères locaux incohérents avec la bougie')
        if self._jour is not None and enrichie.jour_londres < self._jour:
            return None
        if enrichie.unite is UniteTemps.M15 and self._dernier_m15 is not None and b.fin_ms <= self._dernier_m15:
            return None
        self._adopter_jour(enrichie.jour_londres)
        if enrichie.unite is UniteTemps.H1:
            borne = self._calendrier.instant_local(self._jour, self._p.range_h1_atr_frozen_local)
            if borne - self._p.commun.h1_seconds * 1000 <= b.fin_ms <= borne:
                ancienne = self._h1.get(b.fin_ms)
                if ancienne is None or self._gel is None and not ancienne.bougie.valide and b.valide:
                    self._h1[b.fin_ms] = enrichie
            self._essayer_gel(b.fin_ms)
            return None
        self._dernier_m15 = b.fin_ms
        if not b.valide and b.motif_invalidite in ('TROU_DONNEES', 'HORAIRES_INCONNUS'):
            self._en_trou, self._range = True, None
        elif b.valide or b.motif_invalidite == 'AUCUN_BID':
            self._en_trou = False
        if b.debut_ms in self._ouvertures:
            self._m15_range.setdefault(b.debut_ms, enrichie)
        fin_range = self._calendrier.instant_local(self._jour, self._p.range_end_local_exclusive)
        if self._range is None and not self._en_trou and b.fin_ms >= fin_range:
            candidat = construire_range(self._jour, self._m15_range.values(), self._p)
            if not isinstance(candidat, RefusLondon):
                self._range = candidat
        self._essayer_gel(b.fin_ms)
        contexte = self._contexte(b.fin_ms)

        def absence(motif, detail):
            return AbsenceDeSignal(self.identifiant, self._symbole, b.fin_ms, motif, detail, contexte)

        def refuser(refus):
            return absence(refus.motif, refus.detail)

        if self._en_trou:
            return absence(Motif.DATA_GAP, 'TROU_ACTIF')
        if not self._calendrier.jour_actif(enrichie.jour_londres):
            return absence(Motif.OUTSIDE_SESSION, 'JOUR_INACTIF')
        if not self._calendrier.decision_dans_fenetre(b.debut_ms, b.fin_ms, self._p.session_start_local,
                                                     self._p.entry_end_local_exclusive):
            return absence(Motif.OUTSIDE_SESSION, 'HORS_FENETRE')
        i = enrichie.indicateurs
        if not b.valide:
            return absence(Motif.NO_SETUP, 'PAS_DE_CASSURE')
        if i.rang < self._p.commun.warmup_closed_m15_bars - 1:
            return absence(Motif.WARMUP, 'M15_INSUFFISANTES')
        if i.a is None:
            return absence(Motif.WARMUP, 'ATR_M15_INDISPONIBLE')
        if i.a <= 0:
            return absence(Motif.NO_SETUP, 'ATR_NON_POSITIF')
        contexte.update(tr_signal=i.tr, atr_reference=i.a)
        if self._range is None:
            return refuser(construire_range(self._jour, self._m15_range.values(), self._p))
        if self._range.disponible_ms > b.fin_ms:
            return absence(Motif.DATA_GAP, 'ATTENTE_RECALCUL')
        if self._gel is None:
            return absence(Motif.WARMUP, 'ATR_H1_INDISPONIBLE')
        if self._gel.disponible_ms > b.fin_ms:
            return absence(Motif.NO_SETUP, 'GEL_ATR_H1_POSTERIEUR')
        if not self._p.range_min_h1_atr * self._gel.atr <= self._range.largeur <= self._p.range_max_h1_atr * self._gel.atr:
            return absence(Motif.NO_SETUP, 'RANGE_HORS_BORNES')
        if self.position_ouverte:
            return absence(Motif.SYMBOL_BUSY, 'POSITION_METHODE')
        cassure = evaluer_cassure(enrichie, self._range, self._tick_size, self._p)
        if isinstance(cassure, RefusLondon):
            return refuser(cassure)
        contexte.update(fraction_corps=cassure.fraction_corps, fraction_cloture=cassure.fraction_cloture,
                        buffer_cassure=cassure.buffer)
        refus = self._quotas.refus(cassure.sens)
        if refus is not None:
            return refuser(refus)
        stop = calculer_stop(enrichie, self._range, cassure.sens, self._tick_size, self._p)
        if isinstance(stop, RefusLondon):
            return refuser(stop)
        contexte.update(composantes_stop=stop.composantes, composantes_contraignantes=stop.contraignantes)
        return SignalTechnique(self.identifiant, self._symbole, b.fin_ms, cassure.sens, b.cloture, i.a,
                               stop.niveau, stop.multiple_objectif, contexte)


class StrategieLondon:
    """Façade structurelle injectée, avec un moteur indépendant par symbole."""

    def __init__(self, parametres: ParametresLondon, tailles_tick: Mapping[str, Decimal]):
        if not isinstance(parametres, ParametresLondon) or not isinstance(tailles_tick, Mapping):
            raise ErreurLondon('paramètres et tailles de tick par symbole attendus')
        tailles = dict(tailles_tick)
        for symbole, tick in tailles.items():
            if not isinstance(symbole, str) or symbole not in parametres.commun.universe_priority:
                raise ErreurLondon('symbole canonique configuré attendu')
            tick_flottant(tick)
        self.identifiant = parametres.strategy_id
        self._p, self._tailles = parametres, MappingProxyType(tailles)
        self._moteurs = {}

    def _moteur(self, symbole):
        if symbole not in self._tailles:
            raise ErreurLondon('taille de tick absente pour ce symbole')
        if symbole not in self._moteurs:
            self._moteurs[symbole] = MoteurLondon(self._p, symbole, self._tailles[symbole])
        return self._moteurs[symbole]

    def sur_bougie(self, enrichie: BougieEnrichie):
        if not isinstance(enrichie, BougieEnrichie):
            raise ErreurLondon('bougie enrichie attendue')
        return self._moteur(enrichie.bougie.symbole).sur_bougie(enrichie)

    def sur_issue(self, issue: Issue) -> None:
        if not isinstance(issue, Issue) or issue.cle.strategie != self.identifiant:
            raise ErreurLondon('issue London attendue')
        self._moteur(issue.cle.symbole).sur_issue(issue)


def fabriquer_strategie(configuration: ConfigurationFigee, tailles_tick: Mapping[str, Decimal]) -> StrategieLondon:
    if not isinstance(configuration, ConfigurationFigee):
        raise ErreurLondon('configuration figée attendue')
    return StrategieLondon(charger_parametres_london(configuration.technique), tailles_tick)

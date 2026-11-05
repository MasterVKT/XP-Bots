"""Couche 2 de `moteur-ema` : machine à états S01.2 d'un symbole (transitions T1 à T12 du plan maître, R1, R2).

Contrat : `mcl/moteur-ema/contrats/couche-2.md`. Sources : S01.1, S01.2, S01.4 (compteur), S01.6, C08 (position
possédée, sortie), A07 (refus définitif), R1, R2. Ordre suivi à chaque clôture, identique à
`reference.technical.ema_setups` pour la partie technique : changement de jour Londres, position possédée, issue en
attente, fenêtre, données exploitables, cooldown, armement, validité, contact et âge, reprise.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from xpbots.moteur_ema.c0_parametres import ParametresEMA
from xpbots.moteur_ema.c1a_tendance import sens_tendance
from xpbots.moteur_ema.c1b_repli import contact, contexte_armement, repli_valide
from xpbots.moteur_ema.c1c_reprise import est_reprise
from xpbots.noyau.decisions import IssueSignal, Refuse, Rempli, Sens

FORMAT_ETAT = 'xp-moteur-ema-etat-v1'


class EtatTechnique(StrEnum):
    IDLE = 'IDLE'
    ARMED_LONG = 'ARMED_LONG'
    ARMED_SHORT = 'ARMED_SHORT'
    PULLBACK_LONG = 'PULLBACK_LONG'
    PULLBACK_SHORT = 'PULLBACK_SHORT'
    COOLDOWN = 'COOLDOWN'
    OWNED_POSITION = 'OWNED_POSITION'
    ATTENTE_ISSUE = 'ATTENTE_ISSUE'  # sous-état technique R2 : signal émis, issue encore inconnue


class NatureTransition(StrEnum):
    """Ce qui s'est produit à une clôture (journalisé dans l'état du détecteur)."""

    POSITION = 'POSITION'  # position possédée : aucune préparation
    ATTENTE = 'ATTENTE'  # issue du signal encore inconnue (R2)
    HORS_FENETRE = 'HORS_FENETRE'
    DONNEES = 'DONNEES'  # bougie inexploitable : préchauffage, trou, A indisponible
    IGNOREE = 'IGNOREE'  # clôture de cooldown
    AUCUNE = 'AUCUNE'
    ARMEMENT = 'ARMEMENT'
    ANNULATION = 'ANNULATION'  # tendance ou validité violée ; réarmement possible, jamais d'entrée
    EXPIRATION = 'EXPIRATION'  # âge au-delà du maximum ; réarmement possible, jamais d'entrée
    CONTACT = 'CONTACT'  # premier contact : début du repli
    REPLI = 'REPLI'
    REPRISE = 'REPRISE'  # premier signal complet : repli consommé


class IssueInattendue(RuntimeError):
    """Issue ou sortie reçue alors qu'aucun signal n'attend d'issue, ou qu'aucune position n'est possédée."""


class EtatIncompatible(ValueError):
    """État exporté illisible ou incohérent."""


_ARMES = {Sens.ACHAT: EtatTechnique.ARMED_LONG, Sens.VENTE: EtatTechnique.ARMED_SHORT}
_REPLIS = {Sens.ACHAT: EtatTechnique.PULLBACK_LONG, Sens.VENTE: EtatTechnique.PULLBACK_SHORT}
_PREPARATION = frozenset(_ARMES.values()) | frozenset(_REPLIS.values())
_CHAMPS_PRIX = ('o', 'h', 'l', 'c', 'tr', 'e_rapide', 'e_moyenne', 'e_lente', 'e_lente_decalee', 'rsi', 'a_t')


@dataclass(frozen=True)
class ObservationEMA:
    """Clôture M15 vue par la machine. Les valeurs ne sont exigées que si la bougie est exploitable."""

    cloture_ms: int
    jour: date
    dans_fenetre: bool
    exploitable: bool
    o: float | None = None
    h: float | None = None
    l: float | None = None  # noqa: E741
    c: float | None = None
    tr: float | None = None
    e_rapide: float | None = None
    e_moyenne: float | None = None
    e_lente: float | None = None
    e_lente_decalee: float | None = None
    rsi: float | None = None
    a_t: float | None = None

    def __post_init__(self):
        if type(self.cloture_ms) is not int or type(self.jour) is not date:
            raise ValueError('clôture en ms entières et jour Londres (date) attendus')
        if type(self.dans_fenetre) is not bool or type(self.exploitable) is not bool:
            raise ValueError('drapeaux booléens attendus')
        if self.exploitable:
            for nom in _CHAMPS_PRIX:
                v = getattr(self, nom)
                if type(v) not in (int, float) or not math.isfinite(v):
                    raise ValueError(f'{nom} : nombre fini attendu pour une bougie exploitable, reçu {v!r}')
            if not self.a_t > 0 or self.l > self.h:
                raise ValueError('A_t > 0 et L ≤ H attendus')


@dataclass(frozen=True)
class Reprise:
    """Premier signal technique complet : sens, extrêmes de toutes les bougies du repli (signal compris), âge."""

    sens: Sens
    plus_bas: float
    plus_haut: float
    age: int
    debut_ms: int

    @property
    def extreme(self) -> float:
        return self.plus_bas if self.sens is Sens.ACHAT else self.plus_haut


@dataclass(frozen=True)
class Transition:
    nature: NatureTransition
    avant: EtatTechnique
    apres: EtatTechnique
    tendance: Sens | None = None
    reprise: Reprise | None = None


class MachineEtatsEMA:
    """États S01.2 d'un symbole pour une méthode ; état persistable (`exporter`, `importer`)."""

    def __init__(self, p: ParametresEMA):
        self._p = p
        self._etat = EtatTechnique.IDLE
        self._sens: Sens | None = None
        self._debut_ms: int | None = None
        self._age: int | None = None
        self._bas: float | None = None
        self._haut: float | None = None
        self._dernier_jour: date | None = None
        self._cooldown_depuis_ms: int | None = None
        self._cooldown_restantes: int | None = None
        self._signal_cloture_ms: int | None = None
        self._signal_jour: date | None = None
        self._position_ms: int | None = None
        self._jour_compteur: date | None = None
        self._entrees = 0

    @property
    def etat(self) -> EtatTechnique:
        return self._etat

    @property
    def sens(self) -> Sens | None:
        return self._sens

    @property
    def signal_cloture_ms(self) -> int | None:
        """Clôture du signal dont l'issue est attendue (ATTENTE_ISSUE), sinon None."""
        return self._signal_cloture_ms

    def entrees_remplies(self, jour: date) -> int:
        """Entrées remplies du jour Londres `jour` (S01.4) ; jamais remis à zéro par un redémarrage."""
        return self._entrees if jour == self._jour_compteur else 0

    # -- transitions ---------------------------------------------------------------------------------------------

    def etape(self, obs: ObservationEMA) -> Transition:
        if type(obs) is not ObservationEMA:
            raise ValueError('ObservationEMA attendue')
        avant = self._etat
        if obs.jour != self._dernier_jour:  # T10 : changement de jour Londres
            self._dernier_jour = obs.jour
            if self._etat in _PREPARATION or self._etat is EtatTechnique.COOLDOWN:
                self._repos()
        if self._etat is EtatTechnique.OWNED_POSITION:  # T8 : aucune préparation pendant une position
            return self._transition(NatureTransition.POSITION, avant)
        if self._etat is EtatTechnique.ATTENTE_ISSUE:  # T12 (R2)
            return self._transition(NatureTransition.ATTENTE, avant)
        if not obs.dans_fenetre:  # T10 : hors fenêtre, tout est effacé (cooldown compris)
            if self._etat is not EtatTechnique.IDLE:
                self._repos()
            return self._transition(NatureTransition.HORS_FENETRE, avant)
        if not obs.exploitable:  # T10 : trou, préchauffage ; le cooldown n'est pas décompté
            if self._etat in _PREPARATION:
                self._repos()
            return self._transition(NatureTransition.DONNEES, avant)
        if self._etat is EtatTechnique.COOLDOWN:  # T7, T9, R1
            if obs.cloture_ms > self._cooldown_depuis_ms:
                self._cooldown_restantes -= 1
                if self._cooldown_restantes == 0:
                    self._repos()
            return self._transition(NatureTransition.IGNOREE, avant)
        p = self._p
        tendance = sens_tendance(obs.e_rapide, obs.e_moyenne, obs.e_lente, obs.e_lente_decalee)
        if self._etat is EtatTechnique.IDLE:  # T1 : la bougie d'armement n'est jamais repli ni signal
            nature = NatureTransition.ARMEMENT if self._armer(tendance, obs) else NatureTransition.AUCUNE
            return self._transition(nature, avant, tendance)
        s = self._sens
        if tendance is not s or not repli_valide(s, obs.c, obs.e_lente, obs.rsi, obs.a_t, p):  # T4
            self._repos()
            self._armer(tendance, obs)
            return self._transition(NatureTransition.ANNULATION, avant, tendance)
        if self._etat in _ARMES.values():
            if not contact(obs.h, obs.l, obs.e_rapide, obs.e_lente):
                return self._transition(NatureTransition.AUCUNE, avant, tendance)
            self._etat = _REPLIS[s]  # T2 : premier contact, âge 1
            self._debut_ms, self._age, self._bas, self._haut = obs.cloture_ms, 1, obs.l, obs.h
            nature = NatureTransition.CONTACT
        else:
            age = self._age + 1  # T3 : âge t − début + 1
            if age > p.age_max_repli:  # T5
                self._repos()
                self._armer(tendance, obs)
                return self._transition(NatureTransition.EXPIRATION, avant, tendance)
            self._age, self._bas, self._haut = age, min(self._bas, obs.l), max(self._haut, obs.h)
            nature = NatureTransition.REPLI
        if not est_reprise(s, obs.o, obs.h, obs.l, obs.c, obs.tr, obs.e_rapide, obs.rsi, obs.a_t, p):
            return self._transition(nature, avant, tendance)
        reprise = Reprise(s, self._bas, self._haut, self._age, self._debut_ms)  # T6 : repli consommé
        self._effacer_repli()
        self._etat = EtatTechnique.ATTENTE_ISSUE
        self._sens = s
        self._signal_cloture_ms, self._signal_jour = obs.cloture_ms, obs.jour
        return self._transition(NatureTransition.REPRISE, avant, tendance, reprise)

    def appliquer_issue(self, issue: IssueSignal) -> None:
        """Issue définitive du signal en attente : fill (même partiel, T8) ou refus (T7, R2)."""
        if self._etat is not EtatTechnique.ATTENTE_ISSUE:
            raise IssueInattendue(f'aucun signal n\'attend d\'issue (état {self._etat})')
        if type(issue) not in (Rempli, Refuse):
            raise ValueError('issue Rempli ou Refuse attendue')
        if issue.instant_ms < self._signal_cloture_ms:
            raise ValueError('issue antérieure à la clôture du signal')
        if type(issue) is Rempli:  # T8, T11 : une entrée dès le premier volume non nul
            if self._jour_compteur != self._signal_jour:
                self._jour_compteur, self._entrees = self._signal_jour, 0
            self._entrees += 1
            self._etat, self._position_ms = EtatTechnique.OWNED_POSITION, issue.instant_ms
        else:
            self._cooldown(issue.instant_ms)
        self._signal_cloture_ms = self._signal_jour = None

    def notifier_sortie(self, instant_ms: int) -> None:
        """Sortie de la position possédée (T9, R1) : la première clôture strictement postérieure est ignorée."""
        if type(instant_ms) is not int:
            raise ValueError('instant en ms entières attendu')
        if self._etat is not EtatTechnique.OWNED_POSITION:
            raise IssueInattendue(f'aucune position possédée (état {self._etat})')
        if instant_ms < self._position_ms:
            raise ValueError('sortie antérieure au remplissage')
        self._position_ms = None
        self._cooldown(instant_ms)

    def effacer(self) -> None:
        """Trou de données inexpliqué (C03.6) : armement et repli effacés ; position, issue et cooldown conservés."""
        if self._etat in _PREPARATION:
            self._repos()

    def etat_detecteur(self) -> dict:
        """État du détecteur pour le journal C09."""
        return {'etat': self._etat, 'sens': self._sens, 'age_repli': self._age, 'plus_bas_repli': self._bas,
                'plus_haut_repli': self._haut, 'debut_repli_ms': self._debut_ms,
                'cooldown_restantes': self._cooldown_restantes,
                'entrees_jour': self.entrees_remplies(self._dernier_jour)}

    # -- persistance ---------------------------------------------------------------------------------------------

    def exporter(self) -> dict:
        jour = lambda d: None if d is None else d.isoformat()  # noqa: E731
        return {'format': FORMAT_ETAT, 'etat': self._etat.value,
                'sens': None if self._sens is None else int(self._sens), 'debut_ms': self._debut_ms,
                'age': self._age, 'plus_bas': self._bas, 'plus_haut': self._haut,
                'dernier_jour': jour(self._dernier_jour), 'cooldown_depuis_ms': self._cooldown_depuis_ms,
                'cooldown_restantes': self._cooldown_restantes, 'signal_cloture_ms': self._signal_cloture_ms,
                'signal_jour': jour(self._signal_jour), 'position_ms': self._position_ms,
                'jour_compteur': jour(self._jour_compteur), 'entrees': self._entrees}

    @classmethod
    def importer(cls, p: ParametresEMA, donnees: dict) -> MachineEtatsEMA:
        machine = cls(p)
        try:
            if donnees['format'] != FORMAT_ETAT or set(donnees) != set(machine.exporter()):
                raise EtatIncompatible('format ou clés de l\'état exporté inattendus')
            machine._etat = EtatTechnique(donnees['etat'])
            machine._sens = None if donnees['sens'] is None else Sens(donnees['sens'])
            machine._debut_ms, machine._age = donnees['debut_ms'], donnees['age']
            machine._bas, machine._haut = donnees['plus_bas'], donnees['plus_haut']
            machine._dernier_jour = cls._jour(donnees['dernier_jour'])
            machine._cooldown_depuis_ms = donnees['cooldown_depuis_ms']
            machine._cooldown_restantes = donnees['cooldown_restantes']
            machine._signal_cloture_ms = donnees['signal_cloture_ms']
            machine._signal_jour = cls._jour(donnees['signal_jour'])
            machine._position_ms = donnees['position_ms']
            machine._jour_compteur = cls._jour(donnees['jour_compteur'])
            machine._entrees = donnees['entrees']
        except (KeyError, TypeError, ValueError) as erreur:
            if isinstance(erreur, EtatIncompatible):
                raise
            raise EtatIncompatible(f'état exporté illisible : {erreur}') from erreur
        machine._verifier()
        return machine

    # -- interne -------------------------------------------------------------------------------------------------

    @staticmethod
    def _jour(texte):
        return None if texte is None else date.fromisoformat(texte)

    def _verifier(self):
        e = self._etat
        entiers = (self._debut_ms, self._age, self._cooldown_depuis_ms, self._cooldown_restantes,
                   self._signal_cloture_ms, self._position_ms)
        if any(v is not None and type(v) is not int for v in entiers) or type(self._entrees) is not int \
                or self._entrees < 0 or any(v is not None and type(v) not in (int, float)
                                            for v in (self._bas, self._haut)):
            raise EtatIncompatible('types de l\'état exporté inattendus')
        groupes = {
            'sens': ((self._sens,), e in _PREPARATION
                     or e in (EtatTechnique.ATTENTE_ISSUE, EtatTechnique.OWNED_POSITION)),
            'repli': ((self._debut_ms, self._age, self._bas, self._haut), e in _REPLIS.values()),
            'cooldown': ((self._cooldown_depuis_ms, self._cooldown_restantes), e is EtatTechnique.COOLDOWN),
            'signal': ((self._signal_cloture_ms, self._signal_jour), e is EtatTechnique.ATTENTE_ISSUE),
            'position': ((self._position_ms,), e is EtatTechnique.OWNED_POSITION),
        }
        for nom, (valeurs, attendu) in groupes.items():
            if any(v is None for v in valeurs) if attendu else any(v is not None for v in valeurs):
                raise EtatIncompatible(f'état {e} incohérent ({nom})')
        if e in _PREPARATION and e not in (_ARMES[self._sens], _REPLIS[self._sens]):
            raise EtatIncompatible('sens incohérent avec l\'état')
        if self._cooldown_restantes is not None and self._cooldown_restantes <= 0:
            raise EtatIncompatible('cooldown épuisé')

    def _transition(self, nature, avant, tendance=None, reprise=None) -> Transition:
        return Transition(nature, avant, self._etat, tendance, reprise)

    def _armer(self, tendance: Sens | None, obs: ObservationEMA) -> bool:
        if tendance is not None and contexte_armement(tendance, obs.c, obs.e_rapide, obs.rsi, self._p):
            self._etat, self._sens = _ARMES[tendance], tendance
            return True
        return False

    def _effacer_repli(self):
        self._debut_ms = self._age = self._bas = self._haut = None

    def _repos(self):
        self._etat, self._sens = EtatTechnique.IDLE, None
        self._effacer_repli()
        self._cooldown_depuis_ms = self._cooldown_restantes = None

    def _cooldown(self, depuis_ms: int):
        self._repos()
        self._etat = EtatTechnique.COOLDOWN
        self._cooldown_depuis_ms, self._cooldown_restantes = depuis_ms, self._p.clotures_cooldown

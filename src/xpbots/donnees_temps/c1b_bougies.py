"""Couche 1b de `donnees-temps` : bougies Bid clôturées et qualification des intervalles (C03 points 2, 4 à 6).

Contrat : `mcl/donnees-temps/contrats/couche-1b.md`. R4 : un intervalle attendu sans Bid alors que le flux était
établi est incomplet (`SANS_BID`). R5 : la couverture vient de l'appelant (flux réel ou manifeste), aucun seuil
de silence n'est inventé.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from xpbots.donnees_temps.c0_parametres_seances import CalendrierSeances
from xpbots.noyau.marche import Bougie, Tick
from xpbots.noyau.temps import MS_PAR_SECONDE, Instant

MOTIF_COUVERTURE = 'COUVERTURE'
MOTIF_SANS_BID = 'SANS_BID'


class TickHorsOrdre(ValueError):
    """Tick qui ne suit pas strictement le précédent, ou d'un autre symbole."""


class HorlogeEnRecul(ValueError):
    """Avance d'horloge vers un instant antérieur à l'instant courant."""


@dataclass(frozen=True)
class ClotureIntervalle:
    """Intervalle [ouverture, clôture) clôturé et sa qualification."""

    symbole: str
    periode_s: int
    ouverture_ms: int
    cloture_ms: int
    bougie: Bougie | None
    attendu: bool
    complet: bool
    motif_incomplet: str | None
    couverture_etablie: bool


@dataclass
class _EnFormation:
    ouverture_ms: int
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741 (notation OHLC de la spécification)
    c: Decimal
    nb_ticks: int


class ConstructeurBougies:
    """Bougies Bid d'un symbole et d'une période ; un intervalle se clôt quand l'horloge atteint sa fin."""

    def __init__(self, symbole: str, periode_s: int, seances: CalendrierSeances, debut_observation_ms: int):
        if type(periode_s) is not int or periode_s <= 0 or type(debut_observation_ms) is not int:
            raise ValueError('période ou début d\'observation invalide')
        if seances.symbole != symbole:
            raise ValueError('calendrier de séances d\'un autre symbole')
        self.symbole = symbole
        self.periode_s = periode_s
        self._p = periode_s * MS_PAR_SECONDE
        self._seances = seances
        premiere = -(-debut_observation_ms // self._p) * self._p  # premier intervalle entièrement observé
        self._premiere_ouverture = premiere
        self._prochaine_cloture = premiere + self._p
        self._horloge = debut_observation_ms
        self._couverture: list[list] = []  # [début, fin | None], triés, disjoints
        self._en_formation: _EnFormation | None = None
        self._dernier: Instant | None = None
        self._termine = False
        self.ticks_ignores = 0
        self.intervalle_final_abandonne = False

    @property
    def couverture_etablie(self) -> bool:
        return bool(self._couverture) and self._couverture[-1][1] is None

    def _verifier_actif(self):
        if self._termine:
            raise RuntimeError('constructeur déjà terminé')

    def couverture(self, instant_ms: int, etablie: bool) -> list[ClotureIntervalle]:
        """Transition de couverture du flux à un instant, après clôture des intervalles terminés."""
        if type(etablie) is not bool:
            raise ValueError('etablie doit être un booléen')
        closes = self.avancer(instant_ms)
        if etablie and not self.couverture_etablie:
            self._couverture.append([instant_ms, None])
        elif not etablie and self.couverture_etablie:
            if self._couverture[-1][0] == instant_ms:
                self._couverture.pop()
            else:
                self._couverture[-1][1] = instant_ms
        return closes

    def ajouter_tick(self, tick: Tick) -> list[ClotureIntervalle]:
        if type(tick) is not Tick or tick.symbole != self.symbole:
            raise TickHorsOrdre(f'tick d\'un autre symbole que {self.symbole}')
        if self._dernier is not None and not tick.instant > self._dernier:
            raise TickHorsOrdre(f'{self.symbole} : tick non strictement postérieur au précédent')
        closes = self.avancer(tick.instant.ms)
        self._dernier = tick.instant
        t = tick.instant.ms
        if t < self._premiere_ouverture:
            self.ticks_ignores += 1
            return closes
        ouverture = t - t % self._p
        bid = tick.bid
        etat = self._en_formation
        if etat is None:
            self._en_formation = _EnFormation(ouverture, bid, bid, bid, bid, 1)
        else:
            etat.h = max(etat.h, bid)
            etat.l = min(etat.l, bid)
            etat.c = bid
            etat.nb_ticks += 1
        return closes

    def avancer(self, instant_ms: int) -> list[ClotureIntervalle]:
        self._verifier_actif()
        if type(instant_ms) is not int:
            raise ValueError('instant en millisecondes entières attendu')
        if instant_ms < self._horloge:
            raise HorlogeEnRecul(f'{self.symbole} : horloge en recul')
        self._horloge = instant_ms
        closes = []
        while self._prochaine_cloture <= instant_ms:
            cloture = self._evaluer(self._prochaine_cloture - self._p, self._prochaine_cloture)
            if cloture is not None:
                closes.append(cloture)
            self._prochaine_cloture += self._p
        self._elaguer()
        return closes

    def terminer(self, fin_ms: int) -> list[ClotureIntervalle]:
        """Fin des données : clôt les intervalles terminés, abandonne l'intervalle en cours."""
        closes = self.avancer(fin_ms)
        self.intervalle_final_abandonne = self._en_formation is not None
        self._en_formation = None
        self._termine = True
        return closes

    def _couvert(self, debut: int, fin: int) -> bool:
        curseur = debut
        for a, b in self._couverture:
            fin_couverture = float('inf') if b is None else b
            if fin_couverture <= curseur:
                continue
            if a > curseur:
                return False
            curseur = fin_couverture
            if curseur >= fin:
                return True
        return curseur >= fin

    def _evaluer(self, ouverture: int, cloture: int) -> ClotureIntervalle | None:
        portions = self._seances.portion_ouverte(ouverture, cloture)
        etat = self._en_formation
        if etat is not None and etat.ouverture_ms != ouverture:
            raise RuntimeError('bougie en formation hors de l\'intervalle évalué')
        attendu = bool(portions)
        if etat is None and not attendu:
            return None
        couvert = all(self._couvert(a, b) for a, b in portions)
        complet = etat is not None and couvert
        motif = None if complet or not attendu else (MOTIF_COUVERTURE if not couvert else MOTIF_SANS_BID)
        if not attendu:  # marché officiellement fermé : la bougie existe si un Bid existe
            complet, motif = etat is not None, None
        bougie = None
        if etat is not None:
            bougie = Bougie(self.symbole, self.periode_s, ouverture, etat.o, etat.h, etat.l, etat.c, etat.nb_ticks,
                            complet)
            self._en_formation = None
        return ClotureIntervalle(self.symbole, self.periode_s, ouverture, cloture, bougie, attendu, complet, motif,
                                 self.couverture_etablie)

    def _elaguer(self):
        # Une couverture terminée avant l'intervalle en cours ne sert plus à aucune évaluation.
        debut_utile = self._prochaine_cloture - self._p
        while self._couverture and self._couverture[0][1] is not None and self._couverture[0][1] <= debut_utile:
            self._couverture.pop(0)

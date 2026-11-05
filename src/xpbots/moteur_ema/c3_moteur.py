"""Couche 3 de `moteur-ema` (enveloppe) : méthode S01 `EMA_V3` derrière le port `Strategie`.

Contrat : `mcl/moteur-ema/contrats/couche-3.md`. Sources : S01.1 à S01.6, C03 points 6, 7 et 11, C06 (B_SL), C08
(étape 4 : limites de la méthode avant tout autre contrôle), C09 (motifs, état du détecteur), A07.
Une machine d'états par symbole ; l'état est persisté par le port `Stockage` après chaque changement.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from xpbots.donnees_temps.c1a_sessions import SessionsLondres
from xpbots.donnees_temps.c1c_indicateurs import CLE_TR, cle_ema, cle_ema_decalee, cle_rsi
from xpbots.moteur_ema.c0_parametres import ParametresEMA
from xpbots.moteur_ema.c1d_stop import stop_technique
from xpbots.moteur_ema.c2_machine_etats import (IssueInattendue, MachineEtatsEMA, NatureTransition, ObservationEMA,
                                                Transition)
from xpbots.noyau.decisions import CleIntention, IssueSignal, MotifRefus, Refuse, ResultatTechnique, Signal
from xpbots.noyau.json_canonique import charger_strict, serialiser
from xpbots.noyau.marche import BougieEnrichie, EvenementDonnees, NatureEvenementDonnees, StatutBougie
from xpbots.noyau.ports import Stockage

PREFIXE_STOCKAGE = 'moteur_ema'

_MOTIFS_STATUT = {StatutBougie.WARMUP: MotifRefus.WARMUP, StatutBougie.DATA_GAP: MotifRefus.DATA_GAP}
_MOTIFS_TRANSITION = {NatureTransition.POSITION: MotifRefus.SYMBOL_BUSY,
                      NatureTransition.ATTENTE: MotifRefus.UNKNOWN_ORDER_STATE}


class MoteurEMA:
    """Signal EMA_V3 ou motif technique à chaque clôture M15 ; issues, sorties et trous appliqués à l'état."""

    def __init__(self, parametres: ParametresEMA, sessions: SessionsLondres, ticks: Mapping[str, Decimal],
                 stockage: Stockage):
        if type(parametres) is not ParametresEMA or type(sessions) is not SessionsLondres:
            raise ValueError('ParametresEMA et SessionsLondres attendus')
        if not isinstance(ticks, Mapping) or not ticks:
            raise ValueError('au moins un symbole avec son tick_size attendu')
        for symbole, tick in ticks.items():
            if type(symbole) is not str or not symbole or type(tick) is not Decimal or not tick.is_finite() \
                    or not tick > 0:
                raise ValueError(f'tick_size décimal strictement positif attendu pour {symbole!r}')
        self.strategie_id = parametres.strategie_id
        self._p = parametres
        self._sessions = sessions
        self._ticks = dict(ticks)
        self._stockage = stockage
        rapide, moyenne, lente = parametres.periodes_ema
        self._cles = (cle_ema(rapide), cle_ema(moyenne), cle_ema(lente),
                      cle_ema_decalee(lente, parametres.decalage_pente), cle_rsi(parametres.periode_rsi), CLE_TR)
        self._machines = {symbole: self._charger(symbole) for symbole in self._ticks}

    @property
    def symboles(self) -> tuple[str, ...]:
        return tuple(self._machines)

    def machine(self, symbole: str) -> MachineEtatsEMA:
        try:
            return self._machines[symbole]
        except KeyError as erreur:
            raise ValueError(f'symbole non configuré pour {self.strategie_id} : {symbole!r}') from erreur

    # -- port Strategie ------------------------------------------------------------------------------------------

    def sur_cloture(self, bougie: BougieEnrichie) -> ResultatTechnique:
        if type(bougie) is not BougieEnrichie:
            raise ValueError('BougieEnrichie attendue')
        symbole = bougie.bougie.symbole
        machine = self.machine(symbole)
        obs = self._observation(bougie)
        transition = machine.etape(obs)
        resultat = self._resultat(bougie, obs, machine, transition)
        self._sauver(symbole)
        return resultat

    def appliquer_issue(self, cle: CleIntention, issue: IssueSignal) -> None:
        machine = self.machine(cle.symbole)
        if cle.strategie != self.strategie_id or machine.signal_cloture_ms != cle.cloture_ms \
                or machine.sens is not cle.sens:
            raise IssueInattendue(f'aucun signal en attente pour {cle.texte()}')
        machine.appliquer_issue(issue)
        self._sauver(cle.symbole)

    def notifier_sortie(self, symbole: str, instant_ms: int) -> None:
        self.machine(symbole).notifier_sortie(instant_ms)
        self._sauver(symbole)

    def sur_evenement_donnees(self, evenement: EvenementDonnees) -> None:
        """Un trou inexpliqué efface armement et repli (C03.6) ; les autres événements sont sans effet."""
        if evenement.nature is NatureEvenementDonnees.TROU and evenement.symbole in self._machines:
            self._machines[evenement.symbole].effacer()
            self._sauver(evenement.symbole)

    # -- interne -------------------------------------------------------------------------------------------------

    def _observation(self, be: BougieEnrichie) -> ObservationEMA:
        b = be.bougie
        jour = self._sessions.jour_londres(b.cloture_ms)
        dans_fenetre = self._sessions.dans_fenetre(b.ouverture_ms, b.cloture_ms, self._p.debut_session,
                                                   self._p.fin_entrees_exclue)
        exploitable = (be.statut is StatutBougie.OK and be.a_t is not None
                       and all(cle in be.indicateurs for cle in self._cles))
        if not exploitable:
            return ObservationEMA(b.cloture_ms, jour, dans_fenetre, False)
        e_rapide, e_moyenne, e_lente, e_lente_decalee, rsi, tr = (be.indicateurs[cle] for cle in self._cles)
        return ObservationEMA(b.cloture_ms, jour, dans_fenetre, True, float(b.o), float(b.h), float(b.l), float(b.c),
                              tr, e_rapide, e_moyenne, e_lente, e_lente_decalee, rsi, be.a_t)

    def _resultat(self, be: BougieEnrichie, obs: ObservationEMA, machine: MachineEtatsEMA,
                  transition: Transition) -> ResultatTechnique:
        nature = transition.nature
        if nature in _MOTIFS_TRANSITION:
            return self._motif(_MOTIFS_TRANSITION[nature], machine, transition)
        if be.statut in _MOTIFS_STATUT:
            return self._motif(_MOTIFS_STATUT[be.statut], machine, transition)
        if nature is NatureTransition.HORS_FENETRE:
            return self._motif(MotifRefus.OUTSIDE_SESSION, machine, transition)
        if nature is NatureTransition.DONNEES:  # indicateurs ou A_t indisponibles malgré le statut OK
            return self._motif(MotifRefus.WARMUP, machine, transition)
        if nature is not NatureTransition.REPRISE:
            return self._motif(MotifRefus.NO_SETUP, machine, transition)
        r = transition.reprise
        stop = stop_technique(r.sens, obs.c, r.extreme, obs.a_t, self._ticks[be.bougie.symbole], self._p)
        niveaux = {'b_sl': stop.b_sl, 'tampon': stop.tampon, 'distance_stop': stop.distance,
                   'extreme_repli': r.extreme, 'plus_bas_repli': r.plus_bas, 'plus_haut_repli': r.plus_haut,
                   'age_repli': r.age, 'debut_repli_ms': r.debut_ms}
        if stop.trop_large:  # S01.4 : repli consommé, cooldown
            machine.appliquer_issue(Refuse(MotifRefus.STOP_TOO_WIDE, obs.cloture_ms))
            return self._motif(MotifRefus.STOP_TOO_WIDE, machine, transition, niveaux)
        if machine.entrees_remplies(obs.jour) >= self._p.entrees_max_jour:  # S01.4, C08 étape 4
            machine.appliquer_issue(Refuse(MotifRefus.DAILY_ENTRY_CAP, obs.cloture_ms))
            return self._motif(MotifRefus.DAILY_ENTRY_CAP, machine, transition, niveaux)
        etat = self._etat(machine, transition, niveaux)
        signal = Signal(self.strategie_id, be.bougie.symbole, obs.cloture_ms, r.sens, be.bougie.c, obs.a_t,
                        stop.b_sl, self._p.multiple_objectif, etat)
        return ResultatTechnique(signal, None, etat)

    def _motif(self, motif, machine, transition, niveaux=None) -> ResultatTechnique:
        return ResultatTechnique(None, motif, self._etat(machine, transition, niveaux))

    @staticmethod
    def _etat(machine: MachineEtatsEMA, transition: Transition, niveaux=None) -> dict:
        etat = machine.etat_detecteur()
        etat.update(transition=transition.nature, tendance=transition.tendance)
        etat.update(niveaux or {})
        return etat

    def _cle_stockage(self, symbole: str) -> str:
        return f'{PREFIXE_STOCKAGE}/{self.strategie_id}/{symbole}'

    def _charger(self, symbole: str) -> MachineEtatsEMA:
        octets = self._stockage.lire(self._cle_stockage(symbole))
        if octets is None:
            return MachineEtatsEMA(self._p)
        return MachineEtatsEMA.importer(self._p, charger_strict(octets))

    def _sauver(self, symbole: str) -> None:
        self._stockage.ecrire(self._cle_stockage(symbole),
                              serialiser(self._machines[symbole].exporter()).encode('utf-8'))

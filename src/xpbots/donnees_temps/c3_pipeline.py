"""Couche 3 de `donnees-temps` (enveloppe) : bougies enrichies et événements de données d'un symbole.

Contrat : `mcl/donnees-temps/contrats/couche-3.md`. Sources : C03 points 1 à 7 ; R4, R5 et R6′ du registre.
"""
from __future__ import annotations

from typing import Callable, Sequence

from xpbots.donnees_temps.c0_parametres_seances import CalendrierSeances
from xpbots.donnees_temps.c1a_sessions import SessionsLondres
from xpbots.donnees_temps.c1b_bougies import ClotureIntervalle, ConstructeurBougies, TickHorsOrdre
from xpbots.donnees_temps.c2_etat_indicateurs import EtatIndicateursSymbole, SpecIndicateurs
from xpbots.noyau.marche import BougieEnrichie, EvenementDonnees, NatureEvenementDonnees, StatutBougie, Tick
from xpbots.noyau.temps import MS_PAR_SECONDE

Recuperation = Callable[[str, int, int], Sequence[Tick] | None]
Sortie = BougieEnrichie | EvenementDonnees

MOTIF_INDISPONIBLE = 'RECUPERATION_INDISPONIBLE'
MOTIF_INCOMPLET = 'HISTORIQUE_INCOMPLET'
MOTIF_INVALIDE = 'HISTORIQUE_INVALIDE'


class PipelineMarche:
    """Ticks, couverture et horloge d'un symbole → bougies enrichies et événements de données, dans l'ordre."""

    def __init__(self, symbole: str, periode_s: int, seances: CalendrierSeances, sessions: SessionsLondres,
                 spec: SpecIndicateurs, debut_observation_ms: int, recuperation: Recuperation | None = None,
                 etat: EtatIndicateursSymbole | None = None):
        self.symbole = symbole
        self._periode_s = periode_s
        self._seances = seances
        self._sessions = sessions
        self._spec = spec
        self._recuperation = recuperation
        self._constructeur = ConstructeurBougies(symbole, periode_s, seances, debut_observation_ms)
        if etat is not None and etat.spec != spec:
            raise ValueError('état restauré d\'une autre spécification d\'indicateurs')
        self._etat = etat if etat is not None else EtatIndicateursSymbole(spec)
        self._en_trou = False
        self._debut_trou: int | None = None
        self._sauvegarde: dict | None = None
        self._prechargement_signale = self._etat.empreinte_prechargement is not None
        self._en_attente: list[Sortie] = []
        if etat is not None and etat.derniere_cloture_ms is not None:
            self._verifier_reprise(debut_observation_ms)

    @property
    def etat(self) -> EtatIndicateursSymbole:
        return self._etat

    @property
    def en_trou(self) -> bool:
        return self._en_trou

    def sur_tick(self, tick: Tick) -> list[Sortie]:
        return self._traiter(self._constructeur.ajouter_tick(tick))

    def sur_couverture(self, instant_ms: int, etablie: bool) -> list[Sortie]:
        return self._traiter(self._constructeur.couverture(instant_ms, etablie))

    def sur_horloge(self, instant_ms: int) -> list[Sortie]:
        return self._traiter(self._constructeur.avancer(instant_ms))

    def terminer(self, fin_ms: int) -> list[Sortie]:
        return self._traiter(self._constructeur.terminer(fin_ms))

    # -- interne -----------------------------------------------------------------------------------------------

    def _verifier_reprise(self, debut_observation_ms: int):
        p = self._periode_s * MS_PAR_SECONDE
        premiere_ouverture = -(-debut_observation_ms // p) * p
        derniere = self._etat.derniere_cloture_ms
        if derniere < premiere_ouverture and self._seances.portion_ouverte(derniere, premiere_ouverture):
            self._entrer_en_trou(derniere)
            self._en_attente.append(self._evenement(NatureEvenementDonnees.TROU, derniere, derniere,
                                                    premiere_ouverture, {'motif': 'REDEMARRAGE'}))

    def _traiter(self, clotures: list[ClotureIntervalle]) -> list[Sortie]:
        sorties, self._en_attente = self._en_attente, []
        for cloture in clotures:
            sorties += self._cloture(cloture)
        return sorties

    def _evenement(self, nature, instant_ms, debut_ms=None, fin_ms=None, details=None) -> EvenementDonnees:
        return EvenementDonnees(self.symbole, nature, instant_ms, debut_ms, fin_ms, details or {})

    def _enrichie(self, cloture: ClotureIntervalle, statut: StatutBougie, indicateurs=None) -> BougieEnrichie:
        jour = self._sessions.jour_londres(cloture.cloture_ms)
        if indicateurs is None:
            return BougieEnrichie(cloture.bougie, statut, {}, None, jour)
        return BougieEnrichie(cloture.bougie, statut, indicateurs.valeurs, indicateurs.a_t, jour)

    def _appliquer(self, cloture: ClotureIntervalle) -> list[Sortie]:
        indicateurs = self._etat.appliquer(cloture.bougie)
        sorties = self._signaler_prechargement(cloture.cloture_ms)
        statut = StatutBougie.OK if self._etat.pret else StatutBougie.WARMUP
        return sorties + [self._enrichie(cloture, statut, indicateurs)]

    def _signaler_prechargement(self, instant_ms: int) -> list[Sortie]:
        empreinte = self._etat.empreinte_prechargement
        if empreinte is None or self._prechargement_signale:
            return []
        self._prechargement_signale = True
        return [self._evenement(NatureEvenementDonnees.PRECHARGEMENT, instant_ms, empreinte.premiere_ouverture_ms,
                                empreinte.derniere_cloture_ms, {'nombre': empreinte.nombre,
                                                                'sha256': empreinte.sha256})]

    def _entrer_en_trou(self, debut_ms: int):
        self._en_trou = True
        self._debut_trou = debut_ms
        self._sauvegarde = self._etat.exporter()

    def _cloture(self, cloture: ClotureIntervalle) -> list[Sortie]:
        if not cloture.complet:
            sorties: list[Sortie] = [self._evenement(NatureEvenementDonnees.TROU, cloture.cloture_ms,
                                                     cloture.ouverture_ms, cloture.cloture_ms,
                                                     {'motif': cloture.motif_incomplet})]
            if not self._en_trou:
                self._entrer_en_trou(cloture.ouverture_ms)
            if cloture.bougie is not None:
                sorties.append(self._enrichie(cloture, StatutBougie.DATA_GAP))
            if cloture.couverture_etablie:
                sorties += self._recuperer(cloture.cloture_ms, None)[0]
            return sorties
        if not self._en_trou:
            return self._appliquer(cloture)
        if not cloture.couverture_etablie:
            return [self._enrichie(cloture, StatutBougie.DATA_GAP)]
        evenements, appliquee = self._recuperer(cloture.cloture_ms, cloture)
        reconstruite, indicateurs = appliquee
        statut = StatutBougie.OK if self._etat.pret else StatutBougie.WARMUP
        return evenements + [self._enrichie(reconstruite, statut, indicateurs)]

    def _recuperer(self, fin_ms: int, courante: ClotureIntervalle | None):
        """Sort du trou à `fin_ms` : récupération complète (`RECUPERATION`) ou recalcul sur les bougies valides (R6′).

        L'état d'avant le trou est conservé ; seules les reconstructions complètes de `[début du trou, fin)` sont
        appliquées, dans l'ordre ; la clôture courante complète l'est en direct si sa reconstruction manque ou est
        incomplète. Rend (événements, (clôture appliquée, indicateurs) de la clôture courante ou None).
        """
        debut = self._debut_trou
        historique = self._recuperation(self.symbole, debut, fin_ms) if self._recuperation else None
        clotures = None if historique is None else self._reconstruire(historique, debut, fin_ms)
        complet = clotures is not None and all(c.complet for c in clotures) and (
            courante is None or (bool(clotures) and clotures[-1].ouverture_ms == courante.ouverture_ms))
        motif = (None if complet else MOTIF_INDISPONIBLE if historique is None
                 else MOTIF_INVALIDE if clotures is None else MOTIF_INCOMPLET)
        self._etat = EtatIndicateursSymbole.importer(self._spec, self._sauvegarde)
        anterieures = [c for c in clotures or () if c.complet
                       and (courante is None or c.ouverture_ms < courante.ouverture_ms)]
        for cloture in anterieures:
            self._etat.appliquer(cloture.bougie)
        appliquees, appliquee = len(anterieures), None
        if courante is not None:
            remplacantes = [c for c in clotures or () if c.ouverture_ms == courante.ouverture_ms and c.complet]
            retenue = remplacantes[0] if remplacantes else courante
            appliquees += len(remplacantes)
            appliquee = (retenue, self._etat.appliquer(retenue.bougie))
        self._sortir_du_trou()
        if complet:
            evenements = [self._evenement(NatureEvenementDonnees.RECUPERATION, fin_ms, debut, fin_ms,
                                          {'bougies': appliquees})]
        else:
            evenements = [self._evenement(NatureEvenementDonnees.RECALCUL, fin_ms, debut, fin_ms,
                                          {'motif': motif, 'bougies': appliquees})]
        evenements += self._signaler_prechargement(fin_ms)
        return evenements, appliquee

    def _reconstruire(self, historique, debut: int, fin: int) -> list[ClotureIntervalle] | None:
        constructeur = ConstructeurBougies(self.symbole, self._periode_s, self._seances, debut)
        constructeur.couverture(debut, True)
        clotures = []
        try:
            for tick in historique:
                if type(tick) is not Tick or not debut <= tick.instant.ms < fin:
                    return None
                clotures += constructeur.ajouter_tick(tick)
            clotures += constructeur.terminer(fin)
        except (TickHorsOrdre, ValueError):
            return None
        return clotures

    def _sortir_du_trou(self):
        self._en_trou = False
        self._debut_trou = None
        self._sauvegarde = None

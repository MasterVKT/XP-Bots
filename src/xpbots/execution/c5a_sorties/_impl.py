"""Les demandes de sortie précèdent les nouvelles entrées ; aucun ordre n'est envoyé."""
from dataclasses import dataclass
from collections.abc import Mapping

from xpbots.execution.c0a_types import ErreurExecution, RefusExecution, instant
from xpbots.execution.c0b_controles import ControleFondamental
from xpbots.execution.c0e_echeances import premiere_echeance
from xpbots.execution.c1b_gardes import GardesCompte
from xpbots.execution.c4_cycle import CycleOrdre
from xpbots.noyau.c0c_configuration import ExportTechnique
from xpbots.noyau.c1c_domaine import CauseCloture, CleIntention, DecisionFondamentale, Motif, verifier_motif

_PRIORITES = (CauseCloture.ARRET_GLOBAL, CauseCloture.GARDE_QUOTIDIENNE,
    CauseCloture.PROTECTION, CauseCloture.RISQUE_APRES_REMPLISSAGE, CauseCloture.FLATTEN,
    CauseCloture.ANNONCE, CauseCloture.HEURE_SORTIE, CauseCloture.DUREE_MAXIMALE,
    CauseCloture.FERMETURE_NATIVE, CauseCloture.BLACKOUT)


@dataclass(frozen=True)
class SortieObligatoire:
    cle: CleIntention
    cause: CauseCloture
    priorite: int
    motif: Motif | None = None
    detail: str | None = None

    def __post_init__(self):
        if not isinstance(self.cle, CleIntention) or self.cause not in _PRIORITES:
            raise ErreurExecution('clé et cause obligatoires attendues')
        if type(self.priorite) is not int or self.priorite != _PRIORITES.index(self.cause):
            raise ErreurExecution('priorité incohérente')
        if self.motif is not None:
            verifier_motif(self.motif, self.detail)
        elif self.detail is not None:
            raise ErreurExecution('détail sans motif')


@dataclass(frozen=True)
class PlanSorties:
    demandes: tuple[SortieObligatoire, ...] = ()
    prochaine_echeance_ms: int | None = None
    refus: RefusExecution | None = None

    def __post_init__(self):
        demandes = tuple(self.demandes)
        if any(not isinstance(d, SortieObligatoire) for d in demandes) or len({d.cle for d in demandes}) != len(demandes):
            raise ErreurExecution('demandes uniques attendues')
        if self.prochaine_echeance_ms is not None:
            instant(self.prochaine_echeance_ms)
        if self.refus is not None and not isinstance(self.refus, RefusExecution):
            raise ErreurExecution('refus attendu')
        object.__setattr__(self, 'demandes', demandes)


def evaluer_sorties(cycles, technique, profils, gardes, fondamental, instant_ms):
    instant(instant_ms)
    cycles = tuple(cycles)
    if (not isinstance(technique, ExportTechnique) or not isinstance(profils, Mapping)
            or not isinstance(gardes, GardesCompte) or any(not isinstance(c, CycleOrdre) for c in cycles)
            or len({c.etat.cle for c in cycles}) != len(cycles)):
        raise ErreurExecution('composants réels et cycles uniques attendus')
    if any(c.etat.dernier_ms > instant_ms for c in cycles):
        raise ErreurExecution('cycle futur')
    refus = None
    liste = None
    try:
        if not isinstance(fondamental, ControleFondamental):
            raise ValueError('port fondamental obligatoire')
        liste = fondamental.clotures_obligatoires(instant_ms)
        if not isinstance(liste, tuple) or len(set(liste)) != len(liste) or any(s not in technique.commun.universe_priority for s in liste):
            raise ValueError('liste de clôtures mal formée')
    except Exception:
        refus = RefusExecution(Motif.ENVIRONMENT_NOT_READY, 'controle_fondamental')
    demandes, futures = [], []
    for cycle in cycles:
        e = cycle.etat
        if not e.volume_ouvert:
            continue
        candidats = []
        garde = gardes.refus()
        if garde is not None:
            causes = {Motif.GLOBAL_DRAWDOWN_HALT: CauseCloture.ARRET_GLOBAL,
                      Motif.DAILY_LOSS_LOCK: CauseCloture.GARDE_QUOTIDIENNE}
            if garde.motif in causes:
                candidats.append((causes[garde.motif], garde.motif, garde.detail))
            else:
                refus = garde
        if e.cause_sortie in _PRIORITES:
            candidats.append((e.cause_sortie, e.motif_sortie, e.detail_sortie))
        try:
            if liste is not None:
                decision = fondamental.evaluer(e.cle.symbole, e.cle.sens, instant_ms)
                if not isinstance(decision, DecisionFondamentale):
                    raise ValueError('décision fondamentale attendue')
                if e.cle.symbole in liste and not decision.cloture_obligatoire:
                    raise ValueError('liste et décision contradictoires')
                if decision.cloture_obligatoire:
                    couple = (decision.motif, decision.detail)
                    if couple == (Motif.FUNDAMENTAL_DIRECTION, 'RISK_STATE_FLATTEN'):
                        cause = CauseCloture.FLATTEN
                    elif couple == (Motif.NEWS_WINDOW, 'ANNONCE_HIGH'):
                        cause = CauseCloture.ANNONCE
                    else:
                        raise ValueError('cause de clôture fondamentale incohérente')
                    candidats.append((cause, *couple))
        except Exception:
            refus = RefusExecution(Motif.ENVIRONMENT_NOT_READY, 'controle_fondamental')
        profil = profils.get(e.cle.symbole)
        echeance = premiere_echeance(e.premier_fill_ms, e.cle.strategie, technique,
                                    getattr(profil, 'horaires', None))
        if echeance.instant_ms is None:
            refus = RefusExecution(echeance.motif, echeance.detail)
            candidats.append((CauseCloture.PROTECTION, echeance.motif, echeance.detail))
        elif echeance.instant_ms <= instant_ms:
            candidats.extend((cause, None, None) for cause in echeance.causes)
        else:
            futures.append(echeance.instant_ms)
        if candidats:
            cause, motif, detail = min(candidats, key=lambda v: _PRIORITES.index(v[0]))
            demandes.append(SortieObligatoire(e.cle, cause, _PRIORITES.index(cause), motif, detail))
    demandes.sort(key=lambda d: (d.priorite, d.cle.texte()))
    return PlanSorties(tuple(demandes), min(futures) if futures else None, refus)

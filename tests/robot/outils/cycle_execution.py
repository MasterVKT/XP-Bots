"""Bloc réel 0 à 4 ; seul le calcul courtier et ses réponses sont synthétiques."""
from dataclasses import replace
from decimal import Decimal as D
from types import SimpleNamespace

from robot.doublures.calculs_execution import CalculSynthetique
from robot.outils.execution_partagee import T, commun, signal, profil, cotation
from xpbots.execution.c0a_types import EtatCompte
from xpbots.execution.c0d_prix import construire_niveaux, recalculer_objectif
from xpbots.execution.c1b_gardes import GardesCompte, reconstituer_base_utc
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.execution.c3_dimensionnement import dimensionner, PlanDimensionnement
from xpbots.execution.c4_cycle import CycleOrdre, ReponseCourtier, NatureReponse
from xpbots.noyau.c1b_instrument import Intervalle


def bloc_cycle(*, signal_=None, profil_=None, commun_=None, cotation_=None, autres_frais=D(0)):
    s, p, params = signal_ or signal(), profil_ or profil(), commun_ or commun()
    q = cotation_ or cotation(symbole=s.symbole, instant_fournisseur_ms=s.cloture_ms, instant_reception_ms=s.cloture_ms)
    compte = EtatCompte(s.cloture_ms, D(100), D(100), D(0))
    minuit = s.cloture_ms // 86_400_000 * 86_400_000
    garde = GardesCompte(params)
    preuve = reconstituer_base_utc(compte, (), Intervalle(minuit, s.cloture_ms+1), aucune_position_minuit=True)
    assert garde.observer(compte, preuve) is None
    registre = RegistreReservations(params)
    port = CalculSynthetique(compte, p, autres_frais=autres_frais)
    niveaux = construire_niveaux(s, q, p, params)
    plan = dimensionner(s, niveaux, p, compte, registre, garde, port, params, 'synthetique')
    assert isinstance(plan, PlanDimensionnement), plan
    registre.reserver(plan.reservation, compte, plan.version_reservations)
    cycle = CycleOrdre(params, s, plan, p, 16)
    return SimpleNamespace(cycle=cycle, params=params, signal=s, profil=p, cotation=q, compte=compte,
                           registre=registre, garde=garde, port=port, plan=plan)


def remplissage(bloc, *, reference='fill-1', instant_ms=None, **changements):
    t = bloc.signal.cloture_ms+1 if instant_ms is None else instant_ms
    n = bloc.plan.niveaux
    donnees = dict(transaction='deal-1', ticket='position-1', ordre='ordre-1',
        volume_cumule=bloc.plan.volume, volume_position=bloc.plan.volume, prix_moyen=n.entree,
        execution_ms=t, frais_entree=D(0), sl=n.stop, tp=n.objectif, reliquat=D(0), reliquat_annule=True)
    donnees.update(changements)
    return ReponseCourtier(NatureReponse.REMPLISSAGE, bloc.plan.reservation.cle, reference, t, donnees)


def cloture(bloc, *, reference='close-1', instant_ms=None, **changements):
    t = bloc.signal.cloture_ms+2 if instant_ms is None else instant_ms
    donnees = dict(ticket='position-1', volume_restant=D(0), prix=bloc.plan.niveaux.objectif,
                   execution_ms=t, frais_sortie=D(0), cause='TAKE_PROFIT')
    donnees.update(changements)
    return ReponseCourtier(NatureReponse.CLOTURE, bloc.plan.reservation.cle, reference, t, donnees)

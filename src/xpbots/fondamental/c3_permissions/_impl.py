"""Permissions obligatoires et garde d'annonces, sans fournisseur de remplacement."""
from dataclasses import dataclass, field

from xpbots.execution.c0b_controles import ControleFondamental
from xpbots.fondamental.c0_types import (DirectionFondamentale, ErreurFondamental, EtatRisque, instant)
from xpbots.fondamental.c1b_annonces import EtatCalendrier, GardeAnnonces
from xpbots.fondamental.c2_etat_permissions import EtatPermissions, RegistrePermissions
from xpbots.noyau.c1c_domaine import DecisionFondamentale, Motif, Sens


@dataclass(frozen=True)
class EtatFondamental:
    permissions: EtatPermissions = field(default_factory=EtatPermissions)
    calendrier: EtatCalendrier = field(default_factory=EtatCalendrier)
    dernier_ms: int = 0

    def __post_init__(self):
        instant(self.dernier_ms)
        if not isinstance(self.permissions, EtatPermissions) or not isinstance(self.calendrier, EtatCalendrier):
            raise ErreurFondamental('sous-états réels requis')
        if (self.permissions.dernier_ms > self.dernier_ms
                or any(v.reception_ms > self.dernier_ms for v in self.calendrier.versions)):
            raise ErreurFondamental('état contenant une réception future')


class PermissionsFondamentales(ControleFondamental):
    def __init__(self, commun, convertir_serveur, etat=None):
        e = EtatFondamental() if etat is None else etat
        if not isinstance(e, EtatFondamental):
            raise ErreurFondamental('état fondamental réel requis')
        self._permissions = RegistrePermissions(commun, e.permissions)
        self._annonces = GardeAnnonces(commun, convertir_serveur, e.calendrier)
        self._commun = commun
        self._dernier = e.dernier_ms

    @property
    def etat(self):
        return EtatFondamental(self._permissions.etat, self._annonces.etat, self._dernier)

    def _temps(self, t):
        instant(t)
        if t < self._dernier:
            raise ErreurFondamental('recul du temps fondamental')

    def recevoir_permission(self, symbole, octets, reception_ms):
        self._temps(reception_ms)
        resultat = self._permissions.recevoir(symbole, octets, reception_ms)
        self._dernier = reception_ms
        return resultat

    def recevoir_calendrier(self, octets, reception_ms, table):
        self._temps(reception_ms)
        resultat = self._annonces.recevoir(octets, reception_ms, table)
        self._dernier = reception_ms
        return resultat

    def interrompre(self, symbole, instant_ms):
        self._temps(instant_ms)
        resultat = self._permissions.interrompre(symbole, instant_ms)
        self._dernier = instant_ms
        return resultat

    def avancer(self, instant_ms):
        self._temps(instant_ms)
        resultat = self._permissions.avancer(instant_ms)
        self._dernier = instant_ms
        return resultat

    def prochaine_echeance_ms(self, instant_ms):
        instant(instant_ms)
        dates = (self._permissions.prochaine_echeance_ms(instant_ms),
                 self._annonces.prochaine_echeance_ms(instant_ms))
        return min((t for t in dates if t is not None), default=None)

    def evaluer(self, symbole, sens, instant_ms):
        if not isinstance(sens, Sens):
            raise ErreurFondamental('sens canonique requis')
        consultation = self._permissions.consulter(symbole, instant_ms)
        m = consultation.permission.message if consultation.permission is not None else None
        if consultation.detail is None and m.risk_state is EtatRisque.FLATTEN:
            return DecisionFondamentale(False, Motif.FUNDAMENTAL_DIRECTION, 'RISK_STATE_FLATTEN', True)
        annonces = self._annonces.evaluer(symbole, instant_ms)
        if annonces.cloture_obligatoire:
            return annonces
        if consultation.detail is not None:
            return DecisionFondamentale(False, Motif.FUNDAMENTAL_INVALID, consultation.detail)
        if m.risk_state is EtatRisque.NO_NEW:
            return DecisionFondamentale(False, Motif.FUNDAMENTAL_DIRECTION, 'RISK_STATE_NO_NEW')
        if ((m.direction is DirectionFondamentale.LONG_ONLY and sens is Sens.VENTE)
                or (m.direction is DirectionFondamentale.SHORT_ONLY and sens is Sens.ACHAT)):
            return DecisionFondamentale(False, Motif.FUNDAMENTAL_DIRECTION, m.direction.value)
        return annonces

    def clotures_obligatoires(self, instant_ms):
        instant(instant_ms)
        return tuple(s for s in self._commun.universe_priority
            if self.evaluer(s, Sens.ACHAT, instant_ms).cloture_obligatoire)

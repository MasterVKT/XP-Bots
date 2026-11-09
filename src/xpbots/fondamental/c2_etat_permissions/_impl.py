"""État C05 sans horloge, stockage ni fournisseur implicite."""
from dataclasses import dataclass

from xpbots.fondamental.c0_types import (ErreurFondamental, MessagePermission,
    devises_pour, entier, instant, millisecondes)
from xpbots.fondamental.c1a_message import ErreurPermission, decoder_message, valider_message
from xpbots.noyau.c0c_configuration import ParametresCommuns


@dataclass(frozen=True)
class PermissionRecue:
    message: MessagePermission
    reception_ms: int

    def __post_init__(self):
        if not isinstance(self.message, MessagePermission):
            raise ErreurFondamental('message réel requis')
        instant(self.reception_ms)

    @property
    def symbole(self): return self.message.symbole

    @property
    def instant_ms(self): return self.reception_ms


@dataclass(frozen=True)
class InterruptionPermission:
    symbole: str
    instant_ms: int

    def __post_init__(self):
        devises_pour(self.symbole)
        instant(self.instant_ms)


@dataclass(frozen=True)
class SuiviHeartbeat:
    symbole: str
    sequence: int
    prochain_ms: int
    expiration_signalee: bool = False

    def __post_init__(self):
        devises_pour(self.symbole)
        entier(self.sequence, 1)
        instant(self.prochain_ms)
        if type(self.expiration_signalee) is not bool:
            raise ErreurFondamental('indicateur expiration booléen requis')


@dataclass(frozen=True)
class EtatPermissions:
    historique: tuple = ()
    curseurs: tuple = ()
    dernier_ms: int = 0

    def __post_init__(self):
        instant(self.dernier_ms)
        for nom, types in (('historique', (PermissionRecue, InterruptionPermission)),
                           ('curseurs', (SuiviHeartbeat,))):
            valeur = getattr(self, nom)
            if not isinstance(valeur, (tuple, list)) or any(not isinstance(v, types) for v in valeur):
                raise ErreurFondamental('état de permissions typé requis')
            object.__setattr__(self, nom, tuple(valeur))


@dataclass(frozen=True)
class ConsultationPermission:
    permission: PermissionRecue | None
    detail: str | None


@dataclass(frozen=True)
class ReceptionPermission:
    acceptee: bool
    ignoree: bool
    raison: str | None = None
    permission: PermissionRecue | None = None


@dataclass(frozen=True)
class EvenementSuivi:
    nature: str
    symbole: str
    sequence: int
    instant_ms: int
    echeance_ms: int
    nombre: int = 1

    def __post_init__(self):
        if self.nature not in ('HEARTBEAT_MANQUE', 'PERMISSION_EXPIREE'):
            raise ErreurFondamental('suivi inconnu')
        devises_pour(self.symbole)
        entier(self.sequence, 1)
        entier(self.nombre, 1)
        instant(self.instant_ms)
        instant(self.echeance_ms)
        if self.echeance_ms > self.instant_ms:
            raise ErreurFondamental('échéance future non détectable')


class RegistrePermissions:
    def __init__(self, commun, etat=None):
        if not isinstance(commun, ParametresCommuns):
            raise ErreurFondamental('paramètres communs réels requis')
        self._commun = commun
        self._periode = millisecondes(commun.fundamental_expected_heartbeat_seconds)
        if self._periode <= 0:
            raise ErreurFondamental('cadence positive requise')
        e = EtatPermissions() if etat is None else etat
        if not isinstance(e, EtatPermissions):
            raise ErreurFondamental('état réel requis')
        self._hist = list(e.historique)
        self._par_symbole = {s: [] for s in commun.universe_priority}
        self._dernieres = {}
        dernier = 0
        for v in self._hist:
            if v.symbole not in self._par_symbole or not dernier <= v.instant_ms <= e.dernier_ms:
                raise ErreurFondamental('historique non causal')
            if isinstance(v, PermissionRecue):
                valider_message(v.message, v.reception_ms, v.reception_ms, commun)
                precedent = self._dernieres.get(v.symbole)
                if precedent and v.message.sequence <= precedent.message.sequence:
                    raise ErreurFondamental('séquence de reprise non croissante')
                self._dernieres[v.symbole] = v
            elif self._par_symbole[v.symbole] and isinstance(self._par_symbole[v.symbole][-1], InterruptionPermission):
                raise ErreurFondamental('interruption répétée dans la reprise')
            self._par_symbole[v.symbole].append(v)
            dernier = v.instant_ms
        self._curseurs = {c.symbole: c for c in e.curseurs}
        if len(self._curseurs) != len(e.curseurs) or set(self._curseurs) != set(self._dernieres):
            raise ErreurFondamental('curseurs absents ou répétés')
        for s, c in self._curseurs.items():
            m = self._dernieres[s].message
            debut = m.issued_at_ms + self._periode
            if (c.sequence != m.sequence or c.prochain_ms < debut
                    or (c.prochain_ms - debut) % self._periode
                    or (c.prochain_ms > debut and (c.prochain_ms - self._periode > e.dernier_ms
                        or c.prochain_ms - self._periode >= m.valid_until_ms))
                    or (c.expiration_signalee and m.valid_until_ms > e.dernier_ms)):
                raise ErreurFondamental('curseur de reprise incohérent')
        self._dernier = e.dernier_ms

    @property
    def etat(self):
        return EtatPermissions(tuple(self._hist), tuple(self._curseurs[s] for s in
            self._commun.universe_priority if s in self._curseurs), self._dernier)

    def _temps(self, t):
        instant(t)
        if t < self._dernier:
            raise ErreurFondamental('recul du temps logique')

    def _symbole(self, s):
        devises_pour(s)
        if s not in self._par_symbole:
            raise ErreurFondamental('symbole hors univers chargé')

    def recevoir(self, symbole, octets, reception_ms):
        self._symbole(symbole)
        self._temps(reception_ms)
        precedente = self._dernieres.get(symbole)
        if precedente:
            try:
                relu = decoder_message(octets, symbole, precedente.reception_ms,
                    precedente.reception_ms, self._commun)
                if relu == precedente.message:
                    return ReceptionPermission(False, True, permission=precedente)
            except ErreurPermission:
                pass
        try:
            m = decoder_message(octets, symbole, reception_ms, reception_ms, self._commun)
        except ErreurPermission as erreur:
            return ReceptionPermission(False, False, erreur.detail)
        if precedente and m.sequence <= precedente.message.sequence:
            return ReceptionPermission(False, False, 'SEQUENCE_NON_CROISSANTE')
        recue = PermissionRecue(m, reception_ms)
        self._hist.append(recue)
        self._par_symbole[symbole].append(recue)
        self._dernieres[symbole] = recue
        self._curseurs[symbole] = SuiviHeartbeat(symbole, m.sequence, m.issued_at_ms + self._periode)
        self._dernier = reception_ms
        return ReceptionPermission(True, False, permission=recue)

    def interrompre(self, symbole, instant_ms):
        self._symbole(symbole)
        self._temps(instant_ms)
        if self._hist and instant_ms < self._hist[-1].instant_ms:
            raise ErreurFondamental('réception antérieure au dernier événement')
        h = self._par_symbole[symbole]
        if h and isinstance(h[-1], InterruptionPermission):
            return False
        v = InterruptionPermission(symbole, instant_ms)
        self._hist.append(v)
        h.append(v)
        self._dernier = instant_ms
        return True

    def consulter(self, symbole, instant_ms):
        self._symbole(symbole)
        instant(instant_ms)
        dernier = None
        permission = None
        for v in reversed(self._par_symbole[symbole]):
            if v.instant_ms <= instant_ms:
                if dernier is None: dernier = v
                if isinstance(v, PermissionRecue):
                    permission = v
                    break
        if isinstance(dernier, InterruptionPermission):
            return ConsultationPermission(permission, 'INTERRUPTION')
        if permission is None:
            return ConsultationPermission(None, 'ABSENTE')
        return ConsultationPermission(permission,
            'PERIMEE' if instant_ms >= permission.message.valid_until_ms else None)

    def avancer(self, instant_ms):
        self._temps(instant_ms)
        if self._hist and instant_ms < self._hist[-1].instant_ms:
            raise ErreurFondamental('suivi antérieur à une réception')
        evenements = []
        for s in self._commun.universe_priority:
            if s not in self._dernieres: continue
            m = self._dernieres[s].message
            c = self._curseurs[s]
            fin = min(instant_ms, m.valid_until_ms - 1)
            if c.prochain_ms <= fin:
                nombre = (fin - c.prochain_ms) // self._periode + 1
                evenements.append(EvenementSuivi('HEARTBEAT_MANQUE', s, m.sequence,
                    instant_ms, c.prochain_ms, nombre))
                self._curseurs[s] = SuiviHeartbeat(s, m.sequence, c.prochain_ms + nombre * self._periode,
                    c.expiration_signalee)
            if not c.expiration_signalee and m.valid_until_ms <= instant_ms:
                evenements.append(EvenementSuivi('PERMISSION_EXPIREE', s, m.sequence,
                    instant_ms, m.valid_until_ms))
                courant = self._curseurs[s]
                self._curseurs[s] = SuiviHeartbeat(s, m.sequence, courant.prochain_ms, True)
        self._dernier = instant_ms
        return tuple(evenements)

    def prochaine_echeance_ms(self, instant_ms):
        instant(instant_ms)
        echeances = []
        for s, recue in self._dernieres.items():
            fin = recue.message.valid_until_ms
            c = self._curseurs[s]
            if c.prochain_ms < fin: echeances.append(c.prochain_ms)
            if not c.expiration_signalee: echeances.append(fin)
        return max(instant_ms, min(echeances)) if echeances else None

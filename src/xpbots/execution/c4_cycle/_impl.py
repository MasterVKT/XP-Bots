"""Machine C08 pure, construite par transitions ; aucune exécution externe ici."""
from dataclasses import dataclass, field, replace
from decimal import Context, Decimal, ROUND_FLOOR, localcontext
from enum import StrEnum
import hashlib
from types import MappingProxyType
from typing import Mapping

from xpbots.execution.c0a_types import (
    EtatIntention, ErreurExecution, RefusExecution, decimal_fini, instant, texte,
)
from xpbots.execution.c0d_prix import NiveauxExecutables, recalculer_objectif
from xpbots.execution.c1a_calcul import appeler_calcul
from xpbots.execution.c3_dimensionnement import PlanDimensionnement, dimensionner
from xpbots.noyau.c0b_nombres import decimal_depuis
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1a_marche import Cotation
from xpbots.noyau.c1b_instrument import ProfilInstrument
from xpbots.noyau.c1c_domaine import (
    CauseCloture, CleIntention, Issue, Motif, NatureIssue, Sens, SignalTechnique, verifier_motif,
)
from xpbots.noyau.c2_journal import TypeEnregistrement

D = Decimal


def _enum(classe, valeur):
    try:
        return classe(valeur)
    except (TypeError, ValueError) as erreur:
        raise ErreurExecution(f'{classe.__name__} invalide') from erreur


def _booleen(v):
    if type(v) is not bool:
        raise ErreurExecution('booléen attendu')
    return v


def _entier(v, minimum=0):
    if type(v) is not int or v < minimum:
        raise ErreurExecution('entier hors borne')
    return v


def _texte(v):
    texte(v)
    return v


def _instant(v):
    instant(v)
    return v


def _decimal(v, strict=False):
    decimal_fini(v, 'valeur', D(0), strict)
    return v


def _optionnel(verifier):
    return lambda v: None if v is None else verifier(v)


def _ms(secondes):
    """Facteur d'unité ms/s ; aucune durée métier n'est définie ici."""
    return int(decimal_depuis(secondes) * 1000)


class NatureCommande(StrEnum):
    ENTREE = 'ENTREE'
    TP = 'TP'
    CLOTURE = 'CLOTURE'
    ANNULATION = 'ANNULATION'
    RAPPROCHEMENT = 'RAPPROCHEMENT'
    ALERTE = 'ALERTE'
    MINUTERIE = 'MINUTERIE'


class NatureReponse(StrEnum):
    ACCUSE = 'ACCUSE'
    REMPLISSAGE = 'REMPLISSAGE'
    PROTECTIONS = 'PROTECTIONS'
    CLOTURE = 'CLOTURE'
    ANNULATION = 'ANNULATION'


class StatutAccuse(StrEnum):
    ACCEPTE = 'ACCEPTE'
    REFUSE = 'REFUSE'
    INCONNU = 'INCONNU'


_POSITIF = lambda v: _decimal(v, True)
_SENS = lambda v: _enum(Sens, v)
_CAUSE = lambda v: _enum(CauseCloture, v)
_MOTIF = lambda v: _enum(Motif, v)
_COMMANDES = {
    NatureCommande.ENTREE: dict(symbole_courtier=_texte, sens=_SENS, volume=_POSITIF, prix=_POSITIF,
        sl=_POSITIF, tp=_POSITIF, deviation_points=_entier, mode_remplissage=_texte,
        magic=lambda v: _entier(v, 1), commentaire=_texte, risque_initial=_decimal,
        budget_gele=_POSITIF, expire_ms=_instant),
    NatureCommande.TP: dict(ticket=_texte, sl=_POSITIF, tp=_POSITIF),
    NatureCommande.CLOTURE: dict(ticket=_texte, volume=_POSITIF, cause=_CAUSE,
        motif=_optionnel(_MOTIF), detail=_optionnel(_texte), priorite=_entier),
    NatureCommande.ANNULATION: dict(ordre=_texte),
    NatureCommande.RAPPROCHEMENT: dict(symbole_courtier=_texte, magic=lambda v: _entier(v, 1),
        commentaire=_texte, depuis_ms=_instant),
    NatureCommande.ALERTE: dict(code=_texte, gravite=_texte),
    NatureCommande.MINUTERIE: dict(echeance_ms=_instant),
}
_REPONSES = {
    NatureReponse.ACCUSE: dict(commande=_texte, statut=lambda v: _enum(StatutAccuse, v),
        code_natif=_texte, definitif=_booleen, ordre=_optionnel(_texte)),
    NatureReponse.REMPLISSAGE: dict(transaction=_texte, ticket=_texte, ordre=_optionnel(_texte),
        volume_cumule=_POSITIF, volume_position=_decimal, prix_moyen=_POSITIF, execution_ms=_instant,
        frais_entree=_optionnel(_decimal), sl=_optionnel(_POSITIF), tp=_optionnel(_POSITIF),
        reliquat=_decimal, reliquat_annule=_booleen),
    NatureReponse.PROTECTIONS: dict(ticket=_texte, sl=_optionnel(_POSITIF), tp=_optionnel(_POSITIF)),
    NatureReponse.CLOTURE: dict(ticket=_texte, volume_restant=_decimal, prix=_POSITIF,
        execution_ms=_instant, frais_sortie=_decimal, cause=_CAUSE),
    NatureReponse.ANNULATION: dict(ordre=_texte, confirmee=_booleen),
}


def _trame(objet, enumeration, schemas):
    if not isinstance(objet.cle, CleIntention):
        raise ErreurExecution('clé réelle attendue')
    texte(objet.reference)
    instant(objet.instant_ms)
    nature = _enum(enumeration, objet.nature)
    if not isinstance(objet.donnees, Mapping) or set(objet.donnees) != set(schemas[nature]):
        raise ErreurExecution('champs exacts de la trame attendus')
    valeurs = {nom: verifier(objet.donnees[nom]) for nom, verifier in schemas[nature].items()}
    object.__setattr__(objet, 'nature', nature)
    object.__setattr__(objet, 'donnees', MappingProxyType(valeurs))


@dataclass(frozen=True)
class IdentiteCourtier:
    magic: int
    commentaire: str

    def __post_init__(self):
        _entier(self.magic, 1)
        if self.magic >= 1 << 63:
            raise ErreurExecution('magic hors des 63 bits positifs')
        texte(self.commentaire)


def identifier_courtier(cle, longueur_empreinte):
    if not isinstance(cle, CleIntention):
        raise ErreurExecution('clé réelle attendue')
    octets = f'{cle.deploiement}|{cle.strategie}'.encode('utf-8')
    magic = int.from_bytes(hashlib.sha256(octets).digest()[:8], 'big') & ((1 << 63) - 1)
    return IdentiteCourtier(magic or 1, 'XPB3:' + cle.empreinte(longueur_empreinte))


@dataclass(frozen=True)
class CommandeExecution:
    nature: NatureCommande
    cle: CleIntention
    reference: str
    instant_ms: int
    donnees: Mapping

    def __post_init__(self):
        _trame(self, NatureCommande, _COMMANDES)
        d = self.donnees
        if self.nature is NatureCommande.ENTREE:
            if d['sens'] is not self.cle.sens or d['expire_ms'] <= self.instant_ms:
                raise ErreurExecution('sens ou validité incohérents')
            if d['mode_remplissage'] not in ('FOK', 'IOC', 'RETURN') or d['magic'] >= 1 << 63:
                raise ErreurExecution('mode ou magic invalide')
            if not d['sens'].signe * (d['prix']-d['sl']) > 0 or not d['sens'].signe * (d['tp']-d['prix']) > 0:
                raise ErreurExecution('protections incohérentes avec le sens')
        if self.nature is NatureCommande.CLOTURE:
            if d['motif'] is None:
                if d['detail'] is not None:
                    raise ErreurExecution('détail sans motif')
            else:
                verifier_motif(d['motif'], d['detail'])
        if self.nature is NatureCommande.MINUTERIE and d['echeance_ms'] < self.instant_ms:
            raise ErreurExecution('minuterie antérieure')


@dataclass(frozen=True)
class ReponseCourtier:
    nature: NatureReponse
    cle: CleIntention
    reference: str
    instant_ms: int
    donnees: Mapping

    def __post_init__(self):
        _trame(self, NatureReponse, _REPONSES)
        d = self.donnees
        if 'execution_ms' in d and d['execution_ms'] > self.instant_ms:
            raise ErreurExecution('exécution future')
        if self.nature is NatureReponse.REMPLISSAGE and d['volume_position'] > d['volume_cumule']:
            raise ErreurExecution('position supérieure au volume exécuté')


@dataclass(frozen=True)
class PreuvePersistance:
    revision: int
    references: tuple[str, ...]

    def __post_init__(self):
        _entier(self.revision, 1)
        if not isinstance(self.references, (tuple, list)):
            raise ErreurExecution('références attendues')
        refs = tuple(self.references)
        for ref in refs:
            texte(ref)
        if len(set(refs)) != len(refs):
            raise ErreurExecution('références dupliquées')
        object.__setattr__(self, 'references', refs)


@dataclass(frozen=True)
class PreuveAbsence:
    cle: CleIntention
    instant_ms: int
    debut_ms: int
    fin_ms: int
    historique_complet: bool
    envoi_termine: bool
    absence_definitive: bool
    aucun_ordre: bool
    aucune_position: bool
    aucune_execution: bool

    def __post_init__(self):
        if not isinstance(self.cle, CleIntention):
            raise ErreurExecution('clé attendue')
        for nom in ('instant_ms', 'debut_ms', 'fin_ms'):
            instant(getattr(self, nom))
        if not self.debut_ms <= self.fin_ms <= self.instant_ms:
            raise ErreurExecution('couverture de preuve incohérente')
        for nom in ('historique_complet', 'envoi_termine', 'absence_definitive',
                    'aucun_ordre', 'aucune_position', 'aucune_execution'):
            _booleen(getattr(self, nom))


@dataclass(frozen=True)
class EtatCycle:
    cle: CleIntention
    statut: EtatIntention = EtatIntention.RESERVEE
    dernier_ms: int = 0
    envoi_ms: int | None = None
    accuse_recu: bool = False
    numero_commande: int = 0
    reponses_recues: tuple[ReponseCourtier, ...] = ()
    premier_fill_ms: int | None = None
    volume_cumule: Decimal = D(0)
    volume_ouvert: Decimal = D(0)
    prix_moyen: Decimal | None = None
    frais_entree: Decimal | None = None
    ticket_position: str | None = None
    ticket_ordre: str | None = None
    sl_natif: Decimal | None = None
    tp_natif: Decimal | None = None
    niveaux_reels: NiveauxExecutables | None = None
    quota_compte: bool = False
    reliquat_annule: bool = True
    annulation_demandee: bool = False
    tentatives_protection: int = 0
    prochaine_protection_ms: int | None = None
    protections_validees: bool = False
    risque_verifie: bool = False
    inconnu_ms: int | None = None
    prochain_rapprochement_ms: int | None = None
    alerte_inconnue: bool = False
    volume_cible: Decimal | None = None
    cause_sortie: CauseCloture | None = None
    motif_sortie: Motif | None = None
    detail_sortie: str | None = None
    priorite_sortie: int | None = None
    sortie_en_cours: bool = False
    prochain_reessai_ms: int | None = None
    instant_cloture_ms: int | None = None
    cause_cloture_native: CauseCloture | None = None

    def __post_init__(self):
        if not isinstance(self.cle, CleIntention):
            raise ErreurExecution('clé de cycle attendue')
        object.__setattr__(self, 'statut', _enum(EtatIntention, self.statut))
        instant(self.dernier_ms)
        for nom in ('envoi_ms', 'premier_fill_ms', 'prochaine_protection_ms', 'inconnu_ms',
                    'prochain_rapprochement_ms', 'prochain_reessai_ms', 'instant_cloture_ms'):
            v = getattr(self, nom)
            if v is not None:
                instant(v)
        for nom in ('envoi_ms', 'premier_fill_ms', 'inconnu_ms', 'instant_cloture_ms'):
            if getattr(self, nom) is not None and getattr(self, nom) > self.dernier_ms:
                raise ErreurExecution('fait du cycle postérieur à sa connaissance')
        for nom in ('accuse_recu', 'quota_compte', 'reliquat_annule', 'annulation_demandee', 'protections_validees',
                    'risque_verifie', 'alerte_inconnue', 'sortie_en_cours'):
            _booleen(getattr(self, nom))
        for nom in ('numero_commande', 'tentatives_protection'):
            _entier(getattr(self, nom))
        if self.priorite_sortie is not None:
            _entier(self.priorite_sortie)
        for nom in ('volume_cumule', 'volume_ouvert'):
            _decimal(getattr(self, nom))
        if self.frais_entree is not None:
            _decimal(self.frais_entree)
        if self.volume_cible is not None:
            _decimal(self.volume_cible)
        for nom in ('prix_moyen', 'sl_natif', 'tp_natif'):
            if getattr(self, nom) is not None:
                _POSITIF(getattr(self, nom))
        for nom in ('ticket_position', 'ticket_ordre'):
            if getattr(self, nom) is not None:
                texte(getattr(self, nom))
        if self.volume_ouvert > self.volume_cumule or self.quota_compte != (self.volume_cumule > 0):
            raise ErreurExecution('volumes ou quota incohérents')
        if self.volume_cumule > 0 and (self.premier_fill_ms is None or self.prix_moyen is None or self.ticket_position is None):
            raise ErreurExecution('remplissage incomplet')
        if self.niveaux_reels is not None and not isinstance(self.niveaux_reels, NiveauxExecutables):
            raise ErreurExecution('niveaux réels attendus')
        for nom in ('cause_sortie', 'cause_cloture_native'):
            if getattr(self, nom) is not None:
                object.__setattr__(self, nom, _enum(CauseCloture, getattr(self, nom)))
        if self.motif_sortie is not None:
            m, d = verifier_motif(self.motif_sortie, self.detail_sortie)
            object.__setattr__(self, 'motif_sortie', m)
            object.__setattr__(self, 'detail_sortie', d)
        elif self.detail_sortie is not None:
            raise ErreurExecution('détail sans motif de sortie')
        if not isinstance(self.reponses_recues, (tuple, list)):
            raise ErreurExecution('réponses reçues attendues')
        rs = tuple(self.reponses_recues)
        if any(not isinstance(r, ReponseCourtier) or r.cle != self.cle or r.instant_ms > self.dernier_ms for r in rs):
            raise ErreurExecution('réponse restaurée incohérente')
        if len({r.reference for r in rs}) != len(rs):
            raise ErreurExecution('réponses dupliquées')
        object.__setattr__(self, 'reponses_recues', rs)
        if self.statut is EtatIntention.ENVOYEE and self.envoi_ms is None:
            raise ErreurExecution('envoi sans instant')
        if self.statut is EtatIntention.INCONNUE and self.inconnu_ms is None:
            raise ErreurExecution('inconnu sans instant')
        if self.statut in (EtatIntention.OUVERTE, EtatIntention.REMPLIE_PARTIELLE) and self.volume_ouvert <= 0:
            raise ErreurExecution('position ouverte sans volume')
        if self.statut is EtatIntention.CLOTURE_DEMANDEE and self.cause_sortie is None:
            raise ErreurExecution('clôture sans cause')
        if self.statut is EtatIntention.CLOTUREE and (self.volume_ouvert or self.instant_cloture_ms is None or self.cause_cloture_native is None or not self.reliquat_annule):
            raise ErreurExecution('clôture non confirmée')
        if self.statut in (EtatIntention.REFUSEE, EtatIntention.EXPIREE) and self.volume_cumule:
            raise ErreurExecution('exécution positive assimilée à un refus')


@dataclass(frozen=True)
class TraceCycle:
    type: TypeEnregistrement
    donnees: Mapping

    def __post_init__(self):
        object.__setattr__(self, 'type', _enum(TypeEnregistrement, self.type))
        if not isinstance(self.donnees, Mapping) or any(not isinstance(k, str) for k in self.donnees):
            raise ErreurExecution('trace attendue')
        for v in self.donnees.values():
            if v is not None and not isinstance(v, (str, bool, int, Decimal)):
                raise ErreurExecution('valeur de trace scalaire attendue')
            if isinstance(v, Decimal):
                decimal_fini(v, 'trace')
        object.__setattr__(self, 'donnees', MappingProxyType(dict(self.donnees)))


@dataclass(frozen=True)
class EffetsCycle:
    etat: EtatCycle
    commandes: tuple[CommandeExecution, ...] = ()
    issues: tuple[Issue, ...] = ()
    traces: tuple[TraceCycle, ...] = ()

    def __post_init__(self):
        if not isinstance(self.etat, EtatCycle):
            raise ErreurExecution('état attendu')
        for nom, type_ in (('commandes', CommandeExecution), ('issues', Issue), ('traces', TraceCycle)):
            valeurs = tuple(getattr(self, nom))
            if any(not isinstance(v, type_) for v in valeurs):
                raise ErreurExecution('effets mal typés')
            if nom != 'traces' and any(v.cle != self.etat.cle for v in valeurs):
                raise ErreurExecution('effet d’une autre intention')
            object.__setattr__(self, nom, valeurs)


class CycleOrdre:
    def __init__(self, commun, signal, plan, profil, longueur_empreinte, etat=None):
        if not isinstance(commun, ParametresCommuns) or not isinstance(signal, SignalTechnique) or not isinstance(plan, PlanDimensionnement) or not isinstance(profil, ProfilInstrument):
            raise ErreurExecution('composants réels du cycle attendus')
        cle = plan.reservation.cle
        if (cle.strategie, cle.symbole, cle.cloture_ms, cle.sens) != (signal.strategie, signal.symbole, signal.cloture_ms, signal.sens):
            raise ErreurExecution('signal et plan incohérents')
        if profil.symbole != cle.symbole or profil.tick_size != plan.niveaux.tick_size:
            raise ErreurExecution('profil et plan incohérents')
        self._commun, self._signal, self._plan, self._profil = commun, signal, plan, profil
        self._identite = identifier_courtier(cle, longueur_empreinte)
        if etat is not None and not isinstance(etat, EtatCycle):
            raise ErreurExecution('état réel attendu')
        self._etat = etat or EtatCycle(cle, dernier_ms=plan.instantane_ms)
        if self._etat.cle != cle or self._etat.dernier_ms < signal.cloture_ms:
            raise ErreurExecution('état d’une autre intention')
        if self._etat.niveaux_reels is not None and self._etat.niveaux_reels.stop != plan.niveaux.stop:
            raise ErreurExecution('SL restauré différent du SL initial')
        if self._etat.tentatives_protection > commun.protective_update_max_attempts:
            raise ErreurExecution('trop de tentatives restaurées')

    @property
    def etat(self):
        return self._etat

    @property
    def prochaine_echeance_ms(self):
        e = self._etat
        dates = [v for v in (e.prochaine_protection_ms, e.prochain_rapprochement_ms, e.prochain_reessai_ms) if v is not None]
        if e.statut is EtatIntention.ENVOYEE:
            dates.append(e.envoi_ms + _ms(self._commun.request_ack_timeout_seconds))
        if e.premier_fill_ms is not None and not e.protections_validees and e.volume_ouvert and e.cause_sortie is None:
            dates.append(e.premier_fill_ms + _ms(self._commun.protective_update_deadline_seconds))
        return min(dates) if dates else None

    def _mettre(self, **champs):
        self._etat = replace(self._etat, **champs)

    def _toucher(self, instant_ms):
        instant(instant_ms)
        if instant_ms < self._etat.dernier_ms:
            raise ErreurExecution('événement antérieur')
        self._mettre(dernier_ms=instant_ms)

    def _verifier_cotation(self, cotation, instant_ms):
        if cotation is not None and (not isinstance(cotation, Cotation) or cotation.symbole != self._signal.symbole
                or cotation.instant_fournisseur_ms > instant_ms or cotation.instant_reception_ms > instant_ms):
            raise ErreurExecution('cotation connue du symbole attendue')

    def _commande(self, nature, **donnees):
        numero = self._etat.numero_commande + 1
        reference = f'{self._etat.cle.empreinte(64)}:{nature.value}:{numero}'
        c = CommandeExecution(nature, self._etat.cle, reference, self._etat.dernier_ms, donnees)
        self._mettre(numero_commande=numero)
        return c

    def _effets(self, commandes=(), issues=(), traces=()):
        return EffetsCycle(self._etat, tuple(commandes), tuple(issues), tuple(traces))

    def _trace_commande(self, commande):
        return TraceCycle(TypeEnregistrement.ORDRE, {
            'cle': commande.cle.texte(), 'reference': commande.reference,
            'commande': commande.nature.value, **commande.donnees})

    def preparer_envoi(self, instant_ms):
        instant(instant_ms)
        if self._etat.statut is not EtatIntention.RESERVEE or self._etat.envoi_ms is not None:
            return self._effets()
        fin = self._signal.cloture_ms + _ms(self._commun.entry_signal_ttl_seconds)
        if instant_ms >= fin:
            raise ErreurExecution('TTL fermé avant préparation de l’envoi')
        self._toucher(instant_ms)
        mode = next((m for m in ('FOK', 'IOC', 'RETURN') if m in self._profil.modes_remplissage), None)
        if mode is None:
            raise ErreurExecution('mode de remplissage inconnu')
        n = self._plan.niveaux
        with localcontext(Context(prec=48)):
            deviation = int((self._plan.mesure_risque.glissement / self._profil.point).to_integral_value(rounding=ROUND_FLOOR))
        self._mettre(statut=EtatIntention.ENVOYEE, envoi_ms=instant_ms, reliquat_annule=False)
        entree = self._commande(NatureCommande.ENTREE,
            symbole_courtier=self._profil.symbole_courtier, sens=self._signal.sens,
            volume=self._plan.volume, prix=n.entree, sl=n.stop, tp=n.objectif,
            deviation_points=deviation, mode_remplissage=mode, magic=self._identite.magic,
            commentaire=self._identite.commentaire, risque_initial=self._plan.risque,
            budget_gele=self._plan.budget_gele, expire_ms=fin)
        minuterie = self._commande(NatureCommande.MINUTERIE,
            echeance_ms=instant_ms + _ms(self._commun.request_ack_timeout_seconds))
        return self._effets((entree, minuterie), traces=(self._trace_commande(entree),))

    def sur_reponse(self, reponse, cotation=None):
        if not isinstance(reponse, ReponseCourtier) or reponse.cle != self._etat.cle:
            raise ErreurExecution('réponse de cette intention attendue')
        ancienne = next((r for r in self._etat.reponses_recues if r.reference == reponse.reference), None)
        if ancienne is not None:
            if ancienne != reponse:
                raise ErreurExecution('réponse répétée contradictoire')
            return self._effets()
        self._verifier_cotation(cotation, reponse.instant_ms)
        avant = self._etat
        try:
            self._toucher(reponse.instant_ms)
            d = reponse.donnees
            if reponse.nature is NatureReponse.ACCUSE:
                effets = self._accuser(reponse)
            elif reponse.nature is NatureReponse.REMPLISSAGE:
                effets = self._remplir(reponse, cotation)
            elif reponse.nature is NatureReponse.CLOTURE:
                effets = self._clore(reponse)
            elif reponse.nature is NatureReponse.ANNULATION:
                effets = self._annuler(reponse)
            else:
                effets = self._proteger(reponse, cotation)
            self._mettre(reponses_recues=self._etat.reponses_recues + (reponse,))
            trace = TraceCycle(TypeEnregistrement.REPONSE, {
                'cle': reponse.cle.texte(), 'reference': reponse.reference,
                'reponse': reponse.nature.value, **d})
            return self._effets(effets.commandes, effets.issues, effets.traces + (trace,))
        except Exception:
            self._etat = avant
            raise

    def _accuser(self, reponse):
        d = reponse.donnees
        try:
            empreinte, nom_nature, numero = d['commande'].split(':')
        except ValueError as erreur:
            raise ErreurExecution('référence de commande mal formée') from erreur
        if (empreinte != self._etat.cle.empreinte(64)
                or not numero.isascii() or not numero.isdigit()
                or not 1 <= int(numero) <= self._etat.numero_commande):
            raise ErreurExecution('accusé d’une commande inconnue')
        nature = _enum(NatureCommande, nom_nature)
        if nature in (NatureCommande.MINUTERIE, NatureCommande.ALERTE):
            raise ErreurExecution('accusé sans action de courtier')
        if nature is not NatureCommande.ENTREE:
            if self._etat.statut in (EtatIntention.CLOTUREE, EtatIntention.REFUSEE, EtatIntention.EXPIREE):
                return self._effets()
            if nature is NatureCommande.TP and d['statut'] is StatutAccuse.REFUSE and self._etat.tentatives_protection >= self._commun.protective_update_max_attempts:
                return self.demander_cloture(reponse.instant_ms, CauseCloture.PROTECTION,
                    motif=Motif.PROTECTION_ERROR, detail='TP_NON_RETABLI', peut_envoyer=True)
            if nature is NatureCommande.CLOTURE and d['statut'] is not StatutAccuse.ACCEPTE:
                self._mettre(sortie_en_cours=d['statut'] is StatutAccuse.INCONNU,
                    prochain_reessai_ms=reponse.instant_ms+_ms(self._commun.exit_retry_interval_seconds))
                return self._effets(self._rapprochement())
            return self._effets()
        if int(numero) != 1 or self._etat.envoi_ms is None:
            raise ErreurExecution('accusé d’une autre entrée')
        if d['statut'] is StatutAccuse.INCONNU:
            if self._etat.statut in (EtatIntention.CLOTUREE, EtatIntention.REFUSEE, EtatIntention.EXPIREE):
                return self._effets()
            if not self._etat.volume_ouvert:
                self._mettre(statut=EtatIntention.INCONNUE,
                             inconnu_ms=self._etat.inconnu_ms if self._etat.inconnu_ms is not None else reponse.instant_ms)
            return self._effets(self._rapprochement())
        if d['statut'] is StatutAccuse.REFUSE:
            if self._etat.volume_cumule > 0:
                alerte = TraceCycle(TypeEnregistrement.ALERTE, {
                    'cle': self._etat.cle.texte(), 'alerte': 'REFUS_APRES_EXECUTION', 'code_natif': d['code_natif']})
                return self._effets(traces=(alerte,))
            if self._etat.statut in (EtatIntention.REFUSEE, EtatIntention.EXPIREE):
                return self._effets()
            self._mettre(statut=EtatIntention.REFUSEE, accuse_recu=True,
                prochain_rapprochement_ms=None, prochaine_protection_ms=None, prochain_reessai_ms=None)
            issue = Issue(self._etat.cle, NatureIssue.REFUSEE, reponse.instant_ms,
                          Motif.ENVIRONMENT_NOT_READY, 'REFUS_COURTIER')
            return self._effets(issues=(issue,))
        if self._etat.statut not in (EtatIntention.REFUSEE, EtatIntention.EXPIREE, EtatIntention.CLOTUREE):
            self._mettre(accuse_recu=True, ticket_ordre=d['ordre'] if d['ordre'] is not None else self._etat.ticket_ordre)
        return self._effets()

    def _remplir(self, reponse, cotation):
        d = reponse.donnees
        connue = next((r for r in self._etat.reponses_recues
            if r.nature is NatureReponse.REMPLISSAGE and r.donnees['transaction'] == d['transaction']), None)
        if connue is not None:
            for nom in ('ticket', 'volume_cumule', 'prix_moyen', 'execution_ms'):
                if connue.donnees[nom] != d[nom]:
                    raise ErreurExecution('transaction répétée contradictoire')
            if d['frais_entree'] is not None and d['volume_cumule'] == self._etat.volume_cumule:
                self._mettre(frais_entree=d['frais_entree'], risque_verifie=False)
            return self._effets()
        if d['volume_cumule'] <= self._etat.volume_cumule:
            if self._etat.premier_fill_ms is not None and d['execution_ms'] < self._etat.premier_fill_ms:
                self._mettre(premier_fill_ms=d['execution_ms'])
            return self._effets()
        n = recalculer_objectif(self._plan.niveaux, d['prix_moyen'], cotation)
        premier = self._etat.premier_fill_ms is None
        premier_ms = d['execution_ms'] if premier else min(self._etat.premier_fill_ms, d['execution_ms'])
        annule = d['reliquat_annule'] and d['reliquat'] == 0
        statut = EtatIntention.REMPLIE_PARTIELLE if d['volume_cumule'] < self._plan.volume or not annule else EtatIntention.OUVERTE
        if d['volume_position'] == 0:
            statut = EtatIntention.INCONNUE
        inconnue = self._etat.inconnu_ms
        if statut is EtatIntention.INCONNUE and inconnue is None:
            inconnue = reponse.instant_ms
        self._mettre(statut=statut, premier_fill_ms=premier_ms,
            volume_cumule=d['volume_cumule'], volume_ouvert=d['volume_position'], prix_moyen=d['prix_moyen'],
            frais_entree=d['frais_entree'], ticket_position=d['ticket'],
            ticket_ordre=d['ordre'] if d['ordre'] is not None else self._etat.ticket_ordre,
            sl_natif=d['sl'], tp_natif=d['tp'], niveaux_reels=n if isinstance(n, NiveauxExecutables) else None,
            quota_compte=True, reliquat_annule=annule, protections_validees=False,
            risque_verifie=False, inconnu_ms=inconnue,
            annulation_demandee=False if annule else self._etat.annulation_demandee)
        issues = (Issue(self._etat.cle, NatureIssue.REMPLIE, d['execution_ms']),) if premier else ()
        trace = TraceCycle(TypeEnregistrement.EXECUTION, {'cle': self._etat.cle.texte(), **d})
        commandes = []
        if not annule:
            if self._etat.ticket_ordre is not None and not self._etat.annulation_demandee:
                commandes.append(self._commande(NatureCommande.ANNULATION, ordre=self._etat.ticket_ordre))
                self._mettre(annulation_demandee=True)
            commandes.extend(self._rapprochement())
        elif self._etat.volume_ouvert == 0:
            if self._etat.instant_cloture_ms is not None:
                fin = self._finaliser_cloture()
                return self._effets(issues=issues+fin.issues, traces=(trace,)+fin.traces)
            commandes.extend(self._rapprochement())
        else:
            self._mettre(inconnu_ms=None, prochain_rapprochement_ms=None)
        if self._etat.volume_ouvert > 0:
            protection = self._evaluer_protection(cotation)
            commandes.extend(protection.commandes)
        return self._effets(commandes, issues, (trace,))

    def _evaluer_protection(self, cotation=None):
        e = self._etat
        if not e.volume_ouvert:
            return self._effets()
        n = recalculer_objectif(self._plan.niveaux, e.prix_moyen, cotation)
        if not isinstance(n, NiveauxExecutables) or e.sl_natif != self._plan.niveaux.stop:
            self._mettre(protections_validees=False, prochaine_protection_ms=None)
            return self.demander_cloture(e.dernier_ms, CauseCloture.PROTECTION,
                motif=Motif.PROTECTION_ERROR, detail='SL_ABSENT', peut_envoyer=True)
        self._mettre(niveaux_reels=n)
        if n.objectif_depasse:
            return self.demander_cloture(e.dernier_ms, CauseCloture.PROTECTION,
                motif=Motif.PROTECTION_ERROR, detail='TP_DEPASSE', peut_envoyer=True)
        if e.tp_natif == n.objectif:
            self._mettre(protections_validees=True, prochaine_protection_ms=None)
            return self._effets()
        self._mettre(protections_validees=False)
        if e.cause_sortie is not None:
            return self._effets()
        fin = e.premier_fill_ms + _ms(self._commun.protective_update_deadline_seconds)
        if e.dernier_ms >= fin:
            return self.demander_cloture(e.dernier_ms, CauseCloture.PROTECTION,
                motif=Motif.PROTECTION_ERROR, detail='TP_NON_RETABLI', peut_envoyer=True)
        if e.prochaine_protection_ms is None:
            delais = self._commun.protective_update_retry_delays_seconds
            cible = fin if e.tentatives_protection >= self._commun.protective_update_max_attempts else min(fin, e.dernier_ms + _ms(delais[e.tentatives_protection]))
            self._mettre(prochaine_protection_ms=cible)
            return self._effets((self._commande(NatureCommande.MINUTERIE, echeance_ms=cible),))
        return self._effets()

    def _proteger(self, reponse, cotation):
        if reponse.donnees['ticket'] != self._etat.ticket_position:
            raise ErreurExecution('protection d’une position étrangère')
        if not self._etat.volume_ouvert:
            return self._effets()
        self._mettre(sl_natif=reponse.donnees['sl'], tp_natif=reponse.donnees['tp'])
        e = self._evaluer_protection(cotation)
        return self._effets(e.commandes, traces=(TraceCycle(TypeEnregistrement.PROTECTION,
            {'cle': self._etat.cle.texte(), **reponse.donnees}),))

    def _rapprochement(self):
        e = self._etat
        debut = e.inconnu_ms if e.inconnu_ms is not None else e.dernier_ms
        limite = debut + _ms(self._commun.reconcile_fast_window_seconds)
        intervalle = self._commun.reconcile_fast_poll_seconds if e.dernier_ms < limite else self._commun.reconcile_slow_poll_seconds
        self._mettre(inconnu_ms=debut, prochain_rapprochement_ms=e.dernier_ms+_ms(intervalle))
        requete = self._commande(NatureCommande.RAPPROCHEMENT,
            symbole_courtier=self._profil.symbole_courtier, magic=self._identite.magic,
            commentaire=self._identite.commentaire, depuis_ms=e.envoi_ms if e.envoi_ms is not None else self._plan.instantane_ms)
        minuterie = self._commande(NatureCommande.MINUTERIE, echeance_ms=self._etat.prochain_rapprochement_ms)
        return [requete, minuterie]

    def _annuler(self, reponse):
        d = reponse.donnees
        if d['ordre'] != self._etat.ticket_ordre:
            raise ErreurExecution('annulation d’un ordre étranger')
        if self._etat.statut in (EtatIntention.CLOTUREE, EtatIntention.REFUSEE, EtatIntention.EXPIREE):
            return self._effets()
        if not d['confirmee']:
            return self._effets(self._rapprochement())
        self._mettre(reliquat_annule=True, annulation_demandee=False,
                     prochain_rapprochement_ms=None)
        if self._etat.volume_ouvert == 0 and self._etat.instant_cloture_ms is not None:
            return self._finaliser_cloture()
        if self._etat.volume_ouvert > 0:
            self._mettre(inconnu_ms=None)
        return self._effets()

    def _clore(self, reponse):
        d = reponse.donnees
        if self._etat.statut is EtatIntention.CLOTUREE and d['volume_restant'] == 0:
            return self._effets()
        if self._etat.premier_fill_ms is None:
            self._mettre(statut=EtatIntention.INCONNUE, inconnu_ms=self._etat.dernier_ms,
                         instant_cloture_ms=d['execution_ms'], cause_cloture_native=d['cause'])
            return self._effets(self._rapprochement(), traces=(TraceCycle(TypeEnregistrement.CLOTURE_POSITION,
                {'cle': self._etat.cle.texte(), **d}),))
        if d['ticket'] != self._etat.ticket_position:
            raise ErreurExecution('clôture sans position possédée confirmée')
        if d['volume_restant'] != 0:
            if d['volume_restant'] > self._etat.volume_ouvert:
                raise ErreurExecution('réduction augmentant la position')
            if d['volume_restant'] == self._etat.volume_ouvert:
                return self._effets()
            atteinte = self._etat.volume_cible is not None and self._etat.volume_cible > 0 and d['volume_restant'] <= self._etat.volume_cible
            self._mettre(volume_ouvert=d['volume_restant'], risque_verifie=False, sortie_en_cours=False,
                         prochain_reessai_ms=self._etat.dernier_ms+_ms(self._commun.exit_retry_interval_seconds))
            if atteinte:
                statut = EtatIntention.OUVERTE if self._etat.volume_cumule >= self._plan.volume else EtatIntention.REMPLIE_PARTIELLE
                self._mettre(statut=statut, cause_sortie=None, motif_sortie=None, detail_sortie=None,
                    priorite_sortie=None, volume_cible=None, prochain_reessai_ms=None)
            return self._effets(traces=(TraceCycle(TypeEnregistrement.CLOTURE_POSITION,
                {'cle': self._etat.cle.texte(), **d}),))
        self._mettre(statut=EtatIntention.INCONNUE, inconnu_ms=self._etat.dernier_ms, volume_ouvert=D(0),
            instant_cloture_ms=d['execution_ms'], cause_cloture_native=d['cause'],
            prochaine_protection_ms=None, prochain_rapprochement_ms=None, prochain_reessai_ms=None)
        trace = TraceCycle(TypeEnregistrement.CLOTURE_POSITION, {'cle': self._etat.cle.texte(), **d})
        if not self._etat.reliquat_annule:
            return self._effets(self._rapprochement(), traces=(trace,))
        fin = self._finaliser_cloture()
        return self._effets(issues=fin.issues, traces=(trace,))

    def _finaliser_cloture(self):
        if self._etat.statut is EtatIntention.CLOTUREE:
            return self._effets()
        self._mettre(statut=EtatIntention.CLOTUREE, inconnu_ms=None,
                     prochain_rapprochement_ms=None, prochain_reessai_ms=None, prochaine_protection_ms=None)
        issue = Issue(self._etat.cle, NatureIssue.CLOTUREE, self._etat.instant_cloture_ms,
                      cause=self._etat.cause_cloture_native)
        return self._effets(issues=(issue,))

    def sur_minuterie(self, instant_ms, *, cotation=None, negociable=False):
        _booleen(negociable)
        self._verifier_cotation(cotation, instant_ms)
        self._toucher(instant_ms)
        if self._etat.statut in (EtatIntention.CLOTUREE, EtatIntention.REFUSEE, EtatIntention.EXPIREE):
            return self._effets()
        commandes, traces = [], []
        e = self._etat
        if e.volume_ouvert and e.cause_sortie is not None:
            sortie = self._essayer_sortie(negociable)
            commandes.extend(sortie.commandes)
            traces.extend(sortie.traces)
            if e.prochain_rapprochement_ms is not None and instant_ms >= e.prochain_rapprochement_ms:
                commandes.extend(self._rapprochement())
            commandes.extend(self._alerter_inconnu(traces))
            return self._effets(commandes, traces=traces)
        if e.volume_ouvert:
            protection = self._evaluer_protection(cotation)
            commandes.extend(protection.commandes)
            e = self._etat
            if e.cause_sortie is not None:
                return self._effets(commandes)
            if not e.protections_validees and e.prochaine_protection_ms is not None and instant_ms >= e.prochaine_protection_ms:
                if e.tentatives_protection < self._commun.protective_update_max_attempts:
                    if negociable:
                        tp = self._commande(NatureCommande.TP, ticket=e.ticket_position,
                            sl=self._plan.niveaux.stop, tp=e.niveaux_reels.objectif)
                        commandes.append(tp)
                        self._mettre(tentatives_protection=e.tentatives_protection+1, prochaine_protection_ms=None)
                        commandes.extend(self._evaluer_protection(cotation).commandes)
                    else:
                        fin = e.premier_fill_ms + _ms(self._commun.protective_update_deadline_seconds)
                        cible = min(fin, instant_ms+_ms(self._commun.exit_retry_interval_seconds))
                        self._mettre(prochaine_protection_ms=cible)
                        commandes.append(self._commande(NatureCommande.MINUTERIE, echeance_ms=cible))
        if e.statut is EtatIntention.ENVOYEE and instant_ms >= e.envoi_ms + _ms(self._commun.request_ack_timeout_seconds):
            self._mettre(statut=EtatIntention.INCONNUE, inconnu_ms=instant_ms)
            commandes.extend(self._rapprochement())
        elif e.prochain_rapprochement_ms is not None and instant_ms >= e.prochain_rapprochement_ms:
            commandes.extend(self._rapprochement())
        commandes.extend(self._alerter_inconnu(traces))
        return self._effets(commandes, traces=traces)

    def _alerter_inconnu(self, traces):
        e = self._etat
        if e.inconnu_ms is not None and not e.alerte_inconnue and e.dernier_ms > e.inconnu_ms + _ms(self._commun.reconcile_fast_window_seconds):
            alerte = self._commande(NatureCommande.ALERTE, code='ETAT_ORDRE_INCONNU', gravite='CRITIQUE')
            self._mettre(alerte_inconnue=True)
            traces.append(TraceCycle(TypeEnregistrement.ALERTE, {'cle': e.cle.texte(), **alerte.donnees}))
            return [alerte]
        return []

    def demander_cloture(self, instant_ms, cause, *, motif=None, detail=None, priorite=0, volume_cible=D(0), peut_envoyer=False):
        cause = _enum(CauseCloture, cause)
        _entier(priorite); _decimal(volume_cible); _booleen(peut_envoyer)
        if motif is not None:
            motif, detail = verifier_motif(motif, detail)
        elif detail is not None:
            raise ErreurExecution('détail sans motif')
        self._toucher(instant_ms)
        e = self._etat
        if not e.volume_ouvert:
            return self._effets()
        if volume_cible >= e.volume_ouvert:
            raise ErreurExecution('volume cible ne réduisant pas la position')
        champs = dict(statut=EtatIntention.CLOTURE_DEMANDEE,
            volume_cible=min(e.volume_cible, volume_cible) if e.volume_cible is not None else volume_cible,
            prochaine_protection_ms=None)
        if e.priorite_sortie is None or priorite < e.priorite_sortie:
            champs.update(cause_sortie=cause, motif_sortie=motif, detail_sortie=detail, priorite_sortie=priorite)
        self._mettre(**champs)
        return self._essayer_sortie(peut_envoyer)

    def _essayer_sortie(self, peut_envoyer):
        e = self._etat
        if e.sortie_en_cours:
            self._mettre(prochain_reessai_ms=None)
            return self._effets(self._rapprochement() if e.prochain_rapprochement_ms is None else ())
        if e.prochain_reessai_ms is not None and e.dernier_ms < e.prochain_reessai_ms:
            return self._effets()
        commandes = []
        if peut_envoyer:
            commandes.append(self._commande(NatureCommande.CLOTURE, ticket=e.ticket_position,
                volume=e.volume_ouvert-e.volume_cible, cause=e.cause_sortie,
                motif=e.motif_sortie, detail=e.detail_sortie, priorite=e.priorite_sortie))
            self._mettre(sortie_en_cours=True)
        cible = e.dernier_ms + _ms(self._commun.exit_retry_interval_seconds)
        self._mettre(prochain_reessai_ms=cible)
        commandes.append(self._commande(NatureCommande.MINUTERIE, echeance_ms=cible))
        return self._effets(commandes, traces=tuple(self._trace_commande(c) for c in commandes if c.nature is NatureCommande.CLOTURE))

    def controler_risque(self, registre, gardes, port, instant_ms, cotation=None):
        self._verifier_cotation(cotation, instant_ms)
        self._toucher(instant_ms)
        e = self._etat
        if not e.volume_ouvert or e.niveaux_reels is None:
            return self._effets()
        profil = appeler_calcul(port, 'specifications', self._signal.symbole)
        compte = appeler_calcul(port, 'etat_compte')
        refus = next((v for v in (profil, compte) if isinstance(v, RefusExecution)), None)
        if refus is None and (profil.symbole != self._profil.symbole or profil.symbole_courtier != self._profil.symbole_courtier
                or profil.sous_jacent != self._profil.sous_jacent or profil.tick_size != self._profil.tick_size):
            refus = RefusExecution(Motif.ENVIRONMENT_NOT_READY, 'specifications_modifiees')
        if refus is None and (not e.premier_fill_ms <= compte.instant_ms <= instant_ms or e.volume_ouvert > self._plan.volume):
            refus = RefusExecution(Motif.ENVIRONMENT_NOT_READY, 'remplissage')
        if refus is None:
            refus = dimensionner(self._signal, e.niveaux_reels, profil, compte, registre, gardes, port,
                self._commun, e.cle.deploiement, plan_initial=self._plan, volume_rempli=e.volume_ouvert,
                prix_reel=e.prix_moyen, frais_entree_reels=e.frais_entree)
        if isinstance(refus, PlanDimensionnement):
            self._mettre(risque_verifie=True)
            if refus.volume >= e.volume_ouvert:
                return self._effets()
            return self.demander_cloture(instant_ms, CauseCloture.RISQUE_APRES_REMPLISSAGE,
                motif=Motif.MIN_VOLUME_OR_RISK_REJECT, volume_cible=refus.volume, peut_envoyer=True)
        return self.demander_cloture(instant_ms, CauseCloture.RISQUE_APRES_REMPLISSAGE,
            motif=refus.motif, detail=refus.detail, peut_envoyer=True)

    def confirmer_absence(self, preuve):
        if not isinstance(preuve, PreuveAbsence) or preuve.cle != self._etat.cle:
            raise ErreurExecution('preuve native de cette intention attendue')
        self._toucher(preuve.instant_ms)
        if self._etat.statut in (EtatIntention.CLOTUREE, EtatIntention.REFUSEE, EtatIntention.EXPIREE) or self._etat.quota_compte:
            return self._effets()
        debut = self._etat.envoi_ms if self._etat.envoi_ms is not None else self._plan.instantane_ms
        complete = all(getattr(preuve, nom) for nom in ('historique_complet', 'envoi_termine',
            'absence_definitive', 'aucun_ordre', 'aucune_position', 'aucune_execution'))
        if not complete or preuve.debut_ms > debut or preuve.fin_ms < preuve.instant_ms:
            return self._effets(self._rapprochement())
        self._mettre(statut=EtatIntention.REFUSEE, reliquat_annule=True, inconnu_ms=None,
                     prochain_rapprochement_ms=None, prochaine_protection_ms=None, prochain_reessai_ms=None)
        issue = Issue(self._etat.cle, NatureIssue.REFUSEE, preuve.instant_ms,
                      Motif.ENVIRONMENT_NOT_READY, 'ABSENCE_NATIVE_CONFIRMEE')
        return self._effets(issues=(issue,), traces=(TraceCycle(TypeEnregistrement.RAPPROCHEMENT,
            {'cle': self._etat.cle.texte(), 'absence_confirmee': True}),))

    def reprendre(self, instant_ms):
        precedent = self._etat
        self._toucher(instant_ms)
        if self._etat.statut in (EtatIntention.CLOTUREE, EtatIntention.REFUSEE, EtatIntention.EXPIREE):
            return self._effets()
        debut = precedent.inconnu_ms
        if debut is None:
            debut = (min(instant_ms, precedent.envoi_ms + _ms(self._commun.request_ack_timeout_seconds))
                if precedent.premier_fill_ms is None and precedent.envoi_ms is not None else instant_ms)
        if not self._etat.volume_ouvert:
            self._mettre(statut=EtatIntention.INCONNUE, inconnu_ms=debut)
        else:
            self._mettre(inconnu_ms=debut)
        return self._effets(self._rapprochement())

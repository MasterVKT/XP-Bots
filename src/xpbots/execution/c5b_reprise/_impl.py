"""Reconstruction sur faits connus ; aucun accès à un journal ou au terminal."""
from dataclasses import dataclass, field, replace
from decimal import Decimal

from xpbots.execution.c0a_types import (EtatCompte, EtatReservations, EtatGardes, EtatIntention,
    ErreurExecution, PositionCompte, RefusExecution, decimal_fini, instant, texte)
from xpbots.execution.c1b_gardes import GardesCompte
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.execution.c4_cycle import (CycleOrdre, EtatCycle, ReponseCourtier, NatureReponse,
    PreuveAbsence, identifier_courtier, CommandeExecution, TraceCycle, NatureCommande)
from xpbots.noyau.c1c_domaine import Issue, NatureIssue, Motif, SignalTechnique
from xpbots.noyau.c1b_instrument import ProfilInstrument

_TERMINAUX = (EtatIntention.CLOTUREE, EtatIntention.REFUSEE, EtatIntention.EXPIREE)


def _tuple_type(valeurs, classe):
    valeurs = tuple(valeurs)
    if any(not isinstance(v, classe) for v in valeurs):
        raise ErreurExecution('collection mal typée')
    return valeurs


@dataclass(frozen=True)
class CyclePersiste:
    signal: SignalTechnique
    plan: object
    profil: ProfilInstrument
    etat: EtatCycle

    def __post_init__(self):
        if not isinstance(self.signal, SignalTechnique) or not isinstance(self.profil, ProfilInstrument) or not isinstance(self.etat, EtatCycle):
            raise ErreurExecution('instantané de cycle mal typé')
        # CycleOrdre valide le plan réel sans créer une dépendance directe supplémentaire.


@dataclass(frozen=True)
class EtatReprise:
    cycles: tuple[CyclePersiste, ...] = ()
    reservations: EtatReservations = EtatReservations()
    gardes: EtatGardes | None = None

    def __post_init__(self):
        cs = _tuple_type(self.cycles, CyclePersiste)
        if len({c.etat.cle for c in cs}) != len(cs):
            raise ErreurExecution('cycles dupliqués')
        if not isinstance(self.reservations, EtatReservations) or self.gardes is not None and not isinstance(self.gardes, EtatGardes):
            raise ErreurExecution('états persistants réels attendus')
        object.__setattr__(self, 'cycles', cs)


@dataclass(frozen=True)
class PositionNative:
    ticket: str
    symbole_courtier: str
    volume: Decimal
    magic: int
    commentaire: str
    origine_exclusive: bool = False
    sl: Decimal | None = field(kw_only=True)
    tp: Decimal | None = field(kw_only=True)

    def __post_init__(self):
        _native(self, 'volume')
        if type(self.origine_exclusive) is not bool:
            raise ErreurExecution('preuve exclusive booléenne attendue')
        for nom in ('sl', 'tp'):
            if getattr(self, nom) is not None:
                decimal_fini(getattr(self, nom), nom, Decimal(0), True)


@dataclass(frozen=True)
class OrdreNatif:
    ticket: str
    symbole_courtier: str
    volume_restant: Decimal
    magic: int
    commentaire: str
    nature: NatureCommande = NatureCommande.ENTREE

    def __post_init__(self):
        _native(self, 'volume_restant')
        if self.nature not in (NatureCommande.ENTREE, NatureCommande.CLOTURE):
            raise ErreurExecution('ordre natif d’entrée ou de clôture attendu')
        object.__setattr__(self, 'nature', NatureCommande(self.nature))


def _native(objet, volume):
    texte(objet.ticket); texte(objet.symbole_courtier)
    decimal_fini(getattr(objet, volume), volume, Decimal(0), True)
    if type(objet.magic) is not int or objet.magic < 0 or not isinstance(objet.commentaire, str):
        raise ErreurExecution('identité native mal formée')


@dataclass(frozen=True)
class ObservationNative:
    compte: EtatCompte
    depuis_ms: int
    historique_complet: bool
    positions: tuple[PositionNative, ...] = ()
    ordres: tuple[OrdreNatif, ...] = ()
    reponses: tuple[ReponseCourtier, ...] = ()
    absences: tuple[PreuveAbsence, ...] = ()
    exclusivites: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.compte, EtatCompte) or self.compte.positions:
            raise ErreurExecution('compte brut sans attribution attendu')
        instant(self.depuis_ms)
        if self.depuis_ms > self.compte.instant_ms or type(self.historique_complet) is not bool:
            raise ErreurExecution('couverture historique invalide')
        for nom, classe in (('positions', PositionNative), ('ordres', OrdreNatif),
                            ('reponses', ReponseCourtier), ('absences', PreuveAbsence)):
            vs = _tuple_type(getattr(self, nom), classe)
            identifiants = [getattr(v, 'ticket', getattr(v, 'reference', getattr(v, 'cle', None))) for v in vs]
            if len(set(identifiants)) != len(vs):
                raise ErreurExecution('faits natifs dupliqués')
            if any(getattr(v, 'instant_ms', self.compte.instant_ms) > self.compte.instant_ms for v in vs):
                raise ErreurExecution('fait natif futur')
            object.__setattr__(self, nom, vs)
        xs = tuple(self.exclusivites)
        for s in xs: texte(s)
        if len(set(xs)) != len(xs): raise ErreurExecution('exclusivités dupliquées')
        object.__setattr__(self, 'exclusivites', xs)


@dataclass(frozen=True)
class BilanReprise:
    etat: EtatReprise
    compte: EtatCompte | None
    commandes: tuple[CommandeExecution, ...]
    issues: tuple[Issue, ...]
    traces: tuple[TraceCycle, ...]
    prete: bool
    refus: RefusExecution | None = None

    def __post_init__(self):
        if not isinstance(self.etat, EtatReprise) or self.compte is not None and not isinstance(self.compte, EtatCompte):
            raise ErreurExecution('bilan mal typé')
        for nom, classe in (('commandes', CommandeExecution), ('issues', Issue), ('traces', TraceCycle)):
            object.__setattr__(self, nom, _tuple_type(getattr(self, nom), classe))
        if type(self.prete) is not bool or self.refus is not None and not isinstance(self.refus, RefusExecution):
            raise ErreurExecution('verdict mal typé')


def _construire(commun, etat, longueur):
    if not isinstance(etat, EtatReprise): raise ErreurExecution('état de reprise attendu')
    registre = RegistreReservations(commun, etat.reservations)
    gardes = GardesCompte(commun, etat.gardes)
    cycles = {v.etat.cle: CycleOrdre(commun, v.signal, v.plan, v.profil, longueur, v.etat) for v in etat.cycles}
    rs = {r.cle: r for r in etat.reservations.reservations}
    if any(k not in cycles for k in rs): raise ErreurExecution('réservation orpheline')
    for v in etat.cycles:
        e = v.etat
        if e.statut not in _TERMINAUX:
            r = rs.get(e.cle)
            if r is None or replace(r, remplie=False) != replace(v.plan.reservation, remplie=False) or r.remplie != e.quota_compte:
                raise ErreurExecution('risque initial absent ou incohérent')
    return registre, gardes, cycles


def _exporter(etat, registre, gardes, cycles):
    return EtatReprise(tuple(replace(v, etat=cycles[v.etat.cle].etat) for v in etat.cycles), registre.etat, gardes.etat)


def restaurer(commun, etat, longueur_empreinte, instant_ms):
    instant(instant_ms)
    registre, gardes, cycles = _construire(commun, etat, longueur_empreinte)
    commandes, issues, traces = [], [], []
    for v in etat.cycles:
        if v.etat.statut not in _TERMINAUX:
            registre.verrouiller(v.profil.sous_jacent)
            e = cycles[v.etat.cle].reprendre(instant_ms)
            commandes.extend(e.commandes); issues.extend(e.issues); traces.extend(e.traces)
    return BilanReprise(_exporter(etat, registre, gardes, cycles), None,
        tuple(commandes), tuple(issues), tuple(traces), False,
        RefusExecution(Motif.ENVIRONMENT_NOT_READY, 'rapprochement_initial'))


def rapprocher(commun, etat, longueur_empreinte, observation, *, netting=False, reconstitution=None):
    if not isinstance(observation, ObservationNative) or type(netting) is not bool:
        raise ErreurExecution('observation native et mode attendus')
    registre, gardes, cycles = _construire(commun, etat, longueur_empreinte)
    t = observation.compte.instant_ms
    if any(c.etat.dernier_ms > t for c in cycles.values()): raise ErreurExecution('observation antérieure')
    commandes, issues, traces = [], [], []
    refus = None
    prete = observation.historique_complet
    fiches = {v.etat.cle: v for v in etat.cycles}

    def integrer(e):
        commandes.extend(e.commandes); traces.extend(e.traces)
        for i in e.issues:
            registre.sur_issue(i); issues.append(i)

    for r in observation.reponses:
        if r.cle not in cycles:
            refus = RefusExecution(Motif.ENVIRONMENT_NOT_READY, 'transaction_non_attribuable'); prete = False
            continue
        cycle = cycles[r.cle]
        ancienne = next((v for v in cycle.etat.reponses_recues if v.reference == r.reference), None)
        if ancienne is not None:
            if (ancienne.nature, ancienne.donnees) != (r.nature, r.donnees):
                raise ErreurExecution('historique contradictoire')
            continue
        if cycle.etat.statut in _TERMINAUX and r.nature is NatureReponse.REMPLISSAGE:
            refus = RefusExecution(Motif.ENVIRONMENT_NOT_READY, 'execution_apres_absence_definitive'); prete = False
            registre.verrouiller(fiches[r.cle].profil.sous_jacent)
            continue
        integrer(cycle.sur_reponse(replace(r, instant_ms=t)))

    def proprietaire(natif):
        correspondances = []
        for v in etat.cycles:
            identite = identifier_courtier(v.etat.cle, longueur_empreinte)
            if (natif.symbole_courtier, natif.magic, natif.commentaire) == (v.profil.symbole_courtier, identite.magic, identite.commentaire):
                correspondances.append(v.etat.cle)
        return correspondances[0] if len(correspondances) == 1 else None

    for preuve in observation.absences:
        if preuve.cle not in cycles: raise ErreurExecution('absence d’une intention inconnue')
        conflit = any(proprietaire(n) == preuve.cle for n in (*observation.positions, *observation.ordres))
        if conflit:
            refus = RefusExecution(Motif.ENVIRONMENT_NOT_READY, 'absence_contradictoire'); prete = False
            continue
        integrer(cycles[preuve.cle].confirmer_absence(replace(preuve, instant_ms=t)))

    ps, presentes, ordres_connus, externes = [], set(), set(), set()
    for n in observation.positions:
        k = proprietaire(n)
        v = fiches.get(k)
        e = cycles[k].etat if k is not None else None
        exclusif = not netting or (v is not None and v.profil.symbole in observation.exclusivites and n.origine_exclusive)
        possedee = e is not None and exclusif and e.ticket_position == n.ticket and e.volume_ouvert == n.volume and e.quota_compte
        if possedee:
            ps.append(PositionCompte(n.ticket, k.symbole, v.profil.sous_jacent, n.volume, v.plan.risque, k))
            presentes.add(k)
            if (e.sl_natif, e.tp_natif) != (n.sl, n.tp):
                protection = ReponseCourtier(NatureReponse.PROTECTIONS, k,
                    f'position:{n.ticket}:{t}:{n.sl}:{n.tp}', t,
                    dict(ticket=n.ticket, sl=n.sl, tp=n.tp))
                integrer(cycles[k].sur_reponse(protection))
            traces.append(TraceCycle('PROTECTION', {'cle': k.texte(), 'ticket': n.ticket,
                'sl': n.sl, 'tp': n.tp, 'source': 'C04_POSITION_NATIVE'}))
        else:
            profil = next((v.profil for v in etat.cycles if v.profil.symbole_courtier == n.symbole_courtier), None)
            symbole = profil.symbole if profil is not None else n.symbole_courtier
            sous_jacent = profil.sous_jacent if profil is not None else symbole
            ps.append(PositionCompte(n.ticket, symbole, sous_jacent, n.volume, None))
            externes.add(sous_jacent)
            registre.verrouiller(sous_jacent)
            refus = RefusExecution(Motif.ACCOUNT_RISK_CAP, 'POSITIONS_EXTERNES'); prete = False
    for n in observation.ordres:
        k = proprietaire(n)
        e = cycles[k].etat if k is not None else None
        sortie = n.nature is NatureCommande.CLOTURE
        connue = e is not None and (
            sortie and e.quota_compte and e.sortie_en_cours and e.cause_sortie is not None
            or not sortie and e.statut not in _TERMINAUX and e.ticket_ordre in (None, n.ticket)
                and not (e.quota_compte and e.reliquat_annule))
        if not connue:
            refus = RefusExecution(Motif.ENVIRONMENT_NOT_READY, 'ordre_externe'); prete = False
        else:
            ordres_connus.add(k)
            registre.verrouiller(fiches[k].profil.sous_jacent)
            if not sortie:
                v = fiches[k]
                cycles[k] = CycleOrdre(commun, v.signal, v.plan, v.profil, longueur_empreinte,
                                      replace(cycles[k].etat, ticket_ordre=n.ticket))
    for k, cycle in cycles.items():
        e, v = cycle.etat, fiches[k]
        debut = e.envoi_ms if e.envoi_ms is not None else v.plan.instantane_ms
        couverture = observation.historique_complet and observation.depuis_ms <= debut
        positive = k in presentes and e.reliquat_annule and k not in ordres_connus
        terminal = e.statut in _TERMINAUX and k not in presentes and k not in ordres_connus
        if couverture and (positive or terminal) and v.profil.sous_jacent not in externes:
            registre.deverrouiller(v.profil.sous_jacent)
            if positive:
                statut = e.statut
                if statut is EtatIntention.INCONNUE:
                    statut = EtatIntention.OUVERTE if e.volume_cumule >= v.plan.volume else EtatIntention.REMPLIE_PARTIELLE
                propre = replace(e, statut=statut, inconnu_ms=None, prochain_rapprochement_ms=None)
                cycles[k] = CycleOrdre(commun, v.signal, v.plan, v.profil, longueur_empreinte, propre)
        elif e.statut not in _TERMINAUX:
            registre.verrouiller(v.profil.sous_jacent)
            # Un ordre identifié garde le symbole occupé ; les autres ressources peuvent être qualifiées.
            if k not in ordres_connus or not couverture:
                prete = False
                if refus is None: refus = RefusExecution(Motif.ENVIRONMENT_NOT_READY, 'rapprochement_incomplet')
    compte = replace(observation.compte, positions=tuple(ps))
    garde = gardes.observer(compte, reconstitution)
    if garde is not None: refus = garde
    commandes = [c for c in commandes if c.nature not in (NatureCommande.CLOTURE, NatureCommande.TP, NatureCommande.ANNULATION)
        or c.nature is NatureCommande.ANNULATION and c.cle in ordres_connus
        or c.nature in (NatureCommande.CLOTURE, NatureCommande.TP) and c.cle in presentes]
    traces.append(TraceCycle('RAPPROCHEMENT', {'prete': prete,
        'positions_possedees': len(presentes), 'ordres_identifies': len(ordres_connus),
        'refus': refus.motif.value if refus is not None else None}))
    return BilanReprise(_exporter(etat, registre, gardes, cycles), compte,
        tuple(commandes), tuple(issues), tuple(traces), prete, refus)

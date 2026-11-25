"""Valeurs et calculs purs de la couche 1d, révisables sous harnais complet."""
from dataclasses import dataclass
from decimal import Decimal, localcontext
from xpbots.service_ia.c0_types import (ErreurService, RessourcesIA, entier,
    instant, texte, montant)


def _ressources(r):
    if not isinstance(r,RessourcesIA):raise ErreurService('RESSOURCES_CHARGEES_REQUISES')
    return r


def _tarif(r):
    return next(p for p in r.p['providers'] if 'input_usd_per_million_upper_bound' in p)


def _cout(entree,sortie,prix_entree,prix_sortie):
    entier(entree);entier(sortie)
    pe,ps=montant(prix_entree),montant(prix_sortie)
    with localcontext() as c:
        c.prec=max(c.prec,sum(len(str(v)) for v in (entree,sortie,pe,ps)))
        return (Decimal(entree)*pe+Decimal(sortie)*ps)/Decimal('1e6')


def cout_maximal(ressources,entree=None,sortie=None):
    r=_ressources(ressources)
    entree=r.p['max_input_tokens_upper_bound'] if entree is None else entier(entree)
    sortie=r.p['max_output_tokens_including_reasoning'] if sortie is None else entier(sortie)
    if entree>r.p['max_input_tokens_upper_bound'] or sortie>r.p['max_output_tokens_including_reasoning']:
        raise ErreurService('ENVELOPPE_TOKENS_DEPASSEE')
    tarif=_tarif(r)
    return _cout(entree,sortie,tarif['input_usd_per_million_upper_bound'],
                 tarif['output_usd_per_million_upper_bound'])


def budget_admet(ressources,depense,reserve,prochain,autres='0',taxes='0'):
    r=_ressources(ressources)
    d,v,n,a,t=map(montant,(depense,reserve,prochain,autres,taxes))
    api=montant(r.p['monthly_paid_api_subcap_usd']);total=montant(r.p['monthly_total_budget_usd'])
    if any(x>api for x in (d,v,n)) or any(x>total for x in (a,t)):return False
    return d+v+n<=api and d+v+n+a+t<=total


@dataclass(frozen=True)
class ProfilRoute:
    fournisseur: str
    modele: str
    profil_facturation: str
    quota_tokens_minute: int
    quota_requetes_minute: int
    quota_requetes_jour: int
    quota_tokens_jour: int
    verifie_ms: int | None
    gratuit_confirme: bool = False
    projet_dedie: bool = False
    cle_disponible: bool = False
    prix_entree: Decimal | None = None
    prix_sortie: Decimal | None = None

    def __post_init__(self):
        for v in (self.fournisseur,self.modele,self.profil_facturation):texte(v)
        for v in (self.quota_tokens_minute,self.quota_requetes_minute,
                  self.quota_requetes_jour,self.quota_tokens_jour):entier(v)
        if self.verifie_ms is not None:instant(self.verifie_ms)
        if any(type(v) is not bool for v in (self.gratuit_confirme,self.projet_dedie,self.cle_disponible)):
            raise ErreurService('PROFIL_ROUTE_BOOLEEN_REQUIS')
        for nom in ('prix_entree','prix_sortie'):
            if getattr(self,nom) is not None:object.__setattr__(self,nom,montant(getattr(self,nom)))


@dataclass(frozen=True)
class ReservationAPI:
    tentative_id: str
    job_id: str
    fournisseur: str
    jour: str
    mois: str
    entree_bornee: int
    sortie_max: int
    reserve_usd: Decimal

    def __post_init__(self):
        for v in (self.tentative_id,self.job_id,self.fournisseur,self.jour,self.mois):texte(v)
        entier(self.entree_bornee);entier(self.sortie_max)
        object.__setattr__(self,'reserve_usd',montant(self.reserve_usd))


@dataclass(frozen=True)
class DecisionBudget:
    reservation: ReservationAPI | None = None
    raison: str | None = None

    def __post_init__(self):
        if (self.reservation is None)==(self.raison is None):raise ErreurService('DECISION_BUDGET_AMBIGUE')
        if self.reservation is not None and not isinstance(self.reservation,ReservationAPI):
            raise ErreurService('RESERVATION_REQUISE')
        if self.raison is not None:texte(self.raison)

    @property
    def acceptee(self):return self.reservation is not None

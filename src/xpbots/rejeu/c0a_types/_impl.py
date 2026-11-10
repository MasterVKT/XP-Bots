"""Valeurs du rejeu ; aucune lecture, horloge ou valeur de coût implicite."""
from dataclasses import dataclass,field,fields,is_dataclass
from datetime import date
from decimal import Decimal,Context,localcontext
from enum import Enum
import math
import re
from types import MappingProxyType
from typing import Mapping
from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.noyau.c1b_instrument import Intervalle,ProfilInstrument,HorairesCotation
from xpbots.noyau.c1c_domaine import CleIntention,CauseCloture


class ErreurRejeu(ValueError):pass


def instant(v):
    try:return verifier_instant(v)
    except ValueError as e:raise ErreurRejeu('instant UTC invalide') from e


def entier(v,minimum=0):
    if type(v) is not int or v<minimum:raise ErreurRejeu('entier hors contrat')
    return v


def texte(v):
    if type(v) is not str or not v.strip():raise ErreurRejeu('texte non vide requis')
    try:v.encode('utf-8')
    except UnicodeError as e:raise ErreurRejeu('texte UTF-8 requis') from e
    return v


def montant(v,minimum=None,strict=False):
    if (not isinstance(v,Decimal) or not v.is_finite()
            or minimum is not None and (v<minimum or strict and v==minimum)):
        raise ErreurRejeu('montant décimal hors contrat')
    return v


def _tuple(v):
    if not isinstance(v,(tuple,list)):raise ErreurRejeu('collection explicite requise')
    return tuple(v)


def _figer(v):
    if isinstance(v,Mapping):
        if any(type(k) is not str for k in v):raise ErreurRejeu('clés de contexte textuelles requises')
        return MappingProxyType({k:_figer(x) for k,x in v.items()})
    if isinstance(v,(tuple,list)):return tuple(_figer(x) for x in v)
    if isinstance(v,(set,frozenset)):return frozenset(_figer(x) for x in v)
    if is_dataclass(v):return _figer({f.name:getattr(v,f.name) for f in fields(v)})
    if isinstance(v,Decimal):montant(v);return v
    if type(v) is float and not math.isfinite(v):raise ErreurRejeu('contexte non fini')
    if v is None or isinstance(v,(str,int,float,bool,date,Enum)):return v
    raise ErreurRejeu('valeur de contexte non prise en charge')


@dataclass(frozen=True)
class TarifCommission:
    identifiant:str
    entree_par_lot:Decimal
    minimum_entree:Decimal
    sortie_par_lot:Decimal
    minimum_sortie:Decimal
    def __post_init__(self):
        texte(self.identifiant)
        for v in (self.entree_par_lot,self.minimum_entree,self.sortie_par_lot,self.minimum_sortie):montant(v,Decimal(0))
    def entree(self,volume):
        montant(volume,Decimal(0),True)
        with localcontext(Context(prec=48)):return max(self.minimum_entree,self.entree_par_lot*volume)
    def sortie(self,volume):
        montant(volume,Decimal(0),True)
        with localcontext(Context(prec=48)):return max(self.minimum_sortie,self.sortie_par_lot*volume)


@dataclass(frozen=True)
class ConditionContrat:
    debut_ms:int
    fin_ms:int
    connu_ms:int
    profil:ProfilInstrument
    tarif:TarifCommission
    def __post_init__(self):
        instant(self.debut_ms);instant(self.fin_ms);instant(self.connu_ms)
        if self.fin_ms<=self.debut_ms or self.connu_ms>=self.fin_ms:raise ErreurRejeu('intervalle contractuel inexploitable')
        if not isinstance(self.profil,ProfilInstrument) or not isinstance(self.tarif,TarifCommission):
            raise ErreurRejeu('profil et tarif réels requis')
    def connue_a(self,t):
        instant(t);return self.debut_ms<=t<self.fin_ms and self.connu_ms<=t


def _intervalles(v,borne):
    t=_tuple(v)
    for i in t:
        if not isinstance(i,Intervalle) or i.debut_ms<borne.debut_ms or i.fin_ms>borne.fin_ms:
            raise ErreurRejeu('intervalle de données étranger')
    if any(b.debut_ms<a.fin_ms for a,b in zip(t,t[1:])):raise ErreurRejeu('intervalles non triés ou chevauchants')
    return t


@dataclass(frozen=True)
class ManifesteTicks:
    source:str
    symboles:Mapping
    intervalle:Intervalle
    couverture:tuple
    trous:tuple
    sha256:str
    date_recuperation:date
    extraction:str
    precision_prix:str
    horaires:Mapping
    sequence_origine:str='NATIVE'
    resolution_ms:int=1
    fuseau_original:str='UTC'
    conversion_utc_qualifiee:bool=True
    usage:str='FIXTURE_SYNTHETIQUE'
    def __post_init__(self):
        for v in (self.source,self.extraction,self.precision_prix,self.fuseau_original):texte(v)
        if not isinstance(self.intervalle,Intervalle) or type(self.date_recuperation) is not date:
            raise ErreurRejeu('intervalle et date de récupération requis')
        if type(self.sha256) is not str or re.fullmatch('[0-9a-f]{64}',self.sha256) is None:raise ErreurRejeu('SHA-256 requis')
        if self.sequence_origine not in ('NATIVE','ORDRE_ORIGINAL') or type(self.resolution_ms) is not int or self.resolution_ms!=1:
            raise ErreurRejeu('ordre et précision milliseconde requis')
        if type(self.conversion_utc_qualifiee) is not bool or not self.conversion_utc_qualifiee:raise ErreurRejeu('UTC non qualifié')
        if self.usage not in ('FIXTURE_SYNTHETIQUE','COURTIER_HISTORIQUE','TIERS_CONTREFACTUEL'):raise ErreurRejeu('provenance inconnue')
        if not isinstance(self.symboles,Mapping) or not self.symboles or not isinstance(self.horaires,Mapping):
            raise ErreurRejeu('liaison de symboles et horaires requis')
        s=dict(self.symboles);h=dict(self.horaires)
        for a,b in s.items():texte(a);texte(b)
        if len(set(s.values()))!=len(s) or set(h)!=set(s) or any(not isinstance(v,HorairesCotation) for v in h.values()):
            raise ErreurRejeu('liaison unique et horaires concordants requis')
        c=_intervalles(self.couverture,self.intervalle);t=_intervalles(self.trous,self.intervalle)
        if any(max(a.debut_ms,b.debut_ms)<min(a.fin_ms,b.fin_ms) for a in c for b in t):raise ErreurRejeu('couverture et trou superposés')
        for n,v in (('symboles',MappingProxyType(s)),('horaires',MappingProxyType(h)),('couverture',c),('trous',t)):
            object.__setattr__(self,n,v)


@dataclass(frozen=True)
class Trade:
    cle:CleIntention
    entree_ms:int
    sortie_ms:int
    volume:Decimal
    prix_entree:Decimal
    prix_sortie:Decimal
    profit_brut:Decimal
    frais_entree:Decimal
    frais_sortie:Decimal
    risque_initial:Decimal
    cause:CauseCloture
    contexte:Mapping=field(default_factory=dict)
    def __post_init__(self):
        instant(self.entree_ms);instant(self.sortie_ms)
        if (not isinstance(self.cle,CleIntention) or not isinstance(self.cause,CauseCloture)
                or not self.cle.cloture_ms<=self.entree_ms<=self.sortie_ms):raise ErreurRejeu('trade non causal')
        for v in (self.volume,self.prix_entree,self.prix_sortie,self.risque_initial):montant(v,Decimal(0),True)
        montant(self.profit_brut);montant(self.frais_entree,Decimal(0));montant(self.frais_sortie,Decimal(0))
        if not isinstance(self.contexte,Mapping):raise ErreurRejeu('contexte de trade requis')
        object.__setattr__(self,'contexte',_figer(self.contexte))
    @property
    def net(self):
        with localcontext(Context(prec=48)):return self.profit_brut-self.frais_entree-self.frais_sortie
    @property
    def r_net(self):
        with localcontext(Context(prec=48)):return self.net/self.risque_initial


@dataclass(frozen=True)
class PointCompte:
    instant_ms:int
    fonds_propres:Decimal
    solde:Decimal
    marge_utilisee:Decimal
    def __post_init__(self):
        instant(self.instant_ms);montant(self.fonds_propres);montant(self.solde);montant(self.marge_utilisee,Decimal(0))


@dataclass(frozen=True)
class JourMarche:
    jour:date
    periode:str
    def __post_init__(self):
        if type(self.jour) is not date:raise ErreurRejeu('date de marché requise')
        texte(self.periode)


@dataclass(frozen=True)
class ValeurJour:
    jour:date
    periode:str
    pnl_net:Decimal
    trades_clos:int
    def __post_init__(self):
        JourMarche(self.jour,self.periode);montant(self.pnl_net);entier(self.trades_clos)


@dataclass(frozen=True)
class FactureIA:
    reference:str
    instant_ms:int
    montant_usd:Decimal
    methodes:tuple[str,...]
    nature:str
    reelle:bool=True
    def __post_init__(self):
        texte(self.reference);instant(self.instant_ms);montant(self.montant_usd,Decimal(0))
        m=_tuple(self.methodes)
        for v in m:texte(v)
        if not m or len(set(m))!=len(m) or self.nature not in ('EVENEMENT','BRIEFING','JOURNAL','RECHERCHE') or type(self.reelle) is not bool:
            raise ErreurRejeu('facture IA incohérente')
        object.__setattr__(self,'methodes',m)
    def allocation(self):
        with localcontext(Context(prec=48)):
            part=self.montant_usd/Decimal(len(self.methodes))
            valeurs=[part]*(len(self.methodes)-1)
            valeurs.append(self.montant_usd-sum(valeurs,Decimal(0)))
        return MappingProxyType(dict(zip(self.methodes,valeurs)))


@dataclass(frozen=True)
class EcartRejeu:
    nom:str
    champ:str
    valeur:Decimal|int
    def __post_init__(self):
        texte(self.nom)
        if self.champ in ('OBJECTIF','BUFFER'):montant(self.valeur,Decimal(0),True)
        elif self.champ=='DUREE':entier(self.valeur,1)
        else:raise ErreurRejeu('écart de rejeu inconnu')

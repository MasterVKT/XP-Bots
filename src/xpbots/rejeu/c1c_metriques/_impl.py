"""Mesures hors décision ; les frais natifs et économiques restent réconciliables."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Context,Decimal,localcontext
from types import MappingProxyType
from zoneinfo import ZoneInfo

from xpbots.noyau.c0a_temps import instant_vers_datetime
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1c_domaine import Motif
from xpbots.rejeu.c0a_types import (ErreurRejeu,Trade,PointCompte,JourMarche,ValeurJour,
    FactureIA,entier,montant)
from xpbots.rejeu.c0b_protocole import SeuilsC10

D=Decimal


@dataclass(frozen=True)
class ComptageC09:
    configurations:int
    signaux:int
    refus:object
    entrees:int
    entrees_jours:object

    def __post_init__(self):
        for v in (self.configurations,self.signaux,self.entrees):entier(v)
        if self.signaux>self.configurations or self.entrees>self.signaux:
            raise ErreurRejeu('comptage C09 impossible')
        refus=dict(self.refus)
        for motif,n in refus.items():
            try:Motif(motif)
            except ValueError as e:raise ErreurRejeu('motif C09 inconnu') from e
            entier(n)
        object.__setattr__(self,'refus',MappingProxyType(refus))
        entrees_jours=dict(self.entrees_jours)
        for jour,n in entrees_jours.items():
            if type(jour) is not date:raise ErreurRejeu('dates Londres d’entrée requises')
            entier(n)
        if sum(entrees_jours.values())!=self.entrees:
            raise ErreurRejeu('somme des entrées journalières incohérente')
        object.__setattr__(self,'entrees_jours',MappingProxyType(entrees_jours))


@dataclass(frozen=True)
class Retention:
    ratio:Decimal|None
    statut:str
    reference:int|None
    candidat:int


def retention(candidat,reference,seuils):
    entier(candidat)
    if not isinstance(seuils,SeuilsC10):raise ErreurRejeu('seuils du protocole requis')
    if reference is None:return Retention(None,'N_A',None,candidat)
    entier(reference)
    if not reference:return Retention(None,'N_A',reference,candidat)
    with localcontext(Context(prec=48)):
        ratio=D(candidat)/D(reference)
    return Retention(ratio,'TROP_FAIBLE' if reference<seuils.min_reference else 'EXPLOITABLE',reference,candidat)


@dataclass(frozen=True)
class Facturation:
    factures:tuple
    total:Decimal
    par_methode:object
    recherche:Decimal
    toutes_reelles:bool


def reconcilier_factures(factures):
    uniques={}
    for facture in factures:
        if not isinstance(facture,FactureIA):raise ErreurRejeu('facture originale requise')
        ancienne=uniques.get(facture.reference)
        if ancienne is not None and ancienne!=facture:
            raise ErreurRejeu('référence de facture réécrite')
        uniques[facture.reference]=facture
    valeurs=tuple(sorted(uniques.values(),key=lambda f:(f.instant_ms,f.reference)))
    par_methode=defaultdict(D)
    with localcontext(Context(prec=48)):
        for f in valeurs:
            if f.nature!='RECHERCHE':
                for m,v in f.allocation().items():par_methode[m]+=v
        total=sum((f.montant_usd for f in valeurs),D(0))
        recherche=sum((f.montant_usd for f in valeurs if f.nature=='RECHERCHE'),D(0))
    return Facturation(valeurs,total,MappingProxyType(dict(par_methode)),recherche,all(f.reelle for f in valeurs))


def _cout(f,methode):
    if methode is None:return f.montant_usd
    if f.nature=='RECHERCHE':return D(0)
    return f.allocation().get(methode,D(0))


def _courbe(courbe):
    valeurs=tuple(courbe)
    if not valeurs or any(not isinstance(p,PointCompte) for p in valeurs):
        raise ErreurRejeu('courbe de fonds propres requise')
    if any(b.instant_ms<a.instant_ms for a,b in zip(valeurs,valeurs[1:])):
        raise ErreurRejeu('courbe non chronologique')
    if valeurs[0].fonds_propres<=0:raise ErreurRejeu('capital de départ positif requis')
    return valeurs


def drawdown(courbe):
    valeurs=_courbe(courbe)
    pic=valeurs[0].fonds_propres
    maximum=D(0)
    with localcontext(Context(prec=48)):
        for p in valeurs:
            pic=max(pic,p.fonds_propres)
            maximum=max(maximum,(pic-p.fonds_propres)/pic)
    return maximum


def courbe_economique(courbe,factures=(),methode=None):
    valeurs=_courbe(courbe)
    facturation=reconcilier_factures(factures)
    if any(f.instant_ms<valeurs[0].instant_ms for f in facturation.factures):
        raise ErreurRejeu('facture antérieure au capital de départ')
    evenements=[(p.instant_ms,0,i,p) for i,p in enumerate(valeurs)]
    evenements.extend((f.instant_ms,1,i,f) for i,f in enumerate(facturation.factures))
    resultat=[];cout=D(0);courant=valeurs[0]
    with localcontext(Context(prec=48)):
        for t,nature,_,valeur in sorted(evenements):
            if nature:cout+=_cout(valeur,methode)
            else:courant=valeur
            resultat.append(PointCompte(t,courant.fonds_propres-cout,courant.solde-cout,courant.marge_utilisee))
    return tuple(resultat)


@dataclass(frozen=True)
class BilanMesures:
    comptage:ComptageC09
    positions_closes:int
    resultats_nets:tuple
    pnl_courtier:Decimal
    cout_ia:Decimal
    pnl_economique:Decimal
    esperance:Decimal|None
    esperance_economique:Decimal|None
    profit_factor:Decimal|None
    statut_pf:str
    drawdown_courtier:Decimal
    drawdown_economique:Decimal
    jours_marche:int
    jours_zero:int
    frequence:Decimal|None
    taux_reussite:Decimal|None
    r_moyen_net:Decimal|None
    facturation:Facturation


def calculer_mesures(trades,courbe,jours,comptage,factures=(),methode=None):
    trades=tuple(trades);jours=tuple(jours);courbe=_courbe(courbe)
    if any(not isinstance(t,Trade) for t in trades) or not isinstance(comptage,ComptageC09):
        raise ErreurRejeu('trades et comptage typés requis')
    if len({t.cle for t in trades})!=len(trades):raise ErreurRejeu('positions closes dupliquées')
    if methode is not None:trades=tuple(t for t in trades if t.cle.strategie==methode)
    _jours(jours)
    if len(trades)>comptage.entrees:raise ErreurRejeu('plus de positions closes que d’entrées')
    f=reconcilier_factures(factures)
    with localcontext(Context(prec=48)):
        nets=tuple(t.net for t in trades);n=len(nets)
        pnl=sum(nets,D(0));cout=sum((_cout(v,methode) for v in f.factures),D(0))
        pertes=-sum((v for v in nets if v<0),D(0));gains=sum((v for v in nets if v>0),D(0))
        economique=pnl-cout
        if set(comptage.entrees_jours)-{j.jour for j in jours}:
            raise ErreurRejeu('jour d’entrée absent du panel')
        zero=sum(not comptage.entrees_jours.get(j.jour,0) for j in jours)
        return BilanMesures(comptage,n,nets,pnl,cout,economique,pnl/D(n) if n else None,
            economique/D(n) if n else None,gains/pertes if pertes else None,'CALCULABLE' if pertes else 'SANS_PERTE',
            drawdown(courbe),drawdown(courbe_economique(courbe,f.factures,methode)),len(jours),zero,
            D(comptage.entrees)/D(len(jours)) if jours else None,
            D(sum(v>0 for v in nets))/D(n) if n else None,
            sum((t.r_net for t in trades),D(0))/D(n) if n else None,f)


def _jours(jours):
    if any(not isinstance(j,JourMarche) for j in jours) or len({j.jour for j in jours})!=len(jours):
        raise ErreurRejeu('jours de marché uniques requis')
    if any(b.jour<=a.jour for a,b in zip(jours,jours[1:])):
        raise ErreurRejeu('jours non chronologiques')


def _zone(commun):
    if not isinstance(commun,ParametresCommuns):raise ErreurRejeu('paramètres communs requis')
    return ZoneInfo(commun.session_timezone)


def panel_journalier(trades,jours,commun,factures=(),methode=None):
    jours=tuple(jours);trades=tuple(trades);_jours(jours);zone=_zone(commun)
    if any(not isinstance(t,Trade) for t in trades) or len({t.cle for t in trades})!=len(trades):
        raise ErreurRejeu('positions closes uniques requises')
    sommes={j.jour:D(0) for j in jours};nombres={j.jour:0 for j in jours}
    with localcontext(Context(prec=48)):
        for t in trades:
            if not isinstance(t,Trade):raise ErreurRejeu('trade typé requis')
            if methode is not None and t.cle.strategie!=methode:continue
            jour=instant_vers_datetime(t.sortie_ms).astimezone(zone).date()
            if jour not in sommes:raise ErreurRejeu('sortie absente du panel commun')
            sommes[jour]+=t.net;nombres[jour]+=1
        for f in reconcilier_factures(factures).factures:
            cout=_cout(f,methode)
            if not cout:continue
            jour=instant_vers_datetime(f.instant_ms).astimezone(zone).date()
            if jour not in sommes:raise ErreurRejeu('facture absente du panel commun')
            sommes[jour]-=cout
    return tuple(ValeurJour(j.jour,j.periode,sommes[j.jour],nombres[j.jour]) for j in jours)


def ventiler_trades(trades,commun):
    zone=_zone(commun);groupes=defaultdict(list)
    for t in trades:
        if not isinstance(t,Trade):raise ErreurRejeu('trade typé requis')
        moment=instant_vers_datetime(t.entree_ms).astimezone(zone)
        for nom,valeur in (('methode',t.cle.strategie),('symbole',t.cle.symbole),('heure',moment.hour),
                           ('jour_semaine',moment.weekday()),('sens',t.cle.sens.value)):
            groupes[(nom,valeur)].append(t)
    resultats={}
    with localcontext(Context(prec=48)):
        for cle,ts in groupes.items():
            n=D(len(ts))
            resultats[cle]=MappingProxyType(dict(effectif=len(ts),pnl_net=sum((t.net for t in ts),D(0)),
                taux_reussite=D(sum(t.net>0 for t in ts))/n,r_moyen_net=sum((t.r_net for t in ts),D(0))/n))
    return MappingProxyType(resultats)

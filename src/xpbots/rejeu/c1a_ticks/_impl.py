"""Intégrité du lot avant exposition des ticks ; aucun accès physique."""
from dataclasses import dataclass
from datetime import datetime,time,timedelta
from decimal import Decimal,InvalidOperation
import csv
import hashlib
import math
from zoneinfo import ZoneInfo
from typing import Mapping

from xpbots.noyau.c0a_temps import instant_depuis_datetime,instant_vers_datetime
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.rejeu.c0a_types import ErreurRejeu,ManifesteTicks,JourMarche,texte

COLONNES_TICKS=('canonical_symbol','broker_symbol','time_utc_ms','sequence','bid','ask')


def _naturel(v):
    if not v or not v.isascii() or not v.isdigit():
        raise ErreurRejeu('entier ASCII sans signe requis')
    return int(v)


def _prix(v):
    try:
        d=Decimal(v)
        f=float(d)
    except (InvalidOperation,ValueError,OverflowError) as e:
        raise ErreurRejeu('prix illisible') from e
    if not d.is_finite() or d<=0 or not math.isfinite(f) or Decimal(str(f))!=d:
        raise ErreurRejeu('prix non positif, non fini ou précision perdue')
    return f


@dataclass(frozen=True)
class HistoriqueTicks:
    ticks:tuple
    manifeste:ManifesteTicks

    def __post_init__(self):
        if not isinstance(self.manifeste,ManifesteTicks):
            raise ErreurRejeu('manifeste typé requis')
        valeurs=tuple(self.ticks)
        precedent=None
        for tick in valeurs:
            if not isinstance(tick,Tick):
                raise ErreurRejeu('Tick canonique requis')
            t=tick.instant_fournisseur_ms
            if (tick.instant_reception_ms!=t or tick.ask<tick.bid
                    or self.manifeste.symboles.get(tick.symbole)!=tick.symbole_courtier
                    or not any(i.debut_ms<=t<i.fin_ms for i in self.manifeste.couverture)):
                raise ErreurRejeu('tick étranger à la liaison ou à la couverture déclarée')
            cle=(t,tick.numero)
            if precedent is not None and cle<=precedent:
                raise ErreurRejeu('ordre natif non strict, aucun tri correctif')
            precedent=cle
        if not valeurs:
            raise ErreurRejeu('lot de ticks vide')
        object.__setattr__(self,'ticks',valeurs)

    def __iter__(self):
        return iter(self.ticks)


def analyser_lignes_ticks(lignes,manifeste):
    if not isinstance(manifeste,ManifesteTicks):
        raise ErreurRejeu('manifeste obligatoire avant analyse')
    lignes=tuple(lignes)
    if not lignes or any(type(l) is not str for l in lignes):
        raise ErreurRejeu('lignes UTF-8 explicites requises')
    try:
        empreinte=hashlib.sha256(''.join(lignes).encode('utf-8')).hexdigest()
    except UnicodeError as e:
        raise ErreurRejeu('lot non UTF-8') from e
    if empreinte!=manifeste.sha256:
        raise ErreurRejeu('empreinte du lot différente du manifeste')
    try:
        lecteur=csv.reader(lignes,strict=True)
        if tuple(next(lecteur,()))!=COLONNES_TICKS:
            raise ErreurRejeu('en-tête canonique requis')
        ticks=[]
        for ordinal,champs in enumerate(lecteur):
            if len(champs)!=len(COLONNES_TICKS):
                raise ErreurRejeu('six colonnes de ticks requises')
            symbole,courtier,t,seq,bid,ask=champs
            t=_naturel(t)
            numero=(ordinal if manifeste.sequence_origine=='ORDRE_ORIGINAL' and seq=='' else _naturel(seq))
            ticks.append(Tick(symbole,courtier,t,t,numero,_prix(bid),_prix(ask)))
    except (csv.Error,ValueError) as e:
        raise ErreurRejeu('lot de ticks refusé : '+str(e)) from e
    return HistoriqueTicks(tuple(ticks),manifeste)


def _recoupe(horaires,a,b):
    if a<horaires.debut_validite_ms or b>horaires.fin_validite_ms:
        raise ErreurRejeu('horaires non qualifiés pour le jour de marché')
    for seance in horaires.seances:
        morceaux=[(max(a,seance.debut_ms),min(b,seance.fin_ms))]
        for fermeture in horaires.fermetures:
            suite=[]
            for debut,fin in morceaux:
                if fermeture.fin_ms<=debut or fermeture.debut_ms>=fin:
                    suite.append((debut,fin))
                else:
                    if debut<fermeture.debut_ms:suite.append((debut,fermeture.debut_ms))
                    if fermeture.fin_ms<fin:suite.append((fermeture.fin_ms,fin))
            morceaux=suite
        if any(fin>debut for debut,fin in morceaux):return True
    return False


def jours_marche(manifeste,periode,fenetres,commun):
    if not isinstance(manifeste,ManifesteTicks):raise ErreurRejeu('manifeste requis')
    texte(periode)
    if not isinstance(commun,ParametresCommuns):raise ErreurRejeu('paramètres communs requis')
    jours_ouvres=commun.active_weekdays_local
    londres=ZoneInfo(commun.session_timezone)
    if not isinstance(fenetres,Mapping) or not fenetres or set(fenetres)-set(manifeste.symboles):
        raise ErreurRejeu('fenêtres et symboles déclarés requis')
    intervalles={}
    for symbole,couple in fenetres.items():
        try:
            debut,fin=(v if isinstance(v,time) else time.fromisoformat(v) for v in couple)
        except (TypeError,ValueError) as e:raise ErreurRejeu('fenêtre locale invalide') from e
        if debut>=fin or debut.tzinfo is not None or fin.tzinfo is not None:
            raise ErreurRejeu('fenêtre locale ordonnée requise')
        intervalles[symbole]=(debut,fin)
    borne=manifeste.intervalle
    jour=instant_vers_datetime(borne.debut_ms).astimezone(londres).date()
    dernier=instant_vers_datetime(borne.fin_ms-1).astimezone(londres).date()
    resultat=[]
    while jour<=dernier:
        if jour.weekday() in jours_ouvres:
            ouvert=False
            for symbole,(debut,fin) in intervalles.items():
                a=instant_depuis_datetime(datetime.combine(jour,debut,londres))
                b=instant_depuis_datetime(datetime.combine(jour,fin,londres))
                a=max(a,borne.debut_ms);b=min(b,borne.fin_ms)
                if b>a:
                    # Toutes les fenêtres doivent être qualifiées, même si une autre est ouverte.
                    ouvert=_recoupe(manifeste.horaires[symbole],a,b) or ouvert
            if ouvert:resultat.append(JourMarche(jour,periode))
        jour+=timedelta(days=1)
    return tuple(resultat)

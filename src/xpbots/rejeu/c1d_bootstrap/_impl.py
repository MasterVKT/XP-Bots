"""Un seul générateur local ; aucun assemblage de prix rééchantillonnés."""
from dataclasses import dataclass
from decimal import Context,Decimal,ROUND_FLOOR,localcontext
import hashlib
import random

from xpbots.rejeu.c0a_types import ErreurRejeu,JourMarche,ValeurJour,montant
from xpbots.rejeu.c0b_protocole import ParametresBootstrap

D=Decimal
_CENT_POUR_CENT=100


def _panel(jours):
    jours=tuple(jours)
    if not jours or any(not isinstance(j,JourMarche) for j in jours):
        raise ErreurRejeu('panel de jours typés non vide requis')
    terminees=set();periode=None
    for i,j in enumerate(jours):
        if i and j.jour<=jours[i-1].jour:raise ErreurRejeu('panel non chronologique')
        if j.periode!=periode:
            if j.periode in terminees:raise ErreurRejeu('période interrompue puis reprise')
            if periode is not None:terminees.add(periode)
            periode=j.periode
    return jours


def indices_bootstrap(jours,parametres):
    jours=_panel(jours)
    if not isinstance(parametres,ParametresBootstrap):raise ErreurRejeu('paramètres du protocole requis')
    taille=parametres.bloc_jours;n=len(jours)
    blocs=tuple(tuple(range(i,i+taille)) for i in range(n-taille+1)
        if jours[i].periode==jours[i+taille-1].periode)
    if not blocs:raise ErreurRejeu('aucun bloc continu complet')
    generateur=random.Random(parametres.graine)
    nombre=(n+taille-1)//taille
    for _ in range(parametres.replications):
        tirage=[]
        for _ in range(nombre):tirage.extend(generateur.choice(blocs))
        yield tuple(tirage[:n])


def percentile(valeurs,pourcentage):
    montant(pourcentage,D(0))
    if pourcentage>_CENT_POUR_CENT:raise ErreurRejeu('percentile hors bornes')
    valeurs=tuple(valeurs)
    for v in valeurs:montant(v)
    if not valeurs:return None
    valeurs=sorted(valeurs)
    with localcontext(Context(prec=48)):
        position=D(len(valeurs)-1)*pourcentage/D(_CENT_POUR_CENT)
        bas=int(position.to_integral_value(rounding=ROUND_FLOOR))
        haut=min(bas+1,len(valeurs)-1)
        return valeurs[bas]+(position-D(bas))*(valeurs[haut]-valeurs[bas])


@dataclass(frozen=True)
class IntervalleBootstrap:
    valeurs:tuple
    bas:Decimal|None
    haut:Decimal|None
    invalides:int


@dataclass(frozen=True)
class ResultatBootstrap:
    parametres:ParametresBootstrap
    nombre_jours:int
    esperance_candidat:IntervalleBootstrap
    difference_esperance:IntervalleBootstrap
    gain_incremental:IntervalleBootstrap
    difference_drawdown:IntervalleBootstrap
    empreinte_indices:str


def _drawdown(pnl,capital):
    pic=capital;equity=capital;maximum=D(0)
    for gain in pnl:
        equity+=gain;pic=max(pic,equity);maximum=max(maximum,(pic-equity)/pic)
    return maximum


def bootstrap_apparie(reference,candidat,parametres,capital_initial):
    reference=tuple(reference);candidat=tuple(candidat)
    montant(capital_initial,D(0),True)
    if len(reference)!=len(candidat) or any(not isinstance(v,ValeurJour) for v in reference+candidat):
        raise ErreurRejeu('séries journalières appariées requises')
    jours=_panel(JourMarche(v.jour,v.periode) for v in reference)
    if tuple((v.jour,v.periode) for v in reference)!=tuple((v.jour,v.periode) for v in candidat):
        raise ErreurRejeu('jours appariés différents')
    esperances=[];differences=[];gains=[];drawdowns=[];empreinte=hashlib.sha256()
    invalides_candidat=0;invalides_paire=0
    with localcontext(Context(prec=48)):
        for indices in indices_bootstrap(jours,parametres):
            empreinte.update((','.join(map(str,indices))+'\n').encode('ascii'))
            a=tuple(reference[i] for i in indices);b=tuple(candidat[i] for i in indices)
            pnl_a=sum((v.pnl_net for v in a),D(0));pnl_b=sum((v.pnl_net for v in b),D(0))
            n_a=sum(v.trades_clos for v in a);n_b=sum(v.trades_clos for v in b)
            if n_b:esperances.append(pnl_b/D(n_b))
            else:invalides_candidat+=1
            if n_a and n_b:differences.append(pnl_b/D(n_b)-pnl_a/D(n_a))
            else:invalides_paire+=1
            gains.append(pnl_b-pnl_a)
            drawdowns.append(_drawdown((v.pnl_net for v in b),capital_initial)-_drawdown((v.pnl_net for v in a),capital_initial))
    def intervalle(v,invalides=0):
        return IntervalleBootstrap(tuple(v),percentile(v,parametres.percentile_bas),percentile(v,parametres.percentile_haut),invalides)
    return ResultatBootstrap(parametres,len(jours),intervalle(esperances,invalides_candidat),
        intervalle(differences,invalides_paire),intervalle(gains),intervalle(drawdowns),empreinte.hexdigest())

"""Les entrées portent leur réception ; aucune horloge ou stratégie implicite."""
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping, Protocol, runtime_checkable
from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c2_journal import BRAS,MODES,Enregistrement
from xpbots.execution.c0a_types import RefusExecution,EtatCompte,ControleNatif
from xpbots.noyau.c1b_instrument import ProfilInstrument
from xpbots.execution.c1b_gardes import BaseReconstituee
from xpbots.execution.c4_cycle import ReponseCourtier,PreuvePersistance,CommandeExecution
from xpbots.execution.c5b_reprise import ObservationNative
from xpbots.execution.c6_coordinateur import LotCoordinateur
from xpbots.fondamental.c0_types import TableImportance

REFERENCE='REFERENCE'
IA='IA'


class ErreurOrchestration(ValueError):pass


def instant(v):
    try:return verifier_instant(v)
    except ValueError as e:raise ErreurOrchestration('instant UTC invalide') from e


def entier(v,minimum=0):
    if type(v) is not int or v<minimum:raise ErreurOrchestration('entier hors contrat')
    return v


def texte(v):
    if type(v) is not str or not v.strip():raise ErreurOrchestration('texte non vide requis')
    try:v.encode('utf-8')
    except UnicodeError as e:raise ErreurOrchestration('texte UTF-8 requis') from e
    return v


def _tuple(v):
    if not isinstance(v,(tuple,list)):raise ErreurOrchestration('collection explicite requise')
    return tuple(v)


def _paires(v,classe):
    p=tuple(v.items()) if isinstance(v,Mapping) else _tuple(v)
    resultat={}
    for paire in p:
        if not isinstance(paire,(tuple,list)) or len(paire)!=len(('bras','valeur')):
            raise ErreurOrchestration('paire bras/valeur requise')
        nom,valeur=paire
        if type(nom) is not str or nom not in BRAS or nom in resultat or not isinstance(valeur,classe):
            raise ErreurOrchestration('bras unique connu et valeur typée requis')
        resultat[nom]=valeur
    return tuple(resultat.items())


@runtime_checkable
class Strategie(Protocol):
    identifiant:str
    def sur_bougie(self,bougie):...
    def sur_issue(self,issue):...


@dataclass(frozen=True)
class FabriqueStrategie:
    identifiant:str
    construire:object
    def __post_init__(self):
        texte(self.identifiant)
        if not callable(self.construire):raise ErreurOrchestration('fabrique appelable requise')


@dataclass(frozen=True)
class Deploiement:
    identifiant:str
    mode:str
    fabriques:tuple[FabriqueStrategie,...]
    tailles_tick:Mapping[str,Decimal]
    longueur_empreinte:int
    def __post_init__(self):
        texte(self.identifiant);entier(self.longueur_empreinte,1)
        if type(self.mode) is not str or self.mode not in MODES:raise ErreurOrchestration('mode inconnu')
        f=_tuple(self.fabriques)
        if not f or any(not isinstance(v,FabriqueStrategie) for v in f):raise ErreurOrchestration('fabriques typées requises')
        if len({v.identifiant for v in f})!=len(f):raise ErreurOrchestration('identifiants de stratégie répétés')
        if not isinstance(self.tailles_tick,Mapping) or not self.tailles_tick:raise ErreurOrchestration('tailles explicites requises')
        tailles=dict(self.tailles_tick)
        for s,t in tailles.items():
            texte(s)
            if not isinstance(t,Decimal) or not t.is_finite() or t<=0:raise ErreurOrchestration('tick Decimal positif requis')
        object.__setattr__(self,'fabriques',f)
        object.__setattr__(self,'tailles_tick',MappingProxyType(tailles))


@dataclass(frozen=True)
class ReceptionExterne:
    nature:str
    octets:bytes|None=b''
    symbole:str|None=None
    table:TableImportance|None=None
    def __post_init__(self):
        if self.nature not in ('PERMISSION','CALENDRIER','INTERRUPTION','SNAPSHOT'):
            raise ErreurOrchestration('nature de réception inconnue')
        if not (type(self.octets) is bytes or self.nature=='SNAPSHOT' and self.octets is None):
            raise ErreurOrchestration('octets externes requis')
        if self.nature in ('PERMISSION','INTERRUPTION'):
            texte(self.symbole)
            if self.table is not None or self.nature=='INTERRUPTION' and self.octets:
                raise ErreurOrchestration('permission ou interruption incohérente')
        elif self.nature=='CALENDRIER':
            if self.symbole is not None or not isinstance(self.table,TableImportance):
                raise ErreurOrchestration('classification du calendrier requise')
        elif self.symbole is not None or self.table is not None:raise ErreurOrchestration('snapshot global requis')


@dataclass(frozen=True)
class MiseAJourBras:
    reponses:tuple[ReponseCourtier,...]=()
    observation:ObservationNative|None=None
    base_utc:BaseReconstituee|RefusExecution|None=None
    preuve:PreuvePersistance|None=None
    def __post_init__(self):
        r=_tuple(self.reponses)
        if any(not isinstance(v,ReponseCourtier) for v in r):raise ErreurOrchestration('réponses natives requises')
        for v,c in ((self.observation,ObservationNative),(self.preuve,PreuvePersistance)):
            if v is not None and not isinstance(v,c):raise ErreurOrchestration('mise à jour C08 mal typée')
        if self.base_utc is not None and not isinstance(self.base_utc,(BaseReconstituee,RefusExecution)):
            raise ErreurOrchestration('preuve de minuit typée requise')
        object.__setattr__(self,'reponses',r)


@dataclass(frozen=True)
class EntreeMoteur:
    instant_ms:int
    numero:int
    nature:str='MINUTERIE'
    ticks:tuple[Tick,...]=()
    mises_a_jour:tuple[tuple[str,MiseAJourBras],...]=()
    receptions:tuple[ReceptionExterne,...]=()
    def __post_init__(self):
        instant(self.instant_ms);entier(self.numero,1)
        if self.nature not in ('TICKS','MINUTERIE','PERSISTANCE'):raise ErreurOrchestration('nature d’entrée inconnue')
        ticks=_tuple(self.ticks);receptions=_tuple(self.receptions);maj=_paires(self.mises_a_jour,MiseAJourBras)
        if any(not isinstance(v,Tick) or v.instant_reception_ms!=self.instant_ms for v in ticks):
            raise ErreurOrchestration('ticks reçus au même instant requis')
        if bool(ticks)!=(self.nature=='TICKS'):raise ErreurOrchestration('groupe de ticks incohérent')
        if any(not isinstance(v,ReceptionExterne) for v in receptions):raise ErreurOrchestration('réceptions typées requises')
        if self.nature=='PERSISTANCE' and (not maj or any(v.preuve is None or v.reponses or v.observation is not None for _,v in maj)):
            raise ErreurOrchestration('preuves seules requises')
        if self.nature!='PERSISTANCE' and any(v.preuve is not None for _,v in maj):
            raise ErreurOrchestration('preuve dans un événement distinct requise')
        for _,v in maj:
            if (any(r.instant_ms>self.instant_ms for r in v.reponses)
                    or v.observation is not None and v.observation.compte.instant_ms>self.instant_ms
                    or isinstance(v.base_utc,BaseReconstituee) and v.base_utc.instant_ms>self.instant_ms):
                raise ErreurOrchestration('fait natif futur')
        object.__setattr__(self,'ticks',ticks);object.__setattr__(self,'receptions',receptions)
        object.__setattr__(self,'mises_a_jour',maj)


@dataclass(frozen=True)
class SortieMoteur:
    enregistrements:tuple[Enregistrement,...]
    commandes:tuple[CommandeExecution,...]
    lot:LotCoordinateur|None=None
    def __post_init__(self):
        e=_tuple(self.enregistrements);c=_tuple(self.commandes)
        if any(not isinstance(v,Enregistrement) for v in e) or any(not isinstance(v,CommandeExecution) for v in c):
            raise ErreurOrchestration('sorties canoniques requises')
        if self.lot is not None and not isinstance(self.lot,LotCoordinateur):raise ErreurOrchestration('lot C08 réel requis')
        object.__setattr__(self,'enregistrements',e);object.__setattr__(self,'commandes',c)


@dataclass(frozen=True)
class SortieEvenement:
    numero:int
    instant_ms:int
    sorties:tuple[tuple[str,SortieMoteur],...]=()
    ignoree:bool=False
    def __post_init__(self):
        entier(self.numero,1);instant(self.instant_ms)
        if type(self.ignoree) is not bool:raise ErreurOrchestration('booléen strict requis')
        s=_paires(self.sorties,SortieMoteur)
        if self.ignoree and any(v.enregistrements or v.commandes for _,v in s):
            raise ErreurOrchestration('relecture sans réémission requise')
        object.__setattr__(self,'sorties',s)

    @property
    def par_bras(self):return MappingProxyType(dict(self.sorties))

    @property
    def enregistrements(self):return tuple(e for _,s in self.sorties for e in s.enregistrements)


@dataclass(frozen=True)
class AppelCalcul:
    nom:str
    arguments:tuple
    options:tuple
    resultat:object
    def __post_init__(self):
        texte(self.nom)
        if self.nom not in ('profit','frais_aller_retour','frais_sortie','marge','controler','specifications','etat_compte'):
            raise ErreurOrchestration('méthode CalculCourtier inconnue')
        args=_tuple(self.arguments);options=_tuple(self.options);noms=[]
        for option in options:
            if not isinstance(option,tuple) or len(option)!=len(('nom','valeur')):raise ErreurOrchestration('option nommée requise')
            texte(option[0]);noms.append(option[0])
        if len(set(noms))!=len(noms):raise ErreurOrchestration('options répétées')
        attendu={'controler':ControleNatif,'specifications':ProfilInstrument,'etat_compte':EtatCompte}.get(self.nom,Decimal)
        if not isinstance(self.resultat,(attendu,RefusExecution)):
            raise ErreurOrchestration('résultat de calcul normalisé requis')
        if isinstance(self.resultat,Decimal) and (not self.resultat.is_finite() or self.nom!='profit' and self.resultat<0):
            raise ErreurOrchestration('montant de calcul invalide')
        object.__setattr__(self,'arguments',args);object.__setattr__(self,'options',tuple(sorted(options)))


@dataclass(frozen=True)
class EntreeJournalisee:
    entree:EntreeMoteur
    calculs:tuple[tuple[str,tuple[AppelCalcul,...]],...]
    def __post_init__(self):
        if not isinstance(self.entree,EntreeMoteur):raise ErreurOrchestration('entrée typée requise')
        calculs=_paires(self.calculs,tuple)
        if any(not isinstance(a,AppelCalcul) for _,appels in calculs for a in appels):
            raise ErreurOrchestration('appels de calcul typés requis')
        object.__setattr__(self,'calculs',calculs)

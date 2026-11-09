"""État du bras ; les méthodes de trading et le compte restent indépendants."""
from dataclasses import dataclass,fields,is_dataclass
from datetime import date,datetime
import hashlib
import json
import re
from types import MappingProxyType
from typing import Mapping
from xpbots.orchestration.c0_contrats import (ErreurOrchestration,Strategie,Deploiement,SortieMoteur,
    REFERENCE,IA,instant,entier,texte,AppelCalcul)
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.donnees.c0a_types import BougieEnrichie,UniteTemps
from xpbots.execution.c0b_controles import ControleFondamental
from xpbots.execution.c0a_types import RefusExecution
from xpbots.execution.c1a_calcul import appeler_calcul
from xpbots.execution.c6_coordinateur import CoordinateurCompte,EtatCoordinateur,DossierIntention,LotCoordinateur
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1c_domaine import Issue,AbsenceDeSignal,SignalTechnique,Motif
from xpbots.noyau.c2_journal import (Enregistrement,Enveloppe,TypeEnregistrement,enregistrement,
    empreintes_regles,enregistrement_cloture)


def _signature(c,d,nom):
    return (nom,c.technique.empreinte_canonique,c.ia.empreinte_canonique,d.identifiant,d.mode,
        d.longueur_empreinte,tuple(f.identifiant for f in d.fabriques),tuple(sorted(d.tailles_tick.items())))


def _identifiant(c,d,nom):
    return d.identifiant+(':'+nom if d.mode==c.ia.parametres['default_evaluation_mode'] else '')


@dataclass(frozen=True)
class TraceStrategie:
    identifiant:str
    symbole:str
    nature:str
    instant_ms:int
    valeur:object
    resultat:object=None
    def __post_init__(self):
        texte(self.identifiant);texte(self.symbole);instant(self.instant_ms)
        if self.nature=='BOUGIE':
            if not isinstance(self.valeur,BougieEnrichie):raise ErreurOrchestration('bougie enrichie requise')
        elif self.nature=='ISSUE':
            if not isinstance(self.valeur,Issue) or self.resultat is not None:raise ErreurOrchestration('issue réelle requise')
        else:raise ErreurOrchestration('trace de stratégie inconnue')


@dataclass(frozen=True)
class EtatBras:
    nom:str
    signature:tuple
    coordinateur:EtatCoordinateur
    historique:tuple[TraceStrategie,...]=()
    numero:int=0
    intentions_journalisees:tuple[DossierIntention,...]=()
    empreinte:str=''
    def __post_init__(self):
        if self.nom not in (REFERENCE,IA) or not isinstance(self.coordinateur,EtatCoordinateur):
            raise ErreurOrchestration('bras et état C08 réels requis')
        entier(self.numero)
        for nom,classe in (('historique',TraceStrategie),('intentions_journalisees',DossierIntention)):
            v=getattr(self,nom)
            if not isinstance(v,(tuple,list)) or any(not isinstance(x,classe) for x in v):
                raise ErreurOrchestration('historique de bras typé requis')
            object.__setattr__(self,nom,tuple(v))
        if not isinstance(self.signature,tuple):raise ErreurOrchestration('signature de bras requise')
        if type(self.empreinte) is not str or re.fullmatch('[0-9a-f]{64}',self.empreinte) is None:
            raise ErreurOrchestration('empreinte de reprise requise')


def _empreinte(nom,signature,coordinateur,historique,numero,intentions):
    corps=_journal((nom,signature,coordinateur,historique,numero,intentions))
    try:b=json.dumps(corps,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False,default=str).encode('utf-8')
    except (ValueError,TypeError,UnicodeError) as e:raise ErreurOrchestration('état non représentable') from e
    return hashlib.sha256(b).hexdigest()


def _verifier_etat(e):
    if not isinstance(e,EtatBras) or e.empreinte!=_empreinte(e.nom,e.signature,e.coordinateur,e.historique,e.numero,e.intentions_journalisees):
        raise ErreurOrchestration('état de bras altéré')


def _journal(valeur):
    """Adapter les valeurs pures aux contenus du journal canonique du noyau."""
    if isinstance(valeur,(date,datetime)): return valeur.isoformat()
    if is_dataclass(valeur): return {f.name:_journal(getattr(valeur,f.name)) for f in fields(valeur)}
    if isinstance(valeur,Mapping): return {k:_journal(v) for k,v in valeur.items()}
    if isinstance(valeur,(set,frozenset)): return tuple(_journal(v) for v in sorted(valeur))
    if isinstance(valeur,(tuple,list)): return tuple(_journal(v) for v in valeur)
    return valeur


def _issue(issue):
    if issue is None: return None
    return dict(nature=issue.nature.value,instant_utc_ms=issue.instant_ms,
        motif=issue.motif.value if issue.motif is not None else None,detail=issue.detail,
        cause=issue.cause.value if issue.cause is not None else None)


class PortCalculJournalise:
    def __init__(self,port):
        self._port=port;self._appels=[];self._attendus=None;self._position=0;self._erreur=None
        self._initialisation=()

    @property
    def initialisation(self):return self._initialisation

    def debut_rejeu(self,appels):
        if self._attendus is not None or self._appels:raise ErreurOrchestration('traces précédentes non drainées')
        if not isinstance(appels,(tuple,list)) or any(not isinstance(a,AppelCalcul) for a in appels):
            raise ErreurOrchestration('appels archivés réels requis')
        self._attendus=tuple(appels);self._position=0;self._erreur=None

    def terminer_rejeu(self):
        if self._attendus is None:return
        erreur=self._erreur or ('nombre d’appels différent' if self._position!=len(self._attendus) else None)
        self._attendus=None
        if erreur:raise ErreurOrchestration('divergence de rejeu : '+erreur)

    def drainer(self):
        if self._attendus is not None:raise ErreurOrchestration('rejeu non validé')
        appels=tuple(self._appels);self._appels=[];return appels

    def finir_initialisation(self):
        self.terminer_rejeu();self._initialisation=self.drainer()

    def _appeler(self,nom,args,kwargs):
        options=tuple(sorted(kwargs.items()))
        if self._attendus is None:
            resultat=appeler_calcul(self._port,nom,*args,**kwargs)
        elif (self._position>=len(self._attendus)
                or (self._attendus[self._position].nom,self._attendus[self._position].arguments,
                    self._attendus[self._position].options)!=(nom,args,options)):
            self._erreur='nom, arguments ou options différents'
            resultat=RefusExecution(Motif.ENVIRONMENT_NOT_READY,nom)
        else:
            resultat=self._attendus[self._position].resultat;self._position+=1
        self._appels.append(AppelCalcul(nom,args,options,resultat));return resultat

    def profit(self,*args,**kwargs):return self._appeler('profit',args,kwargs)
    def frais_aller_retour(self,*args,**kwargs):return self._appeler('frais_aller_retour',args,kwargs)
    def frais_sortie(self,*args,**kwargs):return self._appeler('frais_sortie',args,kwargs)
    def marge(self,*args,**kwargs):return self._appeler('marge',args,kwargs)
    def controler(self,*args,**kwargs):return self._appeler('controler',args,kwargs)
    def specifications(self,*args,**kwargs):return self._appeler('specifications',args,kwargs)
    def etat_compte(self,*args,**kwargs):return self._appeler('etat_compte',args,kwargs)


class CoordinateurTrace(CoordinateurCompte):
    def __init__(self,technique,deploiement,profils,profil_compte,port,fondamental,instant_ms,*,
                 appels_initialisation=None,**kwargs):
        self._calculs=PortCalculJournalise(port)
        if appels_initialisation is not None:self._calculs.debut_rejeu(appels_initialisation)
        super().__init__(technique,deploiement,profils,profil_compte,self._calculs,fondamental,instant_ms,**kwargs)
        self._calculs.finir_initialisation()

    @property
    def calculs(self):return self._calculs


class Bras:
    def __init__(self,configuration,deploiement,nom,coordinateur,profils,profil_compte=None,*,
                 fondamental,lecteur_ia=None,port=None,etat=None):
        if not isinstance(configuration,ConfigurationFigee) or not isinstance(deploiement,Deploiement):
            raise ErreurOrchestration('configuration et déploiement réels requis')
        if nom not in (REFERENCE,IA) or not isinstance(coordinateur,CoordinateurCompte):
            raise ErreurOrchestration('bras et coordinateur réels requis')
        if not isinstance(fondamental,ControleFondamental):raise ErreurOrchestration('port C05 requis')
        if lecteur_ia is not None and not isinstance(lecteur_ia,LecteurContexte):raise ErreurOrchestration('lecteur IA réel requis')
        if (lecteur_ia is not None and deploiement.mode in ('DEMO','REEL')
                and not lecteur_ia.politique.execution_reelle):raise ErreurOrchestration('politique réelle explicite requise')
        if set(profils)!=set(deploiement.tailles_tick):raise ErreurOrchestration('profils et tailles concordants requis')
        self.configuration=configuration;self.deploiement=deploiement;self.nom=nom
        self.identifiant=_identifiant(configuration,deploiement,nom)
        self.coordinateur=coordinateur;self.fondamental=fondamental;self.lecteur_ia=lecteur_ia;self.port=port
        self._profils=dict(profils);self._profil_compte=profil_compte
        self._signature=_signature(configuration,deploiement,nom);self._empreintes=empreintes_regles(configuration)
        self._strategies={};self._historique=[];self._instant_action=0;self._numero=0;self._intentions_journalisees={};self._suivi={}
        for f in deploiement.fabriques:
            for symbole,tick in deploiement.tailles_tick.items():
                s=f.construire(configuration,{symbole:tick})
                if not isinstance(s,Strategie) or s.identifiant!=f.identifiant:
                    raise ErreurOrchestration('fabrique de stratégie non conforme')
                if any(s is v for v in self._strategies.values()):raise ErreurOrchestration('instance de stratégie partagée')
                self._strategies[f.identifiant,symbole]=s
                self._suivi[f.identifiant,symbole]=dict(bougies=0,derniere_cloture_ms=None,derniere_issue=None,resultat=None)
        if etat is not None:
            _verifier_etat(etat)
            if (not isinstance(etat,EtatBras) or etat.nom!=nom or etat.signature!=self._signature
                    or etat.coordinateur.dernier_ms>coordinateur.etat.dernier_ms):
                raise ErreurOrchestration('état de bras étranger ou futur')
            for tr in etat.historique:
                cle=(tr.identifiant,tr.symbole)
                if cle not in self._strategies:raise ErreurOrchestration('trace de stratégie étrangère')
                if tr.nature=='BOUGIE':
                    resultat=self._bougie(cle,tr.valeur,tr.instant_ms)
                    if resultat!=tr.resultat:raise ErreurOrchestration('stratégie non déterministe ou historique altéré')
                else:self.appliquer_issue(tr.valeur,instant_ms=tr.instant_ms)
            self._numero=etat.numero
            if len({v.cle for v in etat.intentions_journalisees})!=len(etat.intentions_journalisees):
                raise ErreurOrchestration('journal d’intention dupliqué')
            self._intentions_journalisees={v.cle:v for v in etat.intentions_journalisees}

    @property
    def strategies(self):return MappingProxyType(dict(self._strategies))

    @property
    def profils(self):return MappingProxyType(dict(self._profils))

    @property
    def profil_compte(self):return self._profil_compte

    @property
    def calculs(self):return getattr(self.coordinateur,'calculs',None)

    @property
    def etat(self):
        c=self.coordinateur.etat;h=tuple(self._historique);i=tuple(self._intentions_journalisees.values())
        return EtatBras(self.nom,self._signature,c,h,self._numero,i,_empreinte(self.nom,self._signature,c,h,self._numero,i))

    def _temps_action(self,t):
        instant(t)
        if t<self._instant_action or t>self.coordinateur.etat.dernier_ms:raise ErreurOrchestration('causalité de stratégie invalide')
        self._instant_action=t

    def _bougie(self,cle,b,t):
        self._temps_action(t)
        if (not isinstance(b,BougieEnrichie) or b.bougie.symbole!=cle[-1]
                or b.bougie.instant_disponibilite_ms>t):raise ErreurOrchestration('bougie future ou étrangère')
        r=self._strategies[cle].sur_bougie(b)
        if b.unite is UniteTemps.M15:
            if (not isinstance(r,(AbsenceDeSignal,SignalTechnique)) or r.strategie!=cle[0]
                    or r.symbole!=cle[-1] or r.cloture_ms!=b.bougie.fin_ms):
                raise ErreurOrchestration('résultat technique M15 non conforme')
        elif r is not None:raise ErreurOrchestration('aucun signal H1 requis')
        self._historique.append(TraceStrategie(cle[0],cle[-1],'BOUGIE',t,b,r))
        self._suivi[cle]['bougies']+=1;self._suivi[cle]['derniere_cloture_ms']=b.bougie.fin_ms;self._suivi[cle]['resultat']=r
        return r

    def sur_bougie(self,bougie,*,instant_ms=None):
        if not isinstance(bougie,BougieEnrichie):raise ErreurOrchestration('bougie réelle requise')
        t=self.coordinateur.etat.dernier_ms if instant_ms is None else instant_ms
        if bougie.bougie.symbole not in self._profils:raise ErreurOrchestration('symbole non configuré')
        return tuple(self._bougie(cle,bougie,t) for cle in self._strategies if cle[-1]==bougie.bougie.symbole)

    def appliquer_issue(self,issue,*,instant_ms=None):
        if not isinstance(issue,Issue):raise ErreurOrchestration('issue réelle requise')
        cle=(issue.cle.strategie,issue.cle.symbole)
        if cle not in self._strategies:return
        t=self.coordinateur.etat.dernier_ms if instant_ms is None else instant_ms
        self._temps_action(t)
        if issue.instant_ms>t:raise ErreurOrchestration('issue future')
        self._strategies[cle].sur_issue(issue)
        self._historique.append(TraceStrategie(cle[0],cle[-1],'ISSUE',t,issue))
        self._suivi[cle]['derniere_issue']=issue

    def _enveloppe(self,instant_ms):
        self._numero+=1
        return Enveloppe(self.identifiant,self.nom,self.deploiement.mode,self._numero,instant_ms,self._empreintes)

    def alerte(self,code,instant_ms,**donnees):
        return enregistrement(TypeEnregistrement.ALERTE,self._enveloppe(instant_ms),dict(alerte=code,**donnees))

    def journaliser_cloture(self,bougie,resultat,compte,permission=None,version_calendrier=None,snapshot_ia=None):
        if not isinstance(bougie,BougieEnrichie) or bougie.unite is not UniteTemps.M15:
            raise ErreurOrchestration('clôture M15 réelle requise')
        cle=(getattr(resultat,'strategie',None),bougie.bougie.symbole)
        if cle not in self._suivi or self._suivi[cle]['resultat']!=resultat or self._suivi[cle]['derniere_cloture_ms']!=bougie.bougie.fin_ms:
            raise ErreurOrchestration('résultat non observé par le bras')
        i=bougie.indicateurs
        indicateurs={} if i is None else dict(tr=i.tr,atr=i.atr,a=i.a,rang=i.rang)
        vue={k:_journal(v) for k,v in self._suivi[cle].items() if k!='resultat'}
        r=enregistrement_cloture(self._enveloppe(self.coordinateur.etat.dernier_ms),bougie=bougie.bougie,
            resultat=resultat,profil=self._profils[bougie.bougie.symbole],indicateurs=indicateurs,
            etat_strategie=vue,permission=_journal(permission),version_calendrier=_journal(version_calendrier),
            snapshot_ia=_journal(snapshot_ia))
        return enregistrement(r.type,r.enveloppe,{**r.contenu,'compte':_journal(compte),'courtier':_journal(self._profil_compte)})

    def consommer(self,lot,instant,contexte=None):
        lignes=[]
        for issue in lot.issues:
            self.appliquer_issue(issue)
        for trace in lot.traces:
            lignes.append(enregistrement(trace.type,self._enveloppe(instant),dict(trace.donnees)))
        cycles={c.etat.cle:c for c in lot.etat.reprise.cycles}
        for d in lot.etat.intentions:
            if self._intentions_journalisees.get(d.cle)==d: continue
            self._intentions_journalisees[d.cle]=d
            nouvelles=tuple(i for i in lot.issues if i.cle==d.cle)
            i=nouvelles[-1] if nouvelles else None
            cycle=cycles.get(d.cle);plan=cycle.plan if cycle is not None else None
            motif=d.issue.motif if d.issue is not None else None
            permission,version,description=(contexte(d.cle.symbole,instant) if contexte is not None else (None,None,None))
            contenu=dict(cle=d.cle.texte(),empreinte_cle=d.cle.empreinte(self.deploiement.longueur_empreinte),
                strategie=d.cle.strategie,symbole=d.cle.symbole,sens=d.cle.sens.value,
                tentatives=_journal(d.tentatives),issue=_issue(i),issues_nouvelles=tuple(_issue(v) for v in nouvelles),
                derniere_issue=_issue(d.issue),motif=motif.value if motif is not None else None,
                detail=d.issue.detail if d.issue is not None else None,cout_ia_usd=None,
                etat_intention=d.statut.value,signal=_journal(d.signal),
                instrument=_journal(cycle.profil if cycle is not None else self._profils.get(d.cle.symbole)),
                courtier=_journal(self._profil_compte),compte=_journal(lot.compte),
                permission=_journal(permission),version_calendrier=_journal(version),snapshot_ia=_journal(description),
                risque_initial=plan.risque if plan is not None else None,
                budget_gele=plan.budget_gele if plan is not None else None,
                fonds_propres_reference=plan.fonds_propres_reference if plan is not None else None,
                frais_calcules=plan.mesure_risque.frais if plan is not None else None,
                marge_calculee=plan.marge_totale_consideree if plan is not None else None,
                reservations=_journal(lot.etat.reprise.reservations),gardes=_journal(lot.etat.reprise.gardes))
            lignes.append(enregistrement(TypeEnregistrement.INTENTION,self._enveloppe(instant),contenu))
        return SortieMoteur(tuple(lignes),lot.commandes,lot)



def construire_bras(configuration,deploiement,nom,profils,port,fondamental,instant_ms,*,
                     observation=None,base_utc=None,lecteur_ia=None,etat=None,appels_initialisation=None):
    if not isinstance(configuration,ConfigurationFigee) or not isinstance(deploiement,Deploiement):
        raise ErreurOrchestration('configuration de bras requise')
    if etat is not None and not isinstance(etat,EtatBras):raise ErreurOrchestration('état de bras typé requis')
    if etat is not None:_verifier_etat(etat)
    identifiant=_identifiant(configuration,deploiement,nom)
    coordinateur=CoordinateurTrace(configuration.technique,identifiant,profils,port.profil_compte,port,
        fondamental,instant_ms,longueur_empreinte=deploiement.longueur_empreinte,
        contexte=lecteur_ia if nom==IA else None,mode=deploiement.mode,
        etat=etat.coordinateur if etat is not None else None,observation=observation,base_utc=base_utc,
        appels_initialisation=appels_initialisation)
    return Bras(configuration,deploiement,nom,coordinateur,profils,port.profil_compte,
        fondamental=fondamental,lecteur_ia=lecteur_ia,port=port,etat=etat)

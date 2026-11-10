"""Aucun moteur alternatif : entrées, calculs, issues et décisions appartiennent à C09."""
from collections import defaultdict,deque
from dataclasses import dataclass,fields,replace
from datetime import date,time,timedelta
from decimal import Decimal
from itertools import groupby
import json
import re
from types import MappingProxyType
from typing import Mapping
from zoneinfo import ZoneInfo

from xpbots.noyau.c0a_temps import instant_vers_datetime,instant_depuis_datetime
from xpbots.noyau.c0c_configuration import ConfigurationFigee,analyser_export_technique
from xpbots.noyau.c1c_domaine import (SignalTechnique,AbsenceDeSignal,Motif,NatureIssue)
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.execution.c0a_types import EtatIntention
from xpbots.execution.c4_cycle import (NatureCommande,ReponseCourtier,PreuvePersistance)
from xpbots.execution.c5b_reprise import ObservationNative
from xpbots.execution.c6_coordinateur import LotCoordinateur
from xpbots.orchestration.c0_contrats import Deploiement,FabriqueStrategie,MiseAJourBras,REFERENCE,IA
from xpbots.orchestration.c1_bras import construire_bras
from xpbots.orchestration.c2_moteur import MoteurDecision
from xpbots.contexte_ia.c0_types import charger_parametres,PolitiqueVeto
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.london.c2_moteur import fabriquer_strategie
from xpbots.rejeu.c0a_types import (ErreurRejeu,ManifesteTicks,ConditionContrat,EcartRejeu,
    FactureIA,entier,texte)
from xpbots.rejeu.c0b_protocole import BlocC10,charger_protocole
from xpbots.rejeu.c1a_ticks import analyser_lignes_ticks,jours_marche
from xpbots.rejeu.c1b_simulateur import SimulateurExecution

_FOREX_C09=frozenset({'EURUSD','GBPUSD'})


def symboles_forex_c09():return _FOREX_C09


def _figer(v):
    if isinstance(v,Mapping):return MappingProxyType({k:_figer(x) for k,x in v.items()})
    if isinstance(v,(tuple,list)):return tuple(_figer(x) for x in v)
    return v


def _json(v):
    if isinstance(v,Mapping):return {k:_json(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [_json(x) for x in v]
    if isinstance(v,(date,time)):return v.isoformat()
    return v


@dataclass(frozen=True)
class SourceTicks:
    manifeste:ManifesteTicks
    lire:object
    def __post_init__(self):
        if not isinstance(self.manifeste,ManifesteTicks) or not callable(self.lire):
            raise ErreurRejeu('manifeste et lecteur différé requis')


@dataclass(frozen=True)
class AutorisationReserve:
    option_expresse:bool
    empreinte_robot:str
    verifier_gel:object
    def __post_init__(self):
        if (type(self.option_expresse) is not bool or type(self.empreinte_robot) is not str
                or re.fullmatch('[0-9a-f]{64}',self.empreinte_robot) is None or not callable(self.verifier_gel)):
            raise ErreurRejeu('option, empreinte et port d’attestation du gel requis')


class RegistreReserve:
    def __init__(self):self._empreinte=None;self._historique=[]
    @property
    def historique(self):return tuple(self._historique)
    def verifier(self,intervalle,protocole,autorisation,identifiant):
        reserve=next(b for b in protocole.blocs if b.usage=='RESERVE').intervalle_ms
        if max(intervalle.debut_ms,reserve.debut_ms)>=min(intervalle.fin_ms,reserve.fin_ms):return
        valide=(isinstance(autorisation,AutorisationReserve) and autorisation.option_expresse)
        if valide:
            try:valide=autorisation.verifier_gel(autorisation.empreinte_robot) is True
            except Exception:valide=False
        empreinte=autorisation.empreinte_robot if isinstance(autorisation,AutorisationReserve) else None
        if not valide or self._empreinte is not None and self._empreinte!=empreinte:
            self._historique.append(_figer(dict(action='REFUS_RESERVE',experience=identifiant,empreinte=empreinte)))
            raise ErreurRejeu('test réservé verrouillé : option et gel attesté requis, empreinte stable')
        action='OUVERTURE_RESERVE' if self._empreinte is None else 'CONSULTATION_RESERVE'
        self._empreinte=empreinte
        self._historique.append(_figer(dict(action=action,experience=identifiant,empreinte=empreinte)))


@dataclass(frozen=True)
class DemandeRejeu:
    identifiant:str
    bloc:BlocC10
    scenario:str
    mode:str
    longueur_empreinte:int
    autorisation:AutorisationReserve|None=None
    ecart:EcartRejeu|None=None
    def __post_init__(self):
        texte(self.identifiant);texte(self.scenario);texte(self.mode);entier(self.longueur_empreinte,1)
        if not isinstance(self.bloc,BlocC10) or self.ecart is not None and not isinstance(self.ecart,EcartRejeu):
            raise ErreurRejeu('bloc et écart de recherche typés requis')


@dataclass(frozen=True)
class ControlesRejeu:
    fondamental:object=None
    source_fondamentale:object=None
    lecteur_ia:object=None
    source_ia:object=None
    scenario:str|None=None
    @classmethod
    def technique_neutre(cls,configuration):
        return cls(lecteur_ia=LecteurContexte(charger_parametres(configuration),PolitiqueVeto(True)),
            scenario=ControleTechniqueNeutre.scenario)


class StockageMemoireRejeu:
    def __init__(self):self.dernier_lot=None
    def persister(self,lot):
        if not isinstance(lot,LotCoordinateur):raise ErreurRejeu('lot réel requis')
        if self.dernier_lot is not None and lot.etat.revision<self.dernier_lot.etat.revision:
            raise ErreurRejeu('révision de stockage en recul')
        self.dernier_lot=lot
        return PreuvePersistance(lot.etat.revision,tuple(c.reference for c in lot.preparations))


@dataclass(frozen=True)
class ResultatPilote:
    nombre_ticks:int
    enregistrements:tuple
    reponses:object
    entrees:tuple
    initialisation_calculs:tuple
    gardes:object


def piloter(ticks,moteur,executions,stockages=None,fin_exclusive_ms=None):
    moteur=getattr(moteur,'moteur',moteur)
    if not isinstance(moteur,MoteurDecision):raise ErreurRejeu('moteur commun réel requis')
    executions=dict(executions)
    stockages=dict(stockages) if stockages is not None else {n:StockageMemoireRejeu() for n in executions}
    if (set(executions)!=set(moteur.bras) or set(stockages)!=set(executions)
            or len({id(p) for p in executions.values()})!=len(executions)
            or len({id(p) for p in stockages.values()})!=len(stockages)
            or any(not isinstance(p,SimulateurExecution) for p in executions.values())):
        raise ErreurRejeu('simulateurs et stockages indépendants concordants requis')
    modele=next(iter(executions.values())).scenario
    if any(p.scenario!=modele for p in executions.values()):raise ErreurRejeu('mêmes coûts requis dans les deux bras')
    lignes=[];reponses={n:[] for n in executions};gardes={n:[] for n in executions}
    contextes={n:set() for n in executions};nombre=0;precedent=None
    initialisation=moteur.initialisation_calculs
    def transmettre(sortie,t):
        file=deque((sortie,))
        while file:
            s=file.popleft();lignes.extend(s.enregistrements)
            evenements={n:[] for n in executions};preuves={};entrees={}
            for n,v in s.sorties:
                if v.lot is not None:
                    g=v.lot.etat.reprise.gardes
                    if g is not None and (not gardes[n] or gardes[n][-1][1]!=g):gardes[n].append((t,g))
                evenements[n].extend(executions[n].soumettre(c for c in v.commandes if c.nature is not NatureCommande.ENTREE))
            for n,v in s.sorties:
                try:preuve=stockages[n].persister(v.lot) if v.lot is not None else None
                except (OSError,ValueError):
                    preuve=None;lignes.append(moteur.bras[n].alerte('STOCKAGE_REJEU_INDISPONIBLE',t))
                if preuve is not None:
                    entrees[n]=tuple(c for c in v.commandes if c.nature is NatureCommande.ENTREE)
                    if v.lot.preparations:preuves[n]=preuve
                    dossiers={d.cle:d for d in v.lot.etat.intentions}
                    for c in entrees[n]:
                        if c.cle not in contextes[n]:
                            executions[n].enregistrer_contexte(c.cle,dossiers[c.cle].signal.contexte)
                            contextes[n].add(c.cle)
            for n,commandes in entrees.items():evenements[n].extend(executions[n].soumettre(commandes))
            maj={}
            for n,ev in evenements.items():
                if not ev:continue
                r=tuple(v for v in ev if isinstance(v,ReponseCourtier));reponses[n].extend(r)
                observation=next((v for v in reversed(ev) if isinstance(v,ObservationNative)),None)
                maj[n]=MiseAJourBras(r,observation,executions[n].base_utc())
            if maj:file.append(moteur.traiter_evenement(t,mises_a_jour=maj))
            elif preuves:file.append(moteur.confirmer_persistance(preuves,t))
    def prochaine():
        dates=[moteur.prochaine_echeance_ms]+[p.prochaine_echeance_ms for p in executions.values()]
        return min((t for t in dates if t is not None),default=None)
    def minuteries_avant(borne):
        derniere_echeance=None
        while (e:=prochaine()) is not None and e<borne:
            if derniere_echeance is not None and e<=derniere_echeance:raise ErreurRejeu('minuterie sans progression')
            derniere_echeance=e;maj={}
            for n,p in executions.items():
                r=p.extraire_reponses(e);reponses[n].extend(r);maj[n]=MiseAJourBras(r,base_utc=p.base_utc())
            transmettre(moteur.traiter_evenement(e,mises_a_jour=maj),e)
    for t,groupe in groupby(ticks,key=lambda v:v.instant_reception_ms):
        groupe=tuple(groupe)
        if precedent is not None and t<=precedent:raise ErreurRejeu('groupes de ticks non chronologiques')
        precedent=t;minuteries_avant(t)
        maj={};decision=None
        for n,p in executions.items():
            r=tuple(v for tick in groupe for v in p.sur_tick(tick));reponses[n].extend(r)
            maj[n]=MiseAJourBras(r,base_utc=p.base_utc())
            q=tuple(p.tick_decision(v) for v in groupe)
            if decision is not None and q!=decision:raise ErreurRejeu('cotations de décision différentes entre bras')
            decision=q
        nombre+=len(groupe);transmettre(moteur.traiter_ticks(decision,mises_a_jour=maj),t)
    if fin_exclusive_ms is not None:
        entier(fin_exclusive_ms,1)
        if precedent is not None and fin_exclusive_ms<=precedent:raise ErreurRejeu('borne finale antérieure aux ticks')
        minuteries_avant(fin_exclusive_ms)
        t=fin_exclusive_ms-1
        if precedent is None or t>max(p.instant_ms for p in executions.values()):
            maj={}
            for n,p in executions.items():
                r=p.extraire_reponses(t);reponses[n].extend(r);maj[n]=MiseAJourBras(r,base_utc=p.base_utc())
            transmettre(moteur.traiter_evenement(t,mises_a_jour=maj),t)
    return ResultatPilote(nombre,tuple(lignes),_figer(reponses),moteur.entrees,initialisation,_figer(gardes))


def appliquer_ecart(configuration,ecart,mode):
    if not isinstance(configuration,ConfigurationFigee):raise ErreurRejeu('configuration chargée requise')
    if ecart is None:return configuration
    p=charger_protocole(configuration)
    if mode!='REJEU' or not isinstance(ecart,EcartRejeu) or (ecart.nom,ecart.champ,ecart.valeur) not in p.perturbations:
        raise ErreurRejeu('écart non prescrit ou usage hors rejeu')
    c=configuration.technique
    commun={f.name:getattr(c.commun,f.name) for f in fields(c.commun)}
    london=dict(c.london);ema=dict(c.ema)
    if ecart.champ=='OBJECTIF':
        for methode in (london,ema):
            methode['take_profit_gross_price_r']=float(Decimal(str(methode['take_profit_gross_price_r']))*ecart.valeur)
    elif ecart.champ=='BUFFER':
        commun['structural_buffer_atr']=float(Decimal(str(commun['structural_buffer_atr']))*ecart.valeur)
    else:commun['max_position_wallclock_seconds']=ecart.valeur
    octets=json.dumps(_json(dict(common=commun,london=london,ema=ema)),ensure_ascii=False,
        allow_nan=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    return ConfigurationFigee(analyser_export_technique(octets),configuration.ia)


@dataclass(frozen=True)
class ComptageRejeu:
    configurations:int
    signaux:int
    refus:object
    entrees_jours:object
    @property
    def entrees(self):return sum(self.entrees_jours.values())


@dataclass(frozen=True)
class ResultatBrasRejeu:
    nom:str
    trades:tuple
    courbe:tuple
    premiers_remplissages:tuple
    positions_ouvertes:tuple
    comptages:object
    historique:tuple
    etat:object
    gardes:tuple
    reponses:tuple


@dataclass(frozen=True)
class ResultatExperience:
    demande:DemandeRejeu
    usage:str
    debut_effectif_ms:int
    configuration_origine:ConfigurationFigee
    configuration:ConfigurationFigee
    manifeste:ManifesteTicks
    jours:tuple
    bras:object
    pilote:ResultatPilote
    journal_protocole:tuple
    factures:tuple
    initiales:object
    couverture_complete:bool
    jours_forex:tuple
    regime_fondamental:str
    conditions:tuple=()
    @property
    def complet(self):
        terminaux=(EtatIntention.CLOTUREE,EtatIntention.REFUSEE,EtatIntention.EXPIREE)
        return self.couverture_complete and all(not b.positions_ouvertes
            and all(c.etat.statut in terminaux for c in b.etat.coordinateur.reprise.cycles)
            for b in self.bras.values())


class _StrategieMesuree:
    def __init__(self,primaire,ombre,debut,fin,collecteur,duree_m15):
        self.identifiant=primaire.identifiant;self._primaire=primaire;self._ombre=ombre
        self._debut=debut;self._fin=fin;self._collecteur=collecteur;self._duree=duree_m15
    def sur_issue(self,issue):return self._primaire.sur_issue(issue)
    def sur_bougie(self,b):
        r=self._primaire.sur_bougie(b);brut=self._ombre.sur_bougie(b)
        if b.bougie.duree_ms!=self._duree:return r
        t=b.bougie.fin_ms;cle=(self.identifiant,b.bougie.symbole)
        if self._debut<=t<self._fin:
            n=self._collecteur.setdefault(cle,[0,0])
            n[0]+=isinstance(brut,SignalTechnique);n[1]+=isinstance(r,SignalTechnique)
            return r
        contexte={**getattr(r,'contexte',{}),'prechargement':True,
            'signal_technique_prechargement':isinstance(r,SignalTechnique)}
        return AbsenceDeSignal(self.identifiant,b.bougie.symbole,t,Motif.WARMUP,'M15_INSUFFISANTES',contexte)


def _fabriques_mesurees(fabriques,debut,fin,collecteur,commun):
    duree=timedelta(seconds=commun.timeframe_seconds)//timedelta(milliseconds=1)
    def envelopper(f):
        def construire(c,t):
            primaire=f.construire(c,t);ombre=f.construire(c,t)
            if primaire is ombre:raise ErreurRejeu('fabrique sans instances indépendantes pour la mesure technique')
            return _StrategieMesuree(primaire,ombre,debut,fin,collecteur(),duree)
        return FabriqueStrategie(f.identifiant,construire)
    return tuple(envelopper(f) for f in fabriques)


def _debut_et_usage(demande,protocole):
    debut=demande.bloc.intervalle_ms.debut_ms
    diagnostic=next(b for b in protocole.blocs if b.usage=='DIAGNOSTIC')
    # C10 fixe le premier bilan, puis prolonge la collecte selon les effectifs.
    if demande.bloc.debut>=protocole.prospectif.debut:return debut,protocole.prospectif.usage
    for bloc in protocole.blocs:
        if bloc.debut<=demande.bloc.debut and demande.bloc.fin_exclusive<=bloc.fin_exclusive:
            if bloc.usage=='DIAGNOSTIC':
                d=protocole.debut_diagnostic_v3
                debut=max(debut,instant_depuis_datetime(instant_vers_datetime(debut).replace(year=d.year,month=d.month,day=d.day)))
            return debut,bloc.usage
    if max(demande.bloc.debut,diagnostic.debut)<min(demande.bloc.fin_exclusive,diagnostic.fin_exclusive):
        return debut,'CONTINU_AVEC_DIAGNOSTIC'
    return debut,'HORS_PROTOCOLE'


def executer_experience(configuration,demande,source,conditions,fabriques=None,
        fabrique_controles=None,registre_reserve=None,factures=()):
    if (not isinstance(configuration,ConfigurationFigee) or not isinstance(demande,DemandeRejeu)
            or not isinstance(source,SourceTicks)):
        raise ErreurRejeu('configuration, demande et source typées requises')
    protocole=charger_protocole(configuration)
    try:scenario=protocole.scenario(demande.scenario)
    except ValueError as e:raise ErreurRejeu('scénario de coûts absent du protocole') from e
    if demande.mode not in ('REJEU',configuration.ia.parametres['default_evaluation_mode']):
        raise ErreurRejeu('expérience refusée hors des modes de rejeu')
    derivee=appliquer_ecart(configuration,demande.ecart,demande.mode)
    registre=registre_reserve if registre_reserve is not None else RegistreReserve()
    # Ces deux gardes précèdent le lecteur ET l'itération de ses lignes.
    registre.verifier(demande.bloc.intervalle_ms,protocole,demande.autorisation,demande.identifiant)
    registre.verifier(source.manifeste.intervalle,protocole,demande.autorisation,demande.identifiant)
    debut,usage=_debut_et_usage(demande,protocole);fin=demande.bloc.intervalle_ms.fin_ms
    if debut>=fin:raise ErreurRejeu('diagnostic sans période V3 exploitable')
    if source.manifeste.intervalle.debut_ms>debut or source.manifeste.intervalle.fin_ms<fin:
        raise ErreurRejeu('manifeste ne couvrant pas la période demandée')
    if not callable(fabrique_controles):raise ErreurRejeu('fabrique C05 ou scénario neutre nommé explicitement requis')
    conditions=tuple(conditions)
    if not conditions or any(not isinstance(c,ConditionContrat) for c in conditions):raise ErreurRejeu('conditions datées requises')
    grilles=defaultdict(set)
    for c in conditions:grilles[c.profil.symbole].add(c.profil.tick_size)
    if any(len(v)!=1 for v in grilles.values()):
        raise ErreurRejeu('grille technique historique variable : fabrique non qualifiée pour ce changement')
    factures=tuple(factures)
    if any(not isinstance(f,FactureIA) for f in factures):raise ErreurRejeu('factures originales requises')
    audit=[_figer(dict(action='PROTOCOLE_FIXE_AVANT_LECTURE',experience=demande.identifiant,
        scenario=scenario,bloc=demande.bloc,usage=usage,origine=configuration.technique.empreinte_canonique,
        derivee=derivee.technique.empreinte_canonique,ecart=demande.ecart))]
    historique=analyser_lignes_ticks(source.lire(),source.manifeste)
    ticks=tuple(t for t in historique if t.instant_reception_ms<fin)
    if not ticks or ticks[-1].instant_reception_ms<debut:raise ErreurRejeu('aucun tick dans la période demandée')
    premier=ticks[0].instant_reception_ms
    if premier>debut:raise ErreurRejeu('passé de préchargement absent avant la période')
    creation=instant_depuis_datetime(instant_vers_datetime(premier).replace(hour=0,minute=0,second=0,microsecond=0))
    controles=fabrique_controles(premier)
    if not isinstance(controles,ControlesRejeu):raise ErreurRejeu('composition de contrôles typée requise')
    if controles.scenario==ControleTechniqueNeutre.scenario and controles.fondamental is None:
        fond=ControleTechniqueNeutre()
    elif controles.scenario is None and isinstance(controles.fondamental,PermissionsFondamentales):fond=controles.fondamental
    else:raise ErreurRejeu('choix exclusif C05 réel ou contrôle technique neutre nommé requis')
    ab=demande.mode==configuration.ia.parametres['default_evaluation_mode']
    if ab and not isinstance(controles.lecteur_ia,LecteurContexte):raise ErreurRejeu('lecteur réel requis pour le bras IA')
    fabriques=tuple(fabriques) if fabriques is not None else (
        FabriqueStrategie(derivee.technique.london['strategy_id'],fabriquer_strategie),)
    noms=(REFERENCE,IA) if ab else (REFERENCE,)
    ports={};bras=[];collecteurs={};initiales={};symboles=set(source.manifeste.symboles)
    if set(grilles)!=symboles:raise ErreurRejeu('conditions et manifeste de symboles discordants')
    tailles={s:next(iter(grilles[s])) for s in source.manifeste.symboles}
    courant={}
    d=Deploiement(demande.identifiant,demande.mode,
        _fabriques_mesurees(fabriques,debut,fin,lambda:courant['collecteur'],derivee.technique.commun),tailles,demande.longueur_empreinte)
    for nom in noms:
        p=SimulateurExecution(derivee,conditions,creation,scenario);p.avancer_au(premier);ports[nom]=p
        collecteurs[nom]={}
        courant['collecteur']=collecteurs[nom]
        observation=p.observation();base=p.base_utc()
        initiales[nom]=(p.profils,p.profil_compte,premier,observation,base)
        bras.append(construire_bras(derivee,d,nom,p.profils,p,fond,premier,
            observation=observation,base_utc=base,lecteur_ia=controles.lecteur_ia if nom==IA else None))
    m=source.manifeste
    moteur=MoteurDecision(derivee,bras,m.horaires,{s:m.couverture for s in m.symboles},
        controle_fondamental=controles.fondamental,lecteur_ia=controles.lecteur_ia,
        source_fondamentale=controles.source_fondamentale,source_ia=controles.source_ia,
        scenario_fondamental=controles.scenario)
    r=piloter(ticks,moteur,ports,fin_exclusive_ms=fin)
    fenetres={}
    definitions=[p for p in (derivee.technique.london,derivee.technique.ema) if any(f.identifiant==p['strategy_id'] for f in fabriques)]
    if not definitions:raise ErreurRejeu('fenêtre de la méthode inconnue du protocole')
    for s in source.manifeste.symboles:
        fenetres[s]=(min(p['session_start_local'] for p in definitions),max(p['entry_end_local_exclusive'] for p in definitions))
    def panel(fenetres):
        return tuple(j for j in jours_marche(m,demande.bloc.nom,fenetres,derivee.technique.commun)
            if instant_vers_datetime(debut).date()<=j.jour<demande.bloc.fin_exclusive) if fenetres else ()
    jours=panel(fenetres);jours_forex=panel({s:f for s,f in fenetres.items() if s in _FOREX_C09})
    zone=ZoneInfo(derivee.technique.commun.session_timezone);resultats={}
    for b in bras:
        p=ports[b.nom];etat=b.etat;comptages={}
        for f in fabriques:
            for s in m.symboles:
                cle=(f.identifiant,s);configurations,signaux=collecteurs[b.nom].get(cle,(0,0))
                refus=defaultdict(int);vues=set()
                for tr in etat.historique:
                    if tr.nature!='ISSUE' or (tr.identifiant,tr.symbole)!=cle:continue
                    i=tr.valeur
                    if i.instant_ms<debut or i.nature not in (NatureIssue.REFUSEE,NatureIssue.EXPIREE) or i.motif is None:continue
                    k=(i.cle,i.instant_ms,i.motif)
                    if k not in vues:refus[i.motif.value]+=1;vues.add(k)
                for dossier in etat.coordinateur.intentions:
                    if (dossier.cle.strategie,dossier.cle.symbole)!=cle:continue
                    for tentative in dossier.tentatives:
                        if tentative.instant_ms<debut or tentative.cause not in (Motif.SPREAD_CAP.value,Motif.ENTRY_GAP.value):continue
                        k=(dossier.cle,tentative.instant_ms,Motif(tentative.cause))
                        if k not in vues:refus[tentative.cause]+=1;vues.add(k)
                entrees=defaultdict(int)
                for k,t in p.premiers_remplissages:
                    if (k.strategie,k.symbole)==cle and debut<=t<fin:
                        entrees[instant_vers_datetime(t).astimezone(zone).date()]+=1
                comptages[cle]=ComptageRejeu(configurations,signaux,_figer(refus),_figer(entrees))
        resultats[b.nom]=ResultatBrasRejeu(b.nom,p.trades,p.courbe,p.premiers_remplissages,
            p.positions_ouvertes,_figer(comptages),etat.historique,etat,r.gardes[b.nom],r.reponses[b.nom])
    audit.extend(registre.historique)
    couverture_complete=True
    for h in m.horaires.values():
        if h.debut_validite_ms>debut or h.fin_validite_ms<fin:
            couverture_complete=False;continue
        bornes=sorted({debut,fin}|{max(debut,min(fin,t)) for i in h.seances+h.fermetures+m.couverture
            for t in (i.debut_ms,i.fin_ms)})
        for a,b in zip(bornes,bornes[1:]):
            if h.ouvert_a(a) and not any(i.debut_ms<=a and b<=i.fin_ms for i in m.couverture):couverture_complete=False
    return ResultatExperience(demande,usage,debut,configuration,derivee,m,jours,_figer(resultats),r,
        tuple(audit),factures,_figer(initiales),couverture_complete,
        jours_forex,controles.scenario or 'PERMISSIONS_EXTERNES',
        tuple(sorted(conditions,key=lambda c:(c.profil.symbole,c.debut_ms,c.fin_ms,c.connu_ms))))


class _PortSansBackend:
    def __init__(self,profil_compte):self.profil_compte=profil_compte
    def _interdit(self,*a,**k):raise AssertionError('backend consulté pendant le rejeu du journal')
    profit=marge=frais_aller_retour=frais_sortie=controler=specifications=etat_compte=_interdit


def rejouer_experience(resultat,fabriques=None,fabrique_controles=None):
    if not isinstance(resultat,ResultatExperience) or not callable(fabrique_controles):
        raise ErreurRejeu('expérience et fabrique de contrôles frais requises')
    c=resultat.configuration;demande=resultat.demande
    _,_,premier,_,_=next(iter(resultat.initiales.values()))
    controles=fabrique_controles(premier)
    fond=controles.fondamental if controles.fondamental is not None else ControleTechniqueNeutre()
    fabriques=tuple(fabriques) if fabriques is not None else (FabriqueStrategie(c.technique.london['strategy_id'],fabriquer_strategie),)
    profils=next(iter(resultat.initiales.values()))[0]
    courant={}
    d=Deploiement(demande.identifiant,demande.mode,
        _fabriques_mesurees(fabriques,resultat.debut_effectif_ms,demande.bloc.intervalle_ms.fin_ms,
            lambda:courant['collecteur'],c.technique.commun),{s:p.tick_size for s,p in profils.items()},demande.longueur_empreinte)
    bras=[];appels=dict(resultat.pilote.initialisation_calculs)
    for nom,(profils,compte,t,observation,base) in resultat.initiales.items():
        courant['collecteur']={}
        bras.append(construire_bras(c,d,nom,profils,_PortSansBackend(compte),fond,t,
            observation=observation,base_utc=base,lecteur_ia=controles.lecteur_ia if nom==IA else None,
            appels_initialisation=appels[nom]))
    m=resultat.manifeste
    moteur=MoteurDecision(c,bras,m.horaires,{s:m.couverture for s in m.symboles},
        controle_fondamental=controles.fondamental,lecteur_ia=controles.lecteur_ia,scenario_fondamental=controles.scenario)
    lignes=tuple(e for j in resultat.pilote.entrees for e in moteur.rejouer(j).enregistrements)
    return lignes,moteur.entrees,_figer({b.nom:b.etat for b in bras})


def executer_blocs(configuration,demandes,sources,conditions,**options):
    demandes=tuple(demandes)
    registre=options.pop('registre_reserve',None) or RegistreReserve()
    return tuple(executer_experience(configuration,d,sources[d.bloc.nom],conditions,
        registre_reserve=registre,**options) for d in demandes)


def executer_continu(configuration,demande,source,conditions,**options):
    if demande.bloc!=charger_protocole(configuration).continu:raise ErreurRejeu('bloc continu C10 exact requis')
    return executer_experience(configuration,demande,source,conditions,**options)


def executer_perturbations(configuration,demande,source,conditions,**options):
    if demande.mode!='REJEU' or demande.ecart is not None:raise ErreurRejeu('base de diagnostic en rejeu sans écart préalable requise')
    return tuple(executer_experience(configuration,replace(demande,
        identifiant=demande.identifiant+':'+nom,ecart=EcartRejeu(nom,champ,valeur)),source,conditions,**options)
        for nom,champ,valeur in charger_protocole(configuration).perturbations)

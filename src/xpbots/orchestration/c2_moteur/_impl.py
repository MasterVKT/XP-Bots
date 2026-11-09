"""Un seul chemin de décision pour la réception, les minuteries et le rejeu."""
from dataclasses import dataclass,fields,is_dataclass
from datetime import date,datetime
from decimal import Decimal
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Mapping
from xpbots.orchestration.c0_contrats import (ErreurOrchestration,EntreeMoteur,EntreeJournalisee,
    MiseAJourBras,SortieMoteur,SortieEvenement,REFERENCE,IA,instant)
from xpbots.orchestration.c1_bras import Bras
from xpbots.donnees.c0a_types import BougieEnrichie,ChangementTrou,UniteTemps
from xpbots.donnees.c1c_couverture import RegistreCouverture
from xpbots.donnees.c3_flux import FluxBougies
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.noyau.c1a_marche import Cotation
from xpbots.noyau.c1c_domaine import SignalTechnique


def _valeur(v):
    if isinstance(v,Enum):return v.value
    if isinstance(v,(Decimal,date,datetime)):return str(v)
    if isinstance(v,bytes):return {'octets':v.hex()}
    if is_dataclass(v):return {f.name:_valeur(getattr(v,f.name)) for f in fields(v)}
    if isinstance(v,Mapping):return {str(k):_valeur(x) for k,x in v.items()}
    if isinstance(v,(set,frozenset)):return sorted((_valeur(x) for x in v),key=str)
    if isinstance(v,(tuple,list)):return [_valeur(x) for x in v]
    return v


def _sceau(v):
    return hashlib.sha256(json.dumps(_valeur(v),sort_keys=True,separators=(',',':'),
        ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class EtatMoteur:
    signature:str
    instant_ms:int
    entrees:tuple
    flux:tuple
    bras:tuple
    fondamental:object
    ia:object
    empreinte:str

    def verifier(self):
        instant(self.instant_ms)
        if self.empreinte!=_sceau(tuple(getattr(self,f.name) for f in fields(self) if f.name!='empreinte')):
            raise ErreurOrchestration('photographie du moteur altérée')


class MoteurDecision:
    def __init__(self,configuration,bras,horaires,periodes_couvertes,*,controle_fondamental=None,
                 lecteur_ia=None,source_fondamentale=None,source_ia=None,scenario_fondamental=None,etat=None):
        bras=tuple(bras)
        if not bras or any(not isinstance(b,Bras) or b.calculs is None for b in bras):
            raise ErreurOrchestration('bras réels avec calculs tracés requis')
        self.bras=MappingProxyType({b.nom:b for b in bras});self.configuration=configuration
        d=bras[0].deploiement
        if len(self.bras)!=len(bras) or any(b.configuration!=configuration or b.deploiement!=d for b in bras):
            raise ErreurOrchestration('déploiement commun et noms de bras uniques requis')
        ab=d.mode==configuration.ia.parametres['default_evaluation_mode']
        if (ab and (set(self.bras)!={REFERENCE,IA} or not isinstance(lecteur_ia,LecteurContexte))) or (not ab and len(bras)!=1):
            raise ErreurOrchestration('composition incompatible avec le mode')
        objets=[id(s) for b in bras for s in b.strategies.values()]
        if (len(set(objets))!=len(objets) or len({id(b.coordinateur) for b in bras})!=len(bras)
                or len({id(b.port) for b in bras})!=len(bras)):
            raise ErreurOrchestration('comptes ou stratégies partagés entre bras')
        if set(horaires)!=set(periodes_couvertes) or any(set(b.profils)!=set(horaires) for b in bras):
            raise ErreurOrchestration('symboles de marché et profils concordants requis')
        if controle_fondamental is None:
            if scenario_fondamental!=ControleTechniqueNeutre.scenario or any(not isinstance(b.fondamental,ControleTechniqueNeutre) for b in bras):
                raise ErreurOrchestration('C05 réel ou scénario neutre explicite requis')
        elif (not isinstance(controle_fondamental,PermissionsFondamentales) or scenario_fondamental is not None
                or any(b.fondamental is not controle_fondamental for b in bras)):
            raise ErreurOrchestration('contrôle C05 commun réel requis')
        if lecteur_ia is not None and not isinstance(lecteur_ia,LecteurContexte):raise ErreurOrchestration('lecteur IA réel requis')
        if any(b.lecteur_ia is not lecteur_ia for b in bras if b.nom==IA):raise ErreurOrchestration('lecteur du bras IA différent')
        self._fond=controle_fondamental;self._ia=lecteur_ia;self._scenario=scenario_fondamental
        self._sources=(source_fondamentale,source_ia)
        for source,attribut,cible in ((source_fondamentale,'controle',controle_fondamental),(source_ia,'lecteur',lecteur_ia)):
            if source is not None and (cible is None or getattr(source,attribut,None) is not cible or not callable(getattr(source,'extraire',None))):
                raise ErreurOrchestration('source externe liée au contrôle requise')
        dates={b.coordinateur.etat.dernier_ms for b in bras}
        if len(dates)!=1:raise ErreurOrchestration('horloges de bras différentes')
        self._instant=dates.pop();self._entrees=[];self._valide=True
        if any(c is not None and c.etat.dernier_ms>self._instant for c in (self._fond,self._ia)):
            raise ErreurOrchestration('contrôle futur au démarrage')
        self._signature=_sceau((configuration.technique.empreinte_canonique,configuration.ia.empreinte_canonique,
            tuple(b.etat.signature for b in bras),horaires,periodes_couvertes,scenario_fondamental))
        self._flux={s:FluxBougies(s,configuration.technique,horaires[s],RegistreCouverture(periodes_couvertes[s])) for s in horaires}
        if etat is not None:
            if not isinstance(etat,EtatMoteur):raise ErreurOrchestration('état moteur typé requis')
            etat.verifier()
            if etat.signature!=self._signature or etat.instant_ms!=self._instant:
                raise ErreurOrchestration('état moteur étranger ou horloges différentes')
            if etat.fondamental!=self._etat_controle(self._fond) or etat.ia!=self._etat_controle(self._ia):
                raise ErreurOrchestration('contrôles non restaurés')
            if len(etat.bras)!=len(bras) or any((a.nom,a.signature,a.historique,a.numero,a.intentions_journalisees)!=
                    (b.etat.nom,b.etat.signature,b.etat.historique,b.etat.numero,b.etat.intentions_journalisees)
                    for a,b in zip(etat.bras,bras)):
                raise ErreurOrchestration('bras non restaurés')
            if tuple(s for s,_ in etat.flux)!=tuple(horaires):raise ErreurOrchestration('flux étrangers')
            self._flux={s:FluxBougies.reprendre(json.loads(v),configuration.technique,horaires[s],RegistreCouverture(periodes_couvertes[s])) for s,v in etat.flux}
            self._entrees=list(etat.entrees)
            if any(not isinstance(e,EntreeJournalisee) or e.entree.numero!=i+1 or e.entree.instant_ms>self._instant for i,e in enumerate(self._entrees)):
                raise ErreurOrchestration('journal de reprise incohérent')

    @staticmethod
    def _etat_controle(c):return None if c is None else c.etat

    def _verifier(self):
        if not self._valide:raise ErreurOrchestration('moteur invalidé ; reprise requise')

    @property
    def entrees(self):return tuple(self._entrees)

    @property
    def initialisation_calculs(self):return tuple((n,b.calculs.initialisation) for n,b in self.bras.items())

    @property
    def etat(self):
        self._verifier()
        v=(self._signature,self._instant,self.entrees,
            tuple((s,json.dumps(f.exporter_etat(),sort_keys=True,separators=(',',':'))) for s,f in self._flux.items()),
            tuple(b.etat for b in self.bras.values()),self._etat_controle(self._fond),self._etat_controle(self._ia))
        return EtatMoteur(*v,_sceau(v))

    @property
    def prochaine_echeance_ms(self):
        self._verifier();dates=[b.coordinateur.prochaine_echeance_ms for b in self.bras.values()]
        dates.extend(c.prochaine_echeance_ms(self._instant) for c in (self._fond,self._ia) if c is not None)
        dates.extend(s.prochaine_reception_ms for s in self._sources if s is not None)
        return min((t for t in dates if t is not None),default=None)

    def _contexte(self,nom,symbole,t):
        if self._fond is None:permission,version={'scenario':self._scenario},None
        else:
            e=self._fond.etat;h=[v for v in e.permissions.historique if v.symbole==symbole and v.instant_ms<=t]
            permission=dict(permission=next((v for v in reversed(h) if hasattr(v,'message')),None),dernier_evenement=h[-1] if h else None)
            version=next((v for v in reversed(e.calendrier.versions) if v.reception_ms<=t),None)
        return permission,version,self._ia.description(symbole,t) if self._ia is not None and nom==IA else None

    def _recevoir(self,e):
        traces=[];t=e.instant_ms
        for p in e.receptions:
            if p.nature=='SNAPSHOT':r=self._ia.recevoir(p.octets,t)
            elif p.nature=='PERMISSION':r=self._fond.recevoir_permission(p.symbole,p.octets,t)
            elif p.nature=='CALENDRIER':r=self._fond.recevoir_calendrier(p.octets,t,p.table)
            else:
                r=self._fond.interrompre(p.symbole,t)
                traces.append(dict(code='PERMISSION_INTERROMPUE',symbole=p.symbole,change=r,instant_ms=t));continue
            statut='ACCEPTE' if r.acceptee else 'RELU' if r.ignoree else 'REJETE'
            trace=dict(code=p.nature+'_'+statut,raison=r.raison,symbole=p.symbole)
            if p.nature=='PERMISSION':trace['sequence']=r.permission.message.sequence if r.permission else None
            if p.nature=='CALENDRIER':trace['version']=r.version.version if r.version else None
            if p.nature=='SNAPSHOT':trace.update(sequence=r.snapshot.snapshot.sequence if r.snapshot else None,ajoutes=r.ajoutes)
            traces.append(trace)
        if self._fond is not None:
            traces.extend(dict(code=v.nature,**{f.name:getattr(v,f.name) for f in fields(v)}) for v in self._fond.avancer(t))
        if self._ia is not None:self._ia.avancer(t)
        return traces

    def _preparer(self,e):
        self._verifier()
        if not isinstance(e,EntreeMoteur):raise ErreurOrchestration('entrée moteur typée requise')
        if self._entrees and e==self._entrees[-1].entree:return False
        if e.numero!=len(self._entrees)+1 or e.instant_ms<self._instant:raise ErreurOrchestration('séquence ou temps invalide')
        if any(t.symbole not in self._flux for t in e.ticks) or any(n not in self.bras for n,_ in e.mises_a_jour):
            raise ErreurOrchestration('entrée étrangère')
        for p in e.receptions:
            if (p.nature=='SNAPSHOT' and self._ia is None) or (p.nature!='SNAPSHOT' and self._fond is None):
                raise ErreurOrchestration('réception sans contrôle réel')
            if p.symbole is not None and p.symbole not in self._flux:raise ErreurOrchestration('réception étrangère')
        return True

    def traiter(self,e):
        if not self._preparer(e):return SortieEvenement(e.numero,e.instant_ms,ignoree=True)
        try:
            traces=self._recevoir(e);t=e.instant_ms;updates=dict(e.mises_a_jour)
            lignes={n:[b.alerte(v['code'],t,**{k:x for k,x in v.items() if k not in ('code','instant_ms')}) for v in traces] for n,b in self.bras.items()}
            commandes={n:[] for n in self.bras};lots={}
            def consommer(n,lot):
                b=self.bras[n];s=b.consommer(lot,t,lambda sym,temps:self._contexte(n,sym,temps))
                lignes[n].extend(s.enregistrements);commandes[n].extend(s.commandes);lots[n]=lot
            if e.nature=='PERSISTANCE':
                for n,u in updates.items():consommer(n,self.bras[n].coordinateur.confirmer_persistance(u.preuve,t))
            else:
                cotations={v.symbole:Cotation(v.symbole,Decimal(str(v.bid)),Decimal(str(v.ask)),v.instant_fournisseur_ms,t) for v in e.ticks}
                for n,b in self.bras.items():
                    u=updates.get(n,MiseAJourBras())
                    consommer(n,b.coordinateur.traiter(t,cotations=tuple(cotations.values()),reponses=u.reponses,observation=u.observation,base_utc=u.base_utc))
                bougies=[]
                for tick in e.ticks:
                    for v in self._flux[tick.symbole].sur_tick(tick):
                        if isinstance(v,BougieEnrichie):bougies.append(v)
                        else:
                            donnees=dict(symbole=v.symbole,connu_utc_ms=v.instant_ms)
                            if isinstance(v,ChangementTrou):donnees.update(nature=v.nature.value,intervalle_utc_ms=v.intervalle_ms)
                            for n,b in self.bras.items():lignes[n].append(b.alerte('DATA_GAP' if isinstance(v,ChangementTrou) else v.raison,t,**donnees))
                priorite=self.configuration.technique.commun.universe_priority
                bougies.sort(key=lambda b:(b.bougie.fin_ms,0 if b.unite is UniteTemps.H1 else 1,priorite.index(b.bougie.symbole)))
                signaux={n:[] for n in self.bras}
                for v in bougies:
                    for n,b in self.bras.items():
                        for r in b.sur_bougie(v,instant_ms=t):
                            if v.unite is UniteTemps.M15:
                                lignes[n].append(b.journaliser_cloture(v,r,lots[n].compte,*self._contexte(n,v.bougie.symbole,t)))
                                if isinstance(r,SignalTechnique):signaux[n].append(r)
                for n,b in self.bras.items():
                    if signaux[n]:consommer(n,b.coordinateur.traiter(t,signaux=tuple(signaux[n]),base_utc=updates.get(n,MiseAJourBras()).base_utc))
            calculs=[]
            for n,b in self.bras.items():
                b.calculs.terminer_rejeu();calculs.append((n,b.calculs.drainer()))
            self._entrees.append(EntreeJournalisee(e,tuple(calculs)));self._instant=t
            return SortieEvenement(e.numero,t,tuple((n,SortieMoteur(tuple(lignes[n]),tuple(commandes[n]),lots.get(n))) for n in self.bras))
        except Exception:
            self._valide=False
            raise

    def rejouer(self,j):
        if not isinstance(j,EntreeJournalisee):raise ErreurOrchestration('entrée journalisée réelle requise')
        if self._entrees and j==self._entrees[-1]:return SortieEvenement(j.entree.numero,j.entree.instant_ms,ignoree=True)
        if not self._preparer(j.entree):raise ErreurOrchestration('calculs réécrits pour une entrée répétée')
        if tuple(n for n,_ in j.calculs)!=tuple(self.bras):raise ErreurOrchestration('bras de calcul différents')
        for n,appels in j.calculs:self.bras[n].calculs.debut_rejeu(appels)
        s=self.traiter(j.entree)
        if self._entrees[-1]!=j:self._valide=False;raise ErreurOrchestration('journal divergent')
        return s

    def _entree(self,t,nature,ticks=(),mises_a_jour=()):
        e=EntreeMoteur(t,len(self._entrees)+1,nature,tuple(ticks),mises_a_jour)
        self._preparer(e)
        receptions=tuple(v for s in self._sources if s is not None for v in s.extraire(t))
        return EntreeMoteur(t,e.numero,nature,e.ticks,e.mises_a_jour,receptions)

    def traiter_ticks(self,ticks,*,mises_a_jour=()):
        ticks=tuple(ticks)
        if not ticks:raise ErreurOrchestration('groupe de ticks vide')
        return self.traiter(self._entree(ticks[0].instant_reception_ms,'TICKS',ticks,mises_a_jour))

    def traiter_evenement(self,instant_ms,*,mises_a_jour=()):
        return self.traiter(self._entree(instant_ms,'MINUTERIE',mises_a_jour=mises_a_jour))

    def confirmer_persistance(self,preuves,instant_ms):
        return self.traiter(self._entree(instant_ms,'PERSISTANCE',mises_a_jour=tuple((n,MiseAJourBras(preuve=p)) for n,p in dict(preuves).items())))

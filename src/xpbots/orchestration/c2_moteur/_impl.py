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
from xpbots.execution.c6_coordinateur import EtatCoordinateur
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.fondamental.c2_etat_permissions import PermissionRecue
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.noyau.c1a_marche import Cotation
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle
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


def _empreinte_journal(entrees):
    empreinte=hashlib.sha256(b'').hexdigest()
    for j in entrees:
        if not isinstance(j,EntreeJournalisee):raise ErreurOrchestration('journal de checkpoint mal typé')
        empreinte=_sceau((empreinte,j))
    return empreinte


def _paires_json_marche(paires):
    resultat={}
    for k,v in paires:
        if k in resultat:raise ErreurOrchestration('clé JSON de marché en double')
        resultat[k]=v
    return resultat


def _json_marche(octets):
    def interdit(_):raise ErreurOrchestration('nombre de marché non fini')
    try:
        return json.loads(octets.decode('utf-8'),object_pairs_hook=_paires_json_marche,parse_constant=interdit)
    except (ValueError,UnicodeError,TypeError) as e:
        raise ErreurOrchestration('document de marché invalide') from e


def _intervalles_marche(valeurs):
    if type(valeurs) is not list:raise ErreurOrchestration('liste d’intervalles requise')
    resultat=[]
    for v in valeurs:
        if type(v) is not list or len(v)!=2:raise ErreurOrchestration('couple de bornes requis')
        resultat.append(Intervalle(*v))
    if resultat!=sorted(resultat):raise ErreurOrchestration('intervalles non ordonnés')
    return tuple(resultat)


def _horaires_marche(h):
    if type(h) is not dict or set(h)!={'seances','fermetures','debut_validite_ms','fin_validite_ms'}:
        raise ErreurOrchestration('champs des horaires invalides')
    return HorairesCotation(_intervalles_marche(h['seances']),_intervalles_marche(h['fermetures']),
                            h['debut_validite_ms'],h['fin_validite_ms'])


def _horaires_document(h):
    return dict(seances=[[i.debut_ms,i.fin_ms] for i in h.seances],
                fermetures=[[i.debut_ms,i.fin_ms] for i in h.fermetures],
                debut_validite_ms=h.debut_validite_ms,fin_validite_ms=h.fin_validite_ms)


class _CouvertureCourante:
    """Port C03 en mémoire ; ses valeurs ne changent que par une réception journalisée."""
    def __init__(self,periodes):self.registre=RegistreCouverture(periodes)
    def periodes(self,jusqua_ms):return self.registre.periodes(jusqua_ms)


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


@dataclass(frozen=True)
class CheckpointMoteur:
    signature:str
    instant_ms:int
    numero_entrees:int
    empreinte_journal:str
    flux:tuple
    bras:tuple
    fondamental:object
    ia:object
    empreinte:str

    def __post_init__(self):
        object.__setattr__(self,'flux',tuple(tuple(v) for v in self.flux))
        object.__setattr__(self,'bras',tuple(self.bras))

    def verifier(self):
        instant(self.instant_ms)
        if type(self.numero_entrees) is not int or self.numero_entrees<0:
            raise ErreurOrchestration('compteur du checkpoint invalide')
        for h in (self.signature,self.empreinte_journal,self.empreinte):
            if type(h) is not str or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):
                raise ErreurOrchestration('empreinte du checkpoint invalide')
        valeurs=tuple(getattr(self,f.name) for f in fields(self) if f.name!='empreinte')
        if self.empreinte!=_sceau(valeurs):raise ErreurOrchestration('checkpoint du moteur altéré')


@dataclass(frozen=True)
class CheckpointJournalMoteur:
    signature:str
    instant_ms:int
    numero_entrees:int
    empreinte_journal:str
    flux:tuple
    coordinateurs:tuple
    fondamental:object
    ia:object
    empreinte:str

    def __post_init__(self):
        object.__setattr__(self,'flux',tuple(tuple(v) for v in self.flux))
        object.__setattr__(self,'coordinateurs',tuple(tuple(v) for v in self.coordinateurs))

    def verifier(self):
        instant(self.instant_ms)
        if type(self.numero_entrees) is not int or self.numero_entrees<0:
            raise ErreurOrchestration('compteur du checkpoint journal invalide')
        for h in (self.signature,self.empreinte_journal,self.empreinte):
            if type(h) is not str or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):
                raise ErreurOrchestration('empreinte du checkpoint journal invalide')
        noms=[]
        for paire in self.coordinateurs:
            if (len(paire)!=len(('bras','etat')) or paire[0] not in (REFERENCE,IA)
                    or not isinstance(paire[1],EtatCoordinateur) or paire[1].dernier_ms>self.instant_ms):
                raise ErreurOrchestration('coordinateur du checkpoint journal invalide')
            noms.append(paire[0])
        if not noms or len(set(noms))!=len(noms):
            raise ErreurOrchestration('bras du checkpoint journal invalides')
        for valeur,schema,champs in ((self.fondamental,'xp-verification-c05-v1',
                ('schema','dernier_ms','dernier_permissions_ms','evenements','permissions','curseurs','calendrier')),
                (self.ia,'xp-verification-ia-v1',('schema','dernier_ms','snapshot','vetos'))):
            if valeur is not None:
                if type(valeur) is not tuple or len(valeur)!=len(champs) or valeur[0]!=schema:
                    raise ErreurOrchestration('engagement de controle du checkpoint journal invalide')
                instant(valeur[1])
                if valeur[1]>self.instant_ms:raise ErreurOrchestration('engagement de controle futur')
        valeurs=tuple(getattr(self,f.name) for f in fields(self) if f.name!='empreinte')
        if self.empreinte!=_sceau(valeurs):raise ErreurOrchestration('checkpoint journal du moteur altere')


class MoteurDecision:
    def __init__(self,configuration,bras,horaires,periodes_couvertes,*,controle_fondamental=None,
                 lecteur_ia=None,source_fondamentale=None,source_ia=None,scenario_fondamental=None,etat=None,
                 checkpoint=None,entrees=()):
        try:journal=tuple(entrees)
        except TypeError as erreur:raise ErreurOrchestration('journal de checkpoint requis') from erreur
        if checkpoint is not None:
            if etat is not None or not isinstance(checkpoint,CheckpointMoteur):
                raise ErreurOrchestration('checkpoint typé exclusif requis')
            checkpoint.verifier()
            if len(journal)!=checkpoint.numero_entrees or _empreinte_journal(journal)!=checkpoint.empreinte_journal:
                raise ErreurOrchestration('journal différent du checkpoint')
            v=(checkpoint.signature,checkpoint.instant_ms,journal,checkpoint.flux,checkpoint.bras,
                checkpoint.fondamental,checkpoint.ia)
            etat=EtatMoteur(*v,_sceau(v))
        elif journal:raise ErreurOrchestration('journal sans checkpoint')
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
        self._horaires=dict(horaires);self._marche={}
        self._couvertures={s:_CouvertureCourante(periodes_couvertes[s]) for s in horaires}
        self._flux={s:FluxBougies(s,configuration.technique,horaires[s],self._couvertures[s]) for s in horaires}
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
            self._flux={s:self._reprendre_flux(s,json.loads(v),etat.instant_ms) for s,v in etat.flux}
            self._entrees=list(etat.entrees)
            if any(not isinstance(e,EntreeJournalisee) or e.entree.numero!=i+1 or e.entree.instant_ms>self._instant for i,e in enumerate(self._entrees)):
                raise ErreurOrchestration('journal de reprise incohérent')
        self._empreinte_entrees=_empreinte_journal(self._entrees)
        self._cache_verifications={}

    @staticmethod
    def _etat_controle(c):return None if c is None else c.etat

    def _verifier(self):
        if not self._valide:raise ErreurOrchestration('moteur invalidé ; reprise requise')

    @property
    def entrees(self):return tuple(self._entrees)

    def entrees_depuis(self,numero):
        self._verifier()
        if type(numero) is not int or not 0<=numero<=len(self._entrees):
            raise ErreurOrchestration('indice du journal invalide')
        return tuple(self._entrees[numero:])

    @property
    def initialisation_calculs(self):return tuple((n,b.calculs.initialisation) for n,b in self.bras.items())

    @property
    def etat(self):
        self._verifier()
        v=(self._signature,self._instant,self.entrees,
            tuple((s,self._exporter_flux(s,f)) for s,f in self._flux.items()),
            tuple(b.etat for b in self.bras.values()),self._etat_controle(self._fond),self._etat_controle(self._ia))
        return EtatMoteur(*v,_sceau(v))

    def exporter_checkpoint(self):
        self._verifier()
        v=(self._signature,self._instant,len(self._entrees),self._empreinte_entrees,
            tuple((s,self._exporter_flux(s,f)) for s,f in self._flux.items()),
            tuple(b.etat for b in self.bras.values()),self._etat_controle(self._fond),self._etat_controle(self._ia))
        return CheckpointMoteur(*v,_sceau(v))

    def exporter_checkpoint_journal(self):
        self._verifier()
        fondamental,ia=self._verification_controles()
        v=(self._signature,self._instant,len(self._entrees),self._empreinte_entrees,
            tuple((s,self._exporter_flux(s,f)) for s,f in self._flux.items()),
            tuple((n,b.coordinateur.etat) for n,b in self.bras.items()),
            fondamental,ia)
        return CheckpointJournalMoteur(*v,_sceau(v))

    def _verification_controles(self):
        nouveau={}
        def empreinte(cle,obj):
            ancien=self._cache_verifications.get(cle)
            h=ancien[1] if ancien is not None and ancien[0] is obj else _sceau(obj)
            nouveau[cle]=(obj,h)
            return h
        fondamental=None;ia=None
        if self._fond is not None:
            e=self._fond.etat;derniers={};permissions={}
            for fait in e.permissions.historique:
                derniers[fait.symbole]=fait
                if isinstance(fait,PermissionRecue):permissions[fait.symbole]=fait
            def faits(valeurs,nature):
                return tuple((s,f.instant_ms,empreinte((nature,s),f)) for s,f in sorted(valeurs.items()))
            v=e.calendrier.versions[-1] if e.calendrier.versions else None
            calendrier=None if v is None else (v.version,v.export_ms,v.reception_ms,empreinte(('calendrier',),v))
            fondamental=('xp-verification-c05-v1',e.dernier_ms,e.permissions.dernier_ms,
                         faits(derniers,'evenement'),faits(permissions,'permission'),e.permissions.curseurs,calendrier)
        if self._ia is not None:
            e=self._ia.etat;r=e.dernier_snapshot
            dernier=None if r is None else (r.snapshot.sequence,r.snapshot.genere_ms,r.reception_ms,
                                            r.snapshot.empreinte_integration,r.snapshot.empreinte_payload)
            vetos=tuple((v.veto.event_id,v.connu_ms,v.veto.valid_from_ms,v.veto.valid_until_ms,
                         empreinte(('veto',v.veto.event_id),v.veto),v.preuve.snapshot.sequence,
                         v.preuve.snapshot.empreinte_payload,v.preuve.reception_ms)
                        for v in sorted(e.scelles,key=lambda v:v.veto.event_id) if v.veto.valid_until_ms>e.dernier_ms)
            ia=('xp-verification-ia-v1',e.dernier_ms,dernier,vetos)
        self._cache_verifications=nouveau
        return fondamental,ia

    def _exporter_flux(self,s,f):
        v=f.exporter_etat()
        if s in self._marche:v=dict(schema='xp-flux-moteur-v2',flux=v,marche=self._marche[s])
        return json.dumps(v,sort_keys=True,separators=(',',':'))

    def _valider_marche(self,s,d,t):
        if (type(d) is not dict or set(d)!={'schema','version','horaires','periodes_couvertes'}
                or d['schema']!='xp-etat-marche-v1' or type(d['version']) is not int or d['version']<=0):
            raise ErreurOrchestration('champs ou version du fait de marché invalides')
        try:
            h=self._horaires[s] if d['horaires'] is None else _horaires_marche(d['horaires'])
            if not h.debut_validite_ms<=t<h.fin_validite_ms:
                raise ErreurOrchestration('horaires non valides à réception')
            periodes=_intervalles_marche(d['periodes_couvertes'])
            if any(p.fin_ms>t for p in periodes):raise ErreurOrchestration('couverture future refusée')
            return h,RegistreCouverture(periodes)
        except ValueError as e:
            raise ErreurOrchestration('valeurs du fait de marché invalides') from e

    def _recevoir_marche(self,p,t):
        d=_json_marche(p.octets)
        if type(d) is not dict or type(d.get('version')) is not int:
            raise ErreurOrchestration('version de marché entière requise')
        empreinte=hashlib.sha256(p.octets).hexdigest();ancien=self._marche.get(p.symbole)
        if ancien is not None and d['version']<=ancien['version']:
            if d['version']==ancien['version'] and empreinte==ancien['empreinte_message']:return False
            raise ErreurOrchestration('version de marché reculée ou contradictoire')
        h,registre=self._valider_marche(p.symbole,d,t)
        self._horaires[p.symbole]=h;self._couvertures[p.symbole].registre=registre
        self._flux[p.symbole].actualiser_horaires(h)
        self._marche[p.symbole]=dict(version=d['version'],empreinte_message=empreinte,reception_ms=t,horaires=_horaires_document(h),
            periodes_couvertes=[[i.debut_ms,i.fin_ms] for i in registre.periodes(t)])
        return True

    def _reprendre_flux(self,s,v,t):
        if type(v) is dict and v.get('schema')=='xp-flux-moteur-v2':
            if set(v)!={'schema','flux','marche'}:raise ErreurOrchestration('enveloppe de flux invalide')
            d=v['marche']
            if (type(d) is not dict or set(d)!={'version','empreinte_message','reception_ms','horaires','periodes_couvertes'}
                    or type(d['empreinte_message']) is not str or len(d['empreinte_message'])!=64
                    or any(c not in '0123456789abcdef' for c in d['empreinte_message'])):
                raise ErreurOrchestration('état de marché invalide')
            instant(d['reception_ms'])
            if d['reception_ms']>t or type(d['horaires']) is not dict:
                raise ErreurOrchestration('connaissance de marché future ou incomplète')
            h,registre=self._valider_marche(s,dict(schema='xp-etat-marche-v1',version=d['version'],
                horaires=d['horaires'],periodes_couvertes=d['periodes_couvertes']),d['reception_ms'])
            self._horaires[s]=h;self._couvertures[s].registre=registre;self._marche[s]=d
            v=v['flux']
        return FluxBougies.reprendre(v,self.configuration.technique,self._horaires[s],self._couvertures[s])

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
            if p.nature=='MARCHE':
                if self._recevoir_marche(p,t):traces.append(dict(code='MARCHE_ACTUALISE',symbole=p.symbole,version=self._marche[p.symbole]['version']))
                continue
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
            if (p.nature=='SNAPSHOT' and self._ia is None) or (p.nature not in ('SNAPSHOT','MARCHE') and self._fond is None):
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
            j=EntreeJournalisee(e,tuple(calculs))
            self._entrees.append(j);self._empreinte_entrees=_sceau((self._empreinte_entrees,j));self._instant=t
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

"""SQLite est l'autorité ; JSONL est sa projection réparable."""
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json

from xpbots.app.c0_configuration import ErreurApplication
from xpbots.execution.c4_cycle import PreuvePersistance
from xpbots.infra.c0c_sqlite import DepotSQLite
from xpbots.infra.c0d_journal import JournalFichiers
from xpbots.noyau.c2_journal import serialiser
from xpbots.orchestration.c0_contrats import SortieEvenement,EntreeJournalisee
from xpbots.orchestration.c2_moteur import MoteurDecision,CheckpointJournalMoteur
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur


def _json(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def _document(b):
    if type(b) is not bytes:raise ErreurApplication('OCTETS_ARCHIVE_REQUIS')
    d=json.loads(b.decode('utf-8'))
    if _json(d)!=b:raise ErreurApplication('ARCHIVE_CANONIQUE_REQUISE')
    return d


@dataclass(frozen=True)
class PersistanceSession:
    numero:int
    preuves:tuple
    projection_reussie:bool


class SessionDurable:
    def __init__(self,depot,journal,initialisation,*,reprise=None):
        if not isinstance(depot,DepotSQLite) or not isinstance(journal,JournalFichiers):
            raise ErreurApplication('DEPOT_ET_JOURNAL_REELS_REQUIS')
        _document(initialisation)
        self._depot=depot;self._journal=journal;self._initialisation=initialisation
        self._signature=sha256(initialisation).hexdigest()
        self._numero=0;self._global=0;self._moteur=0;self._noms_livres=None
        self._sorties_en_attente={}
        self._chaine=sha256(b'').hexdigest()
        precedent=self._charger();self._reprise_en_attente=None
        if reprise is not None:
            if not isinstance(reprise,CheckpointJournalMoteur):raise ErreurApplication('MARQUEUR_REPRISE_INVALIDE')
            reprise.verifier()
            if (precedent is None or reprise.signature!=precedent['checkpoint'].signature
                    or reprise.instant_ms!=precedent['checkpoint'].instant_ms
                    or reprise.numero_entrees!=precedent['checkpoint'].numero_entrees
                    or reprise.empreinte_journal!=precedent['checkpoint'].empreinte_journal):
                raise ErreurApplication('MARQUEUR_REPRISE_HORS_PREFIXE')
            self._reprise_en_attente=reprise

    def _charger(self):
        b=self._depot.charger()
        if b is None:
            if self._depot.dernier_numero or self._depot.entrees():raise ErreurApplication('ETAT_DURABLE_ABSENT')
            return None
        d=deserialiser_valeur(b)
        if (not isinstance(d,Mapping) or set(d)!={'schema','signature','numero','dernier_entree_externe','empreinte_entrees','checkpoint','courtier','livres'}
                or d['schema']!='xp-session-direct-v2' or d['signature']!=self._signature
                or type(d['numero']) is not int or d['numero']!=self._depot.dernier_numero
                or type(d['dernier_entree_externe']) is not int or not isinstance(d['checkpoint'],CheckpointJournalMoteur)
                or not isinstance(d['livres'],Mapping)):
            raise ErreurApplication('ETAT_DURABLE_INCOHERENT')
        cp=d['checkpoint'];cp.verifier();moteur=[];reprises=[];livres={n:[] for n in d['livres']};initial=None
        entrees=self._depot.entrees()
        if len(entrees)!=d['dernier_entree_externe']:raise ErreurApplication('JOURNAL_DURABLE_TRONQUE')
        chaine=sha256(b'').hexdigest()
        for numero,b in enumerate(entrees,1):
            chaine=sha256(chaine.encode('ascii')+b).hexdigest()
            e=_document(b)
            if (set(e)!={'numero','instant_reception_utc_ms','type_evenement','contenu'}
                    or type(e['numero']) is not int or e['numero']!=numero
                    or type(e['instant_reception_utc_ms']) is not int or e['instant_reception_utc_ms']>cp.instant_ms):
                raise ErreurApplication('ENVELOPPE_DURABLE_INCOHERENTE')
            nature=e['type_evenement'];contenu=_json(e['contenu'])
            if nature=='INITIALISATION':
                if initial is not None or numero!=1 or contenu!=self._initialisation:
                    raise ErreurApplication('INITIALISATION_DURABLE_ETRANGERE')
                initial=contenu
            elif nature=='ENTREE_MOTEUR':
                j=deserialiser_valeur(contenu)
                if not isinstance(j,EntreeJournalisee) or j.entree.numero!=len(moteur)+1:
                    raise ErreurApplication('ENTREE_MOTEUR_DURABLE_INCOHERENTE')
                moteur.append(j)
            elif nature=='REPRISE_MOTEUR':
                marqueur=deserialiser_valeur(contenu)
                if not isinstance(marqueur,CheckpointJournalMoteur):raise ErreurApplication('MARQUEUR_REPRISE_INVALIDE')
                marqueur.verifier()
                if (initial is None or marqueur.signature!=cp.signature or marqueur.numero_entrees!=len(moteur)
                        or marqueur.instant_ms>e['instant_reception_utc_ms']
                        or moteur and marqueur.instant_ms!=moteur[-1].entree.instant_ms):
                    raise ErreurApplication('MARQUEUR_REPRISE_HORS_PREFIXE')
                reprises.append(marqueur)
            elif type(nature) is str and nature.startswith('LIVRE:') and nature[len('LIVRE:'):] in livres:
                livres[nature[len('LIVRE:'):]].append(contenu)
            else:raise ErreurApplication('NATURE_ARCHIVE_INCONNUE')
        if chaine!=d['empreinte_entrees']:raise ErreurApplication('CHAINE_DURABLE_ALTEREE')
        if initial is None or len(moteur)!=cp.numero_entrees:
            raise ErreurApplication('INITIALISATION_OU_JOURNAL_MOTEUR_ABSENT')
        gardes={nom:e.reprise.gardes for nom,e in cp.coordinateurs}
        for nom,nature,actif,_,_ in self._depot.arrets():
            if actif:
                g=gardes.get(nom)
                if (g is None or nature=='GLOBAL' and not g.arret_global
                        or nature=='QUOTIDIEN:'+g.jour_utc.isoformat() and not g.verrou_quotidien):
                    raise ErreurApplication('ARRET_DURABLE_NON_RESTAURE')
        self._numero=d['numero'];self._global=len(entrees);self._moteur=cp.numero_entrees
        self._noms_livres=set(livres)
        self._chaine=chaine
        resultat=dict(initialisation=initial,checkpoint=cp,entrees=tuple(moteur),courtier=d['courtier'],
                    livres={n:dict(checkpoint=d['livres'][n],operations=tuple(v)) for n,v in livres.items()})
        if reprises:resultat['reprises']=tuple(reprises)
        return resultat

    def charger(self):return self._charger()

    def persister(self,moteur,sortie=None,*,courtier=None,livres=None):
        if not isinstance(moteur,MoteurDecision) or sortie is not None and not isinstance(sortie,SortieEvenement):
            raise ErreurApplication('MOTEUR_ET_SORTIE_REELS_REQUIS')
        cp=moteur.exporter_checkpoint_journal();nouveaux=moteur.entrees_depuis(self._moteur)
        if sortie is not None and sortie.numero!=cp.numero_entrees:
            raise ErreurApplication('SORTIE_DIFFERENTE_DU_CHECKPOINT')
        livres=dict(livres or {})
        if not set(livres)<=set(moteur.bras) or self._noms_livres is not None and set(livres)!=self._noms_livres:
            raise ErreurApplication('LIVRES_DURABLES_ETRANGERS')
        entrees=[];global_=self._global
        def ajouter(nature,octets):
            nonlocal global_
            contenu=_document(octets);global_+=1
            entrees.append((global_,_json(dict(numero=global_,instant_reception_utc_ms=cp.instant_ms,
                                              type_evenement=nature,contenu=contenu))))
        if self._numero==0:ajouter('INITIALISATION',self._initialisation)
        if self._reprise_en_attente is not None:
            if (self._reprise_en_attente.numero_entrees!=self._moteur
                    or self._reprise_en_attente.signature!=cp.signature):
                raise ErreurApplication('MARQUEUR_REPRISE_HORS_PREFIXE')
            ajouter('REPRISE_MOTEUR',serialiser_valeur(self._reprise_en_attente))
        for j in nouveaux:ajouter('ENTREE_MOTEUR',serialiser_valeur(j))
        checkpoints={}
        for nom,v in livres.items():
            if not isinstance(v,Mapping) or set(v)!={'checkpoint','operations'}:
                raise ErreurApplication('DELTA_LIVRE_INVALIDE')
            _document(v['checkpoint']);checkpoints[nom]=v['checkpoint']
            for b in v['operations']:ajouter('LIVRE:'+nom,b)
        attente=dict(self._sorties_en_attente)
        if sortie is not None and sortie.numero>self._moteur:
            ancienne=attente.get(sortie.numero)
            if ancienne is not None and ancienne!=sortie:
                raise ErreurApplication('SORTIE_NON_COMMITEE_CONTRADICTOIRE')
            attente[sortie.numero]=sortie
        decisions=tuple(serialiser(e).encode('utf-8') for n in sorted(attente) for e in attente[n].enregistrements)
        intentions=[];reservations=[];arrets=[];largeur=len(sha256().hexdigest())
        for nom,e in cp.coordinateurs:
            intentions.extend((d.cle.empreinte(largeur),d.statut.value,serialiser_valeur(d)) for d in e.intentions)
            reservations.extend((r.cle.empreinte(largeur),r.risque_initial,r.volume) for r in e.reprise.reservations.reservations)
            g=e.reprise.gardes
            if g is not None:
                arrets.extend(((nom,'GLOBAL',g.arret_global,None),
                               (nom,'QUOTIDIEN:'+g.jour_utc.isoformat(),g.verrou_quotidien,None)))
        numero=self._numero+1
        chaine=self._chaine
        for _,b in entrees:chaine=sha256(chaine.encode('ascii')+b).hexdigest()
        etat=serialiser_valeur(dict(schema='xp-session-direct-v2',signature=self._signature,numero=numero,
            dernier_entree_externe=global_,empreinte_entrees=chaine,checkpoint=cp,courtier=courtier,livres=checkpoints))
        self._sorties_en_attente=attente
        self._depot.persister(numero,cp.instant_ms,etat,entrees=entrees,decisions=decisions,
            intentions=intentions,reservations=reservations,arrets=arrets)
        # À partir d'ici le COMMIT est acquis, indépendamment de la projection.
        self._numero=numero;self._global=global_;self._moteur=cp.numero_entrees;self._noms_livres=set(livres)
        self._chaine=chaine
        self._reprise_en_attente=None
        derniere=attente.get(cp.numero_entrees);self._sorties_en_attente={}
        preuves=tuple((nom,PreuvePersistance(s.lot.etat.revision,tuple(c.reference for c in s.lot.preparations)))
            for nom,s in derniere.sorties if s.lot is not None and s.lot.preparations) if derniere is not None else ()
        projection=True
        try:self._journal.ajouter(((numero,cp.instant_ms,decisions,tuple(b for _,b in entrees)),))
        except (OSError,ValueError):projection=False
        return PersistanceSession(numero,preuves,projection)

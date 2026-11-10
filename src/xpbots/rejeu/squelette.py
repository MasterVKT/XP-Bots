"""Façades S1/S5 vers le lecteur, le simulateur et le pilote communs de phase 10."""
from dataclasses import dataclass,field
from datetime import date
from decimal import Decimal
import hashlib
from types import MappingProxyType
from typing import Sequence
from xpbots.contexte_ia.c0_types import instant as instant_ia
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.fondamental.c0_types import TableImportance,devises_pour,instant
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.noyau.c0a_temps import aligner,instant_vers_datetime
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1b_instrument import HorairesCotation,Intervalle,construire_profil_instrument
from xpbots.noyau.c2_journal import Enregistrement
from xpbots.execution.c4_cycle import ReponseCourtier
from xpbots.orchestration.c0_contrats import ReceptionExterne
from xpbots.rejeu.c0a_types import ManifesteTicks,ConditionContrat,TarifCommission
from xpbots.rejeu.c0b_protocole import ScenarioExecution
from xpbots.rejeu.c1a_ticks import analyser_lignes_ticks as analyser_ticks_manifestes
from xpbots.rejeu.c1b_simulateur import SimulateurExecution
from xpbots.rejeu.c2_executeur import StockageMemoireRejeu,piloter

COLONNES_TICKS=('canonical_symbol','broker_symbol','time_utc_ms','sequence','bid','ask')

@dataclass(frozen=True)
class PaquetFondamental:
    instant_ms: int
    nature: str
    octets: bytes = b''
    symbole: str | None = None
    table: TableImportance | None = None

    def __post_init__(self):
        instant(self.instant_ms)
        if self.nature not in ('PERMISSION','CALENDRIER','INTERRUPTION') or type(self.octets) is not bytes:
            raise ValueError('paquet C05 synthétique mal typé')
        if self.nature=='CALENDRIER':
            if not isinstance(self.table,TableImportance) or self.symbole is not None:
                raise ValueError('classification explicite du calendrier requise')
        else:
            devises_pour(self.symbole)
            if self.table is not None or (self.nature=='INTERRUPTION' and self.octets):
                raise ValueError('paquet de permission incohérent')


class SourceFondamentaleScenario:
    """Doublure des seules arrivées externes ; le contrôle et ses couches sont réels."""
    def __init__(self,controle,paquets):
        if not isinstance(controle,PermissionsFondamentales):raise ValueError('port C05 réel requis')
        self.controle=controle;self._paquets=tuple(paquets);self._index=0
        precedent=controle.etat.dernier_ms
        for p in self._paquets:
            if not isinstance(p,PaquetFondamental) or p.instant_ms<precedent:
                raise ValueError('paquets typés et chronologiques requis')
            precedent=p.instant_ms

    @property
    def prochaine_reception_ms(self):
        return self._paquets[self._index].instant_ms if self._index<len(self._paquets) else None

    def extraire(self,t):
        instant(t);receptions=[]
        if self.prochaine_reception_ms is not None and self.prochaine_reception_ms<t:
            raise ValueError('réception externe sautée par le pilote')
        while self.prochaine_reception_ms==t:
            p=self._paquets[self._index];receptions.append(ReceptionExterne(p.nature,p.octets,p.symbole,p.table));self._index+=1
        return tuple(receptions)

    def recevoir(self,t):
        instant(t);traces=[]
        if self.prochaine_reception_ms is not None and self.prochaine_reception_ms<t:
            raise ValueError('réception C05 sautée par le pilote de rejeu')
        while self.prochaine_reception_ms==t:
            p=self._paquets[self._index]
            if p.nature=='INTERRUPTION':
                change=self.controle.interrompre(p.symbole,t)
                traces.append(dict(alerte='PERMISSION_INTERROMPUE',symbole=p.symbole,change=change,instant_ms=t))
            else:
                r=(self.controle.recevoir_permission(p.symbole,p.octets,t) if p.nature=='PERMISSION'
                    else self.controle.recevoir_calendrier(p.octets,t,p.table))
                statut='ACCEPTE' if r.acceptee else 'RELU' if r.ignoree else 'REJETE'
                traces.append(dict(alerte=p.nature+'_'+statut,symbole=p.symbole,instant_ms=t,
                    raison=r.raison,sequence=r.permission.message.sequence if p.nature=='PERMISSION' and r.permission else None,
                    version=r.version.version if p.nature=='CALENDRIER' and r.version else None))
            self._index+=1
        return tuple(traces)


@dataclass(frozen=True)
class PaquetSnapshot:
    instant_ms: int
    octets: bytes | None

    def __post_init__(self):
        instant_ia(self.instant_ms)
        if self.octets is not None and type(self.octets) is not bytes:
            raise ValueError('snapshot externe en octets ou absent requis')


class SourceSnapshotScenario:
    """Seules les arrivées externes sont scénarisées ; lecteur et cache réels."""
    def __init__(self,lecteur,paquets):
        if not isinstance(lecteur,LecteurContexte):raise ValueError('lecteur IA réel requis')
        self.lecteur=lecteur;self._paquets=tuple(paquets);self._index=0
        precedent=lecteur.etat.dernier_ms
        for p in self._paquets:
            if not isinstance(p,PaquetSnapshot) or p.instant_ms<precedent:
                raise ValueError('snapshots typés et chronologiques requis')
            precedent=p.instant_ms

    @property
    def prochaine_reception_ms(self):
        return self._paquets[self._index].instant_ms if self._index<len(self._paquets) else None

    def extraire(self,t):
        instant_ia(t);receptions=[]
        if self.prochaine_reception_ms is not None and self.prochaine_reception_ms<t:
            raise ValueError('réception externe sautée par le pilote')
        while self.prochaine_reception_ms==t:
            p=self._paquets[self._index];receptions.append(ReceptionExterne('SNAPSHOT',p.octets));self._index+=1
        return tuple(receptions)

    def recevoir(self,t):
        instant_ia(t);traces=[]
        if self.prochaine_reception_ms is not None and self.prochaine_reception_ms<t:
            raise ValueError('réception IA sautée par le pilote de rejeu')
        while self.prochaine_reception_ms==t:
            p=self._paquets[self._index];r=self.lecteur.recevoir(p.octets,t)
            statut='ACCEPTE' if r.acceptee else 'RELU' if r.ignoree else 'REJETE'
            traces.append(dict(alerte='SNAPSHOT_'+statut,instant_ms=t,raison=r.raison,
                sequence=r.snapshot.snapshot.sequence if r.snapshot else None,ajoutes=r.ajoutes))
            self._index+=1
        return tuple(traces)


class ErreurDonnees(ValueError):
    """Refus de la façade CSV historique ; aucune qualification de provenance réelle."""


def analyser_lignes_ticks(lignes,manifeste=None):
    """Le manifeste réel est préféré ; sinon déclaration explicite d'une fixture LF."""
    lignes=tuple(lignes)
    try:
        if manifeste is None:
            lignes=tuple(l.rstrip('\r\n')+'\n' for l in lignes)
            if not lignes or tuple(lignes[0].rstrip('\n').split(','))!=COLONNES_TICKS:
                raise ErreurDonnees('en-tête CSV inattendu ou fichier vide')
            # Seules les métadonnées sont relevées ici, sans trier ni produire de Tick.
            symboles={};instants=[]
            for ligne in lignes[1:]:
                symbole,natif,t,_,_,_=ligne.rstrip('\n').split(',')
                if symbole in symboles and symboles[symbole]!=natif:raise ErreurDonnees('liaison native modifiée')
                symboles[symbole]=natif;instants.append(int(t))
            if not instants:raise ErreurDonnees('aucun tick dans le fichier')
            intervalle=Intervalle(min(instants),max(instants)+1)
            horaires={s:HorairesCotation((intervalle,),(),intervalle.debut_ms,intervalle.fin_ms+1) for s in symboles}
            manifeste=ManifesteTicks('S1_FIXTURE_LF_DECLAREE',symboles,intervalle,(intervalle,),(),
                hashlib.sha256(''.join(lignes).encode('utf-8')).hexdigest(),
                instant_vers_datetime(intervalle.debut_ms).date(),'FAÇADE_S1_LF','DECIMAL_TEXTE',horaires)
        return iter(analyser_ticks_manifestes(lignes,manifeste))
    except (ValueError,TypeError,OverflowError) as erreur:
        raise ErreurDonnees(str(erreur)) from erreur


def hypotheses_marche_squelette(ticks: Sequence[Tick], configuration: ConfigurationFigee
                                ) -> tuple[dict[str, HorairesCotation], dict[str, tuple[Intervalle, ...]]]:
    """Horaires et périodes couvertes de l'hypothèse du squelette, par symbole (voir l'en-tête du module)."""
    duree = configuration.technique.commun.h1_seconds * 1000
    etendues: dict[str, tuple[int, int]] = {}
    for tick in ticks:
        debut, fin = etendues.get(tick.symbole, (tick.instant_fournisseur_ms, tick.instant_fournisseur_ms))
        etendues[tick.symbole] = (min(debut, tick.instant_fournisseur_ms), max(fin, tick.instant_fournisseur_ms))
    horaires: dict[str, HorairesCotation] = {}
    periodes: dict[str, tuple[Intervalle, ...]] = {}
    for symbole, (premier, dernier) in etendues.items():
        etendue = Intervalle(aligner(premier, duree), aligner(dernier, duree) + duree)
        # Fermeture explicitement connue ; sa période de validité la dépasse pour le vrai contrôle 0e.
        horaires[symbole] = HorairesCotation((etendue,), (), etendue.debut_ms, etendue.fin_ms + duree)
        periodes[symbole] = (etendue,)
    return horaires, periodes


@dataclass(frozen=True)
class ContratPapier:
    """Données de contrat synthétiques fournies explicitement par la composition."""
    taille_contrat: Decimal
    volume_min: Decimal
    volume_max: Decimal
    volume_pas: Decimal

    def __post_init__(self):
        for v in (self.taille_contrat,self.volume_min,self.volume_max,self.volume_pas):
            if not isinstance(v,Decimal) or not v.is_finite() or v<=0:
                raise ValueError('contrat papier : valeurs décimales positives requises')
        if self.volume_max<self.volume_min or self.volume_min%self.volume_pas:
            raise ValueError('contrat papier : grille incohérente')


def profils_papier(ticks,tailles,contrats,horaires,configuration):
    """Qualifier le modèle S5 déclaré : point=tick, IOC, frais nuls connus, marge à levier constant.

    Ces données sont celles du modèle papier et ne qualifient aucun instrument réellement disponible.
    """
    symboles={t.symbole for t in ticks}
    if set(tailles)!=symboles or set(contrats)!=symboles or set(horaires)!=symboles:
        raise ValueError('taille, contrat et horaires explicites requis pour chaque symbole')
    profils={};commun=configuration.technique.commun
    for s in sorted(symboles):
        noms={t.symbole_courtier for t in ticks if t.symbole==s}
        if len(noms)!=1 or not isinstance(contrats[s],ContratPapier):
            raise ValueError('une seule liaison native et un contrat papier requis')
        pas=tailles[s];c=contrats[s]
        if not isinstance(pas,Decimal) or not pas.is_finite() or pas<=0:
            raise ValueError('taille de tick positive requise')
        debut=min(t.instant_reception_ms for t in ticks)
        champs=dict(symbole=s,symbole_courtier=next(iter(noms)),sous_jacent=s,
            devise_base=s[:-len(commun.account_currency)],devise_cotation=commun.account_currency,
            devise_marge=commun.account_currency,mode_calcul='SYNTHETIQUE_S5',taille_contrat=c.taille_contrat,
            tick_size=pas,point=pas,digits=max(0,-pas.normalize().as_tuple().exponent),valeur_tick=c.taille_contrat*pas,
            volume_min=c.volume_min,volume_max=c.volume_max,volume_pas=c.volume_pas,volume_limite=Decimal(0),
            distance_stops_min_points=0,niveau_gel_points=0,mode_negociation='FULL',mode_execution='MARKET',
            modes_remplissage=frozenset({'IOC'}),protections_a_l_entree=True,convention_declenchement_verifiee=True,
            commission_par_lot_par_cote=Decimal(0),commission_minimum_par_ordre=Decimal(0),commission_nulle_confirmee=True,
            devise_frais=commun.account_currency,swap_achat=Decimal(0),swap_vente=Decimal(0),
            marge_initiale=Decimal(0),marge_maintenance=Decimal(0),horaires=horaires[s],releve_ms=debut)
        resultat=construire_profil_instrument(champs,commun)
        if resultat.non_prets: raise ValueError('profil papier non prêt : '+resultat.non_prets[0])
        profils[s]=resultat.profil
    return profils


class StockageMemoirePapier(StockageMemoireRejeu):
    """Nom historique du stockage mémoire commun, sans durabilité physique."""


class ExecutionPapierMinimale(SimulateurExecution):
    """Façade du simulateur commun, ancien scénario synthétique explicitement nommé."""
    def __init__(self,configuration,profils,creation_ms,scenario=None):
        tarif=TarifCommission('ZERO_DECLARE_SQUELETTE',Decimal(0),Decimal(0),Decimal(0),Decimal(0))
        conditions=tuple(ConditionContrat(p.releve_ms,p.horaires.fin_validite_ms,p.releve_ms,p,tarif)
            for p in profils.values())
        modele=scenario if scenario is not None else ScenarioExecution('SYNTHETIQUE_S5',0,0,Decimal(1))
        super().__init__(configuration,conditions,creation_ms,modele)


@dataclass(frozen=True)
class ResultatRejeu:
    nombre_ticks:int
    enregistrements:tuple[Enregistrement,...]
    reponses:tuple[ReponseCourtier,...]=field(default=())


@dataclass(frozen=True)
class ResultatRejeuAB:
    nombre_ticks:int
    enregistrements:tuple
    reponses:object
    def __post_init__(self):
        object.__setattr__(self,'reponses',MappingProxyType({n:tuple(r) for n,r in self.reponses.items()}))


def rejouer_ab(ticks,moteur,executions,stockages=None):
    r=piloter(ticks,moteur,executions,stockages)
    return ResultatRejeuAB(r.nombre_ticks,r.enregistrements,r.reponses)


def rejouer(ticks,moteur,execution,stockage=None):
    coeur=getattr(moteur,'moteur',moteur)
    if len(coeur.bras)!=1:raise ValueError('un bras unique requis')
    nom=next(iter(coeur.bras))
    r=piloter(ticks,coeur,{nom:execution},{nom:stockage if stockage is not None else StockageMemoirePapier()})
    return ResultatRejeu(r.nombre_ticks,r.enregistrements,r.reponses[nom])

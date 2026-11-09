"""Coutures S1 et S5 : ticks CSV, profils synthétiques déclarés et transport papier C08.

Le modèle papier au prochain tick ne représente pas les délais, coûts ou remplissages partiels C10.
Les contrats et limites sont consignés dans mcl/squelette/COUTURES.md. Aucun accès extérieur ici.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Context, Decimal, localcontext
from itertools import groupby
import math
from typing import Iterable, Iterator, Protocol, Sequence

from xpbots.contexte_ia.c0_types import instant as instant_ia
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.execution.c0a_types import EtatCompte, PositionCompte, ControleNatif
from xpbots.execution.c1b_gardes import MouvementCompte, reconstituer_base_utc
from xpbots.execution.c4_cycle import (CommandeExecution, NatureCommande, ReponseCourtier, NatureReponse,
    StatutAccuse, PreuvePersistance, PreuveAbsence)
from xpbots.execution.c5b_reprise import ObservationNative, PositionNative, OrdreNatif
from xpbots.execution.c6_coordinateur import LotCoordinateur
from xpbots.fondamental.c0_types import TableImportance, devises_pour, instant
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.noyau.c0a_temps import aligner
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1a_marche import ErreurMarche, Tick
from xpbots.noyau.c1b_instrument import (HorairesCotation, Intervalle, ProfilCompte,
    construire_profil_instrument)
from xpbots.noyau.c1c_domaine import Sens, CauseCloture
from xpbots.noyau.c2_journal import Enregistrement
from xpbots.orchestration.squelette import SortieMoteur

COLONNES_TICKS = ('canonical_symbol', 'broker_symbol', 'time_utc_ms', 'sequence', 'bid', 'ask')


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
    """Fichier de ticks refusé : format, ordre ou valeur invalide."""


def _entier(texte: str, nom: str, ligne: int) -> int:
    if not texte.isascii() or not texte.isdigit():
        raise ErreurDonnees(f'ligne {ligne} : {nom} doit être un entier positif ou nul')
    return int(texte)


def _prix(texte: str, nom: str, ligne: int) -> float:
    try:
        valeur = float(texte)
    except ValueError as erreur:
        raise ErreurDonnees(f'ligne {ligne} : {nom} illisible') from erreur
    if not math.isfinite(valeur) or valeur <= 0:
        raise ErreurDonnees(f'ligne {ligne} : {nom} doit être un nombre fini strictement positif')
    return valeur


def analyser_lignes_ticks(lignes: Iterable[str]) -> Iterator[Tick]:
    """Convertir les lignes d'un fichier de ticks en ticks ordonnés ; toute anomalie lève `ErreurDonnees`."""
    iterateur = iter(lignes)
    entete = next(iterateur, None)
    if entete is None:
        raise ErreurDonnees('fichier de ticks vide')
    if tuple(entete.split(',')) != COLONNES_TICKS:
        raise ErreurDonnees(f'en-tête inattendu : {entete!r}')
    precedent: tuple[int, int] | None = None
    for numero, ligne in enumerate(iterateur, start=2):
        champs = ligne.split(',')
        if len(champs) != len(COLONNES_TICKS):
            raise ErreurDonnees(f'ligne {numero} : {len(COLONNES_TICKS)} champs attendus')
        symbole, symbole_courtier, instant, sequence, bid, ask = champs
        if not symbole or not symbole_courtier:
            raise ErreurDonnees(f'ligne {numero} : symbole vide')
        instant_ms = _entier(instant, 'time_utc_ms', numero)
        try:  # en rejeu, l'heure de réception est l'heure fournisseur (P-04)
            tick = Tick(symbole, symbole_courtier, instant_ms, instant_ms, _entier(sequence, 'sequence', numero),
                        _prix(bid, 'bid', numero), _prix(ask, 'ask', numero))
        except ErreurMarche as erreur:
            raise ErreurDonnees(f'ligne {numero} : {erreur}') from erreur
        cle = (tick.instant_fournisseur_ms, tick.numero)
        if precedent is not None and cle <= precedent:
            raise ErreurDonnees(f'ligne {numero} : ticks non strictement ordonnés par instant puis séquence')
        precedent = cle
        yield tick


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


@dataclass
class _PositionPapier:
    commande: CommandeExecution
    ticket: str
    ordre: str
    volume: Decimal
    prix: Decimal
    sl: Decimal | None
    tp: Decimal | None
    premier_fill_ms: int


class StockageMemoirePapier:
    """Transaction mémoire du scénario technique ; aucune durabilité physique."""
    def __init__(self):
        self.dernier_lot=None

    def persister(self,lot):
        if not isinstance(lot,LotCoordinateur): raise ValueError('lot réel requis')
        if self.dernier_lot is not None and lot.etat.revision<self.dernier_lot.etat.revision:
            raise ValueError('révision ancienne')
        self.dernier_lot=lot
        return PreuvePersistance(lot.etat.revision,tuple(c.reference for c in lot.preparations))


class ExecutionPapierMinimale:
    """Frontière S5 : calculs USD synthétiques et exécutions au prochain tick disponible.

    Aucun coût, délai C10 ou remplissage partiel d'entrée ; les réductions sont natives et confirmées.
    Les réserves de glissement C07 ne sont jamais retranchées du résultat réalisé.
    """
    def __init__(self,configuration,profils,creation_ms):
        self.configuration=configuration;self.profils=dict(profils)
        self.creation_ms=creation_ms;self.instant_ms=creation_ms
        self._solde=Decimal(str(configuration.technique.commun.initial_equity_usd))
        self._positions={};self._entrees={};self._clotures={};self._vues=set();self._prix={}
        self._histoire=[];self._mouvements=[];self._vies={};self._termines=set();self._numero=0;self._dernier_tick=None

    @property
    def profil_compte(self):
        p=self.configuration.technique.commun
        return ProfilCompte('PAPIER_S5','MEMOIRE','SYNTHETIQUE','STANDARD',p.account_currency,
            p.account_leverage,'HEDGING','PERCENT',Decimal(0),Decimal(0),self.creation_ms)

    @property
    def positions_ouvertes(self): return tuple(self._positions)

    def avancer_au(self,t):
        if type(t) is not int or t<self.instant_ms: raise ValueError('horloge papier non causale')
        self.instant_ms=t

    def specifications(self,symbole): return self.profils[symbole]

    def profit(self,profil,sens,volume,entree,sortie):
        with localcontext(Context(prec=48)):
            return Decimal(sens.signe)*volume*profil.taille_contrat*(sortie-entree)

    def frais_aller_retour(self,profil,sens,volume): return Decimal(0)
    def frais_sortie(self,profil,sens,volume): return Decimal(0)

    def marge(self,profil,sens,volume,entree):
        with localcontext(Context(prec=48)):
            return volume*profil.taille_contrat*entree/Decimal(self.configuration.technique.commun.account_leverage)

    def _prix_sortie(self,p):
        q=self._prix[p.commande.cle.symbole]
        return q[0] if p.commande.cle.sens is Sens.ACHAT else q[1]

    def etat_compte(self):
        flottant=Decimal(0);marge=Decimal(0);positions=[]
        for k,p in self._positions.items():
            profil=self.profils[k.symbole]
            flottant+=self.profit(profil,k.sens,p.volume,p.prix,self._prix_sortie(p))
            marge+=self.marge(profil,k.sens,p.volume,p.prix)
            positions.append(PositionCompte(p.ticket,k.symbole,profil.sous_jacent,p.volume,
                p.commande.donnees['risque_initial'],k))
        return EtatCompte(self.instant_ms,self._solde+flottant,self._solde,marge,tuple(positions))

    def controler(self,ordre,compte,remplacement=False):
        profil=self.profils[ordre.cle.symbole]
        ancienne=next((self.marge(profil,ordre.cle.sens,p.volume,p.prix)
            for k,p in self._positions.items() if k==ordre.cle),Decimal(0)) if remplacement else Decimal(0)
        totale=compte.marge_utilisee-ancienne+self.marge(profil,ordre.cle.sens,ordre.volume,ordre.entree)
        libre=compte.fonds_propres-totale
        return ControleNatif(profil.horaires.ouvert_a(self.instant_ms),totale,libre,
            compte.fonds_propres>0 and libre>=0,'S5_SYNTHETIQUE')

    def base_utc(self):
        borne=self.instant_ms//86_400_000*86_400_000
        absence=not any(ouverture<=borne and (fermeture is None or fermeture>=borne)
            for ouverture,fermeture in self._vies.values())
        return reconstituer_base_utc(self.etat_compte(),tuple(self._mouvements),
            Intervalle(self.creation_ms,self.instant_ms+1),aucune_position_minuit=absence)

    def _reponse(self,nature,cle,donnees,prefixe):
        self._numero+=1
        r=ReponseCourtier(nature,cle,f'S5:{prefixe}:{self._numero}',self.instant_ms,donnees)
        self._histoire.append(r)
        return r

    def _accuse(self,c,statut,code,ordre=None):
        return self._reponse(NatureReponse.ACCUSE,c.cle,dict(commande=c.reference,statut=statut,
            code_natif=code,definitif=statut is StatutAccuse.REFUSE,ordre=ordre),'accuse')

    def observation(self,cle=None):
        positions=[];ordres=[]
        for k,p in self._positions.items():
            d=p.commande.donnees
            positions.append(PositionNative(p.ticket,self.profils[k.symbole].symbole_courtier,p.volume,
                d['magic'],d['commentaire'],sl=p.sl,tp=p.tp))
        for c,ordre in self._entrees.values():
            d=c.donnees
            ordres.append(OrdreNatif(ordre,d['symbole_courtier'],d['volume'],d['magic'],d['commentaire']))
        for ticket,c in self._clotures.items():
            p=next((p for p in self._positions.values() if p.ticket==ticket),None)
            if p is not None:
                d=p.commande.donnees
                ordres.append(OrdreNatif('C:'+c.reference,d['symbole_courtier'],c.donnees['volume'],
                    d['magic'],d['commentaire'],NatureCommande.CLOTURE))
        absences=()
        if cle is not None and cle in self._termines and cle not in self._entrees and cle not in self._positions:
            if not any(r.cle==cle and r.nature is NatureReponse.REMPLISSAGE for r in self._histoire):
                absences=(PreuveAbsence(cle,self.instant_ms,self.creation_ms,self.instant_ms,True,True,True,True,True,True),)
        return ObservationNative(replace(self.etat_compte(),positions=()),self.creation_ms,True,
            tuple(positions),tuple(ordres),tuple(self._histoire),absences)

    def soumettre(self,commandes):
        evenements=[]
        for c in commandes:
            if not isinstance(c,CommandeExecution): raise TypeError('commande C08 requise')
            if c.nature in (NatureCommande.MINUTERIE,NatureCommande.ALERTE): continue
            if c.reference in self._vues: continue
            self._vues.add(c.reference)
            if c.nature is NatureCommande.RAPPROCHEMENT:
                evenements.append(self.observation(c.cle));continue
            if c.nature is NatureCommande.ENTREE:
                profil=self.profils[c.cle.symbole]
                if (c.cle in self._entrees or c.cle in self._positions
                        or self.instant_ms>=c.donnees['expire_ms'] or not profil.horaires.ouvert_a(self.instant_ms)):
                    self._termines.add(c.cle)
                    evenements.append(self._accuse(c,StatutAccuse.REFUSE,'S5_ENTREE_REFUSEE'));continue
                ordre='O:'+c.cle.empreinte(64)
                self._entrees[c.cle]=(c,ordre)
                evenements.append(self._accuse(c,StatutAccuse.ACCEPTE,'S5_ENTREE_ACCEPTEE',ordre));continue
            if c.nature is NatureCommande.ANNULATION:
                for k,(entree,ordre) in tuple(self._entrees.items()):
                    if ordre==c.donnees['ordre']:
                        del self._entrees[k];self._termines.add(k)
                evenements.append(self._reponse(NatureReponse.ANNULATION,c.cle,
                    dict(ordre=c.donnees['ordre'],confirmee=True),'annulation'));continue
            p=self._positions.get(c.cle)
            if p is None or p.ticket!=c.donnees['ticket']:
                evenements.append(self._accuse(c,StatutAccuse.REFUSE,'S5_POSITION_INCONNUE'));continue
            if c.nature is NatureCommande.TP:
                if c.donnees['sl']!=p.sl:
                    evenements.append(self._accuse(c,StatutAccuse.REFUSE,'S5_SL_INCHANGE_REQUIS'));continue
                p.tp=c.donnees['tp']
                evenements.append(self._reponse(NatureReponse.PROTECTIONS,c.cle,
                    dict(ticket=p.ticket,sl=p.sl,tp=p.tp),'protection'));continue
            if c.nature is NatureCommande.CLOTURE:
                precedente=self._clotures.get(p.ticket)
                if precedente is None or c.donnees['volume']>precedente.donnees['volume']:
                    self._clotures[p.ticket]=c
                evenements.append(self._accuse(c,StatutAccuse.ACCEPTE,'S5_CLOTURE_ACCEPTEE'))
        return tuple(evenements)

    def _fermer(self,k,p,volume,prix,cause):
        volume=min(volume,p.volume);profil=self.profils[k.symbole]
        gain=self.profit(profil,k.sens,volume,p.prix,prix)
        self._solde+=gain;p.volume-=volume
        self._numero+=1
        self._mouvements.append(MouvementCompte(f'S5:solde:{self._numero}',self.instant_ms,gain))
        r=self._reponse(NatureReponse.CLOTURE,k,dict(ticket=p.ticket,volume_restant=p.volume,
            prix=prix,execution_ms=self.instant_ms,frais_sortie=Decimal(0),cause=cause),'cloture')
        if not p.volume:
            del self._positions[k];self._vies[k]=(p.premier_fill_ms,self.instant_ms)
            self._termines.add(k)
        return r

    def sur_tick(self,tick):
        if not isinstance(tick,Tick): raise TypeError('tick requis')
        cle=(tick.instant_reception_ms,tick.numero)
        if self._dernier_tick is not None and cle<=self._dernier_tick: raise ValueError('ordre des ticks papier invalide')
        self.avancer_au(tick.instant_reception_ms);self._dernier_tick=cle
        bid,ask=Decimal(str(tick.bid)),Decimal(str(tick.ask));self._prix[tick.symbole]=(bid,ask)
        reponses=[]
        for k,p in tuple(self._positions.items()):
            if k.symbole!=tick.symbole: continue
            prix=bid if k.sens is Sens.ACHAT else ask
            sl=p.sl is not None and (prix<=p.sl if k.sens is Sens.ACHAT else prix>=p.sl)
            tp=p.tp is not None and (prix>=p.tp if k.sens is Sens.ACHAT else prix<=p.tp)
            if sl or tp:
                reponses.append(self._fermer(k,p,p.volume,prix,CauseCloture.STOP_LOSS if sl else CauseCloture.TAKE_PROFIT))
        for ticket,c in tuple(self._clotures.items()):
            p=self._positions.get(c.cle)
            if p is None:
                del self._clotures[ticket];continue
            if c.cle.symbole!=tick.symbole: continue
            prix=bid if c.cle.sens is Sens.ACHAT else ask
            reponses.append(self._fermer(c.cle,p,c.donnees['volume'],prix,c.donnees['cause']))
            del self._clotures[ticket]
        for k,(c,ordre) in tuple(self._entrees.items()):
            if k.symbole!=tick.symbole: continue
            d=c.donnees;prix=ask if k.sens is Sens.ACHAT else bid
            ticket='P:'+k.empreinte(64)
            p=_PositionPapier(c,ticket,ordre,d['volume'],prix,d['sl'],d['tp'],self.instant_ms)
            self._positions[k]=p;self._vies[k]=(self.instant_ms,None)
            del self._entrees[k];self._termines.add(k)
            reponses.append(self._reponse(NatureReponse.REMPLISSAGE,k,dict(transaction='D:'+ticket,ticket=ticket,
                ordre=ordre,volume_cumule=d['volume'],volume_position=p.volume,prix_moyen=prix,
                execution_ms=self.instant_ms,frais_entree=Decimal(0),sl=p.sl,tp=p.tp,
                reliquat=Decimal(0),reliquat_annule=True),'remplissage'))
        return tuple(reponses)


class Moteur(Protocol):
    def traiter_ticks(self,ticks,**kwargs)->SortieMoteur: ...
    def traiter_evenement(self,instant_ms,**kwargs)->SortieMoteur: ...
    def confirmer_persistance(self,preuve,instant_ms)->SortieMoteur: ...
    def alerte(self,code,instant_ms)->Enregistrement: ...
    @property
    def prochaine_echeance_ms(self)->int|None: ...


@dataclass(frozen=True)
class ResultatRejeu:
    nombre_ticks: int
    enregistrements: tuple[Enregistrement, ...]
    reponses: tuple[ReponseCourtier, ...] = field(default=())


def rejouer(ticks: Iterable[Tick],moteur:Moteur,execution:ExecutionPapierMinimale,stockage=None)->ResultatRejeu:
    """Temps simulé et groupes de réception : natif, sorties, bougies, arbitrage, preuve, envoi."""
    stockage=stockage if stockage is not None else StockageMemoirePapier()
    nombre=0;enregistrements=[];reponses=[]

    def transmettre(sortie,instant):
        file=[sortie]
        while file:
            s=file.pop(0);enregistrements.extend(s.enregistrements)
            entrees=[c for c in s.commandes if c.nature is NatureCommande.ENTREE]
            autres=[c for c in s.commandes if c.nature is not NatureCommande.ENTREE]
            evenements=list(execution.soumettre(autres))
            preuve=None
            try:
                if s.lot is not None: preuve=stockage.persister(s.lot)
            except (OSError,ValueError):
                enregistrements.append(moteur.alerte('STOCKAGE_PAPIER_INDISPONIBLE',instant))
            if entrees and preuve is not None:
                evenements.extend(execution.soumettre(entrees))
            nouvelles=tuple(e for e in evenements if isinstance(e,ReponseCourtier))
            reponses.extend(nouvelles)
            observations=[e for e in evenements if isinstance(e,ObservationNative)]
            if evenements:
                file.append(moteur.traiter_evenement(instant,reponses=nouvelles,
                    observation=observations[-1] if observations else None,base_utc=execution.base_utc()))
            elif s.lot is not None and s.lot.preparations and preuve is not None:
                file.append(moteur.confirmer_persistance(preuve,instant))

    for instant,groupe in groupby(ticks,key=lambda t:t.instant_reception_ms):
        groupe=tuple(groupe)
        while moteur.prochaine_echeance_ms is not None and moteur.prochaine_echeance_ms<instant:
            echeance=moteur.prochaine_echeance_ms
            execution.avancer_au(echeance)
            transmettre(moteur.traiter_evenement(echeance,base_utc=execution.base_utc()),echeance)
        natifs=tuple(r for t in groupe for r in execution.sur_tick(t))
        nombre+=len(groupe);reponses.extend(natifs)
        transmettre(moteur.traiter_ticks(groupe,reponses=natifs,base_utc=execution.base_utc()),instant)
    return ResultatRejeu(nombre,tuple(enregistrements),tuple(reponses))

"""Le livre natif est distinct du coordinateur ; aucune admission de stratégie ici."""
from dataclasses import dataclass,replace
from decimal import Context,Decimal,localcontext
from types import MappingProxyType
from typing import Mapping

from xpbots.noyau.c0a_temps import instant_vers_datetime
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1b_instrument import Intervalle,ProfilCompte
from xpbots.noyau.c1c_domaine import CauseCloture,Sens
from xpbots.execution.c0a_types import EtatCompte,PositionCompte,ControleNatif
from xpbots.execution.c1b_gardes import MouvementCompte,reconstituer_base_utc
from xpbots.execution.c4_cycle import (CommandeExecution,NatureCommande,ReponseCourtier,
    NatureReponse,StatutAccuse,PreuveAbsence)
from xpbots.execution.c5b_reprise import ObservationNative,PositionNative,OrdreNatif
from xpbots.rejeu.c0a_types import (ErreurRejeu,ConditionContrat,PointCompte,Trade,instant,
    entier,montant)
from xpbots.rejeu.c0b_protocole import ScenarioExecution

D=Decimal


@dataclass(frozen=True)
class PlanExecution:
    statut:StatutAccuse=StatutAccuse.ACCEPTE
    retard_accuse_ms:int=0
    fractions:tuple=(D(1),)
    retards_ms:tuple=(0,)
    reliquat_annule:bool=True
    protections:bool=True
    mise_a_jour:bool=True

    def __post_init__(self):
        if not isinstance(self.statut,StatutAccuse):raise ErreurRejeu('statut natif typé requis')
        entier(self.retard_accuse_ms)
        fractions=tuple(self.fractions);retards=tuple(self.retards_ms)
        if not fractions or len(fractions)!=len(retards):raise ErreurRejeu('fractions et délais concordants requis')
        for f in fractions:montant(f,D(0),True)
        for t in retards:entier(t)
        if sum(fractions)>1 or any(b<a for a,b in zip(retards,retards[1:])):
            raise ErreurRejeu('plan natif non causal')
        if any(type(v) is not bool for v in (self.reliquat_annule,self.protections,self.mise_a_jour)):
            raise ErreurRejeu('options natives booléennes requises')
        object.__setattr__(self,'fractions',fractions);object.__setattr__(self,'retards_ms',retards)


@dataclass
class _Entree:
    commande:CommandeExecution
    ordre:str
    plan:PlanExecution
    envoi_ms:int
    index:int=0
    volume_cumule:Decimal=D(0)
    montant_cumule:Decimal=D(0)
    frais:Decimal=D(0)
    frais_variables:Decimal=D(0)
    frais_minimum:Decimal=D(0)


@dataclass
class _Position:
    commande:CommandeExecution
    ticket:str
    ordre:str
    volume:Decimal
    prix:Decimal
    sl:Decimal|None
    tp:Decimal|None
    premier_fill_ms:int
    profil:object
    volume_total:Decimal=D(0)
    frais_entree:Decimal=D(0)
    profit_realise:Decimal=D(0)
    frais_sortie:Decimal=D(0)
    volume_sorti:Decimal=D(0)
    montant_sorti:Decimal=D(0)
    montant_entree:Decimal=D(0)


class SimulateurExecution:
    def __init__(self,configuration,conditions,creation_ms,scenario,plans=None):
        if not isinstance(configuration,ConfigurationFigee) or not isinstance(scenario,ScenarioExecution):
            raise ErreurRejeu('configuration et scénario explicites requis')
        instant(creation_ms)
        conditions=tuple(conditions)
        if not conditions or any(not isinstance(c,ConditionContrat) for c in conditions):
            raise ErreurRejeu('conditions contractuelles datées requises')
        self.configuration=configuration;self.scenario=scenario
        self.creation_ms=creation_ms;self.instant_ms=creation_ms
        self._conditions={}
        devise=configuration.technique.commun.account_currency
        for c in sorted(conditions,key=lambda c:(c.profil.symbole,c.debut_ms)):
            p=c.profil
            if p.devise_cotation!=devise or p.devise_marge!=devise or p.devise_frais!=devise:
                raise ErreurRejeu('modèle de calcul réservé aux contrats cotés dans la devise du compte')
            serie=self._conditions.setdefault(p.symbole,[])
            if serie and (serie[-1].fin_ms>c.debut_ms or serie[-1].profil.symbole_courtier!=p.symbole_courtier
                          or serie[-1].profil.sous_jacent!=p.sous_jacent):
                raise ErreurRejeu('conditions superposées ou liaison native modifiée')
            serie.append(c)
        self._plans=dict(plans or {})
        if any(type(k) is not str or not isinstance(v,PlanExecution) for k,v in self._plans.items()):
            raise ErreurRejeu('plans natifs par référence requis')
        self._solde=D(str(configuration.technique.commun.initial_equity_usd))
        self._positions={};self._entrees={};self._clotures={};self._prix={};self._vues=set()
        self._histoire=[];self._mouvements=[];self._vies={};self._termines=set();self._numero=0
        self._differes=[];self._dernier_tick=None;self._courbe=[PointCompte(creation_ms,self._solde,self._solde,D(0))]
        self._trades=[];self._contextes={};self._premiers=[]

    def _condition(self,symbole):
        c=next((c for c in self._conditions.get(symbole,()) if c.connue_a(self.instant_ms)
                and c.profil.releve_ms<=self.instant_ms),None)
        if c is None:raise ErreurRejeu('conditions historiques absentes ou inconnues à cet instant')
        return c

    @property
    def profils(self):return MappingProxyType({s:self.specifications(s) for s in self._conditions})
    @property
    def profil_compte(self):
        c=self.configuration.technique.commun
        return ProfilCompte('SIMULATEUR_C10','MEMOIRE','SYNTHETIQUE','STANDARD',c.account_currency,
            c.account_leverage,'HEDGING','PERCENT',D(0),D(0),self.creation_ms)
    @property
    def positions_ouvertes(self):return tuple(self._positions)
    @property
    def courbe(self):return tuple(self._courbe)
    @property
    def trades(self):return tuple(self._trades)
    @property
    def reponses(self):return tuple(self._histoire)
    @property
    def premiers_remplissages(self):return tuple(self._premiers)
    @property
    def prochaine_echeance_ms(self):return min((t for t,*_ in self._differes),default=None)

    def enregistrer_contexte(self,cle,contexte):
        if cle in self._contextes:raise ErreurRejeu('contexte causal déjà enregistré')
        def figer(v):
            if isinstance(v,Mapping):return MappingProxyType({k:figer(x) for k,x in v.items()})
            if isinstance(v,(tuple,list)):return tuple(figer(x) for x in v)
            return v
        self._contextes[cle]=figer(contexte)

    def avancer_au(self,t):
        instant(t)
        if t<self.instant_ms:raise ErreurRejeu('horloge simulée en recul')
        if self._positions:
            c=self.configuration.technique.commun
            debut=c.rollover_blackout_utc_start
            for p in self._positions.values():
                jour=instant_vers_datetime(p.premier_fill_ms)
                borne=jour.replace(hour=debut.hour,minute=debut.minute,second=debut.second,microsecond=0)
                if instant_vers_datetime(t)>=borne:
                    raise ErreurRejeu('POSITION_TRAVERSE_BLACKOUT : erreur de code')
        self.instant_ms=t

    def specifications(self,symbole):return self._condition(symbole).profil

    def profit(self,profil,sens,volume,entree,sortie):
        with localcontext(Context(prec=48)):
            return D(sens.signe)*volume*profil.taille_contrat*(sortie-entree)

    def frais_aller_retour(self,profil,sens,volume):
        t=self._condition(profil.symbole).tarif
        with localcontext(Context(prec=48)):return t.entree(volume)+t.sortie(volume)

    def frais_sortie(self,profil,sens,volume):return self._condition(profil.symbole).tarif.sortie(volume)

    def marge(self,profil,sens,volume,entree):
        with localcontext(Context(prec=48)):
            return volume*profil.taille_contrat*entree/D(self.configuration.technique.commun.account_leverage)

    def etat_compte(self):
        flottant=D(0);marge=D(0);positions=[]
        with localcontext(Context(prec=48)):
            for cle,p in self._positions.items():
                bid,ask=self._prix[cle.symbole]
                prix=bid if cle.sens is Sens.ACHAT else ask
                flottant+=self.profit(p.profil,cle.sens,p.volume,p.prix,prix)
                marge+=self.marge(self.specifications(cle.symbole),cle.sens,p.volume,p.prix)
                positions.append(PositionCompte(p.ticket,cle.symbole,p.profil.sous_jacent,p.volume,
                    p.commande.donnees['risque_initial'],cle))
            return EtatCompte(self.instant_ms,self._solde+flottant,self._solde,marge,tuple(positions))

    def controler(self,ordre,compte,remplacement=False):
        profil=self.specifications(ordre.cle.symbole)
        ancienne=D(0)
        if remplacement and ordre.cle in self._positions:
            p=self._positions[ordre.cle];ancienne=self.marge(profil,ordre.cle.sens,p.volume,p.prix)
        with localcontext(Context(prec=48)):
            totale=compte.marge_utilisee-ancienne+self.marge(profil,ordre.cle.sens,ordre.volume,ordre.entree)
            libre=compte.fonds_propres-totale
        return ControleNatif(profil.horaires.ouvert_a(self.instant_ms),totale,libre,
            compte.fonds_propres>0 and libre>=0,'SIMULATION_C10')

    def base_utc(self):
        moment=instant_vers_datetime(self.instant_ms)
        debut=moment.replace(hour=0,minute=0,second=0,microsecond=0)
        absence=not any(instant_vers_datetime(a)<=debut and (b is None or instant_vers_datetime(b)>=debut)
            for a,b in self._vies.values())
        return reconstituer_base_utc(self.etat_compte(),tuple(self._mouvements),
            Intervalle(self.creation_ms,self.instant_ms+1),aucune_position_minuit=absence)

    def _point(self):
        c=self.etat_compte();self._courbe.append(PointCompte(c.instant_ms,c.fonds_propres,c.solde,c.marge_utilisee))

    def _mouvement(self,variation):
        self._numero+=1
        self._mouvements.append(MouvementCompte(f'C10:solde:{self._numero}',self.instant_ms,variation))
        self._solde+=variation

    def _reponse(self,nature,cle,donnees):
        self._numero+=1
        r=ReponseCourtier(nature,cle,f'C10:natif:{self._numero}',self.instant_ms,donnees)
        self._histoire.append(r);return r

    def _accuse(self,c,statut,code,ordre=None):
        return self._reponse(NatureReponse.ACCUSE,c.cle,dict(commande=c.reference,statut=statut,
            code_natif=code,definitif=statut is StatutAccuse.REFUSE,ordre=ordre))

    def extraire_reponses(self,t):
        self.avancer_au(t);pretes=[];futures=[]
        for echeance,c,statut,code,ordre in self._differes:
            if echeance<=t:pretes.append(self._accuse(c,statut,code,ordre))
            else:futures.append((echeance,c,statut,code,ordre))
        self._differes=futures
        return tuple(pretes)

    def observation(self,cle=None):
        positions=[];ordres=[]
        for k,p in self._positions.items():
            d=p.commande.donnees
            positions.append(PositionNative(p.ticket,p.profil.symbole_courtier,p.volume,d['magic'],d['commentaire'],sl=p.sl,tp=p.tp))
        for a in self._entrees.values():
            d=a.commande.donnees
            ordres.append(OrdreNatif(a.ordre,d['symbole_courtier'],d['volume']-a.volume_cumule,d['magic'],d['commentaire']))
        for ticket,(c,_) in self._clotures.items():
            p=self._positions.get(c.cle)
            if p is not None:
                d=p.commande.donnees
                ordres.append(OrdreNatif('C:'+c.reference,p.profil.symbole_courtier,min(p.volume,c.donnees['volume']),
                    d['magic'],d['commentaire'],NatureCommande.CLOTURE))
        absences=()
        if cle is not None and cle in self._termines and cle not in self._entrees and cle not in self._positions:
            if not any(r.cle==cle and r.nature is NatureReponse.REMPLISSAGE for r in self._histoire):
                absences=(PreuveAbsence(cle,self.instant_ms,self.creation_ms,self.instant_ms,True,True,True,True,True,True),)
        return ObservationNative(replace(self.etat_compte(),positions=()),self.creation_ms,True,
            tuple(positions),tuple(ordres),tuple(self._histoire),absences)

    def soumettre(self,commandes):
        reponses=[]
        for c in commandes:
            if not isinstance(c,CommandeExecution):raise TypeError('commande C08 requise')
            if c.instant_ms>self.instant_ms:raise ErreurRejeu('commande future')
            if c.nature in (NatureCommande.MINUTERIE,NatureCommande.ALERTE) or c.reference in self._vues:continue
            self._vues.add(c.reference);plan=self._plans.get(c.reference,PlanExecution())
            if c.nature is NatureCommande.RAPPROCHEMENT:
                reponses.append(self.observation(c.cle));continue
            if c.nature is NatureCommande.ENTREE:
                profil=self.specifications(c.cle.symbole)
                if (c.cle in self._positions or c.cle in self._entrees or self.instant_ms>=c.donnees['expire_ms']
                        or not profil.horaires.ouvert_a(self.instant_ms) or plan.statut is StatutAccuse.REFUSE):
                    self._termines.add(c.cle)
                    reponses.append(self._accuse(c,StatutAccuse.REFUSE,'C10_ENTREE_REFUSEE'));continue
                ordre='O:'+c.cle.empreinte(64)
                self._entrees[c.cle]=_Entree(c,ordre,plan,self.instant_ms)
                if plan.retard_accuse_ms:self._differes.append((self.instant_ms+plan.retard_accuse_ms,c,plan.statut,'C10_ENTREE',ordre))
                else:reponses.append(self._accuse(c,plan.statut,'C10_ENTREE',ordre))
                continue
            if c.nature is NatureCommande.ANNULATION:
                for k,a in tuple(self._entrees.items()):
                    if a.ordre==c.donnees['ordre']:del self._entrees[k];self._termines.add(k)
                reponses.append(self._reponse(NatureReponse.ANNULATION,c.cle,dict(ordre=c.donnees['ordre'],confirmee=True)));continue
            p=self._positions.get(c.cle)
            if p is None or p.ticket!=c.donnees['ticket']:
                reponses.append(self._accuse(c,StatutAccuse.REFUSE,'C10_POSITION_INCONNUE'));continue
            if c.nature is NatureCommande.TP:
                if not plan.mise_a_jour or c.donnees['sl']!=p.sl:
                    reponses.append(self._accuse(c,StatutAccuse.REFUSE,'C10_PROTECTION_REFUSEE'));continue
                p.tp=c.donnees['tp']
                reponses.append(self._reponse(NatureReponse.PROTECTIONS,c.cle,dict(ticket=p.ticket,sl=p.sl,tp=p.tp)))
            elif c.nature is NatureCommande.CLOTURE:
                ancienne=self._clotures.get(p.ticket)
                if ancienne is None or c.donnees['volume']>ancienne[0].donnees['volume']:
                    self._clotures[p.ticket]=(c,self.instant_ms+self.scenario.delai_ms)
                reponses.append(self._accuse(c,StatutAccuse.ACCEPTE,'C10_CLOTURE'))
        return tuple(reponses)

    def tick_decision(self,tick):
        if not isinstance(tick,Tick):raise TypeError('tick requis')
        with localcontext(Context(prec=48)):
            bid=D(str(tick.bid));ask=bid+(D(str(tick.ask))-bid)*self.scenario.facteur_spread
        if ask<bid:raise ErreurRejeu('spread négatif')
        return replace(tick,ask=float(ask))

    def _adverse(self,prix,sens,symbole,entree):
        signe=sens.signe if entree else -sens.signe
        with localcontext(Context(prec=48)):
            resultat=prix+D(signe)*D(self.scenario.ticks_adverses)*self.specifications(symbole).tick_size
        if resultat<=0:raise ErreurRejeu('prix adverse non positif')
        return resultat

    def _fermer(self,cle,p,volume,prix,cause):
        volume=min(volume,p.volume)
        with localcontext(Context(prec=48)):
            brut=self.profit(p.profil,cle.sens,volume,p.prix,prix)
            frais=self._condition(cle.symbole).tarif.sortie(volume)
            self._mouvement(brut-frais)
            p.volume-=volume;p.profit_realise+=brut;p.frais_sortie+=frais
            p.volume_sorti+=volume;p.montant_sorti+=volume*prix
            r=self._reponse(NatureReponse.CLOTURE,cle,dict(ticket=p.ticket,volume_restant=p.volume,
                prix=prix,execution_ms=self.instant_ms,frais_sortie=frais,cause=cause))
            if not p.volume:
                self._trades.append(Trade(cle,p.premier_fill_ms,self.instant_ms,p.volume_total,p.montant_entree/p.volume_total,
                    p.montant_sorti/p.volume_sorti,p.profit_realise,p.frais_entree,p.frais_sortie,
                    p.commande.donnees['risque_initial']*(p.volume_total/p.commande.donnees['volume']),cause,
                    self._contextes.get(cle,{})))
                del self._positions[cle];self._vies[cle]=(p.premier_fill_ms,self.instant_ms);self._termines.add(cle)
                self._clotures.pop(p.ticket,None)
        self._point();return r

    def _proteger(self,cle,p,bid,ask):
        prix=bid if cle.sens is Sens.ACHAT else ask
        sl=p.sl is not None and (prix<=p.sl if cle.sens is Sens.ACHAT else prix>=p.sl)
        tp=p.tp is not None and (prix>=p.tp if cle.sens is Sens.ACHAT else prix<=p.tp)
        if sl or tp:
            prix=self._adverse(prix,cle.sens,cle.symbole,False) if sl else prix
            return self._fermer(cle,p,p.volume,prix,CauseCloture.STOP_LOSS if sl else CauseCloture.TAKE_PROFIT)
        return None

    def sur_tick(self,tick):
        if not isinstance(tick,Tick):raise TypeError('tick requis')
        cle_tick=(tick.instant_reception_ms,tick.numero)
        if self._dernier_tick is not None and cle_tick<=self._dernier_tick:raise ErreurRejeu('ordre natif des ticks invalide')
        self.avancer_au(tick.instant_reception_ms);self._dernier_tick=cle_tick
        self._condition(tick.symbole)
        q=self.tick_decision(tick);bid,ask=D(str(q.bid)),D(str(q.ask));self._prix[tick.symbole]=(bid,ask)
        reponses=list(self.extraire_reponses(self.instant_ms))
        for cle,p in tuple(self._positions.items()):
            if cle.symbole==tick.symbole:
                r=self._proteger(cle,p,bid,ask)
                if r is not None:reponses.append(r)
        for ticket,(c,echeance) in tuple(self._clotures.items()):
            p=self._positions.get(c.cle)
            if p is None:self._clotures.pop(ticket,None);continue
            if c.cle.symbole==tick.symbole and self.instant_ms>=echeance:
                prix=bid if c.cle.sens is Sens.ACHAT else ask
                reponses.append(self._fermer(c.cle,p,c.donnees['volume'],self._adverse(prix,c.cle.sens,c.cle.symbole,False),c.donnees['cause']))
                self._clotures.pop(ticket,None)
        for cle,a in tuple(self._entrees.items()):
            if cle.symbole!=tick.symbole or a.index>=len(a.plan.fractions):continue
            if self.instant_ms<a.envoi_ms+self.scenario.delai_ms+a.plan.retards_ms[a.index]:continue
            profil=self.specifications(cle.symbole)
            if not profil.horaires.ouvert_a(self.instant_ms):continue
            d=a.commande.donnees
            with localcontext(Context(prec=48)):
                volume=d['volume']*a.plan.fractions[a.index]
                if volume%profil.volume_pas or volume<=0:raise ErreurRejeu('fraction native hors pas de volume')
                prix=self._adverse(ask if cle.sens is Sens.ACHAT else bid,cle.sens,cle.symbole,True)
                a.volume_cumule+=volume;a.montant_cumule+=volume*prix;a.index+=1
                tarif=self._condition(cle.symbole).tarif
                a.frais_variables+=tarif.entree_par_lot*volume
                a.frais_minimum=max(a.frais_minimum,tarif.minimum_entree)
                frais_cumules=max(a.frais_variables,a.frais_minimum)
                frais=frais_cumules-a.frais;a.frais=frais_cumules;self._mouvement(-frais)
                p=self._positions.get(cle)
                if p is None:
                    p=_Position(a.commande,'P:'+cle.empreinte(64),a.ordre,D(0),prix,
                        d['sl'] if a.plan.protections else None,d['tp'] if a.plan.protections else None,self.instant_ms,profil)
                    self._positions[cle]=p;self._vies[cle]=(self.instant_ms,None);self._premiers.append((cle,self.instant_ms))
                p.prix=(p.volume*p.prix+volume*prix)/(p.volume+volume)
                p.volume+=volume;p.volume_total+=volume;p.frais_entree+=frais;p.montant_entree+=volume*prix
                termine=a.index==len(a.plan.fractions)
                reliquat=d['volume']-a.volume_cumule
                annule=termine and a.plan.reliquat_annule
                reponses.append(self._reponse(NatureReponse.REMPLISSAGE,cle,dict(transaction=f'D:{a.ordre}:{a.index}',
                    ticket=p.ticket,ordre=a.ordre,volume_cumule=a.volume_cumule,volume_position=p.volume,
                    prix_moyen=a.montant_cumule/a.volume_cumule,execution_ms=self.instant_ms,frais_entree=a.frais,
                    sl=p.sl,tp=p.tp,reliquat=reliquat,reliquat_annule=annule or not reliquat)))
                if not reliquat or annule:del self._entrees[cle];self._termines.add(cle)
            self._point()
            r=self._proteger(cle,p,bid,ask)
            if r is not None:reponses.append(r)
        self._point()
        return tuple(reponses)

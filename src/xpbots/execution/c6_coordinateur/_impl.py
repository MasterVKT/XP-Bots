"""Orchestration pure d'un compte : aucun accès au terminal, stockage ou réseau."""
from collections.abc import Mapping
from dataclasses import dataclass, replace, fields
from datetime import timedelta
from decimal import Decimal

from xpbots.execution.c0a_types import EtatCompte, EtatIntention, ErreurExecution, RefusExecution, instant, texte
from xpbots.execution.c0b_controles import ComplementAbsent, ControleTechniqueNeutre
from xpbots.execution.c0c_cotation import EtatCotation, evaluer_cotation
from xpbots.execution.c0d_prix import NiveauxExecutables, construire_niveaux
from xpbots.execution.c0e_echeances import premiere_echeance
from xpbots.execution.c1a_calcul import appeler_calcul
from xpbots.execution.c1b_gardes import GardesCompte
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.execution.c2a_risque import verifier_profil
from xpbots.execution.c2b_arbitrage import candidats_admission
from xpbots.execution.c3_dimensionnement import PlanDimensionnement, dimensionner, revalider_avant_envoi
from xpbots.execution.c4_cycle import (CycleOrdre, CommandeExecution, NatureCommande, ReponseCourtier,
    NatureReponse, PreuvePersistance, TraceCycle)
from xpbots.execution.c5a_sorties import evaluer_sorties
from xpbots.execution.c5b_reprise import CyclePersiste, EtatReprise, ObservationNative, restaurer, rapprocher
from xpbots.noyau.c0c_configuration import ExportTechnique
from xpbots.noyau.c1a_marche import Cotation
from xpbots.noyau.c1b_instrument import ProfilInstrument, ProfilCompte, construire_profil_compte
from xpbots.noyau.c1c_domaine import (CleIntention, SignalTechnique, Issue, NatureIssue,
    DecisionFondamentale, DecisionContexteIA, ContexteIA, Motif)
from xpbots.noyau.c2_journal import MODES, TypeEnregistrement

_TERMINAUX = (EtatIntention.REFUSEE, EtatIntention.EXPIREE, EtatIntention.CLOTUREE)
_CAUSES = (None, 'SPREAD_CAP', 'ENTRY_GAP', 'COTATION_INVALIDE', 'AUCUNE_COTATION')


def _ms(secondes):
    return timedelta(seconds=secondes) // timedelta(milliseconds=1)


@dataclass(frozen=True)
class TentativeCotation:
    instant_ms: int
    cause: str | None
    bid: Decimal | None = None
    ask: Decimal | None = None
    fournisseur_ms: int | None = None
    reception_ms: int | None = None

    def __post_init__(self):
        instant(self.instant_ms)
        if self.cause not in _CAUSES: raise ErreurExecution('cause de cotation inconnue')
        if any(v is not None for v in (self.bid,self.ask,self.fournisseur_ms,self.reception_ms)):
            Cotation('controle',self.bid,self.ask,self.fournisseur_ms,self.reception_ms)
            if self.fournisseur_ms > self.instant_ms or self.reception_ms > self.instant_ms:
                raise ErreurExecution('tentative utilisant une cotation future')


@dataclass(frozen=True)
class DossierIntention:
    cle: CleIntention
    signal: SignalTechnique
    statut: EtatIntention = EtatIntention.EN_ATTENTE_COTATION
    derniere_cause: str | None = None
    tentatives: tuple[TentativeCotation, ...] = ()
    issue: Issue | None = None

    def __post_init__(self):
        if not isinstance(self.cle,CleIntention) or not isinstance(self.signal,SignalTechnique):
            raise ErreurExecution('clé et signal réels attendus')
        if (self.cle.strategie,self.cle.symbole,self.cle.cloture_ms,self.cle.sens) != (self.signal.strategie,self.signal.symbole,self.signal.cloture_ms,self.signal.sens):
            raise ErreurExecution('intention incohérente')
        if not isinstance(self.statut,EtatIntention) or self.derniere_cause not in _CAUSES:
            raise ErreurExecution('état d’intention invalide')
        ts=tuple(self.tentatives)
        if any(not isinstance(t,TentativeCotation) for t in ts) or any(a.instant_ms>b.instant_ms for a,b in zip(ts,ts[1:])):
            raise ErreurExecution('tentatives non causales')
        if self.issue is not None and (not isinstance(self.issue,Issue) or self.issue.cle!=self.cle):
            raise ErreurExecution('issue d’une autre intention')
        object.__setattr__(self,'tentatives',ts)


@dataclass(frozen=True)
class EtatCoordinateur:
    reprise: EtatReprise = EtatReprise()
    intentions: tuple[DossierIntention, ...] = ()
    preparations: tuple[CommandeExecution, ...] = ()
    transmises: tuple[str, ...] = ()
    revision: int = 0
    dernier_ms: int = 0
    demarrage_valide: bool = False
    exclusivites: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.reprise,EtatReprise): raise ErreurExecution('reprise réelle attendue')
        instant(self.dernier_ms)
        if type(self.revision) is not int or self.revision<0 or type(self.demarrage_valide) is not bool:
            raise ErreurExecution('révision ou démarrage invalide')
        for nom,classe,identifiant in (('intentions',DossierIntention,'cle'),('preparations',CommandeExecution,'reference')):
            vs=tuple(getattr(self,nom))
            if any(not isinstance(v,classe) for v in vs) or len({getattr(v,identifiant) for v in vs})!=len(vs):
                raise ErreurExecution('éléments uniques attendus')
            object.__setattr__(self,nom,vs)
        if any(c.nature is not NatureCommande.ENTREE for c in self.preparations):
            raise ErreurExecution('préparation sans entrée')
        for nom in ('transmises','exclusivites'):
            vs=tuple(getattr(self,nom))
            for v in vs: texte(v)
            if len(set(vs))!=len(vs): raise ErreurExecution('références dupliquées')
            object.__setattr__(self,nom,vs)


@dataclass(frozen=True)
class LotCoordinateur:
    etat: EtatCoordinateur
    commandes: tuple[CommandeExecution, ...] = ()
    issues: tuple[Issue, ...] = ()
    traces: tuple[TraceCycle, ...] = ()
    compte: EtatCompte | None = None

    def __post_init__(self):
        if not isinstance(self.etat,EtatCoordinateur): raise ErreurExecution('état du lot attendu')
        if self.compte is not None and not isinstance(self.compte,EtatCompte): raise ErreurExecution('compte du lot attendu')
        for nom,classe in (('commandes',CommandeExecution),('issues',Issue),('traces',TraceCycle)):
            vs=tuple(getattr(self,nom))
            if any(not isinstance(v,classe) for v in vs): raise ErreurExecution('lot mal typé')
            object.__setattr__(self,nom,vs)

    @property
    def preparations(self): return self.etat.preparations


class CoordinateurCompte:
    def __init__(self,technique,deploiement,profils,profil_compte,port,fondamental,instant_ms,*,
                 longueur_empreinte,contexte=None,mode=None,etat=None,observation=None,base_utc=None):
        instant(instant_ms); texte(deploiement)
        if not isinstance(technique,ExportTechnique) or not isinstance(profils,Mapping) or not isinstance(profil_compte,ProfilCompte):
            raise ErreurExecution('configuration et profils C04 attendus')
        if any(not isinstance(p,ProfilInstrument) or p.symbole!=s for s,p in profils.items()) or len({p.sous_jacent for p in profils.values()})!=len(profils):
            raise ErreurExecution('liaison unique des instruments attendue')
        if mode is not None and mode not in MODES: raise ErreurExecution('mode inconnu')
        self._technique,self._p,self._deploiement=technique,technique.commun,deploiement
        self._profils,self._port,self._fondamental=dict(profils),port,fondamental
        self._contexte=contexte if contexte is not None else ComplementAbsent()
        self._longueur,self._mode=longueur_empreinte,mode or technique.commun.default_mode
        mode_marge=profil_compte.mode_marge.upper() if isinstance(profil_compte.mode_marge,str) else ''
        self._netting=mode_marge=='NETTING'
        qualification=construire_profil_compte({f.name:getattr(profil_compte,f.name) for f in fields(ProfilCompte)},self._p)
        self._refus_qualification=None
        if (qualification.non_prets or profil_compte.type_compte.upper()!='STANDARD' or mode_marge not in ('NETTING','HEDGING')
                or profil_compte.releve_ms>instant_ms):
            self._refus_qualification=RefusExecution(Motif.ENVIRONMENT_NOT_READY,'qualification_compte')
        if isinstance(fondamental,ControleTechniqueNeutre) and self._mode in ('DEMO','REEL'):
            self._refus_qualification=RefusExecution(Motif.ENVIRONMENT_NOT_READY,'scenario_technique_interdit')
        if etat is not None and not isinstance(etat,EtatCoordinateur): raise ErreurExecution('état réel attendu')
        sauvegarde=etat or EtatCoordinateur()
        if sauvegarde.dernier_ms>instant_ms: raise ErreurExecution('restauration future')
        if any(v.etat.cle.deploiement!=deploiement for v in sauvegarde.reprise.cycles) or any(v.cle.deploiement!=deploiement for v in sauvegarde.intentions):
            raise ErreurExecution('état d’un autre déploiement')
        dossiers={d.cle:d for d in sauvegarde.intentions}
        if any(v.etat.cle not in dossiers or dossiers[v.etat.cle].signal!=v.signal or dossiers[v.etat.cle].statut!=v.etat.statut
               for v in sauvegarde.reprise.cycles):
            raise ErreurExecution('cycle sans intention concordante')
        self._intentions={d.cle:d for d in sauvegarde.intentions}
        self._preparations={}
        self._transmises=set(sauvegarde.transmises)
        self._revision,self._dernier_ms=sauvegarde.revision,instant_ms
        self._demarrage_valide=False; self._exclusivites=()
        self._compte=None; self._erreur_compte=None; self._refus_reprise=None
        self._refus_sorties=None; self._cotations={}
        self._echeance_sortie=None
        self._commandes_initiales=[]; self._issues_initiales=[]; self._traces_initiales=[]
        b=restaurer(self._p,sauvegarde.reprise,longueur_empreinte,instant_ms)
        self._charger(b.etat)
        for k in self._cycles: self._actualiser_dossier(k)
        self._commandes_initiales.extend(b.commandes)
        for k,d in tuple(self._intentions.items()):
            if d.statut is EtatIntention.EN_ATTENTE_COTATION:
                issue=Issue(k,NatureIssue.REFUSEE,instant_ms,Motif.ENVIRONMENT_NOT_READY,'reprise_sans_entree_retroactive')
                self._intentions[k]=replace(d,statut=EtatIntention.REFUSEE,issue=issue)
                self._issues_initiales.append(issue)
        if observation is not None:
            self._appliquer_observation(observation,base_utc,self._commandes_initiales,self._issues_initiales,self._traces_initiales)

    def _charger(self,etat):
        self._registre=RegistreReservations(self._p,etat.reservations)
        self._gardes=GardesCompte(self._p,etat.gardes)
        self._fiches={v.etat.cle:v for v in etat.cycles}
        self._cycles={k:CycleOrdre(self._p,v.signal,v.plan,v.profil,self._longueur,v.etat) for k,v in self._fiches.items()}

    def _reprise(self):
        return EtatReprise(tuple(replace(v,etat=self._cycles[k].etat) for k,v in self._fiches.items()),self._registre.etat,self._gardes.etat)

    @property
    def etat(self):
        return EtatCoordinateur(self._reprise(),tuple(self._intentions.values()),tuple(self._preparations.values()),
            tuple(sorted(self._transmises)),self._revision,self._dernier_ms,self._demarrage_valide,self._exclusivites)

    @property
    def prochaine_echeance_ms(self):
        dates=[d.signal.cloture_ms+_ms(self._p.entry_signal_ttl_seconds) for d in self._intentions.values()
               if d.statut is EtatIntention.EN_ATTENTE_COTATION or any(c.cle==d.cle for c in self._preparations.values())]
        dates.extend(c.prochaine_echeance_ms for c in self._cycles.values() if c.prochaine_echeance_ms is not None)
        if any(c.etat.volume_ouvert for c in self._cycles.values()):
            dates.append(self._dernier_ms+_ms(self._p.exit_retry_interval_seconds))
        if self._echeance_sortie is not None and self._echeance_sortie>self._dernier_ms: dates.append(self._echeance_sortie)
        return min(dates) if dates else None

    def _toucher(self,t):
        instant(t)
        if t<self._dernier_ms: raise ErreurExecution('événement antérieur')
        self._dernier_ms=t

    def _lot(self,commandes=(),issues=(),traces=()):
        self._revision+=1
        commandes=tuple(c for c in commandes if c.nature not in (NatureCommande.CLOTURE,NatureCommande.TP,NatureCommande.ANNULATION)
            or c.cle in self._cycles and self._cycles[c.cle].etat.statut not in _TERMINAUX)
        return LotCoordinateur(self.etat,commandes,tuple(issues),tuple(traces),self._compte)

    def _actualiser_dossier(self,k,issue=None):
        d=self._intentions.get(k)
        if d is not None:
            self._intentions[k]=replace(d,statut=self._cycles[k].etat.statut,issue=issue or d.issue)

    def _accumuler(self,k,effets,commandes,issues,traces):
        for c in effets.commandes:
            if c.nature is NatureCommande.ENTREE: self._preparations[c.reference]=c
            else: commandes.append(c)
        traces.extend(effets.traces)
        for i in effets.issues:
            self._registre.sur_issue(i); issues.append(i)
            self._actualiser_dossier(k,i)
        self._actualiser_dossier(k)
        e=self._cycles[k].etat
        if e.inconnu_ms is not None: self._registre.verrouiller(self._fiches[k].profil.sous_jacent)
        if e.accuse_recu:
            self._transmises.update(ref for ref,c in self._preparations.items() if c.cle==k)
        if e.accuse_recu or e.quota_compte or e.statut in _TERMINAUX:
            self._preparations={ref:c for ref,c in self._preparations.items() if c.cle!=k}

    def _appliquer_observation(self,o,base,commandes,issues,traces):
        if not isinstance(o,ObservationNative) or o.compte.instant_ms!=self._dernier_ms:
            raise ErreurExecution('observation du même instant attendue')
        b=rapprocher(self._p,self._reprise(),self._longueur,o,netting=self._netting,reconstitution=base)
        deja=self._demarrage_valide
        self._charger(b.etat); self._compte=b.compte
        self._erreur_compte=None
        self._demarrage_valide=deja or b.prete
        self._exclusivites=o.exclusivites
        self._refus_reprise=b.refus
        if deja and b.refus is not None and b.refus.detail=='rapprochement_incomplet': self._refus_reprise=None
        commandes.extend(b.commandes); issues.extend(b.issues); traces.extend(b.traces)
        for i in b.issues: self._actualiser_dossier(i.cle,i)
        for k in self._cycles: self._actualiser_dossier(k)
        self._transmises.update(ref for ref,c in self._preparations.items() if self._cycles[c.cle].etat.accuse_recu)
        self._preparations={ref:c for ref,c in self._preparations.items()
            if not self._cycles[c.cle].etat.accuse_recu and not self._cycles[c.cle].etat.quota_compte
                and self._cycles[c.cle].etat.statut not in _TERMINAUX}

    def _rafraichir_compte(self,base=None):
        c=appeler_calcul(self._port,'etat_compte')
        self._erreur_compte=None
        if isinstance(c,RefusExecution): self._erreur_compte=c
        elif c.instant_ms!=self._dernier_ms: self._erreur_compte=RefusExecution(Motif.ENVIRONMENT_NOT_READY,'instantane_compte')
        else:
            self._compte=c
            self._erreur_compte=self._gardes.observer(c,base)

    def _fond(self,signal):
        if self._fondamental is None: return RefusExecution(Motif.FUNDAMENTAL_INVALID,'ABSENTE')
        try:
            d=self._fondamental.evaluer(signal.symbole,signal.sens,self._dernier_ms)
            if not isinstance(d,DecisionFondamentale): raise ValueError('décision attendue')
            return None if d.admise else RefusExecution(d.motif,d.detail)
        except Exception:
            return RefusExecution(Motif.FUNDAMENTAL_INVALID,'INVALIDE')

    def _ia(self,signal):
        try:
            d=self._contexte.evaluer(signal.symbole,self._dernier_ms)
            if isinstance(d,DecisionContexteIA) and d.etat is ContexteIA.BLOCK:
                return RefusExecution(Motif.AI_CONTEXT_VETO,d.evenement)
        except Exception:
            pass
        return None

    def _refus_avant_prix(self,s):
        if self._refus_qualification is not None: return self._refus_qualification
        if not self._demarrage_valide: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'rapprochement_initial')
        if self._refus_reprise is not None: return self._refus_reprise
        if self._erreur_compte is not None: return self._erreur_compte
        garde=self._gardes.refus()
        if garde is not None: return garde
        for k,c in self._cycles.items():
            e=c.etat
            if e.volume_ouvert and (e.sl_natif!=self._fiches[k].plan.niveaux.stop or e.niveaux_reels is None):
                return RefusExecution(Motif.PROTECTION_ERROR,'SL_ABSENT')
        p=self._profils.get(s.symbole)
        if p is None: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'profil')
        if self._netting and s.symbole not in self._exclusivites: return RefusExecution(Motif.SYMBOL_BUSY,'VERROU_PROPRIETE')
        if any(c.etat.cause_sortie is not None and self._fiches[k].profil.sous_jacent==p.sous_jacent and c.etat.volume_ouvert for k,c in self._cycles.items()):
            return RefusExecution(Motif.SYMBOL_BUSY,'CLOTURE_EN_ATTENTE')
        return self._fond(s) or self._refus_sorties or self._ia(s)

    def _refuser(self,k,refus,issues,*,expire=False):
        d=self._intentions[k]
        if k in self._cycles and self._cycles[k].etat.quota_compte: return
        nature=NatureIssue.EXPIREE if expire else NatureIssue.REFUSEE
        statut=EtatIntention.EXPIREE if expire else EtatIntention.REFUSEE
        i=Issue(k,nature,self._dernier_ms,refus.motif,refus.detail)
        self._intentions[k]=replace(d,statut=statut,issue=i)
        if any(r.cle==k for r in self._registre.etat.reservations): self._registre.sur_issue(i)
        if k in self._cycles:
            v=self._fiches[k]
            e=replace(self._cycles[k].etat,statut=statut,dernier_ms=self._dernier_ms,inconnu_ms=None,
                reliquat_annule=True,prochain_rapprochement_ms=None,prochaine_protection_ms=None,prochain_reessai_ms=None)
            self._cycles[k]=CycleOrdre(self._p,v.signal,v.plan,v.profil,self._longueur,e)
        self._preparations={ref:c for ref,c in self._preparations.items() if c.cle!=k}
        issues.append(i)

    def _profil_courant(self,s):
        p=appeler_calcul(self._port,'specifications',s.symbole)
        if isinstance(p,RefusExecution): return p
        refus=verifier_profil(p,self._p)
        if refus is not None: return refus
        ancien=self._profils.get(s.symbole)
        if ancien is None or (p.symbole,p.symbole_courtier,p.sous_jacent)!=(ancien.symbole,ancien.symbole_courtier,ancien.sous_jacent) or p.releve_ms>self._dernier_ms:
            return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'specifications_modifiees')
        self._profils[s.symbole]=p
        if not any(m in p.modes_remplissage for m in ('FOK','IOC','RETURN')):
            return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'mode_remplissage')
        if not p.horaires.ouvert_a(self._dernier_ms):
            return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'horaires')
        echeance=premiere_echeance(self._dernier_ms,s.strategie,self._technique,p.horaires)
        if echeance.instant_ms is None: return RefusExecution(echeance.motif,echeance.detail)
        if echeance.instant_ms<=self._dernier_ms:
            return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'echeance_sortie_atteinte')
        return p

    def _negociable(self,symbole):
        q=self._cotations.get(symbole); p=self._profils.get(symbole)
        age=_ms(self._p.quote_max_age_seconds)
        return q is not None and p is not None and p.horaires.ouvert_a(self._dernier_ms) and q.ask>=q.bid and (
            0<=self._dernier_ms-q.instant_fournisseur_ms<=age and 0<=self._dernier_ms-q.instant_reception_ms<=age)

    def traiter(self,instant_ms,*,signaux=(),cotations=(),reponses=(),observation=None,base_utc=None):
        signaux,cotations,reponses=tuple(signaux),tuple(cotations),tuple(reponses)
        if any(not isinstance(s,SignalTechnique) or s.cloture_ms>instant_ms for s in signaux): raise ErreurExecution('signaux connus attendus')
        if any(not isinstance(q,Cotation) or q.instant_fournisseur_ms>instant_ms or q.instant_reception_ms>instant_ms for q in cotations): raise ErreurExecution('cotations connues attendues')
        if len({q.symbole for q in cotations})!=len(cotations): raise ErreurExecution('une cotation par symbole attendue')
        if any(not isinstance(r,ReponseCourtier) or r.instant_ms>instant_ms or r.cle not in self._cycles for r in reponses): raise ErreurExecution('réponses connues attendues')
        self._toucher(instant_ms)
        nouveaux=set()
        for q in cotations:
            ancien=self._cotations.get(q.symbole)
            if ancien is None or q.instant_reception_ms>=ancien.instant_reception_ms:
                self._cotations[q.symbole]=q; nouveaux.add(q.symbole)
        commandes,self._commandes_initiales=self._commandes_initiales,[]
        issues,self._issues_initiales=self._issues_initiales,[]
        traces,self._traces_initiales=self._traces_initiales,[]
        for r in reponses:
            c=self._cycles[r.cle]
            ancien=next((v for v in c.etat.reponses_recues if v.reference==r.reference),None)
            if ancien is not None:
                if (ancien.nature,ancien.donnees)!=(r.nature,r.donnees): raise ErreurExecution('réponse répétée contradictoire')
                continue
            if r.nature is NatureReponse.REMPLISSAGE and c.etat.statut in _TERMINAUX and not any(v.cle==r.cle for v in self._registre.etat.reservations):
                self._refus_reprise=RefusExecution(Motif.ENVIRONMENT_NOT_READY,'execution_apres_absence_definitive')
                traces.append(TraceCycle(TypeEnregistrement.ALERTE,{'cle':r.cle.texte(),'alerte':'EXECUTION_CONTRADICTOIRE'}))
                continue
            if 'execution_ms' in r.donnees and r.donnees['execution_ms']<c.etat.envoi_ms:
                raise ErreurExecution('exécution antérieure à cet envoi')
            self._accumuler(r.cle,c.sur_reponse(replace(r,instant_ms=instant_ms),self._cotations.get(r.cle.symbole)),commandes,issues,traces)
        if observation is not None: self._appliquer_observation(observation,base_utc,commandes,issues,traces)
        else: self._rafraichir_compte(base_utc)
        for ref,preparation in tuple(self._preparations.items()):
            if instant_ms>=preparation.donnees['expire_ms']:
                d=self._intentions[preparation.cle]
                self._refuser(d.cle,RefusExecution(Motif.SIGNAL_EXPIRED,d.derniere_cause or 'COTATION_INVALIDE'),issues,expire=True)
        sortie=evaluer_sorties(tuple(self._cycles.values()),self._technique,self._profils,self._gardes,self._fondamental,instant_ms)
        self._echeance_sortie=sortie.prochaine_echeance_ms
        self._refus_sorties=sortie.refus
        for demande in sortie.demandes:
            c=self._cycles[demande.cle]
            e=c.demander_cloture(instant_ms,demande.cause,motif=demande.motif,detail=demande.detail,
                priorite=demande.priorite,peut_envoyer=self._negociable(demande.cle.symbole))
            self._accumuler(demande.cle,e,commandes,issues,traces)
        for k,c in self._cycles.items():
            if any(p.cle==k for p in self._preparations.values()): continue
            e=c.sur_minuterie(instant_ms,cotation=self._cotations.get(k.symbole),negociable=self._negociable(k.symbole))
            self._accumuler(k,e,commandes,issues,traces)
            if (c.etat.volume_ouvert and not c.etat.risque_verifie and c.etat.cause_sortie is None and self._erreur_compte is None
                    and self._fiches[k].profil.sous_jacent not in self._registre.etat.verrous):
                self._accumuler(k,c.controler_risque(self._registre,self._gardes,self._port,instant_ms,self._cotations.get(k.symbole)),commandes,issues,traces)
            elif (c.etat.volume_ouvert and self._fiches[k].profil.sous_jacent in self._registre.etat.verrous
                    and c.etat.prochain_rapprochement_ms is None):
                self._accumuler(k,c.reprendre(instant_ms),commandes,issues,traces)
        nouveaux_signaux=set()
        for s in signaux:
            k=CleIntention(self._deploiement,s.strategie,s.symbole,s.cloture_ms,s.sens)
            if k in self._intentions:
                if self._intentions[k].signal!=s: raise ErreurExecution('clé répétée avec signal contradictoire')
                continue
            self._intentions[k]=DossierIntention(k,s); nouveaux_signaux.add(k)
        attentes=[d for d in self._intentions.values() if d.statut is EtatIntention.EN_ATTENTE_COTATION]
        for cloture in sorted({d.signal.cloture_ms for d in attentes}):
            groupe=[d.signal for d in attentes if d.signal.cloture_ms==cloture]
            for candidat in candidats_admission(groupe,self._p,self._registre):
                s=candidat.signal; k=CleIntention(self._deploiement,s.strategie,s.symbole,s.cloture_ms,s.sens); d=self._intentions[k]
                q=self._cotations.get(s.symbole)
                expire=instant_ms>=s.cloture_ms+_ms(self._p.entry_signal_ttl_seconds)
                if expire:
                    v=evaluer_cotation(s,q,instant_ms,self._p,d.derniere_cause)
                    self._refuser(k,RefusExecution(v.motif,v.detail),issues,expire=True); continue
                refus=self._refus_avant_prix(s)
                if refus is not None: self._refuser(k,refus,issues); continue
                if k not in nouveaux_signaux and s.symbole not in nouveaux: continue
                v=evaluer_cotation(s,q,instant_ms,self._p,d.derniere_cause)
                essai=TentativeCotation(instant_ms,v.derniere_cause,*(
                    (q.bid,q.ask,q.instant_fournisseur_ms,q.instant_reception_ms) if q is not None else (None,None,None,None)))
                d=replace(d,derniere_cause=v.derniere_cause,tentatives=d.tentatives+(essai,)); self._intentions[k]=d
                if v.etat is not EtatCotation.ADMISSIBLE: continue
                profil=self._profil_courant(s)
                if isinstance(profil,RefusExecution): self._refuser(k,profil,issues); continue
                n=construire_niveaux(s,q,profil,self._p)
                if not isinstance(n,NiveauxExecutables): self._refuser(k,RefusExecution(n.motif,n.detail),issues); continue
                plan=dimensionner(s,n,profil,self._compte,self._registre,self._gardes,self._port,self._p,self._deploiement)
                if not isinstance(plan,PlanDimensionnement): self._refuser(k,plan,issues); continue
                reserve=self._registre.reserver(plan.reservation,self._compte,plan.version_reservations)
                if isinstance(reserve,RefusExecution): self._refuser(k,reserve,issues); continue
                c=CycleOrdre(self._p,s,plan,profil,self._longueur)
                self._cycles[k]=c; self._fiches[k]=CyclePersiste(s,plan,profil,c.etat)
                self._accumuler(k,c.preparer_envoi(instant_ms),commandes,issues,traces)
        return self._lot(commandes,issues,traces)

    def confirmer_persistance(self,preuve,instant_ms):
        instant(instant_ms)
        if not isinstance(preuve,PreuvePersistance): raise ErreurExecution('preuve de persistance attendue')
        if preuve.references and all(ref in self._transmises for ref in preuve.references):
            return LotCoordinateur(self.etat,compte=self._compte)
        if preuve.revision!=self._revision or set(preuve.references)!=set(self._preparations):
            raise ErreurExecution('preuve étrangère ou périmée')
        intermediaire=self.traiter(instant_ms)
        commandes,issues,traces=list(intermediaire.commandes),list(intermediaire.issues),list(intermediaire.traces)
        for ref,c in tuple(self._preparations.items()):
            k=c.cle; v=self._fiches[k]; d=self._intentions[k]
            q=self._cotations.get(k.symbole)
            verdict=evaluer_cotation(v.signal,q,instant_ms,self._p,d.derniere_cause)
            essai=TentativeCotation(instant_ms,verdict.derniere_cause,*(
                (q.bid,q.ask,q.instant_fournisseur_ms,q.instant_reception_ms) if q is not None else (None,None,None,None)))
            self._intentions[k]=replace(d,tentatives=d.tentatives+(essai,))
            refus=self._refus_avant_prix(v.signal)
            if verdict.etat is EtatCotation.EXPIREE:
                self._refuser(k,RefusExecution(verdict.motif,verdict.detail),issues,expire=True); continue
            if refus is None and verdict.etat is not EtatCotation.ADMISSIBLE:
                refus=RefusExecution(verdict.motif or Motif.ENVIRONMENT_NOT_READY,
                    None if verdict.motif is not None else 'cotation_avant_ordre')
            profil=self._profil_courant(v.signal) if refus is None else None
            if isinstance(profil,RefusExecution): refus=profil
            if refus is None and (profil.point!=v.profil.point or c.donnees['mode_remplissage'] not in profil.modes_remplissage):
                refus=RefusExecution(Motif.ENVIRONMENT_NOT_READY,'specifications_modifiees')
            if refus is None:
                resultat=revalider_avant_envoi(v.plan,v.signal,profil,self._compte,self._registre,self._gardes,self._port,self._p)
                if isinstance(resultat,RefusExecution): refus=resultat
            if refus is not None: self._refuser(k,refus,issues); continue
            reel=replace(self._cycles[k].etat,envoi_ms=instant_ms,dernier_ms=instant_ms)
            self._cycles[k]=CycleOrdre(self._p,v.signal,v.plan,v.profil,self._longueur,reel)
            commandes.append(c); self._transmises.add(ref); self._preparations.pop(ref)
            traces.append(TraceCycle(TypeEnregistrement.ORDRE,{'cle':k.texte(),'reference':ref,'transmission_autorisee':True}))
        return self._lot(commandes,issues,traces)

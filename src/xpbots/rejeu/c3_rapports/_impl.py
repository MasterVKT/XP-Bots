"""Des résultats calculés ne constituent pas une attestation de données réelles."""
from collections import defaultdict
from dataclasses import dataclass,fields,is_dataclass,replace
from datetime import date,datetime,time
from decimal import Decimal,Context,ROUND_FLOOR,localcontext
from enum import Enum
import json
import math
import re
from types import MappingProxyType
from typing import Mapping
from zoneinfo import ZoneInfo

from xpbots.noyau.c0a_temps import instant_vers_datetime
from xpbots.noyau.c1c_domaine import SignalTechnique,NatureIssue,Motif
from xpbots.rejeu.c0a_types import ErreurRejeu,entier,texte,montant,JourMarche
from xpbots.rejeu.c0b_protocole import charger_protocole
from xpbots.rejeu.c1c_metriques import (ComptageC09,calculer_mesures,retention,
    reconcilier_factures,panel_journalier,ventiler_trades,drawdown)
from xpbots.rejeu.c1d_bootstrap import bootstrap_apparie
from xpbots.rejeu.c2_executeur import ResultatExperience,symboles_forex_c09

D=Decimal


def _figer(v):
    if isinstance(v,Mapping):return MappingProxyType({k:_figer(x) for k,x in v.items()})
    if isinstance(v,(list,tuple)):return tuple(_figer(x) for x in v)
    return v


def _hash(v):
    if v is not None and (type(v) is not str or re.fullmatch('[0-9a-f]{64}',v) is None):
        raise ErreurRejeu('identifiant de preuve SHA-256 requis')


@dataclass(frozen=True)
class PreuvesValidation:
    fiche_c04:str|None=None
    gel_robot:str|None=None
    journaux_demo:str|None=None
    reponses_archivees:str|None=None
    verifier:object=None
    def __post_init__(self):
        for v in (self.fiche_c04,self.gel_robot,self.journaux_demo,self.reponses_archivees):_hash(v)
        if self.verifier is not None and not callable(self.verifier):raise ErreurRejeu('port d’attestation requis')
    def attestee(self,nature):
        valeur=getattr(self,nature)
        if valeur is None or self.verifier is None:return False
        try:return self.verifier(nature,valeur) is True
        except Exception:return False


@dataclass(frozen=True)
class QualificationSemantique:
    fournisseur:str
    empreinte_corpus:str|None
    humain:bool
    nombre_textes:int
    precision:Decimal
    rappel:Decimal
    citations_non_verifiees:int
    def __post_init__(self):
        texte(self.fournisseur);_hash(self.empreinte_corpus)
        if type(self.humain) is not bool:raise ErreurRejeu('vérité terrain humaine explicite requise')
        entier(self.nombre_textes);entier(self.citations_non_verifiees)
        for v in (self.precision,self.rappel):
            montant(v,D(0))
            if v>1:raise ErreurRejeu('proportion sémantique hors bornes')


@dataclass(frozen=True)
class ObservationCoutDemo:
    reference:str
    nature:str
    symbole:str
    delai_ms:int
    ticks_adverses:Decimal
    spread_prix:Decimal
    commission_usd:Decimal
    def __post_init__(self):
        texte(self.reference);texte(self.symbole);entier(self.delai_ms)
        if self.nature not in ('ENTREE','MARCHE','STOP','TP'):raise ErreurRejeu('nature de coût native inconnue')
        montant(self.ticks_adverses);montant(self.spread_prix,D(0));montant(self.commission_usd,D(0))


@dataclass(frozen=True)
class Critere:
    nom:str
    observe:object
    seuil:object
    relation:str
    statut:str
    raison:str|None=None


def _critere(nom,observe,seuil,relation,raison=None):
    if observe is None:return Critere(nom,None,seuil,relation,'NON_EVALUABLE',raison or 'PREUVE_MANQUANTE')
    if relation=='>=':ok=observe>=seuil
    elif relation=='>':ok=observe>seuil
    elif relation=='<=':ok=observe<=seuil
    elif relation=='==':ok=observe==seuil
    else:raise ErreurRejeu('relation de critère inconnue')
    return Critere(nom,observe,seuil,relation,'SATISFAIT' if ok else 'ECHEC',raison)


def _receptions(r,natures=None):
    return tuple((j.entree.instant_ms,p) for j in r.pilote.entrees for p in j.entree.receptions
        if natures is None or p.nature in natures)


def _methodes(r):return tuple(sorted({k[0] for b in r.bras.values() for k in b.comptages}))


def _comparables(a,b,permissions=True,scenario=True):
    if not isinstance(b,ResultatExperience):return False,'REFERENCE_ABSENTE'
    if a.manifeste.sha256!=b.manifeste.sha256 or a.manifeste.symboles!=b.manifeste.symboles:
        return False,'PRIX_DIFFERENTS'
    if (a.debut_effectif_ms,a.demande.bloc.intervalle_ms.fin_ms,_methodes(a))!=(b.debut_effectif_ms,b.demande.bloc.intervalle_ms.fin_ms,_methodes(b)):
        return False,'PERIMETRES_DIFFERENTS'
    if not a.conditions or a.conditions!=b.conditions:return False,'CONDITIONS_CONTRACTUELLES_DIFFERENTES_OU_ABSENTES'
    if scenario and a.demande.scenario!=b.demande.scenario:return False,'COUTS_DIFFERENTS'
    natures_fondamentales={'PERMISSION','CALENDRIER','INTERRUPTION'}
    if permissions and (a.regime_fondamental!=b.regime_fondamental
            or _receptions(a,natures_fondamentales)!=_receptions(b,natures_fondamentales)):
        return False,'PERMISSIONS_OU_RECEPTIONS_DIFFERENTES'
    if a.demande.ecart is not None or b.demande.ecart is not None:return False,'PERTURBATION_DIAGNOSTIQUE'
    return True,None


def _selection(r,nom,methode=None,symbole=None,forex=False):
    b=r.bras[nom];slots={k:v for k,v in b.comptages.items() if (methode is None or k[0]==methode)
        and (symbole is None or k[1]==symbole) and (not forex or k[1] in symboles_forex_c09())}
    refus=defaultdict(int);entrees=defaultdict(int)
    for n in slots.values():
        for k,v in n.refus.items():refus[k]+=v
        for k,v in n.entrees_jours.items():entrees[k]+=v
    comptage=ComptageC09(sum(v.configurations for v in slots.values()),sum(v.signaux for v in slots.values()),
        refus,sum(entrees.values()),entrees)
    trades=tuple(t for t in b.trades if (methode is None or t.cle.strategie==methode)
        and (symbole is None or t.cle.symbole==symbole) and (not forex or t.cle.symbole in symboles_forex_c09()))
    couts=tuple(f for f in r.factures if r.debut_effectif_ms<=f.instant_ms<r.demande.bloc.intervalle_ms.fin_ms) if nom=='IA' and symbole is None else ()
    jours=r.jours_forex if forex else r.jours
    return calculer_mesures(trades,b.courbe,jours,comptage,couts,methode),trades,couts


def _resume(m,coute_ia_defini=True):
    return _figer(dict(configurations=m.comptage.configurations,signaux=m.comptage.signaux,
        refus=m.comptage.refus,entrees=m.comptage.entrees,positions_closes=m.positions_closes,
        resultats_nets=m.resultats_nets,pnl_courtier=m.pnl_courtier,
        cout_ia=m.cout_ia if coute_ia_defini else None,pnl_economique=m.pnl_economique if coute_ia_defini else None,
        esperance=m.esperance,esperance_economique=m.esperance_economique if coute_ia_defini else None,
        profit_factor=m.profit_factor,statut_pf=m.statut_pf,drawdown_courtier=m.drawdown_courtier,
        drawdown_economique=m.drawdown_economique if coute_ia_defini else None,
        jours_marche=m.jours_marche,jours_zero=m.jours_zero,frequence=m.frequence,
        taux_reussite=m.taux_reussite,r_moyen_net=m.r_moyen_net))


def _cle_trade(t):return (t.cle.strategie,t.cle.symbole,t.cle.cloture_ms,t.cle.sens.value)


def _bootstrap(r,nom,reference=None,nom_reference='REFERENCE'):
    # Les symboles et méthodes partagent le panel et les mêmes indices journaliers.
    p=charger_protocole(r.configuration)
    if len(r.jours)<p.bootstrap.bloc_jours:return _figer(dict(statut='NON_EVALUABLE',raison='PANEL_TROP_COURT'))
    m,ts,couts=_selection(r,nom)
    candidat=panel_journalier(ts,r.jours,r.configuration.technique.commun,couts)
    comparable,raison=_comparables(r,reference) if reference is not None else (False,'REFERENCE_V1_ABSENTE')
    if comparable:
        _,a,f=_selection(reference,nom_reference)
        brut=panel_journalier(a,reference.jours,reference.configuration.technique.commun,f)
        if tuple(v.jour for v in brut)!=tuple(v.jour for v in candidat):
            return _figer(dict(statut='NON_COMPARABLE',raison='PANELS_DIFFERENTS'))
        ancien=tuple(replace(v,periode=c.periode) for v,c in zip(brut,candidat))
    else:ancien=candidat
    capital=D(str(r.configuration.technique.commun.initial_equity_usd))
    b=bootstrap_apparie(ancien,candidat,p.bootstrap,capital)
    return _figer(dict(statut='CALCULE',parametres=b.parametres,nombre_jours=b.nombre_jours,
        empreinte_indices=b.empreinte_indices,esperance_candidat=b.esperance_candidat,
        difference_esperance=b.difference_esperance if comparable else None,
        gain_incremental=b.gain_incremental if comparable else None,
        difference_drawdown_journalier=b.difference_drawdown if comparable else None,
        raison_reference=raison))


def _qualification_semantique(q,c):
    p=c.ia.parametres
    if not isinstance(q,QualificationSemantique):return _figer(dict(statut='NON_QUALIFIE',raison='CORPUS_HUMAIN_ABSENT'))
    criteres=(
        _critere('fournisseur_configure',q.fournisseur in {v['id'] for v in p['providers']},True,'=='),
        _critere('corpus_humain_identifie',q.humain and q.empreinte_corpus is not None,True,'=='),
        _critere('textes_annotes',q.nombre_textes,p['model_classification_test_items'],'>='),
        _critere('precision_evenements_materiels',q.precision,D(str(p['model_min_material_event_precision'])),'>='),
        _critere('rappel_evenements_materiels',q.rappel,D(str(p['model_min_material_event_recall'])),'>='),
        _critere('citations_non_verifiees',q.citations_non_verifiees,0,'=='))
    return _figer(dict(statut='QUALIFIE_DECLARE' if all(v.statut=='SATISFAIT' for v in criteres) else 'NON_QUALIFIE',
        fournisseur=q.fournisseur,empreinte_corpus=q.empreinte_corpus,criteres=criteres,
        garde='La precision des evenements materiels ou du JSON ne mesure pas la reussite des trades.'))


def _description_trades(trades):
    trades=tuple(trades);n=len(trades)
    with localcontext(Context(prec=48)):
        return _figer(dict(effectif=n,pnl_net=sum((t.net for t in trades),D(0)),
            taux_reussite=D(sum(t.net>0 for t in trades))/D(n) if n else None,
            r_moyen_net=sum((t.r_net for t in trades),D(0))/D(n) if n else None,
            commissions=sum((t.frais_entree+t.frais_sortie for t in trades),D(0))))


def comparer_routes(gratuite,payante,configuration,*,dossiers=None,prompt=None,
                    regles=None,provenance_masquee=False,attester=None):
    for valeur in (dossiers,prompt,regles):_hash(valeur)
    preuves=all(v is not None for v in (dossiers,prompt,regles)) and provenance_masquee is True
    try:
        preuves=preuves and callable(attester) and all(attester(n,v) is True
            for n,v in (('dossiers_apparies',dossiers),('prompt_commun',prompt),('regles_communes',regles)))
    except Exception:preuves=False
    qs=tuple(_qualification_semantique(q,configuration) for q in (gratuite,payante))
    if (not preuves or any(q['statut']!='QUALIFIE_DECLARE' for q in qs)
            or gratuite.empreinte_corpus!=dossiers or payante.empreinte_corpus!=dossiers
            or gratuite.nombre_textes!=payante.nombre_textes or gratuite.fournisseur==payante.fournisseur):
        return _figer(dict(statut='NON_EVALUABLE',qualifications=qs,raison='COMPARAISON_MASQUEE_ATTESTEE_REQUISE'))
    precision=abs(gratuite.precision-payante.precision);rappel=abs(gratuite.rappel-payante.rappel)
    # Seuils textuels A13.3, fractions de points de pourcentage, non réglables.
    criteres=(_critere('ecart_precision',precision,D('0.02'),'<='),
        _critere('ecart_rappel',rappel,D('0.05'),'<='))
    return _figer(dict(statut='ECARTS_ADMISSIBLES_OBSERVES' if all(c.statut=='SATISFAIT' for c in criteres)
        else 'ROUTES_NON_EQUIVALENTES',criteres=criteres,
        effectifs=(gratuite.nombre_textes,payante.nombre_textes),
        limite='Une non-difference sur ce corpus ne demontre pas une equivalence universelle.'))


def rapport_a11(experience):
    if not isinstance(experience,ResultatExperience):raise ErreurRejeu('expérience réelle du moteur requise')
    r=experience;id_london=r.configuration.technique.london['strategy_id']
    zone=ZoneInfo(r.configuration.technique.commun.session_timezone);sorties={}
    for nom,b in r.bras.items():
        trades=tuple(t for t in b.trades if t.cle.strategie==id_london)
        groupes=defaultdict(list);premieres={};signaux=[];vetos={};refus_heures=defaultdict(int)
        for tr in b.historique:
            if tr.instant_ms<r.debut_effectif_ms or tr.identifiant!=id_london:continue
            if tr.nature=='BOUGIE' and isinstance(tr.resultat,SignalTechnique):
                signal=tr.resultat;moment=instant_vers_datetime(signal.cloture_ms).astimezone(zone)
                premieres.setdefault((signal.symbole,moment.date()),(signal.cloture_ms,signal.sens))
                signaux.append(signal)
            if tr.nature=='ISSUE' and tr.valeur.motif is not None:
                i=tr.valeur
                heure=instant_vers_datetime(i.instant_ms).astimezone(zone).hour
                refus_heures[(i.motif.value,heure)]+=1
                if i.motif is Motif.AI_CONTEXT_VETO:
                    vetos[(i.cle.strategie,i.cle.symbole,i.cle.cloture_ms,i.cle.sens.value)]=i
        for t in trades:
            moment=instant_vers_datetime(t.entree_ms).astimezone(zone)
            ratio=t.contexte.get('rapport_range_atr_h1')
            tranche=int(D(str(ratio)).to_integral_value(rounding=ROUND_FLOOR)) if ratio is not None else None
            premiere=premieres.get((t.cle.symbole,moment.date()))
            axes=(('W_ATR_H1',f'[{tranche},{tranche+1})' if tranche is not None else 'INCONNU'),
                ('premiere_cassure',instant_vers_datetime(premiere[0]).astimezone(zone).hour if premiere else None),
                ('sens',t.cle.sens.value),('stop_local',tuple(t.contexte.get('composantes_contraignantes',()))),
                ('jour_semaine',moment.weekday()),('symbole',t.cle.symbole),('scenario_couts',r.demande.scenario))
            for axe,valeur in axes:groupes[(axe,valeur)].append(t)
        reference=r.bras.get('REFERENCE')
        bloques=tuple(t for t in reference.trades if _cle_trade(t) in vetos) if reference is not None else ()
        nouveaux=tuple(s for s in signaux if any(sym==s.symbole and cloture<s.cloture_ms
            for _,sym,cloture,_ in vetos))
        tardifs=set()
        for e in r.pilote.enregistrements:
            v=e.vers_dict()
            if e.enveloppe.bras!=nom or v.get('motif')!=Motif.AI_CONTEXT_VETO.value:continue
            instant=instant_vers_datetime(e.enveloppe.instant_utc_ms).astimezone(zone)
            limite=datetime.combine(instant.date(),time.fromisoformat(r.configuration.technique.london['entry_end_local_exclusive']),zone)
            description=v.get('snapshot_ia') or {}
            for veto in description.get('vetos',()):
                if instant_vers_datetime(veto['valid_until_ms']).astimezone(zone)>=limite:
                    tardifs.add((v.get('symbole'),instant.date(),veto['event_id']))
        retournements=0
        for (symbole,jour),(t,sens) in premieres.items():
            if any(s.symbole==symbole and s.cloture_ms>t and s.sens is not sens
                   and instant_vers_datetime(s.cloture_ms).astimezone(zone).date()==jour for s in signaux):retournements+=1
        maximum_simultane=0
        for j in r.pilote.entrees:
            for bras,appels in j.calculs:
                if bras!=nom:continue
                for appel in appels:
                    if appel.nom=='etat_compte':
                        nombre=sum(p.symbole in symboles_forex_c09() for p in getattr(appel.resultat,'positions',()))
                        maximum_simultane=max(maximum_simultane,nombre)
        compte=sum(n.entrees for (m,_),n in b.comptages.items() if m==id_london)
        nombre_signaux=sum(n.signaux for (m,_),n in b.comptages.items() if m==id_london)
        with localcontext(Context(prec=48)):
            ratio_fills=D(compte)/D(nombre_signaux) if nombre_signaux else None
            taux_retournement=D(retournements)/D(len(premieres)) if premieres else None
        sorties[nom]=_figer(dict(ventilations=tuple(dict(axe=k[0],valeur=k[1],mesures=_description_trades(ts)) for k,ts in groupes.items()),
            descriptifs=tuple(dict(axe=k[0],valeur=k[1],mesures=v) for k,v in ventiler_trades(trades,r.configuration.technique.commun).items()),
            ratio_remplissage=ratio_fills,refus_par_motif_heure=tuple(dict(motif=m,heure=h,nombre=n) for (m,h),n in refus_heures.items()),
            gagnants_bloques=sum(t.net>0 for t in bloques),perdants_bloques=sum(t.net<0 for t in bloques),
            pnl_reference_bloque=sum((t.net for t in bloques),D(0)),nouveaux_signaux_apres_veto=len(nouveaux),
            vetos_expirant_trop_tard=len(tardifs),taux_retournement_observe=taux_retournement,
            maximum_positions_forex_simultanees=maximum_simultane,
            couts_ia_par_methode=reconcilier_factures(r.factures).par_methode,
            limites=('Retournements observes parmi les signaux emis, sans reconstituer une cassure non journalisee.',
                'Veto expirant trop tard decrit une incompatibilite horaire, pas un trade hypothetique gagnant.',
                'Commissions explicites ; spread et glissement sont deja dans les prix et le resultat net.',
                'Les exclusions C05 et le stop technique ne sont pas attribues au LLM.')))
    return _figer(sorties)


def _retention_a13_non_applicable(c):
    return c.nom.startswith('retention:') and c.statut=='NON_EVALUABLE' and c.raison in ('N_A','TROP_FAIBLE')


def _criteres_a13_satisfaits(criteres):
    applicables=tuple(c for c in criteres if not _retention_a13_non_applicable(c))
    return bool(applicables) and all(c.statut=='SATISFAIT' for c in applicables)


def rapport_a13(experience_ab,qualification_semantique=None,preuves=None):
    r=experience_ab
    if not isinstance(r,ResultatExperience) or set(r.bras)!={'REFERENCE','IA'}:
        return _figer(dict(statut='NON_EVALUABLE',raison='DEUX_PORTEFEUILLES_COMPLETS_REQUIS'))
    preuves=preuves if isinstance(preuves,PreuvesValidation) else PreuvesValidation()
    p=charger_protocole(r.configuration);a,_,_=_selection(r,'REFERENCE');b,_,_=_selection(r,'IA')
    factures_periode=tuple(f for f in r.factures if f.nature!='RECHERCHE'
        and r.debut_effectif_ms<=f.instant_ms<r.demande.bloc.intervalle_ms.fin_ms)
    couts_documentes=bool(factures_periode) and all(f.reelle for f in r.factures)
    c10_atteste=False
    if preuves.gel_robot is not None and preuves.verifier is not None:
        try:c10_atteste=preuves.verifier('validation_c10',preuves.gel_robot) is True
        except Exception:pass
    par_candidat={_cle_trade(t):t for t in r.bras['IA'].trades}
    affectes=[]
    for t in r.bras['REFERENCE'].trades:
        u=par_candidat.get(_cle_trade(t))
        if u is None or (t.entree_ms,t.volume,t.prix_entree,t.sortie_ms,t.net)!=(u.entree_ms,u.volume,u.prix_entree,u.sortie_ms,u.net):
            affectes.append(t)
    zone=ZoneInfo(r.configuration.technique.commun.session_timezone)
    jours_affectes={instant_vers_datetime(t.entree_ms).astimezone(zone).date() for t in affectes}
    criteres=[_critere('jours_marche',len(r.jours),p.seuils.jours_ia,'>='),
        _critere('reference_affectee',len(affectes),p.seuils.affectes_ia,'>='),
        _critere('jours_affectes',len(jours_affectes),p.seuils.jours_affectes_ia,'>='),
        _critere('pnl_ia_apres_couts',b.pnl_economique,D(0),'>'),
        _critere('gain_net_incremental',b.pnl_economique-a.pnl_economique,D(0),'>'),
        _critere('drawdown_non_accru',b.drawdown_economique,a.drawdown_courtier,'<='),
        _critere('couverture_complete',r.complet,True,'=='),
        _critere('permissions_externes_presentes',r.regime_fondamental=='PERMISSIONS_EXTERNES',True,'=='),
        _critere('couts_ia_reels_documentes',couts_documentes,True,'=='),
        _critere('maintien_c10_sous_gel_atteste',c10_atteste,True,'==')]
    retentions=[]
    for methode in _methodes(r):
        for nom in ('REFERENCE','IA'):
            m,_,_=_selection(r,nom,methode)
            criteres.append(_critere('trades_clos:'+nom+':'+methode,m.positions_closes,p.seuils.trades_ia,'>='))
        for symbole in r.manifeste.symboles:
            x=r.bras['REFERENCE'].comptages.get((methode,symbole));y=r.bras['IA'].comptages.get((methode,symbole))
            ratio=retention(y.entrees if y else 0,x.entrees if x else 0,p.seuils)
            retentions.append(dict(methode=methode,symbole=symbole,mesure=ratio))
            criteres.append(_critere('retention:'+methode+':'+symbole,ratio.ratio if ratio.statut=='EXPLOITABLE' else None,
                p.seuils.retention_ia,'>=',ratio.statut))
    boot=_bootstrap(r,'IA',r)
    intervalle=boot.get('gain_incremental')
    criteres.append(_critere('borne_basse_gain_incremental',intervalle.bas if intervalle else None,D(0),'>'))
    semantique=_qualification_semantique(qualification_semantique,r.configuration)
    corpus_atteste=False
    if isinstance(qualification_semantique,QualificationSemantique) and preuves.verifier is not None:
        try:corpus_atteste=preuves.verifier('corpus_humain',qualification_semantique.empreinte_corpus) is True
        except Exception:pass
    preuves_reelles=(r.manifeste.usage=='COURTIER_HISTORIQUE' and r.usage=='PROSPECTIF'
        and r.regime_fondamental=='PERMISSIONS_EXTERNES'
        and all(preuves.attestee(n) for n in ('fiche_c04','gel_robot','journaux_demo','reponses_archivees'))
        and couts_documentes and c10_atteste and corpus_atteste and semantique['statut']=='QUALIFIE_DECLARE')
    numerique=_criteres_a13_satisfaits(criteres)
    return _figer(dict(statut='VALIDE' if numerique and preuves_reelles else 'NON_VALIDE',
        criteres=criteres,reference=_resume(a),ia=_resume(b),retentions=retentions,
        criteres_non_applicables=tuple(c.nom for c in criteres if _retention_a13_non_applicable(c)),
        reference_effectivement_affectee=tuple(_cle_trade(t) for t in affectes),jours_affectes=tuple(sorted(jours_affectes)),
        bootstrap=boot,qualification_semantique=semantique,preuves_reelles_attestees=preuves_reelles,
        garde='Comparaison de deux simulations completes ; aucune perte retiree apres coup.'))


def _rapport_experience(r,references,preuves):
    p=charger_protocole(r.configuration);s=p.seuils;branches={};criteres=[]
    reference=references.get(r.demande.identifiant)
    comparable,raison=_comparables(r,reference)
    reference_bras=reference.bras.get('REFERENCE') if comparable else None
    if r.usage=='RESERVE':
        trace=any(v.get('action') in ('OUVERTURE_RESERVE','CONSULTATION_RESERVE')
            and v.get('empreinte')==preuves.gel_robot for v in r.journal_protocole)
        criteres.append(_critere('reserve_sous_le_gel_atteste',trace if preuves.gel_robot is not None else None,True,'=='))
    for nom,b in r.bras.items():
        m,_,_=_selection(r,nom);fx,_,_=_selection(r,nom,forex=True)
        scopes=[];retentions=[]
        for methode,symbole in b.comptages:
            part,_,_=_selection(r,nom,methode,symbole)
            scopes.append(dict(methode=methode,symbole=symbole,mesures=_resume(part,False),
                cout_ia_par_symbole='NON_ALLOUE',drawdown='COMPTE_PARTAGE'))
            ref=reference_bras.comptages.get((methode,symbole)) if reference_bras is not None else None
            ratio=retention(b.comptages[(methode,symbole)].entrees,ref.entrees if ref is not None else None,s)
            configurations=retention(b.comptages[(methode,symbole)].configurations,ref.configurations if ref is not None else None,s)
            retentions.append(dict(methode=methode,symbole=symbole,transactions=ratio,configurations=configurations))
            criteres.append(_critere('retention:'+nom+':'+methode+':'+symbole,
                ratio.ratio if ratio.statut=='EXPLOITABLE' else None,s.retention,'>=',raison or ratio.statut))
        stress=r.demande.scenario==p.scenarios[-1].nom
        criteres.extend((_critere('esperance:'+nom,m.esperance,D(0),'>'),
            _critere('profit_factor:'+nom,m.profit_factor,s.profit_factor_stress if stress else s.profit_factor_reference,'>=',m.statut_pf),
            _critere('drawdown:'+nom,m.drawdown_courtier,s.drawdown_stress if stress else s.drawdown_reference,'<='),
            _critere('couverture:'+nom,r.complet,True,'==')))
        methodes=set(_methodes(r));attendues={r.configuration.technique.ema['strategy_id'],r.configuration.technique.london['strategy_id']}
        if methodes==attendues:
            criteres.append(_critere('frequence_forex_combinee:'+nom,fx.frequence,s.frequence_forex,'>='))
        boot=_bootstrap(r,nom,reference)
        if r.usage=='RESERVE':
            e=boot.get('esperance_candidat');d=boot.get('difference_esperance')
            criteres.extend((_critere('borne_basse_esperance:'+nom,e.bas if e is not None else None,D(0),'>'),
                _critere('borne_basse_difference:'+nom,d.bas if d is not None else None,D(0),'>')))
        branches[nom]=dict(global_compte=_resume(m),frequence_forex=fx.frequence,
            jours_forex=len(r.jours_forex),par_methode_symbole=scopes,retentions=retentions,
            bootstrap=boot,descriptifs=tuple(dict(axe=k[0],valeur=k[1],mesures=v)
                for k,v in ventiler_trades(b.trades,r.configuration.technique.commun).items()))
    return _figer(dict(experience=r.demande.identifiant,bloc=r.demande.bloc,usage=r.usage,
        scenario=r.demande.scenario,mode=r.demande.mode,methodes=_methodes(r),source=r.manifeste.source,
        provenance=r.manifeste.usage,sha256_prix=r.manifeste.sha256,regime_fondamental=r.regime_fondamental,
        conditions_datees_presentes=bool(r.conditions),ecart=r.demande.ecart,
        empreinte_origine=r.configuration_origine.technique.empreinte_canonique,
        empreinte_executee=r.configuration.technique.empreinte_canonique,bras=branches,criteres=criteres,
        reference_v1='COMPARABLE' if comparable else 'NON_COMPARABLE' if reference is not None else 'N_A',
        raison_reference=raison))


def _effectifs_globaux(experiences):
    groupes=defaultdict(list);resultats=[]
    for r in experiences:
        if r.usage not in ('VALIDATION','RESERVE') or r.demande.ecart is not None:continue
        for nom in r.bras:groupes[(r.demande.scenario,r.demande.mode,_methodes(r),r.regime_fondamental,
            r.configuration.technique.empreinte_canonique,nom)].append(r)
    for cle,rs in groupes.items():
        scenario,mode,methodes,regime,empreinte,bras=cle
        rs=sorted(rs,key=lambda r:r.debut_effectif_ms)
        chevauchement=any(b.debut_effectif_ms<a.demande.bloc.intervalle_ms.fin_ms for a,b in zip(rs,rs[1:]))
        s=charger_protocole(rs[0].configuration).seuils;criteres=[];comptes={}
        for methode in methodes:
            tous=sum(sum(t.cle.strategie==methode for t in r.bras[cle[-1]].trades) for r in rs)
            reserve=sum(sum(t.cle.strategie==methode for t in r.bras[cle[-1]].trades) for r in rs if r.usage=='RESERVE')
            comptes[methode]=dict(total=tous,reserve=reserve)
            criteres.extend((_critere('trades_total:'+methode,None if chevauchement else tous,s.min_trades_total,'>=',
                'EXPERIENCES_CHEVAUCHANTES' if chevauchement else None),
                _critere('trades_reserves:'+methode,None if chevauchement else reserve,s.min_trades_reserve,'>=')))
            for symbole in rs[0].manifeste.symboles:
                n=sum(sum(t.cle.strategie==methode and t.cle.symbole==symbole for t in r.bras[cle[-1]].trades) for r in rs)
                criteres.append(_critere('trades_symbole:'+methode+':'+symbole,None if chevauchement else n,s.min_trades_symbole,'>='))
        criteres.append(_critere('validation_et_reserve_presentes',{r.usage for r in rs}=={'VALIDATION','RESERVE'},True,'=='))
        resultats.append(_figer(dict(scenario=scenario,mode=mode,methodes=methodes,bras=bras,
            regime_fondamental=regime,empreinte_regles=empreinte,
            effectifs=comptes,criteres=criteres,garde='Effectifs agreges, jamais profits ou courbes de comptes additionnes.')))
    return tuple(resultats)


def comparer_couts_demo(experience,observations,preuves=None):
    if not isinstance(experience,ResultatExperience):raise ErreurRejeu('expérience requise')
    observations=tuple(observations)
    if any(not isinstance(o,ObservationCoutDemo) for o in observations):raise ErreurRejeu('observations de coûts normalisées requises')
    if len({o.reference for o in observations})!=len(observations):raise ErreurRejeu('observations natives dupliquées')
    p=charger_protocole(experience.configuration);groupes=defaultdict(list)
    for o in observations:groupes[(o.nature,o.symbole)].append(o)
    def stats(v):
        with localcontext(Context(prec=48)):
            return dict(minimum=min(v),moyenne=sum(v,D(0))/D(len(v)),maximum=max(v))
    lignes=tuple(dict(nature=k[0],symbole=k[1],effectif=len(v),
        delai_ms=stats([D(o.delai_ms) for o in v]),ticks_adverses=stats([o.ticks_adverses for o in v]),
        spread=stats([o.spread_prix for o in v]),commissions=stats([o.commission_usd for o in v])) for k,v in groupes.items())
    atteste=isinstance(preuves,PreuvesValidation) and preuves.attestee('journaux_demo')
    return _figer(dict(statut='OBSERVATIONS_ATTESTEES' if observations and atteste else 'PREUVE_MANQUANTE',
        hypotheses=p.scenarios,observations=lignes,
        limite='Les hypotheses de recherche ne sont pas une mesure de performance du courtier.'))


def _effet_fondamental(experiences):
    lignes=[]
    for neutre in experiences:
        if neutre.regime_fondamental!='TECHNICAL_CONTROL_NEUTRAL':continue
        for externe in experiences:
            if externe.regime_fondamental==neutre.regime_fondamental:continue
            comparable,raison=_comparables(neutre,externe,permissions=False)
            comparable_c05_total=comparable
            if comparable and _receptions(neutre,{'CALENDRIER'})!=_receptions(externe,{'CALENDRIER'}):
                comparable=False;raison='CALENDRIERS_DIFFERENTS_OU_NON_TRACES'
            a,_,_=_selection(neutre,'REFERENCE');b,_,_=_selection(externe,'REFERENCE')
            lignes.append(dict(reference=neutre.demande.identifiant,candidat=externe.demande.identifiant,
                statut='COMPARABLE' if comparable else 'NON_EVALUABLE',raison=raison,
                difference_pnl=b.pnl_courtier-a.pnl_courtier if comparable else None,
                statut_c05_total='COMPARABLE' if comparable_c05_total else 'NON_EVALUABLE',
                difference_pnl_c05_total=b.pnl_courtier-a.pnl_courtier if comparable_c05_total else None,
                perimetre_c05_total='PERMISSIONS_ET_ANNONCES',
                configurations_brutes_reference=a.comptage.configurations,configurations_brutes_candidat=b.comptage.configurations))
    return tuple(_figer(lignes)) if lignes else (_figer(dict(statut='NON_EVALUABLE',raison='COMPARAISON_FONDAMENTALE_MANQUANTE',
        statut_c05_total='NON_EVALUABLE',difference_pnl_c05_total=None,perimetre_c05_total='PERMISSIONS_ET_ANNONCES')),)


def produire_rapport(experiences,references_v1=None,preuves=None,qualification_semantique=None):
    experiences=tuple(experiences)
    if not experiences or any(not isinstance(r,ResultatExperience) for r in experiences):
        raise ErreurRejeu('expériences du vrai moteur requises')
    if len({r.demande.identifiant for r in experiences})!=len(experiences):raise ErreurRejeu('identifiants d’expériences dupliqués')
    references=dict(references_v1 or {});preuves=preuves if isinstance(preuves,PreuvesValidation) else PreuvesValidation()
    tableaux=tuple(_rapport_experience(r,references,preuves) for r in experiences)
    effectifs=_effectifs_globaux(experiences)
    effectifs_qualifiants=tuple(ligne for ligne in effectifs if ligne['regime_fondamental']=='PERMISSIONS_EXTERNES')
    numeriques=bool(effectifs_qualifiants) and all(c.statut=='SATISFAIT' for ligne in effectifs_qualifiants for c in ligne['criteres'])
    applicables=[t for t,r in zip(tableaux,experiences) if r.usage in ('VALIDATION','RESERVE')
        and r.demande.ecart is None and r.regime_fondamental=='PERMISSIONS_EXTERNES']
    numeriques=numeriques and bool(applicables) and all(c.statut=='SATISFAIT' for t in applicables for c in t['criteres'])
    reels=all(r.manifeste.usage=='COURTIER_HISTORIQUE' and r.complet for r in experiences if r.demande.ecart is None)
    attestations={n:preuves.attestee(n) for n in ('fiche_c04','gel_robot','journaux_demo')}
    prospectif=any(r.usage=='PROSPECTIF' and r.regime_fondamental=='PERMISSIONS_EXTERNES'
        and len(r.jours)>=charger_protocole(r.configuration).seuils.jours_ia
        and all(_selection(r,nom,m)[0].positions_closes>=charger_protocole(r.configuration).prospectif_min_trades
            for nom in r.bras for m in _methodes(r)) for r in experiences)
    statut='VALIDE' if numeriques and reels and all(attestations.values()) and prospectif else 'NON_VALIDE'
    facturation=reconcilier_factures(f for r in experiences for f in r.factures)
    voisins=[]
    for r in experiences:
        if r.demande.ecart is not None:
            b=r.bras['REFERENCE'];m,_,_=_selection(r,'REFERENCE')
            voisins.append(dict(experience=r.demande.identifiant,ecart=r.demande.ecart,
                pnl=m.pnl_courtier,drawdown=m.drawdown_courtier,pertes=sum(t.net<0 for t in b.trades),
                arrets_globaux=tuple(t for t,g in b.gardes if g.arret_global),
                arrets_quotidiens=tuple(t for t,g in b.gardes if g.verrou_quotidien)))
    attendus={e[0] for e in charger_protocole(experiences[0].configuration).perturbations}
    groupes_voisins=[]
    for r in experiences:
        if r.demande.ecart is None:continue
        cle=(r.manifeste.sha256,r.manifeste.usage,r.configuration_origine.technique.empreinte_canonique,
            r.debut_effectif_ms,r.demande.bloc.intervalle_ms.fin_ms,r.demande.scenario,r.demande.mode,_methodes(r),r.regime_fondamental)
        groupe=next((g for g in groupes_voisins if g['cle']==cle
            and g['prototype'].conditions==r.conditions and g['prototype'].manifeste.symboles==r.manifeste.symboles
            and _receptions(g['prototype'])==_receptions(r)),None)
        if groupe is None:
            groupe=dict(cle=cle,prototype=r,resultats=[]);groupes_voisins.append(groupe)
        groupe['resultats'].append(r)
    groupes_rapport=tuple(dict(experiences=tuple(r.demande.identifiant for r in g['resultats']),
        scenario=g['prototype'].demande.scenario,
        complet={r.demande.ecart.nom for r in g['resultats']}==attendus
            and len(g['resultats'])==len(attendus) and all(r.complet for r in g['resultats']))
        for g in groupes_voisins)
    voisinage_complet=bool(groupes_rapport) and all(g['complet'] for g in groupes_rapport)
    limites=[]
    if not reels:limites.append('DONNEES_SYNTHETIQUES_CONTREFACTUELLES_OU_INCOMPLETES')
    if not references:limites.append('V1_ABSENTE_RETENTION_N_A')
    if not all(attestations.values()):limites.append('QUALIFICATION_C04_GEL_OU_DEMONSTRATION_MANQUANTE')
    if not prospectif:limites.append('CONFIRMATION_PROSPECTIVE_C10_MANQUANTE')
    if not voisinage_complet:limites.append('SIX_PERTURBATIONS_NON_COMPLETES')
    configuration=experiences[0].configuration
    ema=configuration.technique.ema['strategy_id'];london=configuration.technique.london['strategy_id']
    perimetres=((ema,),(london,),tuple(sorted((ema,london))))
    matrice_attendue={(bloc,scenario.nom,methodes) for bloc in ('DEVELOPPEMENT','VALIDATION','RESERVE')
        for scenario in charger_protocole(configuration).scenarios for methodes in perimetres}
    matrice_attendue.update(('CONTINU_AVEC_DIAGNOSTIC',s.nom,tuple(sorted((ema,london))))
        for s in charger_protocole(configuration).scenarios)
    protocole=charger_protocole(configuration)
    bornes={b.usage:b.intervalle_ms for b in protocole.blocs}
    bornes['CONTINU_AVEC_DIAGNOSTIC']=protocole.continu.intervalle_ms
    qualifies=tuple(r for r in experiences if r.demande.ecart is None and r.usage in bornes
        and r.debut_effectif_ms==bornes[r.usage].debut_ms
        and r.demande.bloc.intervalle_ms.fin_ms==bornes[r.usage].fin_ms)
    matrice_observee={(r.usage,r.demande.scenario,_methodes(r)) for r in qualifies}
    manquants=tuple(sorted(matrice_attendue-matrice_observee))
    if manquants:limites.append('MATRICE_C10_INCOMPLETE')
    matrice_fondamentale={(r.usage,r.demande.scenario,_methodes(r)) for r in qualifies
        if r.regime_fondamental=='PERMISSIONS_EXTERNES'}
    manquants_fondamental=tuple(sorted(matrice_attendue-matrice_fondamentale))
    if manquants_fondamental:limites.append('MATRICE_C05_EXTERNE_INCOMPLETE')
    if limites:statut='NON_VALIDE'
    return _figer(dict(version_schema='xp-rapport-rejeu-v1',statut=statut,criteres_apriori=tableaux,
        effectifs_globaux=effectifs,preuves_attestees=attestations,limites=limites,
        bilan_couts_projet=dict(factures_originales=len(facturation.factures),cout_ia_total=facturation.total,
            depenses_recherche=facturation.recherche,allocations_methodes=facturation.par_methode,
            garde='Les factures communes aux hypotheses sont reconciliees une seule fois.'),
        voisinage=dict(experiences=voisins,complet=voisinage_complet,groupes=groupes_rapport,
            selection_nouveau_reglage=False),
        a11=tuple(dict(experience=r.demande.identifiant,rapport=rapport_a11(r)) for r in experiences),
        a13=tuple(dict(experience=r.demande.identifiant,rapport=rapport_a13(r,qualification_semantique,preuves))
            for r in experiences if set(r.bras)=={'REFERENCE','IA'}),
        effet_fondamental=_effet_fondamental(experiences),
        essais=dict(experiences=len(experiences),perturbations=len(voisins),
            garde='Les essais multiples et l’exploration deja effectuee limitent les conclusions du test retrospectif.'),
        matrice_c10=dict(complete=not manquants,manquants=manquants,
            fondamental_complet=not manquants_fondamental,manquants_fondamental=manquants_fondamental,
            experiences_aux_bornes_completes=tuple(r.demande.identifiant for r in qualifies)),
        comparaison_demo=tuple(dict(experience=r.demande.identifiant,
            rapport=comparer_couts_demo(r,(),preuves)) for r in experiences),
        garde='Une precision JSON ou semantique ne constitue pas un taux de reussite des trades.'))


def rapporter_papier(nombre_ticks,enregistrements,instantanes,configuration):
    entier(nombre_ticks);bras={}
    for nom,v in dict(instantanes).items():
        trades=tuple(v['trades']);courbe=tuple(v['courbe']);premiers=tuple(v['premiers_remplissages'])
        signaux={};refus={}
        for e in enregistrements:
            if e.enveloppe.bras!=nom:continue
            d=e.vers_dict()
            if d['type']=='CLOTURE' and d.get('signal') is not None:
                signaux[(d['strategie'],d['symbole'],e.enveloppe.instant_utc_ms)]=True
            if d['type']=='INTENTION':
                for i in d.get('issues_nouvelles',()):
                    if i.get('motif') is not None:refus[(d['cle'],i['instant_utc_ms'],i['motif'])]=True
        nombres=defaultdict(int)
        for _,_,motif in refus:nombres[motif]+=1
        with localcontext(Context(prec=48)):
            pnl=sum((t.net for t in trades),D(0));n=len(trades)
            bras[nom]=dict(configurations_potentielles=None,raison_configurations='COMPOSITION_SQUELETTE_NON_INSTRUMENTEE',
                signaux_emis=len(signaux),refus_par_motif=dict(nombres),entrees_remplies=len(premiers),
                positions_closes=n,positions_ouvertes=v['positions_ouvertes'],pnl_net_marche=pnl,
                fonds_propres=courbe[-1].fonds_propres,drawdown_fonds_propres=drawdown(courbe),
                taux_reussite=D(sum(t.net>0 for t in trades))/D(n) if n else None,
                r_moyen_net=sum((t.r_net for t in trades),D(0))/D(n) if n else None,
                scenario_couts=v['scenario'])
    return _figer(dict(version_schema='xp-rapport-papier-v1',statut='NON_VALIDE_FIXTURE',
        nombre_ticks=nombre_ticks,bras=bras,
        empreinte_regles=configuration.technique.empreinte_canonique,
        limite='Le rapport complet C10 utilise produire_rapport avec des ResultatExperience qualifies.'))


def _json_rapport(v):
    if isinstance(v,Enum):return v.value
    if isinstance(v,Decimal):
        if not v.is_finite():raise ErreurRejeu('décimal non fini dans le rapport')
        return str(v)
    if isinstance(v,(date,datetime)):return v.isoformat()
    if is_dataclass(v):return {f.name:_json_rapport(getattr(v,f.name)) for f in fields(v)}
    if isinstance(v,Mapping):
        if any(type(k) is not str for k in v):raise ErreurRejeu('clés JSON textuelles requises')
        return {k:_json_rapport(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [_json_rapport(x) for x in v]
    if isinstance(v,(set,frozenset)):return sorted((_json_rapport(x) for x in v),key=str)
    if type(v) is float and not math.isfinite(v):raise ErreurRejeu('nombre non fini dans le rapport')
    if v is None or type(v) in (str,int,float,bool):return v
    raise ErreurRejeu('valeur non sérialisable dans le rapport')


def serialiser_rapport(rapport):
    return json.dumps(_json_rapport(rapport),ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))

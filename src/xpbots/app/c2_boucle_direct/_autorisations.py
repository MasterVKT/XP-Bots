"""Les déclarations du registre doivent correspondre aux rapports physiques."""
from collections.abc import Mapping
from hashlib import sha256
import json

from xpbots.app.c0_configuration import ErreurApplication
from xpbots.infra.c4_assemblage import lire_fichier
from xpbots.rejeu.c3_rapports import serialiser_rapport

_MAX_OCTETS_RAPPORT=64*1024*1024  # Document de validation ; distinct du plafond d'échange D-11.


def _paires(paires):
    resultat={}
    for k,v in paires:
        if k in resultat:raise ErreurApplication('RAPPORT_AVEC_CLE_DUPLIQUEE')
        resultat[k]=v
    return resultat


def _criteres_valides(criteres,non_applicables=()):
    if (not isinstance(criteres,list) or not criteres or not isinstance(non_applicables,(list,tuple))
            or any(type(n) is not str for n in non_applicables)):
        return False
    exclus=frozenset(non_applicables)
    return all(isinstance(c,Mapping) and type(c.get('nom')) is str and bool(c['nom'])
        and (c.get('statut')=='SATISFAIT' or c.get('statut')=='NON_EVALUABLE' and c['nom'] in exclus)
        for c in criteres)


def _rapport(reference,application):
    b=lire_fichier(reference['chemin'],_MAX_OCTETS_RAPPORT)
    if sha256(b).hexdigest()!=reference['sha256']:raise ErreurApplication('EMPREINTE_RAPPORT_DIFFERENTE')
    def invalide(_):raise ErreurApplication('RAPPORT_NON_FINI')
    try:
        d=json.loads(b.decode('utf-8'),object_pairs_hook=_paires,parse_constant=invalide)
        serialiser_rapport(d)
    except (ValueError,UnicodeError,TypeError):raise ErreurApplication('RAPPORT_INVALIDE') from None
    if (not isinstance(d,Mapping) or set(d)!={'schema','commit','empreintes','rapport'}
            or d['schema']!='xp-dossier-validation-v1' or d['commit']!=application.registre['commit']
            or d['empreintes']!=dict(application.registre['empreintes'])):
        raise ErreurApplication('RAPPORT_VALIDATION_ETRANGER')
    r=d['rapport']
    if (not isinstance(r,Mapping) or r.get('version_schema')!='xp-rapport-rejeu-v1'
            or r.get('statut')!='VALIDE' or r.get('limites')!=[]
            or not isinstance(r.get('preuves_attestees'),Mapping)
            or any(r['preuves_attestees'].get(n) is not True for n in ('fiche_c04','gel_robot','journaux_demo'))
            or not isinstance(r.get('matrice_c10'),Mapping)
            or r['matrice_c10'].get('complete') is not True or r['matrice_c10'].get('fondamental_complet') is not True):
        raise ErreurApplication('VALIDATION_C10_NON_ETABLIE')
    lignes=r.get('criteres_apriori')
    if not isinstance(lignes,list) or not lignes:raise ErreurApplication('CRITERES_C10_ABSENTS')
    london=application.configuration.technique.london['strategy_id']
    if not any(isinstance(l,Mapping) and l.get('usage')=='RESERVE' and london in l.get('methodes',[])
               and l.get('provenance')=='COURTIER_HISTORIQUE' and l.get('regime_fondamental')=='PERMISSIONS_EXTERNES'
               for l in lignes):raise ErreurApplication('RESERVE_LONDON_NON_ETABLIE')
    def satisfaits(lignes):
        return bool(lignes) and all(isinstance(l,Mapping) and _criteres_valides(l.get('criteres')) for l in lignes)
    applicables=[l for l in lignes if isinstance(l,Mapping) and l.get('usage') in ('VALIDATION','RESERVE')
        and l.get('regime_fondamental')=='PERMISSIONS_EXTERNES' and l.get('ecart') is None]
    effectifs=r.get('effectifs_globaux')
    externes=[l for l in effectifs if isinstance(l,Mapping) and l.get('regime_fondamental')=='PERMISSIONS_EXTERNES'] if isinstance(effectifs,list) else []
    if (not satisfaits(applicables) or not satisfaits(externes)
            or not isinstance(r.get('voisinage'),Mapping) or r['voisinage'].get('complet') is not True):
        raise ErreurApplication('VALIDATION_C10_CONTRADICTOIRE')
    return r


def verifier_autorisations(application):
    a=application;d=a.registre
    if a.mode not in ('DEMO','REEL'):return
    def decisions(objet):
        return tuple(x for x in d['decisions'] if x['objet']==objet and x['commit']==d['commit']
            and dict(x['empreintes'])==dict(d['empreintes']))
    if a.mode=='REEL':
        candidats=decisions('DEPLOIEMENT_REEL')
        candidat=next((x for x in reversed(candidats) if {'C10_RESERVE','C10_DEMO'}<=set(x['preuves'])),None)
        if candidat is None:raise ErreurApplication('DECISION_DEPLOIEMENT_REEL_REQUISE')
        for n in ('C10_RESERVE','C10_DEMO'):_rapport(candidat['preuves'][n],a)
    if d['activation_veto']:
        ref=dict(chemin=d['statut_a13']['rapport'],sha256=d['statut_a13']['empreinte'])
        if not any(x['preuves'].get('A13')==ref for x in decisions('ACTIVATION_VETO_A13')):
            raise ErreurApplication('DECISION_VETO_A13_REQUISE')
        r=_rapport(ref,a);london=a.configuration.technique.london['strategy_id']
        a13=r.get('a13')
        if not isinstance(a13,list):raise ErreurApplication('VALIDATION_FINANCIERE_A13_ABSENTE')
        valides=[]
        for ligne in a13:
            v=ligne.get('rapport') if isinstance(ligne,Mapping) else None
            if (isinstance(v,Mapping) and v.get('statut')=='VALIDE' and v.get('preuves_reelles_attestees') is True
                    and _criteres_valides(v.get('criteres'),v.get('criteres_non_applicables',())) and any(isinstance(c,Mapping)
                        and c.get('nom')=='trades_clos:IA:'+london and c.get('statut')=='SATISFAIT' for c in v['criteres'])
                    and isinstance(v.get('qualification_semantique'),Mapping)
                    and v['qualification_semantique'].get('statut')=='QUALIFIE_DECLARE'
                    and _criteres_valides(v['qualification_semantique'].get('criteres'))):
                valides.append(v)
        if not valides:raise ErreurApplication('VALIDATION_FINANCIERE_A13_ABSENTE')

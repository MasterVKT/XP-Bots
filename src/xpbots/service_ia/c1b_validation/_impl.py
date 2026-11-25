"""Implémentation de la couche 1b (validation). Révisable sous harnais complet."""
from xpbots.service_ia.c0_types import (ErreurService, RessourcesIA, decoder, texte)


def _sortie(r,sortie):
    if not isinstance(r,RessourcesIA):raise ErreurService('RESSOURCES_CHARGEES_REQUISES')
    texte(sortie,True)
    b=sortie.encode('utf-8')
    if len(b)>r.p['max_response_bytes']:raise ErreurService('SORTIE_TROP_LONGUE')
    return decoder(b)


def _objet(v,schema):
    if type(v) is not dict or set(v)!=set(schema['required']):
        raise ErreurService('CHAMPS_SORTIE_INVALIDES')


def valider_extraction(ressources,sortie,item):
    r=ressources;v=_sortie(r,sortie);s=r.schema('EXTRACTION');_objet(v,s)
    if type(item) is not dict:raise ErreurService('ITEM_REQUIS')
    texte(item.get('item_id'));texte(item.get('provided_text'),True)
    for cle,valeur in v.items():
        if type(valeur) is not str:raise ErreurService('SORTIE_TEXTUELLE_REQUISE')
        autorisees=s['properties'][cle].get('enum')
        if autorisees is not None and valeur not in autorisees:
            raise ErreurService('ENUM_SORTIE_INVALIDE')
    if v['item_id']!=item['item_id']:raise ErreurService('ITEM_ETRANGER')
    citation=v['evidence_quote']
    if len(citation)>r.p['evidence_quote_max_characters']:
        raise ErreurService('CITATION_TROP_LONGUE')
    if citation and citation not in item['provided_text']:
        raise ErreurService('CITATION_NON_TRANSMISE')
    return v


def valider_note(ressources,sortie,kind,evidence_ids):
    r=ressources
    if kind not in ('BRIEFING','JOURNAL','WEEKLY_REVIEW'):raise ErreurService('NOTE_INCONNUE')
    if not isinstance(evidence_ids,(tuple,list,set,frozenset)):raise ErreurService('PREUVES_EXPLICITES_REQUISES')
    for identifiant in evidence_ids:texte(identifiant)
    connus=frozenset(evidence_ids)
    v=_sortie(r,sortie);s=r.schema(kind);_objet(v,s)
    if (type(v['schema_version']) is not str
            or v['schema_version'] not in s['properties']['schema_version']['enum']
            or type(v['kind']) is not str or v['kind']!=kind):
        raise ErreurService('VERSION_OU_KIND_NOTE_INVALIDE')
    for cle,parametre in (('observations','advisory_max_observations'),
                         ('uncertainties','advisory_max_uncertainties'),
                         ('hypotheses','advisory_max_hypotheses')):
        if type(v[cle]) is not list or len(v[cle])>r.p[parametre]:
            raise ErreurService('LISTE_NOTE_HORS_BORNES')
    def court(valeur):
        texte(valeur,True)
        if len(valeur)>r.p['advisory_max_text_characters']:raise ErreurService('TEXTE_NOTE_TROP_LONG')
    for obs in v['observations']:
        _objet(obs,s['properties']['observations']['items']);court(obs['text'])
        ids=obs['evidence_ids']
        if (type(ids) is not list or not 1<=len(ids)<=r.p['advisory_max_evidence_ids_per_observation']
                or any(type(i) is not str or i not in connus for i in ids)):
            raise ErreurService('PREUVE_NOTE_NON_FOURNIE')
    for incertitude in v['uncertainties']:court(incertitude)
    for hypothese in v['hypotheses']:
        _objet(hypothese,s['properties']['hypotheses']['items'])
        court(hypothese['statement']);court(hypothese['validation_plan'])
    if kind=='BRIEFING' and v['hypotheses']:raise ErreurService('HYPOTHESE_DANS_BRIEFING')
    return v

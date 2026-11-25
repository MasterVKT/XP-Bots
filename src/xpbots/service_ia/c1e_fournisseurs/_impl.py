"""Implémentation de la couche 1e (fournisseurs). Révisable sous harnais complet."""
from dataclasses import dataclass
from xpbots.service_ia.c0_types import (ErreurService, RessourcesIA, JobIA,
    RequeteHTTP, ReponseHTTP, canonique, decoder, texte, entier)

_FORMATS_FOURNISSEURS={'GROQ_FREE':'GROQ','GEMINI_FREE':'GEMINI','OPENAI_PAID_OPTIONAL':'OPENAI'}
_HTTP_SUCCES=200  # Code de protocole HTTP, hors effectif financier.


def _fournisseur(r,pid):
    if not isinstance(r,RessourcesIA):raise ErreurService('RESSOURCES_CHARGEES_REQUISES')
    p=r.fournisseur(pid)
    if pid not in _FORMATS_FOURNISSEURS:raise ErreurService('FORMAT_FOURNISSEUR_INCONNU')
    return p,_FORMATS_FOURNISSEURS[pid]


@dataclass(frozen=True)
class UsageFournisseur:
    usage_brut: bytes | None
    tokens_entree: int | None
    tokens_sortie: int | None
    modele_recu: str | None = None

    def __post_init__(self):
        if self.usage_brut is not None:decoder(self.usage_brut)
        for v in (self.tokens_entree,self.tokens_sortie):
            if v is not None:entier(v)
        if self.modele_recu is not None:texte(self.modele_recu)

    @property
    def usage(self):return decoder(self.usage_brut) if self.usage_brut is not None else None


@dataclass(frozen=True)
class RetourFournisseur:
    texte: str
    usage_brut: bytes | None
    tokens_entree: int | None
    tokens_sortie: int | None
    modele_recu: str | None = None

    def __post_init__(self):
        texte(self.texte)
        UsageFournisseur(self.usage_brut,self.tokens_entree,self.tokens_sortie,self.modele_recu)

    @property
    def usage(self):return decoder(self.usage_brut) if self.usage_brut is not None else None


def construire_requete(ressources,job,fournisseur,dossier=None):
    r=ressources;p,format_api=_fournisseur(r,fournisseur)
    if not isinstance(job,JobIA):raise ErreurService('JOB_REEL_REQUIS')
    if job.fournisseur is not None and job.fournisseur!=fournisseur:
        raise ErreurService('FOURNISSEUR_JOB_INCOMPATIBLE')
    d=decoder(job.dossier if dossier is None else dossier)
    if job.kind in ('EXTRACTION','GOLDEN'):
        if set(d)!={'item_id','title','issuer','provided_text'} or d['item_id']!=job.item_id:
            raise ErreurService('DOSSIER_EXTRACTION_INVALIDE')
        texte(d['item_id']);texte(d['title'],True);texte(d['provided_text'])
        if d['issuer'] not in {f['issuer'] for f in r.p['feeds']}:
            raise ErreurService('ISSUER_DOSSIER_INVALIDE')
    schema=r.schema(job.kind);prompt=r.prompt(job.kind);user=canonique(d).decode('utf-8')
    nom=schema['properties']['schema_version']['enum'][0].replace('-','_')
    maximum=r.p['max_output_tokens_including_reasoning']
    if format_api=='GROQ':
        if p['strict_json_schema'] is not True:raise ErreurService('CONTRAINTE_API_MODIFIEE')
        corps=dict(model=p['model'],messages=[dict(role='system',content=prompt),dict(role='user',content=user)],
            temperature=p['temperature'],reasoning_effort=p['reasoning_effort'],
            max_completion_tokens=maximum,stream=False,
            response_format=dict(type='json_schema',json_schema=dict(name=nom,strict=True,schema=schema)))
    elif format_api=='GEMINI':
        if p['structured_json'] is not True:raise ErreurService('CONTRAINTE_API_MODIFIEE')
        corps=dict(systemInstruction=dict(parts=[dict(text=prompt)]),
            contents=[dict(role='user',parts=[dict(text=user)])],
            generationConfig=dict(temperature=p['temperature'],maxOutputTokens=maximum,
                thinkingConfig=dict(thinkingLevel=p['thinking_level'].upper()),
                responseMimeType='application/json',responseJsonSchema=schema))
    else:
        if p['strict_json_schema'] is not True or p['automatic_prompt_cache_storage_enabled'] is not False:
            raise ErreurService('CONTRAINTE_API_MODIFIEE')
        corps=dict(model=p['model'],input=[dict(role='system',content=prompt),dict(role='user',content=user)],
            reasoning=dict(effort=p['reasoning_effort']),max_output_tokens=maximum,
            service_tier=p['service_tier'],store=False,stream=False,
            text=dict(format=dict(type='json_schema',name=nom,strict=True,schema=schema)))
    return RequeteHTTP(p['endpoint'],'POST',(('Content-Type','application/json'),),canonique(corps),
        r.p['http_inference_timeout_seconds'],r.p['max_response_bytes'],fournisseur)


def _compteur(usage,cle):
    if type(usage) is not dict:return None
    v=usage.get(cle)
    return v if type(v) is int and v>=0 else None


def _sans_outil(message):
    if (message.get('refusal') not in (None,'') or message.get('tool_calls') not in (None,[])
            or message.get('function_call') is not None):raise ErreurService('REFUS_OU_OUTIL')


def _groq(v):
    choix=v['choices'][0];message=choix['message']
    if choix['finish_reason']!='stop' or type(message) is not dict:raise ErreurService('SORTIE_NON_TERMINEE')
    _sans_outil(message)
    return message['content']


def _gemini(v):
    feedback=v.get('promptFeedback',{})
    if type(feedback) is not dict or feedback.get('blockReason') not in (None,''):
        raise ErreurService('REPONSE_BLOQUEE')
    candidat=v['candidates'][0]
    if candidat['finishReason']!='STOP':raise ErreurService('SORTIE_NON_TERMINEE')
    parties=candidat['content']['parts']
    if type(parties) is not list:raise ErreurService('PARTIES_INVALIDES')
    textes=[]
    for partie in parties:
        if type(partie) is not dict or set(partie)-{'text','thought','thoughtSignature'}:
            raise ErreurService('REFUS_OU_OUTIL')
        if 'thought' in partie and type(partie['thought']) is not bool:
            raise ErreurService('PARTIE_THOUGHT_INVALIDE')
        if partie.get('thought') is True:continue
        if 'text' in partie:
            texte(partie['text'],True);textes.append(partie['text'])
    return ''.join(textes)


def _openai(v):
    if v.get('status')!='completed' or v.get('incomplete_details') is not None:
        raise ErreurService('SORTIE_NON_TERMINEE')
    sorties=v['output']
    if type(sorties) is not list:raise ErreurService('OUTPUT_INVALIDE')
    textes=[]
    for bloc in sorties:
        if type(bloc) is not dict:raise ErreurService('BLOC_OUTPUT_INVALIDE')
        if bloc.get('type')=='reasoning':continue
        if bloc.get('type')!='message':raise ErreurService('REFUS_OU_OUTIL')
        _sans_outil(bloc)
        contenu=bloc['content']
        if type(contenu) is not list:raise ErreurService('CONTENU_OUTPUT_INVALIDE')
        for partie in contenu:
            if type(partie) is not dict or partie.get('type')!='output_text':
                raise ErreurService('REFUS_OU_OUTIL')
            texte(partie['text'],True);textes.append(partie['text'])
    return ''.join(textes)


def _corps(r,reponse):
    if not isinstance(reponse,ReponseHTTP):raise ErreurService('REPONSE_HTTP_REQUISE')
    if len(reponse.corps)>r.p['max_response_bytes']:raise ErreurService('REPONSE_TROP_LONGUE')
    return decoder(reponse.corps)


def _usage(format_api,v):
    brut=v.get('usageMetadata') if format_api=='GEMINI' else v.get('usage')
    if type(brut) is not dict:brut=None
    if format_api=='GROQ':i,o=_compteur(brut,'prompt_tokens'),_compteur(brut,'completion_tokens')
    elif format_api=='GEMINI':
        i=_compteur(brut,'promptTokenCount');total=_compteur(brut,'totalTokenCount')
        o=total-i if total is not None and i is not None and total>=i else None
    else:i,o=_compteur(brut,'input_tokens'),_compteur(brut,'output_tokens')
    modele=v.get('modelVersion') if format_api=='GEMINI' else v.get('model')
    if type(modele) is not str or not modele.strip():modele=None
    return UsageFournisseur(canonique(brut) if brut is not None else None,i,o,modele)


def extraire_usage(ressources,fournisseur,reponse):
    _,format_api=_fournisseur(ressources,fournisseur)
    return _usage(format_api,_corps(ressources,reponse))


def decoder_reponse(ressources,fournisseur,reponse):
    _,format_api=_fournisseur(ressources,fournisseur)
    v=_corps(ressources,reponse)
    if reponse.statut!=_HTTP_SUCCES:raise ErreurService('STATUT_HTTP_NON_SUCCES')
    try:
        contenu={'GROQ':_groq,'GEMINI':_gemini,'OPENAI':_openai}[format_api](v)
        usage=_usage(format_api,v)
        return RetourFournisseur(contenu,usage.usage_brut,usage.tokens_entree,
            usage.tokens_sortie,usage.modele_recu)
    except ErreurService:raise
    except (KeyError,TypeError,IndexError,ValueError):raise ErreurService('FORMAT_REPONSE_INVALIDE') from None

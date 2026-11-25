"""Réponses A08 fabriquées ; aucun client distant ni donnée de compte."""
from xpbots.service_ia.c0_types import ReponseHTTP, canonique
from .support import ressources, document, extraction


def enveloppe(pid,sortie=None,usage=True):
    r=ressources();sortie=canonique(extraction()).decode() if sortie is None else sortie
    if pid==r.p['providers'][0]['id']:
        v=dict(choices=[dict(finish_reason='stop',message=dict(role='assistant',content=sortie))],
               model=r.fournisseur(pid)['model'])
        if usage:v['usage']=dict(prompt_tokens=100,completion_tokens=50)
    elif pid==r.p['providers'][1]['id']:
        v=dict(candidates=[dict(finishReason='STOP',content=dict(parts=[dict(text=sortie)]))],
               modelVersion=r.fournisseur(pid)['model'])
        if usage:v['usageMetadata']=dict(promptTokenCount=100,totalTokenCount=150,thoughtsTokenCount=10)
    else:
        v=dict(status='completed',model=r.fournisseur(pid)['model'],output=[
            dict(type='reasoning',summary=[]),
            dict(type='message',content=[dict(type='output_text',text=sortie)])])
        if usage:v['usage']=dict(input_tokens=100,output_tokens=50,output_tokens_details=dict(reasoning_tokens=10))
    return v


def reponse(pid,sortie=None,usage=True,statut=200):
    return ReponseHTTP(statut,(),canonique(enveloppe(pid,sortie,usage)),document().collecte_ms)

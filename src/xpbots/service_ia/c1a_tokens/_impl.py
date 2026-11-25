"""Implémentation de la couche 1a (tokens). Révisable sous harnais complet."""
from dataclasses import dataclass
from xpbots.service_ia.c0_types import (ErreurService, RessourcesIA, RequeteHTTP,
    canonique, decoder, entier, texte)


def _ressources(r):
    if not isinstance(r,RessourcesIA):raise ErreurService('RESSOURCES_CHARGEES_REQUISES')
    return r


def compter_entree(ressources,corps):
    r=_ressources(ressources)
    if type(corps) is not bytes:raise ErreurService('CORPS_SERIALISE_REQUIS')
    try:corps.decode('utf-8')
    except UnicodeError:raise ErreurService('CORPS_UTF8_REQUIS') from None
    return len(corps)+r.p['input_count_fallback_utf8_overhead_tokens']


@dataclass(frozen=True)
class RequeteBornee:
    requete: RequeteHTTP
    dossier: bytes
    tokens_entree: int
    documents_retires: tuple = ()

    def __post_init__(self):
        if not isinstance(self.requete,RequeteHTTP) or self.requete.corps is None:
            raise ErreurService('REQUETE_AVEC_CORPS_REQUISE')
        decoder(self.dossier);entier(self.tokens_entree)
        object.__setattr__(self,'documents_retires',tuple(self.documents_retires))
        for identifiant in self.documents_retires:texte(identifiant)


def preparer_requete(ressources,dossier,construire,*,reduire_documents=False):
    r=_ressources(ressources)
    if type(reduire_documents) is not bool or not callable(construire):
        raise ErreurService('PREPARATION_INVALIDE')
    objet=decoder(dossier);retires=[]
    if reduire_documents:
        if 'provided_text' in objet:raise ErreurService('EXTRACTION_INTEGRALE_REQUISE')
        docs=objet.get('documents')
        if type(docs) is not list:raise ErreurService('DOCUMENTS_EXPLICITES_REQUIS')
        for doc in docs:
            if type(doc) is not dict:raise ErreurService('DOCUMENT_OBJET_REQUIS')
            texte(doc.get('item_id'))
    while True:
        transmis=canonique(objet)
        requete=construire(transmis)
        if not isinstance(requete,RequeteHTTP) or requete.corps is None:
            raise ErreurService('CONSTRUCTEUR_HORS_CONTRAT')
        decoder(requete.corps)
        borne=compter_entree(r,requete.corps)
        if borne<=r.p['max_input_tokens_upper_bound']:
            return RequeteBornee(requete,transmis,borne,tuple(retires))
        if not reduire_documents or not objet['documents']:return None
        retires.append(objet['documents'].pop()['item_id'])

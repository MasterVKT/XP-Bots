"""Seule émission HTTP ; aucune clé n'entre dans les valeurs archivées."""
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from http.client import HTTPException
from xpbots.service_ia.c0_types import (ErreurService,RessourcesIA,RequeteHTTP,ReponseHTTP,texte,instant)

_ENTETES_REQUETE=frozenset(('content-type','accept','if-none-match','if-modified-since'))
_ENTETES_REPONSE=frozenset(('content-type','retry-after','location','etag','last-modified'))


class _SansRedirection(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None


class TransportHTTP:
    def __init__(self,ressources,horloge,*,ouvreur=None,cles=None,autoriser_http_reel=False):
        if not isinstance(ressources,RessourcesIA) or type(autoriser_http_reel) is not bool:
            raise ErreurService('PARAMETRES_HTTP_INVALIDES')
        self.r=ressources;self.h=horloge;self._cles={};self._ouvreur=ouvreur
        if cles is not None:
            if type(cles) is not dict:raise ErreurService('CLES_HTTP_INVALIDES')
            for pid,v in cles.items():
                ressources.fournisseur(pid);texte(v)
                if any(c in v for c in '\r\n'):raise ErreurService('CLE_HTTP_INVALIDE')
                self._cles[pid]=v
        if ouvreur is None and autoriser_http_reel:self._ouvreur=build_opener(_SansRedirection())
        if self._ouvreur is not None and not callable(getattr(self._ouvreur,'open',None)):
            raise ErreurService('OUVREUR_HTTP_REQUIS')

    def _verifier(self,q):
        if not isinstance(q,RequeteHTTP):raise ErreurService('REQUETE_HTTP_REQUISE')
        if any(k.casefold() not in _ENTETES_REQUETE for k,_ in q.entetes):raise ErreurService('ENTETE_HTTP_INTERDITE')
        if q.fournisseur is not None:
            f=self.r.fournisseur(q.fournisseur)
            if q.url!=f['endpoint'] or q.methode!='POST' or q.corps is None:
                raise ErreurService('ENDPOINT_HTTP_INTERDIT')
            if q.timeout_s>self.r.p['http_inference_timeout_seconds'] or q.max_octets>self.r.p['max_response_bytes']:
                raise ErreurService('LIMITES_HTTP_INCORRECTES')
        else:
            u=urlsplit(q.url)
            if (q.methode!='GET' or q.corps is not None or u.port not in (None,443)
                    or u.hostname not in {urlsplit(f['url']).hostname for f in self.r.p['feeds']}
                    or q.timeout_s>self.r.p['rss_http_timeout_seconds'] or q.max_octets>self.r.p['rss_max_download_bytes']):
                raise ErreurService('SOURCE_HTTP_INTERDITE')

    def __call__(self,q):
        self._verifier(q)
        if self._ouvreur is None:raise OSError('HTTP_NON_AUTORISE')
        headers=dict(q.entetes)
        if q.fournisseur is not None:
            cle=self._cles.get(q.fournisseur)
            if cle is None:raise OSError('CLE_HTTP_ABSENTE')
            # Les formats REST reconnus sont ceux des codecs A08, pas des modèles déduits.
            if q.fournisseur==self.r.p['providers'][1]['id']:headers['x-goog-api-key']=cle
            else:headers['Authorization']='Bearer '+cle
        requete=Request(q.url,data=q.corps,headers=headers,method=q.methode)
        reponse=None
        try:
            try:reponse=self._ouvreur.open(requete,timeout=q.timeout_s)
            except HTTPError as e:reponse=e
            if reponse.geturl()!=q.url:raise OSError('REDIRECTION_IMPLICITE_INTERDITE')
            entetes=[]
            for nom in _ENTETES_REPONSE:
                valeurs=reponse.headers.get_all(nom) or []
                if len(valeurs)>1:raise OSError('ENTETE_HTTP_AMBIGUE')
                if valeurs:entetes.append((nom,valeurs[0]))
            b=reponse.read(q.max_octets+1)
            if type(b) is not bytes:raise OSError('CORPS_HTTP_INVALIDE')
            if any(c.encode('utf-8') in b for c in self._cles.values()):
                raise OSError('REPONSE_HTTP_CONFIDENTIELLE')
            return ReponseHTTP(reponse.getcode(),tuple(entetes),b,instant(self.h.maintenant_ms()))
        except (OSError,HTTPException,ValueError,TypeError,AttributeError):
            raise OSError('TRANSPORT_HTTP_INDISPONIBLE') from None
        finally:
            if reponse is not None:
                try:reponse.close()
                except (OSError,ValueError):raise OSError('FERMETURE_HTTP_IMPOSSIBLE') from None

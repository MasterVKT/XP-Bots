"""Collecte A04 par ports externes ; textes et connaissance archivés séparément."""
from dataclasses import dataclass, asdict
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from xpbots.service_ia.c0_types import (ErreurService, RessourcesIA, DocumentIA,
    RequeteHTTP, ReponseHTTP, canonique, entier, instant, iso, texte, utc)
from xpbots.service_ia.c1c_normalisation import normaliser_flux, canoniser_url

_HTTP_SUCCES=200  # Format du protocole HTTP, hors effectif financier.
_REDIRECTIONS_RSS_MAXIMUM=3  # A04, borne documentaire sans champ dans l'export IA.
_REDIRECTIONS=frozenset((301,302,303,307,308))


def _ms(s):return timedelta(seconds=s)//timedelta(milliseconds=1)


@dataclass(frozen=True)
class CollecteRSS:
    issuer: str
    recu_ms: int
    couverture: str
    nouveaux: tuple
    statut: str
    anomalies: tuple = ()

    def __post_init__(self):
        texte(self.issuer);instant(self.recu_ms)
        if self.couverture not in ('COMPLETE','PARTIAL') or self.statut not in ('RECU','NON_MODIFIE','DIFFERE','ERREUR'):
            raise ErreurService('COLLECTE_INVALIDE')
        if not isinstance(self.nouveaux,(tuple,list)) or not isinstance(self.anomalies,(tuple,list)):
            raise ErreurService('COLLECTIONS_REQUISES')
        object.__setattr__(self,'nouveaux',tuple(self.nouveaux));object.__setattr__(self,'anomalies',tuple(self.anomalies))
        if any(not isinstance(d,DocumentIA) for d in self.nouveaux):raise ErreurService('DOCUMENTS_REQUIS')
        for a in self.anomalies:texte(a)


def _document(ligne):
    if type(ligne) is not dict or type(ligne.get('document')) is not dict:
        raise ErreurService('ARCHIVE_DOCUMENT_INVALIDE')
    try:d=DocumentIA(**ligne['document'])
    except TypeError:raise ErreurService('ARCHIVE_DOCUMENT_INVALIDE') from None
    connu=instant(ligne.get('content_known_at'))
    if connu!=d.collecte_ms or ligne.get('item_id')!=d.item_id or ligne.get('text_hash')!=d.hash_texte:
        raise ErreurService('ARCHIVE_DOCUMENT_INCOHERENTE')
    return d


def _correspond(ligne,f):
    d=_document(ligne)
    if d.collecte_ms>f['known_at_ms'] or f['issuer'] is not None and d.issuer!=f['issuer']:return False
    if f.get('debut_ms') is not None and (d.publie_ms is None or d.publie_ms<f['debut_ms']):return False
    if f.get('fin_ms') is not None and (d.publie_ms is None or d.publie_ms>=f['fin_ms']):return False
    urls,hashes=f.get('urls',()),f.get('hashes',())
    if (urls or hashes) and d.url not in urls and d.hash_texte not in hashes:return False
    return True


def _ligne(d):
    return dict(item_id=d.item_id,url=d.url,issuer=d.issuer,
        published_at=iso(d.publie_ms) if d.publie_ms is not None else None,
        first_seen=iso(d.premiere_vue_ms),text_hash=d.hash_texte,text=d.texte,
        parser_version=d.version_parseur,content_known_at=d.collecte_ms,document=asdict(d))


class CollecteurRSS:
    def __init__(self,ressources,depot,http,horloge,*,selectionner=None):
        if not isinstance(ressources,RessourcesIA):raise ErreurService('RESSOURCES_CHARGEES_REQUISES')
        if not callable(http) or not callable(getattr(depot,'transaction',None)):
            raise ErreurService('PORTS_COLLECTEUR_REQUIS')
        if not callable(getattr(horloge,'maintenant_ms',None)):raise ErreurService('HORLOGE_REQUISE')
        if selectionner is not None and not callable(selectionner):raise ErreurService('SELECTEUR_INVALIDE')
        self.r=ressources;self.depot=depot;self.http=http;self.horloge=horloge;self._dernier=None
        self._selectionner=selectionner or self._selection_memoire

    def _maintenant(self):
        t=instant(self.horloge.maintenant_ms())
        if self._dernier is not None and t<self._dernier:raise ErreurService('HORLOGE_EN_RECUL')
        self._dernier=t;return t

    def _feed(self,issuer):
        for f in self.r.p['feeds']:
            if f['issuer']==issuer:return f
        raise ErreurService('SOURCE_HORS_ALLOWLIST')

    def _selection_memoire(self,f):
        return self.depot.transaction(lambda t:tuple(v for v in t['source_items'].values() if _correspond(v,f)))

    def _selection(self,f):
        lignes=tuple(self._selectionner(dict(f)));docs={}
        for ligne in lignes:
            if not _correspond(ligne,f):continue
            d=_document(ligne)
            if d.item_id in docs and docs[d.item_id]!=d:raise ErreurService('ID_ARCHIVE_REECRIT')
            docs[d.item_id]=d
        return tuple(sorted(docs.values(),key=lambda d:(d.publie_ms if d.publie_ms is not None else d.premiere_vue_ms,d.item_id)))

    def documents(self,issuer=None,*,debut_ms=None,fin_ms=None,known_at_ms=None):
        if issuer is not None:self._feed(issuer)
        now=self._maintenant()
        connu=now if known_at_ms is None else instant(known_at_ms)
        if connu>now:raise ErreurService('RECHERCHE_FUTURE')
        for t in (debut_ms,fin_ms):
            if t is not None:instant(t)
        if debut_ms is not None and fin_ms is not None and fin_ms<=debut_ms:
            raise ErreurService('INTERVALLE_RECHERCHE_INVALIDE')
        return self._selection(dict(issuer=issuer,debut_ms=debut_ms,fin_ms=fin_ms,known_at_ms=connu))

    def _reprise(self,reponse,now):
        maximum=utc('9999-12-31T23:59:59.999Z')
        debut=min(maximum,now+_ms(self.r.p['rss_failure_backoff_seconds']))
        valeur=reponse.entete('Retry-After') if isinstance(reponse,ReponseHTTP) else None
        if not valeur:return debut
        valeur=valeur.strip()
        if valeur.isascii() and valeur.isdigit():
            chiffres=valeur.lstrip('0') or '0';borne=str((maximum-now)//_ms(1))
            if len(chiffres)>len(borne) or len(chiffres)==len(borne) and chiffres>borne:return maximum
            return max(debut,now+int(chiffres)*_ms(1))
        try:
            dt=parsedate_to_datetime(valeur)
            if dt.tzinfo is None:return debut
            return max(debut,utc(dt.astimezone(timezone.utc).isoformat()))
        except (ValueError,TypeError,OverflowError):return debut

    def _echec(self,issuer,reponse,raison):
        now=self._maintenant();prochain=self._reprise(reponse,now)
        def operation(t):
            s=t['feed_state'].setdefault(issuer,{})
            s.update(issuer=issuer,coverage='PARTIAL',next_poll_ms=prochain,last_failure_ms=now,
                error=raison,http_status=reponse.statut if isinstance(reponse,ReponseHTTP) else None)
        self.depot.transaction(operation)
        return CollecteRSS(issuer,now,'PARTIAL',(),'ERREUR',(raison,))

    def collecter(self,issuer):
        source=self._feed(issuer);now=self._maintenant()
        etat=self.depot.transaction(lambda t:dict(t['feed_state'].get(issuer,{})))
        suivant=entier(etat.get('next_poll_ms',0))
        if now<suivant:return CollecteRSS(issuer,now,etat.get('coverage','PARTIAL'),(),'DIFFERE')
        headers=[('Accept','application/rss+xml, application/atom+xml, application/xml, text/xml')]
        for cle,nom in (('etag','If-None-Match'),('last_modified','If-Modified-Since')):
            if etat.get(cle):headers.append((nom,etat[cle]))
        cible=source['url'];redirections=0;rep=None
        try:
            while True:
                envoye=self._maintenant()
                q=RequeteHTTP(cible,'GET',tuple(headers),None,self.r.p['rss_http_timeout_seconds'],self.r.p['rss_max_download_bytes'])
                rep=self.http(q);recu=self._maintenant()
                if not isinstance(rep,ReponseHTTP):raise ErreurService('REPONSE_HTTP_REQUISE')
                if not envoye<=rep.recu_ms<=recu:raise ErreurService('REPONSE_NON_CAUSALE')
                if recu-envoye>_ms(q.timeout_s):raise ErreurService('RSS_TARDIF')
                if len(rep.corps)>q.max_octets:raise ErreurService('RSS_TROP_GROS')
                if rep.statut not in _REDIRECTIONS:break
                if redirections>=_REDIRECTIONS_RSS_MAXIMUM:raise ErreurService('REDIRECTIONS_DEPASSEES')
                cible=canoniser_url(self.r,issuer,rep.entete('Location'),cible);redirections+=1
            if rep.statut==304:
                if etat.get('has_copy') is not True:raise ErreurService('304_SANS_COPIE')
                couverture=etat['copy_coverage']
                self.depot.transaction(lambda t:t['feed_state'][issuer].update(coverage=couverture,
                    next_poll_ms=recu+_ms(self.r.p['rss_poll_seconds']),last_success_ms=recu,error=None,http_status=rep.statut))
                return CollecteRSS(issuer,recu,couverture,(),'NON_MODIFIE')
            if rep.statut!=_HTTP_SUCCES:return self._echec(issuer,rep,'RSS_HTTP_REFUSE')
            premier=normaliser_flux(self.r,issuer,rep.corps,recu)
            connus=self._selection(dict(issuer=issuer,known_at_ms=recu,
                urls=tuple(d.url for d in premier.documents),hashes=tuple(d.hash_texte for d in premier.documents))) if premier.documents else ()
            flux=normaliser_flux(self.r,issuer,rep.corps,recu,connus=connus)
            brut=sha256(rep.corps).hexdigest()
            def operation(t):
                nouveaux=[]
                for d in flux.documents:
                    ancienne=t['source_items'].get(d.item_id)
                    if ancienne is None:
                        t['source_items'][d.item_id]=_ligne(d);nouveaux.append(d)
                    elif _document(ancienne).hash_texte!=d.hash_texte:raise ErreurService('ID_DOCUMENT_REECRIT')
                archive='response:'+issuer+':'+brut
                if archive not in t['feed_state']:
                    t['feed_state'][archive]=dict(issuer=issuer,received_at=recu,xml_sha256=brut,
                        raw_response=rep.corps.hex(),item_ids=[d.item_id for d in flux.documents])
                t['feed_state'][issuer]=dict(issuer=issuer,coverage=flux.couverture,
                    copy_coverage=flux.couverture,has_copy=True,last_success_ms=recu,
                    next_poll_ms=recu+_ms(self.r.p['rss_poll_seconds']),etag=rep.entete('ETag'),
                    last_modified=rep.entete('Last-Modified'),http_status=rep.statut,error=None,xml_sha256=brut)
                return tuple(nouveaux)
            nouveaux=self.depot.transaction(operation)
            return CollecteRSS(issuer,recu,flux.couverture,nouveaux,'RECU',flux.anomalies)
        except (OSError,ValueError,TypeError,KeyError):
            return self._echec(issuer,rep,'RSS_INDISPONIBLE_OU_INVALIDE')

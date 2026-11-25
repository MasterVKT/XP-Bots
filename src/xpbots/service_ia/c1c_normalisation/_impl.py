"""Implémentation de la couche 1c (normalisation). Révisable sous harnais complet."""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree
from xpbots.service_ia.c0_types import (ErreurService, RessourcesIA, DocumentIA,
    empreinte, instant, texte, utc)


@dataclass(frozen=True)
class FluxNormalise:
    documents: tuple
    couverture: str
    anomalies: tuple = ()

    def __post_init__(self):
        if not isinstance(self.documents,(tuple,list)) or not isinstance(self.anomalies,(tuple,list)):
            raise ErreurService('COLLECTION_EXPLICITE_REQUISE')
        object.__setattr__(self,'documents',tuple(self.documents))
        object.__setattr__(self,'anomalies',tuple(self.anomalies))
        if any(not isinstance(d,DocumentIA) for d in self.documents):raise ErreurService('DOCUMENTS_REQUIS')
        if self.couverture not in ('COMPLETE','PARTIAL'):raise ErreurService('COUVERTURE_FLUX_INVALIDE')
        for a in self.anomalies:texte(a)


class _HTMLVisible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.morceaux=[];self.masques=[]

    def handle_starttag(self,tag,attrs):
        tag=tag.rsplit(':',1)[-1]
        if tag in ('script','style'):self.masques.append(tag)
        elif not self.masques and tag in ('p','div','br','li','h1','h2','h3','tr'):
            self.morceaux.append('\n')

    def handle_endtag(self,tag):
        tag=tag.rsplit(':',1)[-1]
        if self.masques:
            if self.masques[-1]==tag:self.masques.pop()
        elif tag in ('p','div','li','h1','h2','h3','tr'):self.morceaux.append('\n')

    def handle_data(self,data):
        if not self.masques:self.morceaux.append(data)


def nettoyer_html(valeur):
    texte(valeur,True)
    p=_HTMLVisible()
    try:p.feed(valeur);p.close()
    except (ValueError,RecursionError):raise ErreurService('HTML_INVALIDE') from None
    return ' '.join(''.join(p.morceaux).split())


def _source(r,issuer):
    if not isinstance(r,RessourcesIA):raise ErreurService('RESSOURCES_CHARGEES_REQUISES')
    for f in r.p['feeds']:
        if f['issuer']==issuer:return f
    raise ErreurService('SOURCE_HORS_ALLOWLIST')


def canoniser_url(ressources,issuer,url,base=None):
    source=_source(ressources,issuer);texte(url)
    try:
        p=urlsplit(urljoin(base or source['url'],url))
        origine=urlsplit(source['url'])
        if (p.scheme!='https' or p.hostname!=origine.hostname or p.username or p.password
                or p.port not in (None,443)):raise ErreurService('URL_HORS_ORIGINE_OFFICIELLE')
        return urlunsplit(('https',p.hostname,p.path or '/',p.query,''))
    except ValueError:raise ErreurService('URL_HORS_ORIGINE_OFFICIELLE') from None


def _nom(element):return element.tag.rsplit('}',1)[-1] if type(element.tag) is str else ''


def _champ(element,noms):
    for nom in noms:
        trouve=next((e for e in element if _nom(e)==nom),None)
        if trouve is not None:
            return (ElementTree.tostring(trouve,encoding='unicode') if len(trouve)
                    else (trouve.text or '')).strip()
    return ''


def _publication(valeur):
    if not valeur:return None
    try:
        try:d=datetime.fromisoformat(valeur.replace('Z','+00:00'))
        except ValueError:d=parsedate_to_datetime(valeur)
        if d.tzinfo is None:return None
        return utc(d.astimezone(timezone.utc).isoformat())
    except (ValueError,TypeError,OverflowError):return None


def _lien(item):
    liens=[e for e in item if _nom(e)=='link']
    for e in liens:
        if e.get('rel','alternate')=='alternate':
            return e.get('href') or ''.join(e.itertext()).strip()
    return ''


def _document(r,issuer,item,recu,connus):
    url=canoniser_url(r,issuer,_lien(item))
    titre=nettoyer_html(_champ(item,('title',)))
    contenu=nettoyer_html(_champ(item,('content','encoded','description','summary')))
    if not contenu:raise ErreurService('TEXTE_ABSENT')
    if len((titre+contenu).encode('utf-8'))>r.p['max_document_plaintext_bytes']:
        raise ErreurService('DOCUMENT_TROP_LONG')
    publication=_publication(_champ(item,('pubDate','published','date')))
    couverture='UNDATED' if publication is None else 'FUTURE' if publication>recu else 'COMPLETE'
    identifiant=empreinte(dict(issuer=issuer,url=url,texte=contenu))
    d=DocumentIA(identifiant,url,issuer,titre,contenu,publication,recu,recu,couverture)
    copies=[a for a in connus if a.issuer==issuer and a.hash_texte==d.hash_texte]
    if copies:
        ancien=min(copies,key=lambda a:(a.premiere_vue_ms,a.collecte_ms,a.item_id))
        return replace(ancien,collecte_ms=recu)
    precedents=[a for a in connus if a.issuer==issuer and a.url==url]
    if precedents:
        premier=min(precedents,key=lambda a:(a.premiere_vue_ms,a.collecte_ms,a.item_id))
        d=replace(d,publie_ms=premier.publie_ms,premiere_vue_ms=premier.premiere_vue_ms,
                  couverture=premier.couverture)
    return d


def normaliser_flux(ressources,issuer,xml,recu_ms,connus=()):
    r=ressources;_source(r,issuer);instant(recu_ms)
    if type(xml) is not bytes or len(xml)>r.p['rss_max_download_bytes']:
        raise ErreurService('FLUX_OCTETS_BORNES_REQUIS')
    if not isinstance(connus,(tuple,list)) or any(not isinstance(d,DocumentIA) for d in connus):
        raise ErreurService('HISTORIQUE_DOCUMENTS_REQUIS')
    if any(d.collecte_ms>recu_ms for d in connus):raise ErreurService('HISTORIQUE_NON_CAUSAL')
    try:
        brut=xml.decode('utf-8')
        if '<!DOCTYPE' in brut.upper() or '<!ENTITY' in brut.upper():
            raise ErreurService('DTD_OU_ENTITE_INTERDITE')
        racine=ElementTree.fromstring(brut)
    except (UnicodeError,ElementTree.ParseError,RecursionError):
        raise ErreurService('XML_UTF8_INVALIDE') from None
    if (_nom(racine) not in ('rss','feed','RDF') or _nom(racine)=='rss'
            and not any(_nom(e)=='channel' for e in racine)):
        raise ErreurService('FORMAT_RSS_INCONNU')
    resultat=[];anomalies=[];histoire=list(connus)
    try:
        for item in racine.iter():
            if _nom(item) not in ('item','entry'):continue
            try:
                d=_document(r,issuer,item,recu_ms,histoire)
                if d.item_id not in {a.item_id for a in resultat}:resultat.append(d)
                histoire.append(d)
                if d.couverture!='COMPLETE':anomalies.append('DATE_NON_QUALIFIEE')
            except (ErreurService,UnicodeError):anomalies.append('ITEM_NON_QUALIFIE')
    except RecursionError:raise ErreurService('XML_TROP_PROFOND') from None
    return FluxNormalise(tuple(resultat),'PARTIAL' if anomalies else 'COMPLETE',tuple(anomalies))

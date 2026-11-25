"""Implémentation de la couche 0 (types). Révisable sous harnais complet."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol
from urllib.parse import urlsplit
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c0a_temps import instant_vers_iso
from xpbots.contexte_ia.c0_types import (canonique as _canonique,
    decoder_objet, empreinte as _empreinte, utc as _utc, instant as _instant)

TABLES_IA = ('source_items','llm_jobs','llm_results','policy_events',
    'context_snapshots','api_budget','candidate_decisions','experiment_metrics',
    'api_attempts','provider_state','feed_state','schedule_state','advisories',
    'research_hypotheses','golden_cases','alerts')
_STATUT_HTTP_MINIMUM = 100  # Première classe du protocole HTTP, hors paramètre métier.


class ErreurService(ValueError):
    """Donnée, état ou contrat externe du service refusé, sans secret."""


def entier(v, minimum=0):
    if type(v) is not int or v<minimum:raise ErreurService('ENTIER_INVALIDE')
    return v


def instant(v):
    try:return _instant(v)
    except ValueError:raise ErreurService('INSTANT_INVALIDE') from None


def texte(v, vide=False):
    if type(v) is not str or (not vide and not v.strip()):raise ErreurService('TEXTE_INVALIDE')
    try:v.encode('utf-8')
    except UnicodeError:raise ErreurService('TEXTE_UTF8_INVALIDE') from None
    return v


def montant(v):
    if type(v) is bool:raise ErreurService('MONTANT_INVALIDE')
    try:d=Decimal(str(v))
    except (ValueError,InvalidOperation):raise ErreurService('MONTANT_INVALIDE') from None
    if not d.is_finite() or d<0:raise ErreurService('MONTANT_INVALIDE')
    return d


def canonique(v):
    try:return _canonique(v)
    except ValueError:raise ErreurService('JSON_NON_REPRESENTABLE') from None


def decoder(v):
    try:return decoder_objet(v)
    except ValueError:raise ErreurService('JSON_STRICT_REQUIS') from None


def empreinte(v):
    try:return _empreinte(v)
    except ValueError:raise ErreurService('JSON_NON_REPRESENTABLE') from None


def utc(v):
    try:return _utc(v)
    except ValueError:raise ErreurService('DATE_UTC_INVALIDE') from None


def iso(v):return instant_vers_iso(instant(v))


def url_https(v):
    texte(v)
    try:p=urlsplit(v)
    except ValueError:raise ErreurService('URL_INVALIDE') from None
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.fragment:
        raise ErreurService('URL_HTTPS_PUBLIQUE_REQUISE')
    return v


@dataclass(frozen=True)
class RessourcesIA:
    configuration: ConfigurationFigee
    schema_extraction: bytes
    schema_notes: bytes
    prompts: bytes

    def __post_init__(self):
        if not isinstance(self.configuration,ConfigurationFigee):raise ErreurService('CONFIGURATION_CHARGEE_REQUISE')
        e,n,p=(decoder(v) for v in (self.schema_extraction,self.schema_notes,self.prompts))
        if (e.get('additionalProperties') is not False or n.get('additionalProperties') is not False
                or e.get('type')!='object' or n.get('type')!='object'
                or e.get('properties',{}).get('schema_version',{}).get('enum')!=['fx-text-extraction-v1']
                or n.get('properties',{}).get('schema_version',{}).get('enum')!=['fx-advisory-v1']
                or set(p)!={'extraction','briefing','journal'}):raise ErreurService('RESSOURCES_IA_INVALIDES')
        for v in p.values():texte(v)
        if self.p['local_inference_allowed'] is not False or self.p['synchronous_llm_on_entry_allowed'] is not False:
            raise ErreurService('MODE_IA_INTERDIT')
        if len({v['id'] for v in self.p['providers']})!=len(self.p['providers']):raise ErreurService('FOURNISSEUR_DUPLIQUE')
        for v in self.p['providers']:url_https(v['endpoint']);texte(v['model'])
        for v in self.p['feeds']:url_https(v['url'])

    @property
    def p(self):return self.configuration.ia.parametres

    @property
    def digest(self):return self.configuration.ia.empreinte_canonique

    def schema(self,kind):
        if kind not in ('EXTRACTION','GOLDEN','BRIEFING','JOURNAL','WEEKLY_REVIEW'):raise ErreurService('JOB_INCONNU')
        return decoder(self.schema_extraction if kind in ('EXTRACTION','GOLDEN') else self.schema_notes)

    def prompt(self,kind):
        if kind not in ('EXTRACTION','GOLDEN','BRIEFING','JOURNAL','WEEKLY_REVIEW'):raise ErreurService('JOB_INCONNU')
        return decoder(self.prompts)['extraction' if kind in ('EXTRACTION','GOLDEN') else 'briefing' if kind=='BRIEFING' else 'journal']

    def fournisseur(self,identifiant):
        for v in self.p['providers']:
            if v['id']==identifiant:return v
        raise ErreurService('FOURNISSEUR_HORS_ALLOWLIST')


@dataclass(frozen=True)
class DocumentIA:
    item_id: str
    url: str
    issuer: str
    titre: str
    texte: str
    publie_ms: int | None
    premiere_vue_ms: int
    collecte_ms: int
    couverture: str = 'COMPLETE'
    version_parseur: str = 'rss-v1'
    officiel: bool = True

    def __post_init__(self):
        texte(self.item_id);url_https(self.url);texte(self.issuer);texte(self.titre,True);texte(self.texte,True)
        instant(self.premiere_vue_ms);instant(self.collecte_ms)
        if self.publie_ms is not None:instant(self.publie_ms)
        if self.premiere_vue_ms>self.collecte_ms:raise ErreurService('COLLECTE_NON_CAUSALE')
        if self.couverture not in ('COMPLETE','PARTIAL','UNDATED','FUTURE','TRUNCATED'):raise ErreurService('COUVERTURE_INVALIDE')
        texte(self.version_parseur)
        if type(self.officiel) is not bool:raise ErreurService('ORIGINE_BOOLEENNE_REQUISE')

    @property
    def hash_texte(self):
        from hashlib import sha256
        return sha256(self.texte.encode('utf-8')).hexdigest()

    def item(self,provided_text,scheduled_high_impact_match=False):
        texte(provided_text,True)
        if provided_text and provided_text not in self.texte:raise ErreurService('EXTRAIT_HORS_DOCUMENT')
        if type(scheduled_high_impact_match) is not bool:raise ErreurService('APPARIEMENT_BOOLEEN_REQUIS')
        return dict(item_id=self.item_id,issuer=self.issuer,provided_text=provided_text,
            published_at_utc=iso(self.publie_ms) if self.publie_ms is not None else None,
            first_seen_utc=iso(self.premiere_vue_ms),trusted_official_origin=self.officiel,
            scheduled_high_impact_match=scheduled_high_impact_match)


def _entetes(v):
    try:ps=tuple(tuple(x) for x in v)
    except TypeError:raise ErreurService('ENTETES_INVALIDES') from None
    if any(len(x)!=2 for x in ps):raise ErreurService('ENTETES_INVALIDES')
    for k,val in ps:
        texte(k);texte(val,True)
        if any(c in k+val for c in '\r\n'):raise ErreurService('ENTETE_MULTILIGNE')
    if len({k.casefold() for k,_ in ps})!=len(ps):raise ErreurService('ENTETE_DUPLIQUE')
    return ps


@dataclass(frozen=True)
class RequeteHTTP:
    url: str
    methode: str
    entetes: tuple
    corps: bytes | None
    timeout_s: int | float
    max_octets: int
    fournisseur: str | None = None

    def __post_init__(self):
        url_https(self.url)
        if self.methode not in ('GET','POST'):raise ErreurService('METHODE_INTERDITE')
        object.__setattr__(self,'entetes',_entetes(self.entetes))
        if any(k.casefold() in ('authorization','x-goog-api-key','api-key','cookie') for k,_ in self.entetes):raise ErreurService('SECRET_HORS_TRANSPORT')
        if self.corps is not None and type(self.corps) is not bytes:raise ErreurService('CORPS_OCTETS_REQUIS')
        if type(self.timeout_s) not in (int,float) or not 0<float(self.timeout_s)<float('inf'):raise ErreurService('TIMEOUT_INVALIDE')
        entier(self.max_octets,1)
        if self.fournisseur is not None:texte(self.fournisseur)


@dataclass(frozen=True)
class ReponseHTTP:
    statut: int
    entetes: tuple
    corps: bytes
    recu_ms: int

    def __post_init__(self):
        entier(self.statut,_STATUT_HTTP_MINIMUM)
        if self.statut>599:raise ErreurService('STATUT_HTTP_INVALIDE')
        object.__setattr__(self,'entetes',_entetes(self.entetes))
        if type(self.corps) is not bytes:raise ErreurService('REPONSE_OCTETS_REQUISE')
        instant(self.recu_ms)

    def entete(self,nom):return next((v for k,v in self.entetes if k.casefold()==nom.casefold()),None)


@dataclass(frozen=True)
class JobIA:
    job_id: str
    kind: str
    item_id: str | None
    cree_ms: int
    utile_jusqua_ms: int
    dossier: bytes
    evidence_ids: tuple = ()
    fournisseur: str | None = None

    def __post_init__(self):
        texte(self.job_id)
        if self.kind not in ('EXTRACTION','GOLDEN','BRIEFING','JOURNAL','WEEKLY_REVIEW'):raise ErreurService('JOB_INCONNU')
        if self.item_id is not None:texte(self.item_id)
        if self.kind in ('EXTRACTION','GOLDEN') and self.item_id is None:raise ErreurService('ITEM_REQUIS')
        instant(self.cree_ms);instant(self.utile_jusqua_ms)
        if self.utile_jusqua_ms<=self.cree_ms:raise ErreurService('UTILITE_EXPIREE')
        decoder(self.dossier)
        object.__setattr__(self,'evidence_ids',tuple(self.evidence_ids))
        for i in self.evidence_ids:texte(i)
        if self.fournisseur is not None:texte(self.fournisseur)


@dataclass(frozen=True)
class ResultatIA:
    job_id: str
    fournisseur: str | None
    recu_ms: int
    valide: bytes | None = None
    erreur: str | None = None

    def __post_init__(self):
        texte(self.job_id);instant(self.recu_ms)
        if self.fournisseur is not None:texte(self.fournisseur)
        if self.valide is not None:decoder(self.valide)
        if self.erreur is not None:texte(self.erreur)
        if (self.valide is None)==(self.erreur is None):raise ErreurService('RESULTAT_AMBIGU')


class DepotIA(Protocol):
    def transaction(self,operation):
        """Exécuter operation(tables) exclusivement ; annuler sur exception."""
        ...


class HorlogeIA(Protocol):
    def maintenant_ms(self):...
    def attendre(self,secondes):...

"""Implémentation de la couche 2a (veto). Révisable sous harnais complet."""
from dataclasses import dataclass
from urllib.parse import urlsplit
from xpbots.service_ia.c0_types import (ErreurService, RessourcesIA, DocumentIA,
    empreinte, entier, instant, texte)
from xpbots.service_ia.c1b_validation import valider_extraction
from xpbots.contexte_ia.c0_types import RAISON_VETO, en_ms
from xpbots.fondamental.c0_types import devises_pour
from xpbots.fondamental.c1b_annonces import GardeAnnonces
from xpbots.noyau.c0a_temps import instant_vers_datetime


@dataclass(frozen=True)
class CorrespondanceCalendrier:
    id_evenement: int
    issuer: str
    genre: str

    def __post_init__(self):
        entier(self.id_evenement,1);texte(self.issuer);texte(self.genre)


@dataclass(frozen=True)
class TableAppariement:
    fournisseur: str
    version: str
    known_at_ms: int
    complete: bool
    correspondances: tuple

    def __post_init__(self):
        texte(self.fournisseur);texte(self.version);instant(self.known_at_ms)
        if type(self.complete) is not bool or not isinstance(self.correspondances,(tuple,list)):
            raise ErreurService('TABLE_APPARIEMENT_INVALIDE')
        cs=tuple(self.correspondances)
        if any(not isinstance(c,CorrespondanceCalendrier) for c in cs):raise ErreurService('CORRESPONDANCES_REQUISES')
        if len({c.id_evenement for c in cs})!=len(cs):raise ErreurService('ID_MAPPING_DUPLIQUE')
        object.__setattr__(self,'correspondances',tuple(sorted(cs,key=lambda c:c.id_evenement)))

    @property
    def empreinte(self):
        return empreinte(dict(fournisseur=self.fournisseur,version=self.version,
            known_at_ms=self.known_at_ms,complete=self.complete,
            correspondances=[dict(id_evenement=c.id_evenement,issuer=c.issuer,genre=c.genre) for c in self.correspondances]))


@dataclass(frozen=True)
class AppariementCalendrier:
    valide: bool
    correspondance: bool
    raison: str | None = None
    version_calendrier: int | None = None
    version_mapping: str | None = None
    empreinte_calendrier: str | None = None
    empreinte_mapping: str | None = None

    def __post_init__(self):
        if type(self.valide) is not bool or type(self.correspondance) is not bool:
            raise ErreurService('APPARIEMENT_BOOLEEN_REQUIS')
        if self.valide:
            if self.raison is not None:raise ErreurService('APPARIEMENT_AMBIGU')
            entier(self.version_calendrier,1);texte(self.version_mapping)
            for h in (self.empreinte_calendrier,self.empreinte_mapping):
                if type(h) is not str or len(h)!=len(empreinte({})) or any(c not in '0123456789abcdef' for c in h):
                    raise ErreurService('PREUVE_APPARIEMENT_REQUISE')
        else:
            texte(self.raison)
            if self.correspondance:raise ErreurService('APPARIEMENT_INVALIDE_AVEC_MATCH')


def apparier_calendrier(r,garde,table,document,recu_ms,*,source_valide):
    instant(recu_ms)
    if not isinstance(r,RessourcesIA) or not isinstance(garde,GardeAnnonces) or not isinstance(document,DocumentIA):
        raise ErreurService('TYPES_REELS_REQUIS')
    if type(source_valide) is not bool:raise ErreurService('ETAT_SOURCE_BOOLEEN_REQUIS')
    def non(raison):return AppariementCalendrier(False,False,raison)
    if not source_valide:return non('CALENDRIER_INDISPONIBLE')
    if not isinstance(table,TableAppariement) or not table.complete:return non('MAPPING_INCOMPLET')
    if table.known_at_ms>recu_ms:return non('MAPPING_FUTUR')
    v=garde.version_connue(recu_ms)
    if v is None:return non('CALENDRIER_INDISPONIBLE')
    if table.fournisseur!=v.table.fournisseur:return non('FOURNISSEUR_MAPPING_DIFFERENT')
    commun=r.configuration.technique.commun
    age=en_ms(commun.news_calendar_max_age_seconds)
    if recu_ms-v.export_ms>age or recu_ms-v.reception_ms>age:return non('CALENDRIER_PERIME')
    if (v.couverture.debut_ms>recu_ms
            or v.couverture.fin_ms<recu_ms+en_ms(commun.news_forward_coverage_seconds)):
        return non('COUVERTURE_INSUFFISANTE')
    if document.publie_ms is None:return non('PUBLICATION_NON_DATEE')
    marge=en_ms(r.p['calendar_same_issuer_match_seconds'])
    if v.couverture.debut_ms>document.publie_ms-marge or v.couverture.fin_ms<=document.publie_ms+marge:
        return non('RECHERCHE_NON_COUVERTE')
    devises={f['issuer']:f['currency'] for f in r.p['feeds']}
    suivies={d for s in commun.universe_priority for d in devises_pour(s)}
    index={c.id_evenement:c for c in table.correspondances}
    genre=r.p['calendar_matching_event_kind']
    if any(c.issuer not in {*devises,'OTHER'} or c.genre not in (genre,'OTHER') for c in index.values()):
        return non('MAPPING_HORS_CONTRAT')
    match=False
    for a in v.annonces:
        # La garde native ne conserve que les événements d'importance haute qualifiée.
        c=index.get(a.id_evenement)
        if c is None:return non('ID_HIGH_NON_MAPPE')
        if c.issuer in devises and devises[c.issuer]!=a.devise:return non('DEVISE_MAPPING_INCOMPATIBLE')
        if c.issuer=='OTHER' and c.genre==genre and a.devise in suivies:return non('ISSUER_MONETAIRE_INCONNU')
        if (c.issuer==document.issuer and c.genre==genre
                and a.importance in v.table.hautes and abs(a.instant_ms-document.publie_ms)<=marge):
            match=True
    return AppariementCalendrier(True,match,version_calendrier=v.version,
        version_mapping=table.version,empreinte_calendrier=v.empreinte,empreinte_mapping=table.empreinte)


def construire_veto(r,sortie,document,provided_text,recu_ms,fournisseur,appariement):
    instant(recu_ms)
    if not isinstance(r,RessourcesIA) or not isinstance(document,DocumentIA) or not isinstance(appariement,AppariementCalendrier):
        raise ErreurService('TYPES_REELS_REQUIS')
    r.fournisseur(fournisseur)
    feed=next((f for f in r.p['feeds'] if f['issuer']==document.issuer),None)
    if feed is None:raise ErreurService('ISSUER_HORS_ALLOWLIST')
    item=document.item(provided_text,appariement.correspondance)
    valide=valider_extraction(r,sortie,item)
    if document.couverture!='COMPLETE' or document.publie_ms is None:return None
    if not document.publie_ms<=document.premiere_vue_ms<=document.collecte_ms<=recu_ms:
        raise ErreurService('DOCUMENT_NON_CAUSAL')
    if (not document.officiel or urlsplit(document.url).hostname!=urlsplit(feed['url']).hostname
            or not appariement.valide or appariement.correspondance):return None
    if not (valide['event_class']=='MONETARY_DECISION'
            and valide['temporal_status']=='ANNOUNCED_NOW' and valide['policy_actor']==document.issuer
            and valide['stance'] in ('TIGHTENING','EASING','UNCHANGED')
            and len(valide['evidence_quote'])>=r.p['evidence_quote_min_characters_for_veto']):return None
    fin=document.publie_ms+en_ms(r.p['unscheduled_policy_veto_seconds_from_publication'])
    if recu_ms>=fin:return None
    symboles=[s for s in r.configuration.technique.commun.universe_priority if feed['currency'] in devises_pour(s)]
    return dict(event_id=empreinte(dict(item_id=document.item_id,first_seen=item['first_seen_utc'])),
        reason_code=RAISON_VETO,canonical_symbols=symboles,
        valid_from_utc=instant_vers_datetime(recu_ms).isoformat(),
        valid_until_utc=instant_vers_datetime(fin).isoformat(),item_id=document.item_id,provider_id=fournisseur)

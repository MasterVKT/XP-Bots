"""Service pur réel ; seules les sources réseau, le temps et le dépôt sont externes."""
from dataclasses import dataclass
from xpbots.service_ia.c0_types import canonique, decoder, ReponseHTTP, iso
from xpbots.service_ia.c2b_routeur import RouteurIA
from xpbots.service_ia.c2c_collecteur import CollecteurRSS
from xpbots.service_ia.c3_planificateur import CasDerive, PlanificateurIA
from .support import ressources, document, extraction, Memoire, Horloge
from .support_budget import profil
from .support_http import enveloppe
from .support_rss import rss, item
from .support_calendrier import garde, mapping


class HTTPPlan:
    def __init__(self,r,h):
        self.r=r;self.h=h;self.d=document(t=h.t);self.requetes=[]
        self.hypotheses=[];self.changer=set();self.citations_seules=False;self.modele=None
        self.extraire=None;self.nouvelles=True
    def __call__(self,q):
        self.requetes.append(q)
        if q.methode=='GET':
            corps=rss(item(texte=self.d.texte,publication=iso(self.d.publie_ms))) if self.nouvelles and q.url==self.r.p['feeds'][0]['url'] else rss()
            return ReponseHTTP(200,(),corps,self.h.t)
        d=dossier_requete(self.r,q)
        if 'kind' in d:
            ids=[v['item_id'] for v in d['documents']+d.get('metrics',[])]
            v=dict(schema_version='fx-advisory-v1',kind=d['kind'],
                observations=[dict(text='A synthetic sourced observation.',evidence_ids=ids[:1])] if ids else [],
                uncertainties=[],hypotheses=[] if d['kind']=='BRIEFING' else self.hypotheses)
        else:
            v=extraction(self.d,item_id=d['item_id'],policy_actor=d['issuer'],evidence_quote=d['provided_text'][:52])
            if d['item_id'] in self.changer:v['stance']='EASING'
            if self.citations_seules:v['evidence_quote']=d['provided_text'][-30:]
        if self.extraire is not None:v=self.extraire(q,d,v)
        brut=enveloppe(q.fournisseur,canonique(v).decode())
        if self.modele is not None:
            brut['modelVersion' if q.fournisseur==self.r.p['providers'][1]['id'] else 'model']=self.modele
        return ReponseHTTP(200,(),canonique(brut),self.h.t)


def dossier_requete(r,q):
    v=decoder(q.corps)
    if q.fournisseur==r.p['providers'][0]['id']:s=v['messages'][-1]['content']
    elif q.fournisseur==r.p['providers'][1]['id']:s=v['contents'][0]['parts'][0]['text']
    else:s=v['input'][-1]['content']
    return decoder(s.encode())


class CalendrierPlan:
    def __init__(self,r,d):self.g=garde(r,d);self.table=mapping(d);self.disponible=True
    def __call__(self,t):return self.g,self.table,self.disponible


def cas_fixes(r=None):
    r=r or ressources();d=document();cases=[]
    for n in range(r.p['weekly_golden_cases']):
        ident='case-'+str(n)
        dossier=canonique(dict(item_id=ident,title=d.titre,issuer=d.issuer,provided_text=d.texte))
        cases.append(CasDerive(ident,dossier,canonique(extraction(d,item_id=ident))))
    return tuple(cases)


@dataclass
class EnvironnementPlan:
    r: object
    m: object
    h: object
    http: object
    rt: object
    c: object
    cal: object
    p: object


def composer(t=None,*,cas=(),routes=None):
    r=ressources();h=Horloge(document().collecte_ms if t is None else t);m=Memoire();http=HTTPPlan(r,h)
    rt=RouteurIA(r,m,http,h,[profil(r,h.t)]);c=CollecteurRSS(r,m,http,h);cal=CalendrierPlan(r,http.d)
    p=PlanificateurIA(r,m,rt,c,h,cal,cas_derives=cas,
        routes_auditees=(r.p['providers'][0]['id'],) if routes is None else routes)
    return EnvironnementPlan(r,m,h,http,rt,c,cal,p)


def metrique(e,ident='metric-1',**kw):
    from xpbots.noyau.c0a_temps import instant_vers_datetime
    v=dict(item_id=ident,period=instant_vers_datetime(e.h.t).astimezone(e.p.zone).date().isoformat(),
        strategy=e.r.configuration.technique.commun.simultaneous_strategy_priority[0],
        symbol=e.r.configuration.technique.commun.universe_priority[0],arm='REFERENCE',net_pnl='-1.25',
        trade_count=1,equity_drawdown='0.02',ai_cost_usd='0',known_at_ms=e.h.t,
        dimensions=dict(range_width_atr_h1='1.25',new_signal_after_veto=False),
        refusals=dict(AI_CONTEXT_VETO=1),data_gaps=0)
    v.update(kw);return v

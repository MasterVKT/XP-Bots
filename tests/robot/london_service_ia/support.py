"""Fixtures externes synthétiques ; aucun secret ni réseau."""
from copy import deepcopy
from pathlib import Path
from xpbots.noyau.c0c_configuration import charger_configuration_figee
from xpbots.service_ia.c0_types import (RessourcesIA, DocumentIA, TABLES_IA,
    canonique, ReponseHTTP, JobIA)

ROOT=Path(__file__).resolve().parents[3]

def ressources():
    c=charger_configuration_figee((ROOT/'config/parametres_figes_v3.json').read_bytes(),
        (ROOT/'config/parametres_IA_integration_v1.json').read_bytes(),
        (ROOT/'docs/validation/conservation_ressources.json').read_bytes())
    return RessourcesIA(c,(ROOT/'schemas/schema_extraction_LLM_v1.json').read_bytes(),
        (ROOT/'schemas/schema_notes_IA_v1.json').read_bytes(),(ROOT/'prompts/prompts_IA_v1.json').read_bytes())

class Memoire:
    def __init__(self):self.tables={k:{} for k in TABLES_IA}
    def transaction(self,op):
        t=deepcopy(self.tables);r=op(t);self.tables=t;return deepcopy(r)

class Horloge:
    def __init__(self,t=1794900000000):self.t=t;self.attentes=[]
    def maintenant_ms(self):return self.t
    def attendre(self,s):self.attentes.append(s);self.t+=round(s*1000)

def document(t=1794900000000,issuer='FED',**kw):
    r=ressources();url=next(f['url'] for f in r.p['feeds'] if f['issuer']==issuer)
    v=dict(item_id='article-synthetique',url=url,issuer=issuer,titre='Synthetic release',
        texte='The committee decided today to raise its policy rate. This is a fabricated test.',
        publie_ms=t-1000,premiere_vue_ms=t,collecte_ms=t)
    v.update(kw);return DocumentIA(**v)

def extraction(d=None,**kw):
    d=d or document()
    v=dict(schema_version='fx-text-extraction-v1',item_id=d.item_id,event_class='MONETARY_DECISION',
        temporal_status='ANNOUNCED_NOW',policy_actor=d.issuer,stance='TIGHTENING',evidence_quote=d.texte[:52])
    v.update(kw);return v

def job(d=None,**kw):
    d=d or document()
    v=dict(job_id='job-synthetique',kind='EXTRACTION',item_id=d.item_id,cree_ms=d.collecte_ms,
        utile_jusqua_ms=d.publie_ms+ressources().p['unscheduled_policy_veto_seconds_from_publication']*1000,
        dossier=canonique(dict(item_id=d.item_id,title=d.titre,issuer=d.issuer,provided_text=d.texte)))
    v.update(kw);return JobIA(**v)

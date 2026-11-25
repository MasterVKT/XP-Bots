"""Ouvreur urllib synthétique composant les vraies requêtes A08 et le vrai RSS."""
from pathlib import Path
from xpbots.service_ia.c0_types import canonique, decoder, iso
from xpbots.service_ia.c4_service import ServiceIA
from robot.outils.fondamental import calendrier, octets, ConversionServeurScenario, table_importance
from .support import ressources, document, extraction, Horloge
from .support_budget import profil
from .support_rss import rss, item
from .support_http import enveloppe
from .support_calendrier import mapping
from .support_ouvreur import ReponseOuvree


class OuvreurService:
    def __init__(self,r,h,d=None):self.r=r;self.h=h;self.d=d or document(t=h.t);self.requetes=[];self.bloquer=None;self.usage=True
    def open(self,req,timeout):
        self.requetes.append(req)
        if req.get_method()=='GET':
            b=rss(item(texte=self.d.texte,publication=iso(self.d.publie_ms))) if req.full_url==self.r.p['feeds'][0]['url'] else rss()
        else:
            if self.bloquer:self.bloquer()
            p=next(p for p in self.r.p['providers'] if p['endpoint']==req.full_url);v=decoder(req.data)
            if p['id']==self.r.p['providers'][0]['id']:d=decoder(v['messages'][-1]['content'].encode())
            elif p['id']==self.r.p['providers'][1]['id']:d=decoder(v['contents'][0]['parts'][0]['text'].encode())
            else:d=decoder(v['input'][-1]['content'].encode())
            if 'kind' in d:out=dict(schema_version='fx-advisory-v1',kind=d['kind'],observations=[],uncertainties=[],hypotheses=[])
            else:out=extraction(self.d,item_id=d['item_id'],policy_actor=d['issuer'],evidence_quote=d['provided_text'][:52])
            b=canonique(enveloppe(p['id'],canonique(out).decode(),usage=self.usage))
        return ReponseOuvree(req.full_url,b)


def composer(tmp,*,t=None,h=None,d=None,ouvreur=None):
    r=ressources();h=h or Horloge(document().collecte_ms if t is None else t);d=d or document(t=h.t)
    p=Path(tmp);cal=p/'calendrier.json';cal.write_bytes(octets(calendrier(export_ms=h.t)))
    o=ouvreur or OuvreurService(r,h,d);pid=r.p['providers'][0]['id']
    s=ServiceIA(r,p/'ia.db',p/'context.json',horloge=h,ouvreur=o,cles={pid:'CLE_SYNTHETIQUE_SEULEMENT'},
        profils=[profil(r,h.t)],calendrier=dict(chemin=cal,convertir_serveur=ConversionServeurScenario(),
            table_importance=table_importance(),table_appariement=mapping(d),max_octets=r.p['rss_max_download_bytes']))
    return s,o,h,p

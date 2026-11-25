"""RSS public synthétique et transport externe contrôlé, sans inférence."""
from xpbots.service_ia.c0_types import ReponseHTTP
from xpbots.service_ia.c2c_collecteur import CollecteurRSS
from .support import ressources, document, Memoire, Horloge
from .support_rss import rss, item


class HTTPSynthese:
    def __init__(self,h,actions=()):self.h=h;self.actions=list(actions);self.requetes=[]
    def __call__(self,q):
        self.requetes.append(q)
        if self.actions:return self.actions.pop(0)(q,self)
        return self.reponse(q)
    def reponse(self,q,statut=200,corps=None,entetes=()):
        return ReponseHTTP(statut,entetes,rss(item()) if corps is None else corps,self.h.t)


def composer(*,actions=(),selectionner=None):
    r=ressources();m=Memoire();h=Horloge(document().collecte_ms);http=HTTPSynthese(h,actions)
    return r,m,h,http,CollecteurRSS(r,m,http,h,selectionner=selectionner)


def avancer(r,h):h.t+=r.p['rss_poll_seconds']*1000

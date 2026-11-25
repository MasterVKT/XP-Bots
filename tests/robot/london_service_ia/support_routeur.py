"""Transport et horloge externes synthétiques ; composants internes réels."""
from xpbots.service_ia.c0_types import ReponseHTTP, canonique
from xpbots.service_ia.c1d_budget import RegistreBudget
from xpbots.service_ia.c2b_routeur import RouteurIA
from .support import ressources, document, Memoire, Horloge
from .support_budget import profil
from .support_http import enveloppe


class HTTPScenario:
    def __init__(self,m,h,actions=()):self.m=m;self.h=h;self.actions=list(actions);self.requetes=[]
    def __call__(self,q):
        self.requetes.append(q)
        if not any(a['provider']==q.fournisseur and a['sent_ms']==self.h.t for a in self.m.tables['api_attempts'].values()):
            raise AssertionError('Le transport précède le COMMIT de réservation')
        if self.actions:return self.actions.pop(0)(q,self)
        return self.reponse(q)
    def reponse(self,q,*,sortie=None,usage=True,statut=200,entetes=(),corps=None):
        return ReponseHTTP(statut,entetes,canonique(enveloppe(q.fournisseur,sortie,usage)) if corps is None else corps,self.h.t)


def composer(*,payant=False,profils=None,actions=()):
    r=ressources();m=Memoire();h=Horloge(document().collecte_ms)
    ps=[]
    for f in r.p['providers']:
        p=profil(r,h.t,payant='input_usd_per_million_upper_bound' in f,
            fournisseur=f['id'],modele=f['model'],profil_facturation=f['billing_profile'])
        ps.append(p)
    http=HTTPScenario(m,h,actions)
    if payant:RegistreBudget(r,m).provisionner(str(document().item('')['first_seen_utc'])[:7],'0','0')
    routeur=RouteurIA(r,m,http,h,ps if profils is None else profils,paiement_autorise=payant)
    return r,m,h,http,routeur


def timeout(q,http):
    http.h.attendre(q.timeout_s)
    raise TimeoutError('Ce texte arbitraire ne doit jamais être archivé')

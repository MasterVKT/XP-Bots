"""Frontière exacte urllib, octets et headers synthétiques, jamais de socket."""
from email.message import Message


class ReponseOuvree:
    def __init__(self,url,corps=b'',statut=200,entetes=()):
        self.url=url;self.corps=corps;self.statut=statut;self.headers=Message();self.fermee=False;self.plafonds=[]
        for k,v in entetes:self.headers[k]=v
    def geturl(self):return self.url
    def getcode(self):return self.statut
    def read(self,n):self.plafonds.append(n);return self.corps[:n]
    def close(self):self.fermee=True


class OuvreurScenario:
    def __init__(self,action=None):self.action=action;self.requetes=[];self.reponses=[]
    def open(self,requete,timeout):
        self.requetes.append((requete,timeout))
        r=self.action(requete,timeout) if self.action else ReponseOuvree(requete.full_url)
        self.reponses.append(r);return r

"""Horloge et publication physiques, réutilisant l'infrastructure gelée."""
from datetime import timedelta
from pathlib import Path
from xpbots.infra.c0b_horloge import HorlogeSysteme
from xpbots.infra.c0d_journal import ecrire_atomique
from xpbots.service_ia.c0_types import ErreurService, RessourcesIA, decoder


class HorlogeService:
    def __init__(self,horloge_systeme=None):self._h=horloge_systeme or HorlogeSysteme()
    def maintenant_ms(self):return self._h.utc_ms()
    def attendre(self,secondes):
        if type(secondes) not in (int,float) or not 0<=secondes<float('inf'):raise ErreurService('ATTENTE_INVALIDE')
        self._h.attendre_ms(timedelta(seconds=secondes)//timedelta(milliseconds=1))


class PublieurSnapshot:
    def __init__(self,ressources,chemin,horloge):
        if not isinstance(ressources,RessourcesIA):raise ErreurService('RESSOURCES_REQUISES')
        self.r=ressources;self.chemin=Path(chemin);self.horloge=horloge
    def __call__(self,b):
        decoder(b)
        if len(b)>self.r.p['snapshot_max_bytes']:raise ErreurService('SNAPSHOT_TROP_GRAND')
        pauses=iter(self.r.p['snapshot_write_retry_seconds'])
        while True:
            try:ecrire_atomique(self.chemin,b);return
            except OSError:
                pause=next(pauses,None)
                if pause is None:raise OSError('PUBLICATION_ATOMIQUE_ECHOUEE') from None
                self.horloge.attendre(pause)

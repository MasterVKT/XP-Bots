"""Composition réelle 0–6 ; les seuls calculs natifs et permissions sont synthétiques."""
from dataclasses import replace
from decimal import Decimal as D
from types import SimpleNamespace
from robot.outils.execution_partagee import T, configuration, profil, signal, cotation
from robot.doublures.calculs_execution import CalculSynthetique
from xpbots.execution.c0a_types import EtatCompte, PositionCompte
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.execution.c1b_gardes import reconstituer_base_utc
from xpbots.execution.c4_cycle import PreuvePersistance
from xpbots.execution.c5b_reprise import ObservationNative
from xpbots.execution.c6_coordinateur import CoordinateurCompte
from xpbots.noyau.c1b_instrument import Intervalle, ProfilCompte, HorairesCotation


class CalculMultiSynthetique(CalculSynthetique):
    def __init__(self,compte,profils):
        super().__init__(compte,next(iter(profils.values())))
        self.profils=profils

    def specifications(self,symbole):
        self.appels.append(('specifications',symbole))
        return self.profils[symbole]


def bloc_coordinateur(*,t=T,fondamental=...,contexte=None,profil_compte=None,mode='REJEU',etat=None,
                     observation=...,technique=None,exclusivites=()):
    conf=technique or configuration(); p=conf.commun
    h=HorairesCotation((Intervalle(t-86400000,t+86400000),),(),t-86400000,t+172800000)
    profils={s:profil(symbole=s,symbole_courtier=s+'synth',sous_jacent=s,horaires=h,releve_ms=t)
             for s in p.universe_priority}
    compte=EtatCompte(t,D(100),D(100),D(0))
    port=CalculMultiSynthetique(compte,profils)
    minuit=t//86400000*86400000
    base=reconstituer_base_utc(compte,(),Intervalle(minuit,t+1),aucune_position_minuit=True)
    pc=profil_compte or ProfilCompte('synthetique','synthetique','SYNTHETIQUE','STANDARD',p.account_currency,
        p.account_leverage,'HEDGING','PERCENT',D(0),D(0),t)
    f=ControleTechniqueNeutre() if fondamental is ... else fondamental
    o=ObservationNative(compte,minuit,True,exclusivites=exclusivites) if observation is ... else observation
    c=CoordinateurCompte(conf,'synthetique',profils,pc,port,f,t,longueur_empreinte=16,
        contexte=contexte,mode=mode,etat=etat,observation=o,base_utc=base)
    return SimpleNamespace(coordinateur=c,port=port,profils=profils,profil_compte=pc,compte=compte,
                           technique=conf,fondamental=f,base=base)


def traiter(b,t=T,**kwargs):
    b.port.compte=replace(b.port.compte,instant_ms=t)
    return b.coordinateur.traiter(t,**kwargs)


def confirmer(b,lot,t=T):
    b.port.compte=replace(b.port.compte,instant_ms=t)
    return b.coordinateur.confirmer_persistance(PreuvePersistance(lot.etat.revision,
        tuple(c.reference for c in lot.preparations)),t)


def bloc_remplissage(b,lot):
    v=lot.etat.reprise.cycles[0]
    return SimpleNamespace(signal=v.signal,plan=v.plan,profil=v.profil)


def positionner(b,v,t,volume=None):
    volume=v.plan.volume if volume is None else volume
    pos=PositionCompte('position-1',v.signal.symbole,v.profil.sous_jacent,volume,v.plan.risque,v.plan.reservation.cle)
    b.port.compte=replace(b.port.compte,instant_ms=t,positions=(pos,),marge_utilisee=volume)

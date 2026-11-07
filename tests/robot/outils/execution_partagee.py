"""Profils, signaux et instantanés synthétiques pour les calculs C06/C07 ; aucune donnée réelle."""
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
from robot.outils.configuration import configuration_figee
from xpbots.noyau.c0a_temps import instant_depuis_iso
from xpbots.noyau.c1a_marche import Cotation
from xpbots.noyau.c1b_instrument import ProfilInstrument,HorairesCotation,Intervalle,construire_profil_instrument
from xpbots.noyau.c1c_domaine import SignalTechnique,Sens,CleIntention

def configuration(): return configuration_figee().technique
def commun(): return configuration().commun
T=instant_depuis_iso('2026-11-06T08:15:00.000Z')
def signal(sens=Sens.ACHAT,symbole='EURUSD',strategie='LONDON_V3',**changes):
    return replace(SignalTechnique(strategie,symbole,T,sens,1.1003,.0005,1.0998 if sens is Sens.ACHAT else 1.1008,2),**changes)
def cle(signal_=None):
    s=signal_ or signal(); return CleIntention('synthetique',s.strategie,s.symbole,s.cloture_ms,s.sens)
def cotation(**changes): return replace(Cotation('EURUSD',D('1.1003'),D('1.1004'),T,T),**changes)
def profil(**changes):
    p=ProfilInstrument('EURUSD','EURUSDsynth','EURUSD','EUR','USD','USD','FOREX',D(1000),D('.00001'),D('.00001'),5,D('.01'),D('.1'),D(1),D('.1'),D(0),0,0,'FULL','MARKET',frozenset({'IOC'}),True,True,D(0),D(0),True,'USD',D(0),D(0),D(0),D(0),HorairesCotation((Intervalle(T-86400000,T+86400000),),(),T-86400000,T+172800000),T)
    return replace(p,**changes)

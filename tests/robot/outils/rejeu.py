"""Fixtures synthétiques déclarées, couches métier réelles."""
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
import hashlib

from robot.outils.orchestration import C,T,composer_bras
from robot.outils.cycle_execution import bloc_cycle
from robot.outils.execution_partagee import signal
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1b_instrument import Intervalle,HorairesCotation
from xpbots.noyau.c1c_domaine import Sens
from xpbots.rejeu.c0a_types import ManifesteTicks,TarifCommission,ConditionContrat
from xpbots.rejeu.c0b_protocole import charger_protocole


def lot_csv(lignes=None,*,debut=T,fin=T+3600000,**options):
    lignes=tuple(lignes if lignes is not None else (
        'canonical_symbol,broker_symbol,time_utc_ms,sequence,bid,ask\n',
        f'EURUSD,EURUSD,{debut},0,1.1,1.1001\n'))
    horaires=HorairesCotation((Intervalle(debut,fin),),(),debut,fin+3600000)
    valeurs=dict(source='FABRIQUE_TEST',symboles={'EURUSD':'EURUSD'},intervalle=Intervalle(debut,fin),
        couverture=(Intervalle(debut,fin),),trous=(),sha256=hashlib.sha256(''.join(lignes).encode()).hexdigest(),
        date_recuperation=date(2026,11,10),extraction='SYNTHESE',precision_prix='DECIMALE_NATIVE',horaires={'EURUSD':horaires})
    valeurs.update(options)
    return lignes,ManifesteTicks(**valeurs)


def cas_simulateur(sens=Sens.ACHAT,scenario='REFERENCE',tarif=None,plans=None):
    from xpbots.rejeu.c1b_simulateur import SimulateurExecution
    b=bloc_cycle(signal_=signal(sens=sens))
    t=b.signal.cloture_ms;creation=t//86400000*86400000
    c=b.cycle.preparer_envoi(t).commandes[0]
    tarif=tarif or TarifCommission('ZERO_DECLARE',D(0),D(0),D(0),D(0))
    condition=ConditionContrat(creation,creation+86400000,creation,b.profil,tarif)
    s=charger_protocole(C).scenario(scenario) if isinstance(scenario,str) else scenario
    e=SimulateurExecution(C,(condition,),creation,s,plans)
    e.avancer_au(t)
    return b,e,c


def cotation_test(b,t,bid='1.1',ask='1.1001',numero=None):
    return Tick(b.signal.symbole,b.profil.symbole_courtier,t,t,t if numero is None else numero,float(bid),float(ask))


def experience_courte(*,jour=date(2023,1,2),mode='REJEU',scenario='REFERENCE',perte=False):
    from datetime import datetime,timedelta,timezone
    from xpbots.noyau.c0a_temps import instant_depuis_datetime
    from xpbots.rejeu.c0b_protocole import BlocC10
    from xpbots.rejeu.c2_executeur import SourceTicks,DemandeRejeu
    a=instant_depuis_datetime(datetime.combine(jour,datetime.min.time(),timezone.utc))
    session=a+8*3600000;s=session+900000;t0=a-900000
    dates=(t0,a,session,s,s+249,s+250,s+251,s+900000)
    valeurs=['1.1']*len(dates);valeurs[-2:]=['1.09' if perte else '1.102']*2
    lignes=['canonical_symbol,broker_symbol,time_utc_ms,sequence,bid,ask\n']
    lignes.extend(f'EURUSD,EURUSD,{t},{i},{p},{D(p)+D(".0001")}\n' for i,(t,p) in enumerate(zip(dates,valeurs)))
    lignes,m=lot_csv(lignes,debut=t0,fin=a+86400000)
    b,_,_,_=composer_bras()
    profil=replace(b.profils['EURUSD'],releve_ms=t0,horaires=m.horaires['EURUSD'])
    tarif=TarifCommission('ZERO_DECLARE',D(0),D(0),D(0),D(0))
    conditions=(ConditionContrat(t0,a+86400000,t0,profil,tarif),)
    compteur=[]
    def lire():compteur.append('LECTURE');return iter(lignes)
    d=DemandeRejeu('experience_fixture',BlocC10('VALIDATION_FIXTURE',jour,jour+timedelta(days=1),'VALIDATION'),scenario,mode,16)
    return d,SourceTicks(m,lire),conditions,s,compteur


def fabriques_horloge(clotures,identifiants=None):
    from xpbots.noyau.c1c_domaine import SignalTechnique,AbsenceDeSignal,Motif,NatureIssue
    from xpbots.orchestration.c0_contrats import FabriqueStrategie
    ids=identifiants or (C.technique.london['strategy_id'],)
    class Strategie:
        def __init__(self,identifiant):self.identifiant=identifiant;self.ouverte=False
        def sur_bougie(self,b):
            if b.unite.value!='M15':return None
            x=b.bougie
            if x.fin_ms in clotures and not self.ouverte:
                return SignalTechnique(self.identifiant,x.symbole,x.fin_ms,'ACHAT',x.cloture,.001,x.cloture-.0008,2)
            return AbsenceDeSignal(self.identifiant,x.symbole,x.fin_ms,Motif.NO_SETUP,'PAS_DE_CASSURE')
        def sur_issue(self,i):
            if i.nature is NatureIssue.REMPLIE:self.ouverte=True
            if i.nature is NatureIssue.CLOTUREE:self.ouverte=False
    def fabrique(identifiant):return FabriqueStrategie(identifiant,lambda c,t:Strategie(identifiant))
    return tuple(fabrique(i) for i in ids)


def experience_london(jour,*,mode='REJEU',scenario='REFERENCE'):
    from datetime import datetime,timedelta,timezone
    from xpbots.noyau.c0a_temps import instant_depuis_datetime
    from robot.outils.couture_execution import journee_executable
    from robot.outils.fabrique_ticks import lignes_csv
    from xpbots.rejeu.c0b_protocole import BlocC10
    from xpbots.rejeu.c2_executeur import SourceTicks,DemandeRejeu,AutorisationReserve
    _,fab=journee_executable(jour,C.technique)
    lignes=tuple(l+'\n' for l in lignes_csv(fab))
    debut=fab[0].instant_ms;dernier=fab[-1].instant_ms+1
    fin=max(dernier,instant_depuis_datetime(datetime.combine(jour+timedelta(days=1),datetime.min.time(),timezone.utc)))
    h=HorairesCotation((Intervalle(debut,dernier),),(),debut,fin+3600000)
    lignes,m=lot_csv(lignes,debut=debut,fin=fin,couverture=(Intervalle(debut,dernier),),
        trous=(Intervalle(dernier,fin),) if dernier<fin else (),horaires={'EURUSD':h})
    b,_,_,_=composer_bras()
    profil=replace(b.profils['EURUSD'],releve_ms=m.intervalle.debut_ms,horaires=m.horaires['EURUSD'])
    tarif=TarifCommission('ZERO_DECLARE',D(0),D(0),D(0),D(0))
    condition=ConditionContrat(m.intervalle.debut_ms,m.intervalle.fin_ms,m.intervalle.debut_ms,profil,tarif)
    compteur=[]
    def lire():compteur.append('LECTURE');return iter(lignes)
    d=DemandeRejeu('london_fixture',BlocC10('DIAGNOSTIC_FIXTURE',jour,jour+timedelta(days=1),'DIAGNOSTIC'),scenario,mode,16,
        AutorisationReserve(True,'a'*64,lambda _:True))
    return d,SourceTicks(m,lire),(condition,),compteur

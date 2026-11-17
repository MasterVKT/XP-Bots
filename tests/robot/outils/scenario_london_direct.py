"""Scène externe causale, sans signal ni remplissage substitué au moteur."""
from datetime import date,datetime,time,timezone
from robot.outils.orchestration import C
from robot.outils.faux_mt5 import FauxMT5
from robot.outils.qualification_mt5 import preuve_qualification,exports,iso,natif,octets,JOUR
from robot.outils.fondamental import message,calendrier
from robot.outils.couture_execution import journee_executable
from robot.outils.fabrique_ticks import TickFabrique,instant_ms
from robot.points_entree.test_cat1_c0_configuration import registre
from xpbots.infra.c0a_types import TableHeureServeur,SegmentServeur


class ScenarioLondonDirect:
    def __init__(self,h,mode='PAPER'):
        self.h=h;self.jour=instant_ms(datetime.combine(date(2026,11,9),time(),timezone.utc))
        self.debut=self.jour+8*3600000;h.temps=self.debut;h.monotone=0
        _,self.ticks=journee_executable(date(2026,11,9),C.technique)
        self.sdk=FauxMT5(h.commun,instant_ms=h.temps)
        self.q=preuve_qualification(self.sdk,t=h.temps)
        self.q.update(debut_horaires_ms=self.ticks[0].instant_ms//JOUR*JOUR,fin_horaires_ms=self.jour+3*JOUR)
        self.table=TableHeureServeur('SERVEUR_FIXTURE',1,iso(self.debut-1000),('S01_SYNTHETIQUE_REPETITION',),
            (SegmentServeur(self.ticks[0].instant_ms-JOUR,self.jour+30*JOUR,0),))
        self.registre=registre(mode)
        self.registre['historique']=dict(departs_ticks_utc_ms={'EURUSD':self.ticks[0].instant_ms},depuis_compte_utc_ms=self.jour)
        self.base=h.commun/'Files/XPBots'
        (self.base/'fondamental/v1').mkdir(parents=True);(self.base/'export/v1').mkdir(parents=True)
        self.jours=[dict(jour=j,cotation=[dict(debut='00:00:00',fin='24:00:00')],
            negociation=[dict(debut='00:00:00',fin='23:00:00')]) for j in range(7)]
        self.sequence=0;self.minute=None;self.heure=None;self.curseur=0
        tfill=self.debut+15*60000+250
        ouverture=next(x for x in self.ticks if x.instant_ms==tfill-250)
        self.ticks.append(TickFabrique('EURUSD','EURUSD',tfill,999999,ouverture.bid,ouverture.ask))
        self.ticks.sort(key=lambda x:x.instant_ms)
        self.publier();self.injecter()
        self.boucle=h.nouveau(sdk=self.sdk,document=self.registre,qualification=self.q,table=self.table)
        self.sorties=[];self.iterations=0

    def publier(self,risque='ALLOW',force=False):
        t=self.h.temps
        if force or self.minute!=t//60000:
            self.sequence+=1;self.minute=t//60000
            m=message(sequence=self.sequence,issued_at_utc=iso(t),known_at_utc=iso(t),valid_from_utc=iso(t),
                valid_until_utc=iso(t+int(C.technique.commun.fundamental_max_validity_seconds*1000)),risk_state=risque)
            (self.base/'fondamental/v1/permission_EURUSD.json').write_bytes(octets(m))
            horizon=int((C.technique.commun.news_forward_coverage_seconds+C.technique.commun.news_calendar_max_age_seconds+60)*1000)
            cal=calendrier(version=self.sequence,export_ms=t,export_serveur=natif(t),export_gmt=natif(t),
                fenetre_debut_serveur=natif(self.jour-JOUR),fenetre_fin_serveur=natif(t+horizon))
            (self.base/'export/v1/calendrier.json').write_bytes(octets(cal))
        if self.heure!=t//3600000:
            seances,fermetures=exports(t=t,version=self.sequence,jours=self.jours)
            (self.base/'export/v1/seances_EURUSD.micro.json').write_bytes(octets(seances))
            (self.base/'export/v1/fermetures_exceptionnelles.json').write_bytes(octets(fermetures))
            self.heure=t//3600000

    def injecter(self):
        while self.curseur<len(self.ticks) and self.ticks[self.curseur].instant_ms<=self.h.temps:
            x=self.ticks[self.curseur]
            self.sdk.ajouter_tick('EURUSD.micro',x.instant_ms,float(x.bid),float(x.ask));self.curseur+=1

    def iterer(self):
        sorties=self.boucle.iterer();self.sorties.extend(sorties);self.iterations+=1
        return sorties

    def suivant(self,fin):
        t=self.h.temps;candidats=[fin,(t//60000+1)*60000]
        if self.curseur<len(self.ticks):candidats.append(self.ticks[self.curseur].instant_ms)
        echeances=[self.boucle.moteur.prochaine_echeance_ms]
        echeances.extend(p.prochaine_echeance_ms for p in self.boucle.livres.values())
        candidats.extend(x for x in echeances if x is not None and x>t)
        cible=min(x for x in candidats if x>t)
        self.h.avancer(cible-t);self.injecter();self.publier()

    def jusqua(self,fin,avant=None):
        while self.h.temps<=fin:
            if avant is not None:avant(self)
            self.iterer()
            if self.h.temps>=fin:return
            self.suivant(fin)
            if self.iterations>5000:raise AssertionError('SCENE_SANS_PROGRESSION')

"""Couture phase 7 : vrais C05, coordinateur, journal et moteur London ; arrivées externes scénarisées."""
from dataclasses import replace
from datetime import date, time
from decimal import Decimal as D
import unittest

from robot.outils.configuration import configuration_figee
from robot.outils.fabrique_journees_london import journee_london_prechargee
from robot.outils.fabrique_ticks import lignes_csv, ticks_de_bougies, TickFabrique
from robot.outils.fondamental import (T, message, octets, calendrier, evenement, table_importance,
    ConversionServeurScenario)
from xpbots.app.rejeu_squelette import composer_rejeu_papier
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.execution.c4_cycle import NatureReponse
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.noyau.c0a_temps import instant_vers_iso
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1c_domaine import SignalTechnique, AbsenceDeSignal, Motif
from xpbots.rejeu.squelette import (ContratPapier, PaquetFondamental, SourceFondamentaleScenario,
    StockageMemoirePapier, analyser_lignes_ticks, rejouer)

C=configuration_figee();S=T+900000


def permission(t=S,sequence=1,**changements):
    p=message(sequence=sequence,issued_at_utc=instant_vers_iso(t),known_at_utc=instant_vers_iso(t),
        valid_from_utc=instant_vers_iso(t),valid_until_utc=instant_vers_iso(t+900000))
    p.update(changements)
    return PaquetFondamental(t,'PERMISSION',octets(p),'EURUSD')


def export(t=T,evenements=(),version=1):
    return PaquetFondamental(t,'CALENDRIER',octets(calendrier(version=version,export_ms=t,
        evenements=evenements)),table=table_importance())


class SignalUnique:
    identifiant=C.technique.london['strategy_id']
    def __init__(self):self.signale=False;self.issues=[]
    def sur_bougie(self,b):
        if b.unite.value!='M15':return None
        x=b.bougie
        if not self.signale:
            self.signale=True
            return SignalTechnique(self.identifiant,x.symbole,x.fin_ms,'ACHAT',x.cloture,.001,x.cloture-.0008,2)
        return AbsenceDeSignal(self.identifiant,x.symbole,x.fin_ms,Motif.NO_SETUP,'PAS_DE_CASSURE')
    def sur_issue(self,i):self.issues.append(i)


def ticks_courts(fin=S+120000):
    dates=[T,S,S+1,S+60000,fin]
    return [Tick('EURUSD','EURUSD',t,t,i,1.1,1.1001) for i,t in enumerate(sorted(set(dates)))]


def composer(ticks,paquets=(),strategie=None,controle=None,**options):
    p=controle if controle is not None else PermissionsFondamentales(C.technique.commun,ConversionServeurScenario())
    source=SourceFondamentaleScenario(p,paquets)
    return (*composer_rejeu_papier(C,ticks,{'EURUSD':D('.00001')},
        {'EURUSD':ContratPapier(D('1000'),D('.1'),D('1'),D('.1'))},
        controle_fondamental=p,source_fondamentale=source,strategie=strategie,**options),p)


def lancer(paquets,ticks=None,strategie=None,stockage=None):
    ticks=ticks if ticks is not None else ticks_courts()
    m,e,s,p=composer(ticks,paquets,strategie or SignalUnique())
    r=rejouer(ticks,m,e,stockage or s)
    return r,[v.vers_dict() for v in r.enregistrements],e,p


class TestCoutureFondamentale(unittest.TestCase):
    def test_composition_exige_port_reel_ou_scenario_explicite(self):
        ticks=ticks_courts();args=(C,ticks,{'EURUSD':D('.00001')},
            {'EURUSD':ContratPapier(D('1000'),D('.1'),D('1'),D('.1'))})
        with self.assertRaises(ValueError):composer_rejeu_papier(*args)
        p=PermissionsFondamentales(C.technique.commun,ConversionServeurScenario())
        with self.assertRaises(ValueError):composer_rejeu_papier(*args,controle_fondamental=p,scenario='TECHNICAL_CONTROL_NEUTRAL')
        r,l,_,_=lancer([export()])
        self.assertFalse(any(x.nature is NatureReponse.REMPLISSAGE for x in r.reponses))
        self.assertTrue(any(v.get('motif')=='FUNDAMENTAL_INVALID' for v in l))

    def test_permission_reelle_journalisee_heartbeat_sans_liquidation(self):
        r,l,e,_=lancer([export(),permission()])
        self.assertEqual(sum(x.nature is NatureReponse.REMPLISSAGE for x in r.reponses),1)
        self.assertTrue(e.positions_ouvertes)
        self.assertTrue(any(v.get('alerte')=='HEARTBEAT_MANQUE' and v['instant_utc_ms']==S+60000 for v in l))
        self.assertTrue(any(v.get('alerte')=='PERMISSION_ACCEPTE' and v['sequence']==1 for v in l))
        intentions=[v for v in l if v['type']=='INTENTION']
        self.assertEqual(intentions[0]['permission']['permission']['message']['sequence'],1)
        self.assertEqual(intentions[0]['version_calendrier']['version'],1)
        self.assertNotIn('scenario',intentions[0]['permission'])

    def test_invalide_et_expiration_bloquent_entree_sans_fabriquer_tick(self):
        for paquet in (PaquetFondamental(S,'PERMISSION',b'{}','EURUSD'),
            permission(t=S-1,valid_until_utc=instant_vers_iso(S))):
            with self.subTest(paquet=paquet):
                r,l,_,_=lancer([export(),paquet])
                self.assertFalse(any(x.nature is NatureReponse.REMPLISSAGE for x in r.reponses))
                self.assertEqual(r.nombre_ticks,len(ticks_courts()))
                self.assertTrue(any(v.get('motif')=='FUNDAMENTAL_INVALID' for v in l))

    def test_no_new_et_direction_incompatible_refusent(self):
        for changements in ({'risk_state':'NO_NEW'},{'direction':'SHORT_ONLY'}):
            r,l,_,_=lancer([export(),permission(**changements)])
            self.assertFalse(any(x.nature is NatureReponse.REMPLISSAGE for x in r.reponses))
            self.assertTrue(any(v.get('motif')=='FUNDAMENTAL_DIRECTION' for v in l))

    def test_changement_direction_ne_ferme_pas_et_flatten_ferme(self):
        for risque,attendu in (('ALLOW',False),('FLATTEN',True)):
            ticks=ticks_courts()+[Tick('EURUSD','EURUSD',S+29999,S+29999,20,1.1,1.1001)]
            ticks.sort(key=lambda v:v.instant_reception_ms)
            r,l,e,_=lancer([export(),permission(),permission(S+30000,2,direction='SHORT_ONLY',risk_state=risque)],ticks)
            closes=[v for v in r.reponses if v.nature is NatureReponse.CLOTURE]
            self.assertEqual(bool(closes),attendu)
            self.assertEqual(bool(e.positions_ouvertes),not attendu)
            if attendu:
                self.assertEqual(closes[0].donnees['cause'].value,'FLATTEN')
                self.assertTrue(any(v['type']=='ORDRE' and v.get('commande')=='CLOTURE'
                    and v['instant_utc_ms']==S+30000 for v in l))

    def test_annonce_apprise_dans_fenetre_ferme_a_reception(self):
        t=S+30000
        ticks=ticks_courts()+[Tick('EURUSD','EURUSD',t-1,t-1,20,1.1,1.1001)]
        ticks.sort(key=lambda v:v.instant_reception_ms)
        r,l,e,_=lancer([export(),permission(),export(t,[evenement(t+600000)],2)],ticks)
        self.assertFalse(e.positions_ouvertes)
        self.assertEqual(next(v for v in r.reponses if v.nature is NatureReponse.CLOTURE).donnees['cause'].value,'ANNONCE')
        self.assertTrue(any(v['type']=='ORDRE' and v.get('commande')=='CLOTURE' and v['instant_utc_ms']==t for v in l))

    def test_sans_cotation_fraiche_demande_prioritaire_puis_envoi_negociable(self):
        class ObservationSortie(StockageMemoirePapier):
            def __init__(self):super().__init__();self.cycles=[]
            def persister(self,lot):
                self.cycles.extend(v.etat for v in lot.etat.reprise.cycles)
                return super().persister(lot)
        stockage=ObservationSortie()
        r,l,e,_=lancer([export(),permission(),permission(S+30000,2,risk_state='FLATTEN')],stockage=stockage)
        demandes=[v for v in stockage.cycles if v.dernier_ms==S+30000 and v.cause_sortie is not None]
        self.assertTrue(demandes)
        self.assertEqual(demandes[0].cause_sortie.value,'FLATTEN')
        self.assertIsNotNone(demandes[0].sl_natif)
        self.assertIsNotNone(demandes[0].tp_natif)
        ordres=[v for v in l if v['type']=='ORDRE' and v.get('commande')=='CLOTURE']
        self.assertEqual(ordres[0]['instant_utc_ms'],S+60000)
        self.assertFalse(e.positions_ouvertes)

    def test_revalidation_avant_transmission_voit_nouveau_no_new(self):
        ticks=ticks_courts();m,e,_,p=composer(ticks,[export(),permission()],SignalUnique())
        class ChangementPendantPersistance(StockageMemoirePapier):
            def persister(self,lot):
                preuve=super().persister(lot)
                if lot.preparations:
                    p.recevoir_permission('EURUSD',permission(sequence=2,risk_state='NO_NEW').octets,S)
                return preuve
        r=rejouer(ticks,m,e,ChangementPendantPersistance())
        self.assertFalse(any(x.nature is NatureReponse.REMPLISSAGE for x in r.reponses))
        self.assertTrue(any(v.vers_dict().get('detail')=='RISK_STATE_NO_NEW' for v in r.enregistrements))

    def test_source_refuse_recul_retard_et_mauvaise_liaison(self):
        p=PermissionsFondamentales(C.technique.commun,ConversionServeurScenario())
        with self.assertRaises(ValueError):SourceFondamentaleScenario(p,[permission(),export()])
        source=SourceFondamentaleScenario(p,[permission()])
        with self.assertRaises(ValueError):source.recevoir(S+1)
        with self.assertRaises(ValueError):PaquetFondamental(T,'CALENDRIER',b'{}')
        with self.assertRaises(ValueError):PaquetFondamental(T,'INTERRUPTION',b'{}','EURUSD')

    def test_rejeu_deterministe_et_interruption_sans_retroactivite(self):
        paquets=[export(),PaquetFondamental(S-1,'INTERRUPTION',symbole='EURUSD'),
            permission(S+1)]
        r,l,_,_=lancer(paquets)
        r2,l2,_,_=lancer(paquets)
        self.assertEqual(l,l2)
        self.assertEqual(r.reponses,r2.reponses)
        self.assertTrue(any(v.get('detail')=='INTERRUPTION' for v in l))
        self.assertFalse(any(x.nature is NatureReponse.REMPLISSAGE for x in r.reponses))

    def test_controle_repris_avant_premier_tick_sans_recul_du_temps(self):
        p=PermissionsFondamentales(C.technique.commun,ConversionServeurScenario())
        p.recevoir_calendrier(export().octets,T,table_importance())
        p.recevoir_permission('EURUSD',permission(T).octets,T)
        reprise=PermissionsFondamentales(C.technique.commun,ConversionServeurScenario(),p.etat)
        dates=(T+120000,T+180000)
        ticks=[Tick('EURUSD','EURUSD',t,t,i,1.1,1.1001) for i,t in enumerate(dates)]
        m,e,s,_=composer(ticks,controle=reprise)
        r=rejouer(ticks,m,e,s)
        lignes=[v.vers_dict() for v in r.enregistrements]
        h=next(v for v in lignes if v.get('alerte')=='HEARTBEAT_MANQUE')
        self.assertEqual((h['instant_utc_ms'],h['echeance_ms'],h['nombre']),(dates[0],T+60000,2))
        self.assertTrue(all(v['instant_utc_ms']>=dates[0] for v in lignes))
        self.assertEqual(r.nombre_ticks,len(ticks))
        p.avancer(T+300000)
        with self.assertRaises(ValueError):composer(ticks,controle=p)

    def test_l14_vraie_journee_london_ete_hiver(self):
        cal=CalendrierLondres.depuis_parametres(C.technique.commun)
        for jour in (date(2026,7,15),date(2026,1,14)):
            with self.subTest(jour=jour):
                session=cal.instant_local(jour,time(8));debut=session+15*60000
                annonce=cal.instant_local(jour,time(9));cloture=annonce-900000
                bougies,_=journee_london_prechargee(jour,C.technique,base=D('1.1'),tr_m15=D('.0008'),tr_h1=D('.0008'))
                bougies=[replace(b,ouverture='1.10110',haut='1.10130',bas='1.10100',cloture='1.10110')
                    if b.debut_ms>=debut else b for b in bougies]
                fab=ticks_de_bougies('EURUSD',bougies)
                fab.append(TickFabrique('EURUSD','EURUSD',cloture+1,0,'1.10110','1.10120'))
                fab.sort(key=lambda x:x.instant_ms)
                fab=[replace(t,sequence=i) for i,t in enumerate(fab,1)]
                ticks=list(analyser_lignes_ticks(lignes_csv(fab)))
                # Composition sans stratégie de test : le vrai moteur London décide la cassure.
                m,e,s,p=composer(ticks,[export(session,[evenement(annonce)]),permission(debut-60000)])
                r=rejouer(ticks,m,e,s);l=[v.vers_dict() for v in r.enregistrements]
                fills=[v for v in r.reponses if v.nature is NatureReponse.REMPLISSAGE]
                closes=[v for v in r.reponses if v.nature is NatureReponse.CLOTURE]
                self.assertEqual(len(fills),1)
                self.assertEqual((len(closes),closes[0].donnees['cause'].value),(1,'ANNONCE'))
                self.assertEqual(closes[0].instant_ms,cloture+1)
                demandes=[v for v in l if v['type']=='ORDRE' and v.get('commande')=='CLOTURE']
                self.assertEqual(demandes[0]['instant_utc_ms'],cloture)
                self.assertFalse(e.positions_ouvertes)
                self.assertTrue(any(v.get('alerte')=='PERMISSION_EXPIREE' for v in l))
                self.assertTrue(any(v.get('alerte')=='HEARTBEAT_MANQUE' for v in l))
                self.assertEqual(sum(v['type']=='CLOTURE' for v in l),len(bougies)-1)
                self.assertEqual(r.nombre_ticks,len(ticks))

"""Vrai service, SQLite et IPC pendant une séance complète des deux moteurs."""
from dataclasses import replace
from datetime import date,time
from decimal import Decimal as D
import tempfile
import threading
import unittest
from robot.outils.configuration import configuration_figee
from robot.outils.fabrique_journees_london import journee_london_prechargee
from robot.outils.fabrique_ticks import lignes_csv,ticks_de_bougies
from robot.outils.fondamental import ConversionServeurScenario
from robot.squelette.test_fondamental import export,permission
from xpbots.app.rejeu_squelette import composer_rejeu_papier_ab
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.contexte_ia.c0_types import PolitiqueVeto,charger_parametres
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.infra.c0e_snapshot import LecteurSnapshot
from xpbots.orchestration.c0_contrats import ReceptionExterne
from xpbots.execution.c4_cycle import NatureReponse
from xpbots.rejeu.squelette import ContratPapier,SourceFondamentaleScenario,analyser_lignes_ticks,rejouer_ab
from .support import document
from .support_service import composer


class SourcePhysiqueScenario:
    """Scénarise seulement les instants externes ; produit et lit réellement le fichier."""
    def __init__(self,service,lecteur,chemin,debut,fin,mode):
        self.s=service;self.lecteur=lecteur;self.chemin=chemin;self.mode=mode
        self._suivant=debut;self.fin=fin;self.lectures=0
        self.fichier=LecteurSnapshot(chemin,service.r.p['snapshot_max_bytes'])
    @property
    def prochaine_reception_ms(self):return self._suivant
    def extraire(self,t):
        if t!=self._suivant:return ()
        self.s.horloge.t=t;self.s.collecter();self.s.inferer()
        if self.mode=='NORMAL':self.s.heartbeat()
        elif self.mode=='CORROMPU':self.chemin.write_bytes(b'{corrompu')
        b,_,_=self.fichier.lire(t);self.lectures+=1
        self._suivant=t+self.s.r.p['snapshot_heartbeat_seconds']*1000
        if self._suivant>self.fin:self._suivant=None
        return (ReceptionExterne('SNAPSHOT',b),)


class CoutureServiceAB(unittest.TestCase):
    def test_http_20_secondes_en_cours_ne_bloque_pas_entree_london_dans_son_ttl(self):
        c=configuration_figee();cal=CalendrierLondres.depuis_parametres(c.technique.commun)
        jour=date(2026,7,15);session=cal.instant_local(jour,time(8));premier=session+900000;second=session+1800000
        bougies,_=journee_london_prechargee(jour,c.technique,base=D('1.1'),tr_m15=D('.0008'),tr_h1=D('.0008'))
        bougies=[replace(v,ouverture='1.10110',haut='1.10190',bas='1.10100',cloture='1.10180') if v.debut_ms==premier else
            replace(v,ouverture='1.10180',haut='1.10200',bas='1.10170',cloture='1.10180') if v.debut_ms>premier else v for v in bougies]
        ticks=list(analyser_lignes_ticks(lignes_csv(ticks_de_bougies('EURUSD',bougies))))
        envoye=premier-1000;entre=threading.Event();liberer=threading.Event();fini=threading.Event();erreurs=[]
        with tempfile.TemporaryDirectory() as tmp:
            service,o,h,p=composer(tmp,t=envoye,d=document(t=envoye,publie_ms=premier-60000))
            with service:
                service.collecter();service.heartbeat()
                def bloquer():entre.set();liberer.wait()
                o.bloquer=bloquer
                def inferer():
                    try:service.inferer()
                    except BaseException as ex:erreurs.append(type(ex).__name__)
                    finally:fini.set()
                worker=threading.Thread(target=inferer);worker.start()
                try:
                    self.assertTrue(entre.wait(3))
                    ia=LecteurContexte(charger_parametres(c),PolitiqueVeto(True))
                    fichier=LecteurSnapshot(p/'context.json',service.r.p['snapshot_max_bytes'])
                    attendu=envoye+service.r.p['http_inference_timeout_seconds']*1000
                    class SourcePendantHTTP:
                        lecteur=ia
                        prochain=premier
                        observations=[]
                        @property
                        def prochaine_reception_ms(self):return self.prochain
                        def extraire(self,t):
                            if t!=self.prochain:return ()
                            h.t=t
                            if t>=attendu:
                                liberer.set()
                                if not fini.wait(3):raise AssertionError('La réponse externe ne termine pas')
                                self.prochain=None
                            else:
                                self.observations.append((t,not fini.is_set()))
                                self.prochain=t+service.r.p['ea_snapshot_poll_seconds']*1000
                            service.heartbeat();b,_,_=fichier.lire(t)
                            return (ReceptionExterne('SNAPSHOT',b),)
                    source=SourcePendantHTTP();fond=PermissionsFondamentales(c.technique.commun,ConversionServeurScenario())
                    m,e,s=composer_rejeu_papier_ab(c,ticks,{'EURUSD':D('.00001')},
                        {'EURUSD':ContratPapier(D('1000'),D('.1'),D('1'),D('.1'))},controle_fondamental=fond,
                        source_fondamentale=SourceFondamentaleScenario(fond,[export(session),permission(premier-60000),permission(second-60000,2)]),
                        lecteur_ia=ia,source_ia=source)
                    r=rejouer_ab(ticks,m,e,s)
                    for bras in ('REFERENCE','IA'):
                        fills=[v for v in r.reponses[bras] if v.nature is NatureReponse.REMPLISSAGE]
                        self.assertEqual(len(fills),1);self.assertEqual(fills[0].cle.cloture_ms,premier)
                    self.assertTrue(source.observations);self.assertTrue(all(en_cours for _,en_cours in source.observations))
                    self.assertFalse(erreurs);self.assertEqual(len([q for q in o.requetes if q.get_method()=='POST']),1)
                    event=service.depot.transaction(lambda t:next(iter(t['policy_events'].values())))
                    self.assertEqual(event['validated_at'],attendu)
                finally:liberer.set();worker.join(5)

    def test_service_physique_rejoue_ete_hiver_et_neutralite_sans_snapshot_valide(self):
        c=configuration_figee();cal=CalendrierLondres.depuis_parametres(c.technique.commun)
        for jour in (date(2026,7,15),date(2026,1,14)):
            for mode in ('NORMAL','ABSENT','CORROMPU'):
                with self.subTest(jour=jour,mode=mode),tempfile.TemporaryDirectory() as tmp:
                    session=cal.instant_local(jour,time(8));premier=session+900000;second=session+1800000
                    b,_=journee_london_prechargee(jour,c.technique,base=D('1.1'),tr_m15=D('.0008'),tr_h1=D('.0008'))
                    b=[replace(v,ouverture='1.10110',haut='1.10190',bas='1.10100',cloture='1.10180') if v.debut_ms==premier else
                        replace(v,ouverture='1.10180',haut='1.10200',bas='1.10170',cloture='1.10180') if v.debut_ms>premier else v for v in b]
                    ticks=list(analyser_lignes_ticks(lignes_csv(ticks_de_bougies('EURUSD',b))))
                    recu=session+8*60000;doc=document(t=recu,publie_ms=session+7*60000)
                    service,ouvreur,h,p=composer(tmp,t=recu,d=doc)
                    with service:
                        ia=LecteurContexte(charger_parametres(c),PolitiqueVeto(True))
                        fond=PermissionsFondamentales(c.technique.commun,ConversionServeurScenario())
                        source_f=SourceFondamentaleScenario(fond,[export(session),permission(premier-60000),permission(second-60000,2)])
                        source_ia=SourcePhysiqueScenario(service,ia,p/'context.json',recu,second+60000,mode)
                        m,e,s=composer_rejeu_papier_ab(c,ticks,{'EURUSD':D('.00001')},
                            {'EURUSD':ContratPapier(D('1000'),D('.1'),D('1'),D('.1'))},
                            controle_fondamental=fond,source_fondamentale=source_f,lecteur_ia=ia,source_ia=source_ia)
                        r=rejouer_ab(ticks,m,e,s);lignes=[v.vers_dict() for v in r.enregistrements]
                        for bras,attendu in (('REFERENCE',premier),('IA',second if mode=='NORMAL' else premier)):
                            fills=[v for v in r.reponses[bras] if v.nature is NatureReponse.REMPLISSAGE]
                            self.assertEqual(len(fills),1);self.assertEqual(fills[0].cle.cloture_ms,attendu)
                        vetos=[v for v in lignes if v.get('motif')=='AI_CONTEXT_VETO']
                        self.assertEqual(bool(vetos),mode=='NORMAL')
                        self.assertTrue(all(v['bras']=='IA' for v in vetos))
                        self.assertFalse(any(v.get('commande')=='ENTREE' and session+22*60000<=v['instant_utc_ms']<second for v in lignes))
                        self.assertGreater(source_ia.lectures,1)
                        self.assertEqual(len([q for q in ouvreur.requetes if q.get_method()=='POST']),1)
                        if mode=='NORMAL':self.assertNotEqual(e['IA'].etat_compte().fonds_propres,e['REFERENCE'].etat_compte().fonds_propres)

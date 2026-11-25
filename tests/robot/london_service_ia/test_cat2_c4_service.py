"""Composition physique réelle, sans API ni clé privée, avec IPC et reprise."""
from pathlib import Path
import tempfile
import threading
import unittest
from xpbots.service_ia.c0_types import decoder, utc, ErreurService, JobIA, canonique
from xpbots.service_ia.c4_service import ServiceIA
from xpbots.infra.c0e_snapshot import LecteurSnapshot
from xpbots.contexte_ia.c0_types import PolitiqueVeto, charger_parametres
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from .support_service import composer,OuvreurService
from .support_ouvreur import ReponseOuvree
from .support import ressources,Horloge


class ServicePhysique(unittest.TestCase):
    def test_suspension_retire_evenement_actif_du_fichier_et_survit_a_reprise_sqlite(self):
        class OuvreurChange(OuvreurService):
            changer=False
            def open(self,req,timeout):
                reponse=super().open(req,timeout)
                if req.get_method()=='POST' and self.changer:
                    v=decoder(reponse.read(self.r.p['max_response_bytes']));reponse.close()
                    v['model']='synthetic-changed-version'
                    return ReponseOuvree(req.full_url,canonique(v))
                return reponse
        with tempfile.TemporaryDirectory() as tmp:
            h=Horloge();o=OuvreurChange(ressources(),h);s,o,h,p=composer(tmp,h=h,ouvreur=o)
            with s:
                s.collecter();s.inferer();s.heartbeat()
                lecteur=LecteurSnapshot(p/'context.json',s.r.p['snapshot_max_bytes'])
                contexte=LecteurContexte(charger_parametres(s.r.configuration),PolitiqueVeto(True))
                contexte.recevoir(lecteur.lire(h.t)[0],h.t)
                self.assertEqual(contexte.evaluer('EURUSD',h.t).etat.value,'BLOCK')
                archives=s.depot.transaction(lambda t:dict(t['policy_events']))
                h.t+=s.r.p['provider_min_request_spacing_seconds']*1000;o.changer=True
                s.routeur.enregistrer(JobIA('note-modele','JOURNAL',None,h.t,h.t+s.r.p['job_deadline_seconds']*1000,
                    canonique(dict(kind='JOURNAL',documents=[],metrics=[]))))
                self.assertIsNone(s.inferer().erreur);s.heartbeat()
                b=lecteur.lire(h.t)[0];self.assertFalse(decoder(b)['payload']['events'])
                contexte.recevoir(b,h.t)
                self.assertEqual(contexte.evaluer('EURUSD',h.t).etat.value,'BLOCK')
                neuf=LecteurContexte(charger_parametres(s.r.configuration),PolitiqueVeto(True));neuf.recevoir(b,h.t)
                self.assertEqual(neuf.evaluer('EURUSD',h.t).etat.value,'NEUTRAL')
                self.assertEqual(s.depot.transaction(lambda t:dict(t['policy_events'])),archives)
            nombre=len(o.requetes)
            with ServiceIA(s.r,p/'ia.db',p/'context.json',horloge=h,ouvreur=o) as reprise:
                self.assertIsNone(reprise.inferer());self.assertFalse(decoder(reprise.heartbeat().octets)['payload']['events'])
                self.assertEqual(len(o.requetes),nombre)

    def test_chaine_complete_physique_et_reprise_sans_reinference(self):
        with tempfile.TemporaryDirectory() as tmp:
            s,o,h,p=composer(tmp)
            with s:
                s.collecter();self.assertIsNone(s.inferer().erreur);a=s.heartbeat();self.assertTrue(a.publie)
                lecteur=LecteurSnapshot(p/'context.json',s.r.p['snapshot_max_bytes'])
                b,t,err=lecteur.lire(h.t);self.assertIsNone(err)
                contexte=LecteurContexte(charger_parametres(s.r.configuration),PolitiqueVeto(True))
                self.assertTrue(contexte.recevoir(b,t).acceptee);self.assertEqual(contexte.evaluer('EURUSD',t).etat.value,'BLOCK')
                event=decoder(b)['payload']['events'][0];fin=utc(event['valid_until_utc'])
            n=len(o.requetes)
            with ServiceIA(s.r,p/'ia.db',p/'context.json',horloge=h,ouvreur=o) as reprise:
                self.assertIsNone(reprise.inferer());self.assertEqual(len(o.requetes),n)
                self.assertEqual(reprise.heartbeat().sequence,2)
                h.t=fin;self.assertFalse(decoder(reprise.heartbeat().octets)['payload']['events'])
    def test_inference_bloquee_ne_retient_pas_snapshot_ou_transaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            s,o,h,p=composer(tmp)
            with s:
                s.collecter();entre=threading.Event();sortir=threading.Event();termine=threading.Event();erreurs=[]
                def blocage():entre.set();sortir.wait(5)
                o.bloquer=blocage
                def inferer():
                    try:s.inferer()
                    except BaseException as e:erreurs.append(type(e).__name__)
                    finally:termine.set()
                th=threading.Thread(target=inferer);th.start()
                try:
                    self.assertTrue(entre.wait(3));a=s.heartbeat();h.t+=s.r.p['snapshot_heartbeat_seconds']*1000;b=s.heartbeat()
                    self.assertTrue(a.publie and b.publie);self.assertEqual(b.sequence,a.sequence+1);self.assertFalse(termine.is_set())
                    self.assertEqual(s.depot.transaction(lambda t:len(t['api_attempts'])),1)
                    with self.assertRaises(ErreurService):s.inferer()
                finally:sortir.set();th.join(5)
                self.assertFalse(erreurs);self.assertTrue(termine.is_set())
                # Les trente secondes simulées excèdent le timeout : l'analyse tardive ne crée pas de veto.
                self.assertFalse(s.planificateur.evenements(h.t))
    def test_usage_inconnu_restaure_suspend_nouveaux_appels_et_garde_reserve(self):
        with tempfile.TemporaryDirectory() as tmp:
            s,o,h,p=composer(tmp);o.usage=False
            with s:s.collecter();self.assertIsNone(s.inferer().erreur);s.heartbeat()
            n=len(o.requetes)
            with ServiceIA(s.r,p/'ia.db',p/'context.json',horloge=h,ouvreur=o) as reprise:
                self.assertGreater(reprise.etat()['usages_inconnus'],0);self.assertIsNone(reprise.inferer())
                self.assertEqual(len(o.requetes),n);self.assertTrue(reprise.heartbeat().publie)

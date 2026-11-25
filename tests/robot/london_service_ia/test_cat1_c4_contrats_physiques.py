"""Probes H08/13.6 opt-in ; aucune clé ni aucun réseau dans la suite courante."""
import os
from pathlib import Path
import unittest
from xpbots.service_ia.c0_types import JobIA,canonique,empreinte
from xpbots.service_ia.c4_service import ServiceIA,HorlogeService
from xpbots.service_ia.c4_service._cli import charger_profil
from .support import ressources


@unittest.skipUnless(os.environ.get('XPBOTS_CONTRATS_API')=='1','H08/13.6 : API/RSS physiques non autorisés')
class ContratsAPIPhysiques(unittest.TestCase):
    def service(self):
        # Cette branche n'est jamais exécutée en phase12 ; tous les chemins sont publics.
        r=ressources();profil=os.environ.get('XPBOTS_SERVICE_PROFILE');base=os.environ.get('XPBOTS_SERVICE_DB')
        snapshot=os.environ.get('XPBOTS_SERVICE_SNAPSHOT')
        if not all((profil,base,snapshot)):self.skipTest('Profil et chemins de qualification H08 requis')
        ps,cles,cal,cas,routes=charger_profil(r,Path(profil),autoriser_cles=True,
            paiement_autorise=os.environ.get('XPBOTS_CONTRATS_API_PAYANTE')=='1')
        return ServiceIA(r,base,snapshot,profils=ps,cles=cles,autoriser_http_reel=True,
            paiement_autorise=os.environ.get('XPBOTS_CONTRATS_API_PAYANTE')=='1',
            calendrier=cal,cas_derives=cas,routes_auditees=routes)
    def verifier_api(self,index):
        with self.service() as s:
            self.assertEqual(s.etat()['usages_inconnus'],0,'Rapprocher les usages anciens avant un nouvel appel de qualification')
            pid=s.r.p['providers'][index]['id'];now=s.horloge.maintenant_ms()
            dossier=dict(item_id='API-CONTRACT-SYNTHETIC',title='Contract probe',issuer=s.r.p['feeds'][0]['issuer'],
                provided_text='This is a synthetic API contract probe. It does not announce a real policy decision.')
            ident=empreinte(dict(provider=pid,instant_ms=now,kind='GOLDEN'))
            j=JobIA(ident,'GOLDEN',dossier['item_id'],now,now+s.r.p['job_deadline_seconds']*1000,
                canonique(dossier),fournisseur=pid)
            resultat=s.routeur.executer(j)
            self.assertIsNone(resultat.erreur,'Contrat API ou admission non qualifiés ; ne pas retirer une contrainte A08')
            self.assertIsNotNone(resultat.valide)
    def verifier_rss(self,index):
        with self.service() as s:
            c=s.collecteur.collecter(s.r.p['feeds'][index]['issuer'])
            if c.statut=='DIFFERE':self.skipTest('Espacement RSS en cours ; relancer après son échéance')
            self.assertIn(c.statut,('RECU','NON_MODIFIE'))
            self.assertEqual(c.couverture,'COMPLETE')
    def test_api_groq(self):self.verifier_api(0)
    def test_api_gemini(self):self.verifier_api(1)
    def test_api_openai_facultative(self):
        if os.environ.get('XPBOTS_CONTRATS_API_PAYANTE')!='1':self.skipTest('Route payante non autorisée')
        self.verifier_api(2)
    def test_rss_fed(self):self.verifier_rss(0)
    def test_rss_ecb(self):self.verifier_rss(1)
    def test_rss_boe(self):self.verifier_rss(2)

"""Catégorie 2 : normaliseur et archives réels, dates de contenu causales."""
import unittest
from copy import deepcopy
from dataclasses import asdict
from xpbots.service_ia.c0_types import ErreurService
from xpbots.service_ia.c2c_collecteur import CollecteurRSS
from .support import document
from .support_rss import rss, item, url
from .support_collecteur import composer, avancer


class JonctionCollecteur(unittest.TestCase):
    def test_meme_texte_republication_et_redemarrage_conservent_identite(self):
        r,m,h,http,c=composer();a=c.collecter('FED');d=a.nouveaux[0];avancer(r,h)
        http.actions=[lambda q,http:http.reponse(q,corps=rss(item(lien=url('FED','/another'))))]
        nouveau=CollecteurRSS(r,m,http,h);b=nouveau.collecter('FED')
        self.assertFalse(b.nouveaux);self.assertEqual(len(m.tables['source_items']),1)
        self.assertEqual(nouveau.documents('FED'),(d,))
    def test_correction_historisee_connue_uniquement_apres_sa_collecte(self):
        r,m,h,http,c=composer();a=c.collecter('FED');d=a.nouveaux[0];t=h.t;ancienne=deepcopy(m.tables['source_items'][d.item_id])
        avancer(r,h);http.actions=[lambda q,http:http.reponse(q,corps=rss(item(texte='The committee did not change the rate. Correction.')))]
        b=c.collecter('FED');corr=b.nouveaux[0]
        self.assertNotEqual(d.item_id,corr.item_id)
        self.assertEqual((corr.publie_ms,corr.premiere_vue_ms),(d.publie_ms,d.premiere_vue_ms))
        self.assertEqual(corr.collecte_ms,h.t);self.assertEqual(m.tables['source_items'][d.item_id],ancienne)
        self.assertEqual(c.documents('FED',known_at_ms=t),(d,))
        self.assertEqual(len(c.documents('FED')),2)
    def test_recherche_issuer_publication_et_connaissance_bornes(self):
        r,m,h,http,c=composer();d=c.collecter('FED').nouveaux[0]
        self.assertEqual(c.documents('FED',debut_ms=d.publie_ms,fin_ms=d.publie_ms+1),(d,))
        self.assertFalse(c.documents('ECB'));self.assertFalse(c.documents('FED',fin_ms=d.publie_ms))
        self.assertFalse(c.documents('FED',known_at_ms=d.collecte_ms-1))
        with self.assertRaises(ErreurService):c.documents(known_at_ms=h.t+1)
    def test_selectionneur_physique_injecte_et_refiltre_sans_futur(self):
        r,m,h,http,c=composer();d=c.collecter('FED').nouveaux[0];appels=[]
        def selection(f):appels.append(f);return list(m.tables['source_items'].values())
        nouveau=CollecteurRSS(r,m,http,h,selectionner=selection)
        self.assertEqual(nouveau.documents('FED'),(d,));self.assertEqual(appels[0]['issuer'],'FED')
        self.assertFalse(nouveau.documents('ECB'))
        self.assertFalse(nouveau.documents('FED',known_at_ms=d.collecte_ms-1))
    def test_documents_non_dates_futurs_et_flux_partiel_restent_documentaires(self):
        r,m,h,http,c=composer()
        http.actions=[lambda q,http:http.reponse(q,corps=rss(item(sans_date=True),item(lien=url('FED','/future'),
            texte='A future synthetic text.',publication='Tue, 17 Nov 2099 10:00:00 GMT'),item(lien='https://evil.test/')))]
        a=c.collecter('FED');self.assertEqual(a.couverture,'PARTIAL')
        self.assertEqual({d.couverture for d in a.nouveaux},{'UNDATED','FUTURE'})
        self.assertEqual(len(m.tables['source_items']),2)
    def test_archive_xml_bornee_et_etat_hors_secret_sans_llm(self):
        r,m,h,http,c=composer();a=c.collecter('FED')
        archives=[v for k,v in m.tables['feed_state'].items() if k.startswith('response:')]
        self.assertEqual(len(archives),1);self.assertIn(a.nouveaux[0].item_id,archives[0]['item_ids'])
        self.assertLessEqual(len(bytes.fromhex(archives[0]['raw_response'])),r.p['rss_max_download_bytes'])
        self.assertFalse(m.tables['llm_jobs']);self.assertFalse(m.tables['api_attempts'])

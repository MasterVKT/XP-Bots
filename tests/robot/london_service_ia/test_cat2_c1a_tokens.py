"""Catégorie 2, couche 1a : ressources et requêtes réelles comparées à l’oracle."""
import unittest
from reference.llm_contracts import token_input_upper_bound
from xpbots.service_ia.c0_types import canonique, decoder, RequeteHTTP
from xpbots.service_ia.c1a_tokens import preparer_requete, compter_entree
from .support import ressources, job

class JonctionTokens(unittest.TestCase):
    def test_corps_complet_prompt_schema_et_dossier(self):
        r=ressources();j=job()
        def construire(dossier):
            corps=canonique(dict(system=r.prompt(j.kind),schema=r.schema(j.kind),dossier=decoder(dossier)))
            return RequeteHTTP(r.p['providers'][0]['endpoint'],'POST',(),corps,
                r.p['http_inference_timeout_seconds'],r.p['max_response_bytes'])
        v=preparer_requete(r,j.dossier,construire)
        self.assertIsNotNone(v)
        self.assertEqual(v.tokens_entree,token_input_upper_bound(v.requete.corps.decode('utf-8')))
        self.assertEqual(decoder(v.dossier),decoder(j.dossier))
        self.assertGreater(v.tokens_entree,compter_entree(r,j.dossier))

    def test_oracle_sur_unicode_vide_et_bornes(self):
        r=ressources()
        for s in ('','é漢字', 'x'*r.p['max_input_tokens_upper_bound']):
            with self.subTest(s=s[:10]):self.assertEqual(compter_entree(r,s.encode('utf-8')),token_input_upper_bound(s))

    def test_preuves_transmises_apres_reduction(self):
        r=ressources();b=canonique(dict(documents=[dict(item_id='retire',texte='x'*r.p['max_input_tokens_upper_bound'])]))
        def construire(b):return RequeteHTTP(r.p['providers'][0]['endpoint'],'POST',(),b,
            r.p['http_inference_timeout_seconds'],r.p['max_response_bytes'])
        v=preparer_requete(r,b,construire,reduire_documents=True)
        self.assertEqual(decoder(v.dossier),{'documents':[]})
        self.assertEqual(v.documents_retires,('retire',))

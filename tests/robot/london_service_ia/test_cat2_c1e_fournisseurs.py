"""Catégorie 2, couche 1e : requêtes et réponses réelles sur les ressources 0."""
from dataclasses import replace
import unittest
from reference.llm_contracts import parse_model_output, parse_advisory_output
from xpbots.service_ia.c0_types import canonique, decoder, JobIA
from xpbots.service_ia.c1e_fournisseurs import construire_requete, decoder_reponse, extraire_usage
from .support import ressources, document, job, extraction
from .support_http import reponse


class JonctionFournisseurs(unittest.TestCase):
    def test_extraction_traverse_job_corps_et_reponse_sans_alteration(self):
        r=ressources();d=document();j=job(d)
        for index,p in enumerate(r.p['providers']):
            with self.subTest(fournisseur=p['id']):
                q=construire_requete(r,j,p['id']);corps=decoder(q.corps)
                user=(corps['messages'][1]['content'] if index==0 else
                      corps['contents'][0]['parts'][0]['text'] if index==1 else corps['input'][1]['content'])
                self.assertEqual(decoder(user.encode()),decoder(j.dossier))
                v=decoder_reponse(r,p['id'],reponse(p['id']))
                self.assertEqual(parse_model_output(v.texte,d.item(d.texte)),extraction(d))
                self.assertEqual(extraire_usage(r,p['id'],reponse(p['id'])).tokens_sortie,v.tokens_sortie)

    def test_notes_emploient_prompt_et_schema_informatifs(self):
        r=ressources();t=document().collecte_ms
        for kind in ('BRIEFING','JOURNAL','WEEKLY_REVIEW'):
            dossier=canonique(dict(documents=[],metrics=dict(evidence_id='metric-synthetic',net_pnl='0')))
            j=JobIA('note-'+kind,kind,None,t,t+r.p['job_deadline_seconds']*1000,dossier,('metric-synthetic',))
            note=dict(schema_version='fx-advisory-v1',kind=kind,observations=[dict(text='Only supplied metrics.',evidence_ids=['metric-synthetic'])],uncertainties=[],hypotheses=[])
            for p in r.p['providers']:
                with self.subTest(kind=kind,fournisseur=p['id']):
                    q=construire_requete(r,j,p['id']);b=decoder(q.corps)
                    schema=(b['response_format']['json_schema']['schema'] if 'response_format' in b else
                            b['generationConfig']['responseJsonSchema'] if 'generationConfig' in b else b['text']['format']['schema'])
                    self.assertEqual(schema,r.schema(kind));self.assertIn(r.prompt(kind),q.corps.decode())
                    v=decoder_reponse(r,p['id'],reponse(p['id'],canonique(note).decode()))
                    self.assertEqual(parse_advisory_output(v.texte,kind,('metric-synthetic',)),note)

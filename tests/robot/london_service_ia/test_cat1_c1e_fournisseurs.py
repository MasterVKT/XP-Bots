"""Catégorie 1, couche 1e : gabarits A08 exacts et décodage des fournisseurs."""
from copy import deepcopy
from dataclasses import replace
import unittest
from xpbots.service_ia.c0_types import ErreurService, canonique, decoder, JobIA
from xpbots.service_ia.c1e_fournisseurs import construire_requete, decoder_reponse, extraire_usage
from .support import ressources, job, document
from .support_http import enveloppe, reponse


class FormatsFournisseurs(unittest.TestCase):
    def setUp(self):self.r=ressources();self.j=job();self.p=self.r.p

    def test_groq_gabarit_exact_schema_objet_et_messages(self):
        p=self.p['providers'][0];q=construire_requete(self.r,self.j,p['id'])
        schema=self.r.schema(self.j.kind);nom=schema['properties']['schema_version']['enum'][0].replace('-','_')
        attendu=dict(model=p['model'],messages=[dict(role='system',content=self.r.prompt(self.j.kind)),
            dict(role='user',content=canonique(decoder(self.j.dossier)).decode())],
            temperature=p['temperature'],reasoning_effort=p['reasoning_effort'],
            max_completion_tokens=self.p['max_output_tokens_including_reasoning'],stream=False,
            response_format=dict(type='json_schema',json_schema=dict(name=nom,strict=True,schema=schema)))
        self.assertEqual(decoder(q.corps),attendu)
        self.assertEqual((q.url,q.timeout_s,q.max_octets),(p['endpoint'],self.p['http_inference_timeout_seconds'],self.p['max_response_bytes']))
        self.assertFalse(any(k.lower()=='authorization' for k,_ in q.entetes))

    def test_gemini_gabarit_rest_exact(self):
        p=self.p['providers'][1];q=construire_requete(self.r,self.j,p['id'])
        attendu=dict(systemInstruction=dict(parts=[dict(text=self.r.prompt(self.j.kind))]),
            contents=[dict(role='user',parts=[dict(text=canonique(decoder(self.j.dossier)).decode())])],
            generationConfig=dict(temperature=p['temperature'],maxOutputTokens=self.p['max_output_tokens_including_reasoning'],
                thinkingConfig=dict(thinkingLevel=p['thinking_level'].upper()),
                responseMimeType='application/json',responseJsonSchema=self.r.schema(self.j.kind)))
        self.assertEqual(decoder(q.corps),attendu)
        self.assertEqual(decoder(q.corps)['generationConfig']['thinkingConfig']['thinkingLevel'],'MINIMAL')

    def test_openai_gabarit_responses_exact_sans_stockage_ni_outil(self):
        p=self.p['providers'][-1];q=construire_requete(self.r,self.j,p['id']);schema=self.r.schema(self.j.kind)
        nom=schema['properties']['schema_version']['enum'][0].replace('-','_')
        attendu=dict(model=p['model'],input=[dict(role='system',content=self.r.prompt(self.j.kind)),
            dict(role='user',content=canonique(decoder(self.j.dossier)).decode())],
            reasoning=dict(effort=p['reasoning_effort']),max_output_tokens=self.p['max_output_tokens_including_reasoning'],
            service_tier=p['service_tier'],store=False,stream=False,
            text=dict(format=dict(type='json_schema',name=nom,strict=True,schema=schema)))
        self.assertEqual(decoder(q.corps),attendu)
        for cle in ('tools','temperature','prompt_cache_retention'):self.assertNotIn(cle,decoder(q.corps))

    def test_dossiers_extraction_et_fournisseurs_hors_contrat_refuses(self):
        pid=self.p['providers'][0]['id'];d=decoder(self.j.dossier)
        for mauvais in (dict(d,account_id='synthetic-forbidden'),dict(d,item_id='foreign'),dict(d,issuer='OTHER')):
            with self.subTest(dossier=mauvais),self.assertRaises(ErreurService):construire_requete(self.r,self.j,pid,canonique(mauvais))
        with self.assertRaises(ErreurService):construire_requete(self.r,self.j,'LOCAL')
        with self.assertRaises(ErreurService):construire_requete(self.r,replace(self.j,fournisseur='LOCAL'),pid)

    def test_compteurs_et_details_bruts_sans_double_compte(self):
        for p in self.p['providers']:
            with self.subTest(fournisseur=p['id']):
                v=decoder_reponse(self.r,p['id'],reponse(p['id']))
                self.assertEqual((v.tokens_entree,v.tokens_sortie),(100,50))
                self.assertEqual(v.modele_recu,p['model']);self.assertIsInstance(v.usage,dict)
                copie=v.usage;copie.clear();self.assertTrue(v.usage)

    def test_usage_absent_inconnu_et_non_zero(self):
        for p in self.p['providers']:
            with self.subTest(fournisseur=p['id']):
                v=decoder_reponse(self.r,p['id'],reponse(p['id'],usage=False))
                self.assertEqual((v.tokens_entree,v.tokens_sortie,v.usage_brut),(None,None,None))

    def test_groq_refus_troncature_et_appels_outils(self):
        pid=self.p['providers'][0]['id'];base=enveloppe(pid);cas=[]
        a=deepcopy(base);a['choices'][0]['finish_reason']='length';cas.append(a)
        for cle,valeur in (('refusal','declined'),('tool_calls',[{'type':'function'}]),('function_call',{})):
            a=deepcopy(base);a['choices'][0]['message'][cle]=valeur;cas.append(a)
        for v in cas:
            with self.subTest(v=v),self.assertRaises(ErreurService):decoder_reponse(self.r,pid,replace(reponse(pid),corps=canonique(v)))

    def test_gemini_ignore_thoughts_et_concatene_texte_final(self):
        pid=self.p['providers'][1]['id'];v=enveloppe(pid);s=v['candidates'][0]['content']['parts'][0]['text'];milieu=len(s)//2
        v['candidates'][0]['content']['parts']=[dict(thought=True,text='private reasoning ignored'),
            dict(thoughtSignature='opaque-signature'),dict(text=s[:milieu]),dict(text=s[milieu:])]
        self.assertEqual(decoder_reponse(self.r,pid,replace(reponse(pid),corps=canonique(v))).texte,s)

    def test_gemini_blocage_finish_et_function_call_refuses(self):
        pid=self.p['providers'][1]['id'];base=enveloppe(pid);cas=[]
        a=deepcopy(base);a['promptFeedback']=dict(blockReason='SAFETY');cas.append(a)
        a=deepcopy(base);a['candidates'][0]['finishReason']='MAX_TOKENS';cas.append(a)
        for partie in (dict(functionCall={'name':'tool'}),dict(inlineData={'data':'x'})):
            a=deepcopy(base);a['candidates'][0]['content']['parts'].append(partie);cas.append(a)
        for v in cas:
            with self.subTest(v=v),self.assertRaises(ErreurService):decoder_reponse(self.r,pid,replace(reponse(pid),corps=canonique(v)))

    def test_openai_raisonnement_puis_plusieurs_messages(self):
        pid=self.p['providers'][-1]['id'];v=enveloppe(pid);s=v['output'][1]['content'][0]['text'];milieu=len(s)//2
        v['output']=[dict(type='reasoning',summary=[dict(text='ignored')]),
            dict(type='message',content=[dict(type='output_text',text=s[:milieu])]),
            dict(type='message',content=[dict(type='output_text',text=s[milieu:])])]
        self.assertEqual(decoder_reponse(self.r,pid,replace(reponse(pid),corps=canonique(v))).texte,s)

    def test_openai_refus_incomplet_et_tool_calls_refuses(self):
        pid=self.p['providers'][-1]['id'];base=enveloppe(pid);cas=[]
        a=deepcopy(base);a['status']='incomplete';cas.append(a)
        a=deepcopy(base);a['output'][1]['content']=[dict(type='refusal',refusal='declined')];cas.append(a)
        a=deepcopy(base);a['output'].append(dict(type='function_call',name='tool'));cas.append(a)
        for v in cas:
            with self.subTest(v=v),self.assertRaises(ErreurService):decoder_reponse(self.r,pid,replace(reponse(pid),corps=canonique(v)))

    def test_usage_lisible_meme_si_sortie_non_terminee_ou_http_en_erreur(self):
        pid=self.p['providers'][0]['id'];v=enveloppe(pid);v['choices'][0]['finish_reason']='length'
        rep=replace(reponse(pid),corps=canonique(v))
        with self.assertRaises(ErreurService):decoder_reponse(self.r,pid,rep)
        u=extraire_usage(self.r,pid,rep);self.assertEqual((u.tokens_entree,u.tokens_sortie),(100,50))
        rep=replace(rep,statut=429)
        self.assertEqual(extraire_usage(self.r,pid,rep).tokens_entree,100)
        with self.assertRaises(ErreurService):decoder_reponse(self.r,pid,rep)

    def test_metriques_invalides_restent_inconnues(self):
        for index,cle_entree,cle_sortie in ((0,'prompt_tokens','completion_tokens'),(2,'input_tokens','output_tokens')):
            pid=self.p['providers'][index]['id']
            for mauvais in (True,-1,1.5,None):
                v=enveloppe(pid);v['usage'][cle_entree]=mauvais
                u=extraire_usage(self.r,pid,replace(reponse(pid),corps=canonique(v)))
                self.assertIsNone(u.tokens_entree);self.assertEqual(u.tokens_sortie,v['usage'][cle_sortie])
        pid=self.p['providers'][1]['id'];v=enveloppe(pid)
        v['usageMetadata']['totalTokenCount']=v['usageMetadata']['promptTokenCount']-1
        self.assertIsNone(extraire_usage(self.r,pid,replace(reponse(pid),corps=canonique(v))).tokens_sortie)

    def test_json_tronque_duplique_et_taille_bornee(self):
        for p in self.p['providers']:
            pid=p['id'];rep=reponse(pid);n=self.p['max_response_bytes']-len(rep.corps)
            self.assertTrue(decoder_reponse(self.r,pid,replace(rep,corps=rep.corps+b' '*n)).texte)
            for mauvais in (rep.corps[:-1],b'{"x":1,"x":2}',rep.corps+b' '*(n+1),b'[]'):
                with self.subTest(pid=pid,taille=len(mauvais)),self.assertRaises(ErreurService):decoder_reponse(self.r,pid,replace(rep,corps=mauvais))

    def test_texte_vide_inutilisable(self):
        for p in self.p['providers']:
            with self.subTest(fournisseur=p['id']),self.assertRaises(ErreurService):decoder_reponse(self.r,p['id'],reponse(p['id'],sortie=''))

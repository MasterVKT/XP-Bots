"""Catégorie 1, couche 0 : types, ressources et ports purs du service IA."""
from dataclasses import FrozenInstanceError, replace
import unittest
from xpbots.service_ia.c0_types import *
from .support import ressources, document, job, Memoire

class TypesService(unittest.TestCase):
    def test_ressources_exportees_et_copies(self):
        r=ressources();self.assertEqual(r.prompt('GOLDEN'),r.prompt('EXTRACTION'))
        s=r.schema('EXTRACTION');s['required']=[]
        self.assertTrue(r.schema('EXTRACTION')['required'])
        self.assertEqual(r.digest,r.configuration.ia.empreinte_canonique)
        self.assertEqual(r.fournisseur(r.p['providers'][0]['id'])['model'],r.p['providers'][0]['model'])
        with self.assertRaises(ErreurService):r.fournisseur('LOCAL')

    def test_refus_ressources(self):
        r=ressources()
        for champ in ('schema_extraction','schema_notes','prompts'):
            with self.subTest(champ=champ),self.assertRaises(ErreurService):replace(r,**{champ:b'{"x":1,"x":2}'})

    def test_document_immuable_et_causal(self):
        d=document();self.assertEqual(len(d.hash_texte),64)
        self.assertEqual(d.item(d.texte)['provided_text'],d.texte)
        with self.assertRaises(FrozenInstanceError):d.issuer='OTHER'
        for kw in (dict(premiere_vue_ms=d.collecte_ms+1),dict(officiel=1),dict(publie_ms=True),dict(couverture='SAFE')):
            with self.subTest(kw=kw),self.assertRaises(ErreurService):replace(d,**kw)
        self.assertIsNone(replace(d,publie_ms=None).item('')['published_at_utc'])
        with self.assertRaises(ErreurService):d.item('invented')

    def test_dates_et_entiers_stricts(self):
        d=document();self.assertEqual(utc(iso(d.collecte_ms)),d.collecte_ms)
        for x in (True,-1,1.5,'1'):
            with self.subTest(x=x),self.assertRaises(ErreurService):entier(x)
        for x in ('NaN','Infinity','-1',True):
            with self.subTest(x=x),self.assertRaises(ErreurService):montant(x)
        for x in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'[]'):
            with self.subTest(x=x),self.assertRaises(ErreurService):decoder(x)

    def test_http_sans_secret(self):
        q=RequeteHTTP('https://example.invalid/x','GET',(),None,10,1024)
        self.assertEqual(replace(q,entetes=(('Content-Type','application/json'),)).entetes,
                         (('Content-Type','application/json'),))
        self.assertEqual(ReponseHTTP(200,(('ETag','v1'),),b'x',0).entete('etag'),'v1')
        for kw in (dict(url='http://example.invalid'),dict(url='https://user:pass@example.invalid'),
                   dict(entetes=(('Authorization','synthetic'),)),dict(timeout_s=True),dict(max_octets=False),
                   dict(entetes=(('x','a\r\nb'),)),dict(entetes=(('x','1'),('X','2')))):
            with self.subTest(kw=kw),self.assertRaises(ErreurService):replace(q,**kw)

    def test_job_et_resultat(self):
        j=job();self.assertEqual(decoder(j.dossier)['item_id'],j.item_id)
        for kw in (dict(cree_ms=True),dict(utile_jusqua_ms=j.cree_ms),dict(kind='ORDER'),dict(item_id=None)):
            with self.subTest(kw=kw),self.assertRaises(ErreurService):replace(j,**kw)
        with self.assertRaises(ErreurService):ResultatIA('j',None,0)
        self.assertEqual(ResultatIA('j',None,0,erreur='NEUTRAL').erreur,'NEUTRAL')

    def test_port_transaction_rollback(self):
        m=Memoire()
        def echouer(t):t['api_budget']['x']={};raise ValueError('synthetic')
        with self.assertRaises(ValueError):m.transaction(echouer)
        self.assertFalse(m.tables['api_budget'])

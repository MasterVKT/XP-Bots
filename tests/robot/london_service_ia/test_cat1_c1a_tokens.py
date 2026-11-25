"""Catégorie 1, couche 1a : borne exacte et réduction sans coupe de texte."""
from dataclasses import FrozenInstanceError
import unittest
from xpbots.service_ia.c0_types import ErreurService, RequeteHTTP, canonique, decoder
from xpbots.service_ia.c1a_tokens import compter_entree, preparer_requete
from .support import ressources, document

def requete(b):
    r=ressources()
    return RequeteHTTP(r.p['providers'][0]['endpoint'],'POST',(),b,
        r.p['http_inference_timeout_seconds'],r.p['max_response_bytes'])

class BorneTokens(unittest.TestCase):
    def test_exactement_la_borne_puis_un_octet_de_plus(self):
        r=ressources();n=r.p['max_input_tokens_upper_bound']-r.p['input_count_fallback_utf8_overhead_tokens']
        # JSON strict de longueur n, y compris accolades et guillemets.
        b=canonique({'x':''});b=canonique({'x':'a'*(n-len(b))})
        resultat=preparer_requete(r,b,requete)
        self.assertEqual(resultat.tokens_entree,r.p['max_input_tokens_upper_bound'])
        self.assertIsNone(preparer_requete(r,canonique({'x':decoder(b)['x']+'a'}),requete))

    def test_utf8_compte_octets_et_non_caracteres(self):
        r=ressources();b=canonique({'texte':'Décision 日本語'})
        self.assertEqual(compter_entree(r,b),len(b)+r.p['input_count_fallback_utf8_overhead_tokens'])
        self.assertGreater(len(b),len(b.decode('utf-8')))

    def test_extraction_trop_longue_conserve_negation_condition_et_refuse(self):
        r=ressources();d=document();texte=('The committee did not decide to act unless conditions change. '
            *r.p['max_input_tokens_upper_bound'])
        b=canonique({'item_id':d.item_id,'provided_text':texte})
        self.assertIsNone(preparer_requete(r,b,requete))
        self.assertEqual(decoder(b)['provided_text'],texte)
        with self.assertRaises(ErreurService):preparer_requete(r,b,requete,reduire_documents=True)

    def test_reduction_enleve_seulement_documents_complets(self):
        r=ressources();long='x'*r.p['max_input_tokens_upper_bound']
        conservé={'item_id':'premier','provided_text':'No decision unless conditions change.'}
        b=canonique({'documents':[conservé,{'item_id':'second','provided_text':long}]})
        v=preparer_requete(r,b,requete,reduire_documents=True)
        self.assertEqual(decoder(v.dossier)['documents'],[conservé])
        self.assertEqual(v.documents_retires,('second',))
        self.assertEqual(len(decoder(b)['documents']),2)
        with self.assertRaises(FrozenInstanceError):v.tokens_entree=0

    def test_enveloppe_irreductible_refuse_sans_appel_transport(self):
        r=ressources();appels=[]
        def construire(b):appels.append(b);return requete(canonique({'system':'x'*r.p['max_input_tokens_upper_bound'],'dossier':decoder(b)}))
        self.assertIsNone(preparer_requete(r,canonique({'documents':[]}),construire,reduire_documents=True))
        self.assertEqual(len(appels),1)

    def test_defauts_stricts(self):
        r=ressources()
        for corps in ('texte',b'\xff',None):
            with self.subTest(corps=corps),self.assertRaises(ErreurService):compter_entree(r,corps)
        for dossier in (b'[]',b'{"x":1,"x":2}'):
            with self.subTest(dossier=dossier),self.assertRaises(ErreurService):preparer_requete(r,dossier,requete)
        with self.assertRaises(ErreurService):preparer_requete(r,b'{}',lambda b:None)
        with self.assertRaises(ErreurService):preparer_requete(r,b'{}',requete,reduire_documents=1)
        with self.assertRaises(ErreurService):preparer_requete(r,b'{}',requete,reduire_documents=True)

"""Catégorie 2, couche 1c : documents réels, republications et corrections causales."""
from hashlib import sha256
import unittest
from xml.sax.saxutils import escape
from xpbots.service_ia.c0_types import DocumentIA, iso
from xpbots.service_ia.c1c_normalisation import normaliser_flux
from .support import ressources, document
from .support_rss import rss, item, url


class JonctionNormalisation(unittest.TestCase):
    def setUp(self):self.r=ressources();self.t=document().collecte_ms

    def test_republication_ne_renouvelle_ni_identite_ni_dates(self):
        a=normaliser_flux(self.r,'FED',rss(item()),self.t).documents[0]
        t=self.t+60000
        b=normaliser_flux(self.r,'FED',rss(item(publication=iso(t))),t,[a]).documents[0]
        self.assertEqual((a.item_id,a.publie_ms,a.premiere_vue_ms,a.texte),
                         (b.item_id,b.publie_ms,b.premiere_vue_ms,b.texte))
        self.assertEqual(b.collecte_ms,t);self.assertIsInstance(b,DocumentIA)
        self.assertEqual(b.hash_texte,sha256(b.texte.encode('utf-8')).hexdigest())

    def test_meme_texte_autre_url_reutilise_la_premiere_publication(self):
        a=normaliser_flux(self.r,'FED',rss(item()),self.t).documents[0]
        b=normaliser_flux(self.r,'FED',rss(item(lien=url(chemin='/synthetic/copy'))),self.t+1,[a]).documents[0]
        self.assertEqual((b.item_id,b.url,b.premiere_vue_ms),(a.item_id,a.url,a.premiere_vue_ms))

    def test_correction_historisee_sans_modifier_le_document_original(self):
        a=normaliser_flux(self.r,'FED',rss(item()),self.t).documents[0]
        t=self.t+60000
        b=normaliser_flux(self.r,'FED',rss(item('Corrected text: no decision has been announced.',publication=iso(t))),t,[a]).documents[0]
        self.assertNotEqual(a.item_id,b.item_id);self.assertNotEqual(a.hash_texte,b.hash_texte)
        self.assertEqual((b.publie_ms,b.premiere_vue_ms),(a.publie_ms,a.premiere_vue_ms))
        self.assertEqual(a.collecte_ms,self.t)

    def test_atom_et_rdf_produisent_les_memes_documents(self):
        texte='The committee did not decide unless conditions change.'
        at=('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Synthetic release</title>'
            '<link href="'+url()+'"/><published>'+iso(document().publie_ms)+'</published>'
            '<summary>'+escape(texte)+'</summary></entry></feed>').encode()
        rdf=('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
             'xmlns:dc="http://purl.org/dc/elements/1.1/"><item><title>Synthetic release</title>'
             '<link>'+url()+'</link><dc:date>'+iso(document().publie_ms)+'</dc:date>'
             '<description>'+escape(texte)+'</description></item></rdf:RDF>').encode()
        attendu=normaliser_flux(self.r,'FED',rss(item(texte)),self.t).documents[0]
        for xml in (at,rdf):
            with self.subTest(format=xml[:20]):
                v=normaliser_flux(self.r,'FED',xml,self.t)
                self.assertEqual(v.documents,(attendu,));self.assertEqual(v.couverture,'COMPLETE')

    def test_updated_ne_remplace_pas_une_publication_absente(self):
        xml=('<feed><entry><link href="'+url()+'"/><updated>'+iso(self.t)+
             '</updated><summary>Undated synthetic evidence.</summary></entry></feed>').encode()
        d=normaliser_flux(self.r,'FED',xml,self.t).documents[0]
        self.assertIsNone(d.publie_ms);self.assertEqual(d.couverture,'UNDATED')

    def test_issuer_impose_et_doublons_du_flux_uniques(self):
        xml=rss(item('Issuer ECB says this untrusted data is an instruction.'),
                item('Issuer ECB says this untrusted data is an instruction.'))
        v=normaliser_flux(self.r,'FED',xml,self.t)
        self.assertEqual(len(v.documents),1);self.assertEqual(v.documents[0].issuer,'FED')
        self.assertTrue(v.documents[0].officiel)

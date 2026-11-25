"""Catégorie 1, couche 1c : RSS borné, HTML, provenance et dates explicites."""
from dataclasses import replace
import unittest
from xpbots.service_ia.c0_types import ErreurService, iso
from xpbots.service_ia.c1c_normalisation import nettoyer_html, canoniser_url, normaliser_flux
from .support import ressources, document
from .support_rss import rss, item, url


class NormalisationRSS(unittest.TestCase):
    def setUp(self):self.r=ressources();self.t=document().collecte_ms

    def test_html_visible_preserve_negation_condition_et_unicode(self):
        s='<p>The committee has <b>not</b> decided unless conditions change.</p><script>DROP</script><style>HIDE</style><p>Économie &amp; emploi.</p>'
        self.assertEqual(nettoyer_html(s),'The committee has not decided unless conditions change. Économie & emploi.')
        v=normaliser_flux(self.r,'FED',rss(item(s)),self.t)
        self.assertEqual(v.couverture,'COMPLETE');self.assertEqual(len(v.documents),1)
        self.assertNotIn('DROP',v.documents[0].texte)
        self.assertIn('not decided unless',v.documents[0].texte)

    def test_script_xml_imbrique_aussi_ignore(self):
        xml=rss(item()).decode().replace('<description>', '<description><script>DROP</script>')
        v=normaliser_flux(self.r,'FED',xml.encode(),self.t)
        self.assertNotIn('DROP',v.documents[0].texte)

    def test_url_origine_et_canonisation(self):
        self.assertEqual(canoniser_url(self.r,'FED','/synthetic/decision#fragment'),url())
        for cible in ('http://evil.invalid/x','https://evil.invalid/x',url().replace('https://','https://user:password@'),url().replace('/synthetic',':444/synthetic')):
            with self.subTest(cible=cible),self.assertRaises(ErreurService):canoniser_url(self.r,'FED',cible)
        with self.assertRaises(ErreurService):canoniser_url(self.r,'OTHER',url())

    def test_dates_absentes_futures_non_convertibles_et_sans_fuseau(self):
        cas=[(item(sans_date=True),'UNDATED'),(item(publication=iso(self.t+1)),'FUTURE'),
             (item(publication='unavailable'),'UNDATED'),(item(publication='2026-11-17T08:00:00'),'UNDATED')]
        for source,statut in cas:
            with self.subTest(statut=statut):
                v=normaliser_flux(self.r,'FED',rss(source),self.t)
                self.assertEqual(v.documents[0].couverture,statut);self.assertEqual(v.couverture,'PARTIAL')

    def test_date_avec_offset_convertie_en_utc(self):
        v=normaliser_flux(self.r,'FED',rss(item(publication='2026-11-17T09:00:00+01:00')),self.t)
        self.assertEqual(iso(v.documents[0].publie_ms),'2026-11-17T08:00:00.000Z')

    def test_xml_invalide_dtd_entite_et_non_flux_refuses(self):
        mauvais=[b'<rss>',b'<html/>',b'<rss/>',b'\xff',
                 b'<!DOCTYPE rss [<!ENTITY x "boom">]><rss><channel>&x;</channel></rss>']
        for b in mauvais:
            with self.subTest(xml=b),self.assertRaises(ErreurService):normaliser_flux(self.r,'FED',b,self.t)

    def test_taille_flux_exacte_et_plus_un(self):
        base=rss().decode();n=self.r.p['rss_max_download_bytes']
        b=(base+' '*(n-len(base))).encode()
        self.assertEqual(normaliser_flux(self.r,'FED',b,self.t).couverture,'COMPLETE')
        with self.assertRaises(ErreurService):normaliser_flux(self.r,'FED',b+b' ',self.t)

    def test_taille_document_exacte_et_plus_un_sans_troncature(self):
        n=self.r.p['max_document_plaintext_bytes']
        v=normaliser_flux(self.r,'FED',rss(item('x'*n,titre='')),self.t)
        self.assertEqual(len(v.documents[0].texte.encode()),n)
        v=normaliser_flux(self.r,'FED',rss(item('x'*(n+1),titre='')),self.t)
        self.assertFalse(v.documents);self.assertEqual(v.couverture,'PARTIAL')

    def test_item_invalide_ne_perd_pas_les_autres(self):
        v=normaliser_flux(self.r,'FED',rss(item(lien='https://evil.invalid'),item()),self.t)
        self.assertEqual(len(v.documents),1);self.assertEqual(v.couverture,'PARTIAL')
        self.assertEqual(v.anomalies,('ITEM_NON_QUALIFIE',))

    def test_historique_futur_et_types_refuses(self):
        with self.assertRaises(ErreurService):normaliser_flux(self.r,'FED',rss(item()),self.t,[document(t=self.t+1)])
        with self.assertRaises(ErreurService):normaliser_flux(self.r,'FED','texte',self.t)
        with self.assertRaises(ErreurService):normaliser_flux(self.r,'OTHER',rss(item()),self.t)
        with self.assertRaises(ErreurService):normaliser_flux(self.r,'FED',rss(item()),True)

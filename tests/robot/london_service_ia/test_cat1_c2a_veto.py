"""Catégorie 1 : veto A06, frontières inclusives et causalité du texte transmis."""
import unittest
from dataclasses import replace
from xpbots.service_ia.c0_types import ErreurService, canonique
from xpbots.service_ia.c2a_veto import (CorrespondanceCalendrier, TableAppariement,
    AppariementCalendrier, apparier_calendrier, construire_veto)
from .support import ressources, document, extraction
from .support_calendrier import garde, mapping, appariement, evenement


class Veto(unittest.TestCase):
    def setUp(self):
        self.r=ressources();self.d=document();self.p=self.r.p['providers'][0]['id']
        self.a=appariement(self.r,self.d)
    def veto(self,d=None,a=None,t=None,**kw):
        d=d or self.d
        return construire_veto(self.r,canonique(extraction(d,**kw)).decode(),d,d.texte,
            d.collecte_ms if t is None else t,self.p,a or self.a)
    def test_aucun_veto_discours_historique_condition_acteur_ou_stance(self):
        for kw in ({'event_class':'CENTRAL_BANK_SPEECH'},{'temporal_status':'HISTORICAL'},
                {'temporal_status':'CONDITIONAL'},{'policy_actor':'ECB'},{'stance':'UNCLEAR'}):
            with self.subTest(kw=kw):self.assertIsNone(self.veto(**kw))
    def test_citation_minimum_inclus_et_revalidation(self):
        n=self.r.p['evidence_quote_min_characters_for_veto']
        self.assertIsNone(self.veto(evidence_quote=self.d.texte[:n-1]))
        self.assertIsNotNone(self.veto(evidence_quote=self.d.texte[:n]))
        with self.assertRaises(ErreurService):self.veto(evidence_quote='not present in transmitted text')
    def test_expiration_exacte_sans_prolongation(self):
        fin=self.d.publie_ms+self.r.p['unscheduled_policy_veto_seconds_from_publication']*1000
        self.assertIsNotNone(self.veto(t=fin-1));self.assertIsNone(self.veto(t=fin))
        self.assertEqual(self.veto()['valid_until_utc'],self.veto(t=fin-1)['valid_until_utc'])
    def test_origine_non_officielle_ou_domaine_imite(self):
        self.assertIsNone(self.veto(d=replace(self.d,officiel=False)))
        self.assertIsNone(self.veto(d=replace(self.d,url='https://www.federalreserve.gov.evil.test/release')))
    def test_source_non_datee_partielle_future_documentaire(self):
        for d in (replace(self.d,publie_ms=None,couverture='UNDATED'),replace(self.d,couverture='PARTIAL'),
                replace(self.d,publie_ms=self.d.collecte_ms+1,couverture='FUTURE')):
            with self.subTest(d=d):self.assertIsNone(self.veto(d=d))
    def test_collecte_correction_future_et_publication_incoherente_refusees(self):
        for d in (replace(self.d,collecte_ms=self.d.collecte_ms+1),
                replace(self.d,publie_ms=self.d.premiere_vue_ms+1)):
            with self.assertRaises(ErreurService):self.veto(d=d,t=self.d.collecte_ms)
    def test_calendrier_indisponible_ou_match_ne_donne_pas_veto(self):
        self.assertIsNone(self.veto(a=AppariementCalendrier(False,False,'ABSENT')))
        self.assertIsNone(self.veto(a=replace(self.a,correspondance=True)))
    def test_mapping_structure_stricte_immuable_et_empreinte_ordonnee(self):
        cs=[CorrespondanceCalendrier(3,'ECB','OTHER'),CorrespondanceCalendrier(2,'FED','POLICY_DECISION')]
        a=mapping(self.d,correspondances=cs);cs.clear()
        self.assertEqual(len(a.correspondances),2)
        self.assertEqual(a.empreinte,replace(a,correspondances=tuple(reversed(a.correspondances))).empreinte)
        for cs in ([a.correspondances[0]]*2,[object()]):
            with self.assertRaises(ErreurService):mapping(self.d,correspondances=cs)
        with self.assertRaises(ErreurService):CorrespondanceCalendrier(True,'FED','OTHER')
        with self.assertRaises(ErreurService):AppariementCalendrier(True,False)
    def test_source_derniere_lecture_invalide_prime_sur_cache(self):
        g=garde(self.r,self.d)
        a=apparier_calendrier(self.r,g,mapping(self.d),self.d,self.d.collecte_ms,source_valide=False)
        self.assertFalse(a.valide)
    def test_mapping_futur_incomplet_ou_autre_source_invalide(self):
        g=garde(self.r,self.d)
        for kw in ({'known_at_ms':self.d.collecte_ms+1},{'complete':False},{'fournisseur':'AUTRE'}):
            with self.subTest(kw=kw):
                a=apparier_calendrier(self.r,g,mapping(self.d,**kw),self.d,self.d.collecte_ms,source_valide=True)
                self.assertFalse(a.valide)

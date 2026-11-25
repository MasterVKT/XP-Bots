"""Catégorie 2 : calendrier C05, validateur A05 et oracle A06 réels."""
import unittest
from dataclasses import replace
from reference.llm_contracts import build_policy_event
from robot.outils.fondamental import heure_native, calendrier, octets, table_importance
from xpbots.service_ia.c0_types import canonique, iso
from xpbots.service_ia.c2a_veto import CorrespondanceCalendrier, apparier_calendrier, construire_veto
from .support import ressources, document, extraction
from .support_calendrier import garde, mapping, appariement, evenement


class JonctionVeto(unittest.TestCase):
    def test_egalite_oracle_trois_issuers_fournisseurs_stances(self):
        r=ressources()
        for issuer in (f['issuer'] for f in r.p['feeds']):
            d=document(issuer=issuer);a=appariement(r,d)
            for p in r.p['providers']:
                for stance in ('TIGHTENING','EASING','UNCHANGED'):
                    v=extraction(d,stance=stance)
                    self.assertEqual(construire_veto(r,canonique(v).decode(),d,d.texte,d.collecte_ms,p['id'],a),
                        build_policy_event(v,d.item(d.texte),iso(d.collecte_ms),p['id'],True))
    def test_match_bornes_fermees_et_aucune_heuristique_du_nom(self):
        r=ressources();d=document(publie_ms=document().collecte_ms);dt=r.p['calendar_same_issuer_match_seconds']*1000
        for ecart,attendu in ((-dt,True),(dt,True),(-dt-1000,False),(dt+1000,False)):
            e=evenement(d.publie_ms+ecart,nom='Un nom ne permet pas de classer cet événement')
            a=appariement(r,d,annonces=[e],correspondances=[CorrespondanceCalendrier(e['id_evenement'],d.issuer,r.p['calendar_matching_event_kind'])])
            self.assertTrue(a.valide);self.assertEqual(a.correspondance,attendu)
    def test_discours_et_autre_issuer_pas_match(self):
        r=ressources();d=document();e=evenement(d.collecte_ms)
        for issuer,genre,devise in (('FED','OTHER','USD'),('ECB',r.p['calendar_matching_event_kind'],'EUR')):
            a=appariement(r,d,annonces=[dict(e,devise=devise)],correspondances=[CorrespondanceCalendrier(e['id_evenement'],issuer,genre)])
            self.assertTrue(a.valide);self.assertFalse(a.correspondance)
    def test_high_non_mappe_ou_currency_issuer_inconnus_invalide(self):
        r=ressources();d=document();e=evenement(d.collecte_ms)
        for cs in ([],[CorrespondanceCalendrier(e['id_evenement'],'ECB','OTHER')],
                [CorrespondanceCalendrier(e['id_evenement'],'OTHER',r.p['calendar_matching_event_kind'])],
                [CorrespondanceCalendrier(e['id_evenement'],'FED','SPEECH_INVENTE')]):
            self.assertFalse(appariement(r,d,annonces=[e],correspondances=cs).valide)
    def test_fraicheur_calendrier_limite_inclusive_et_horizon(self):
        r=ressources();d=document();age=r.configuration.technique.commun.news_calendar_max_age_seconds*1000
        g=garde(r,d);m=mapping(d)
        self.assertTrue(apparier_calendrier(r,g,m,d,d.collecte_ms+age,source_valide=True).valide)
        self.assertFalse(apparier_calendrier(r,g,m,d,d.collecte_ms+age+1,source_valide=True).valide)
        g=garde(r,d,fenetre_fin_serveur=heure_native(d.collecte_ms+3600000))
        self.assertFalse(apparier_calendrier(r,g,m,d,d.collecte_ms,source_valide=True).valide)
    def test_recherche_complete_et_version_connue_sans_futur(self):
        r=ressources();d=document();g=garde(r,d);m=mapping(d)
        fut=d.collecte_ms+1000
        self.assertTrue(g.recevoir(octets(calendrier(version=2,export_ms=fut)),fut,table_importance()).acceptee)
        a=apparier_calendrier(r,g,m,d,d.collecte_ms,source_valide=True)
        self.assertEqual(a.version_calendrier,1)
        debut=d.publie_ms-r.p['calendar_same_issuer_match_seconds']*1000+1000
        g=garde(r,d,fenetre_debut_serveur=heure_native(debut))
        self.assertFalse(apparier_calendrier(r,g,m,d,d.collecte_ms,source_valide=True).valide)

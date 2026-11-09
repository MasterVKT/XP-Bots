"""Catégorie 2, couche 3 : bloc réel, oracle partiel et préfixes de réception."""
import unittest
from robot.outils.contexte_ia import T,evenement,octets,parametres,snapshot
from reference.llm_contracts import overlay_decision
from xpbots.contexte_ia.c0_types import PolitiqueVeto
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.noyau.c0a_temps import instant_vers_iso


class TestJonctionContexte(unittest.TestCase):
    def test_matrice_oracle_reel_sur_0_a_3(self):
        mauvais=snapshot();mauvais['sha256']='0'*64
        for s,t in ((snapshot(),T+120000),(mauvais,T+120000),({},T+120000),
            (snapshot(),T+119999),(snapshot(),T+210000),(snapshot(),T+210001),
            (snapshot(sequence=0),T+120000),(snapshot(evenements=[]),T+120000),
            (snapshot(evenements=[evenement(reason_code='AUTRE')]),T+120000)):
            with self.subTest(s=s,t=t):
                l=LecteurContexte(parametres(),PolitiqueVeto(True));l.recevoir(octets(s),t)
                self.assertEqual(l.evaluer('EURUSD',t).etat.value,overlay_decision(s,instant_vers_iso(t),'EURUSD'))

    def test_oracle_cache_heartbeat_vide_recul_et_corruption(self):
        l=LecteurContexte(parametres(),PolitiqueVeto(True));s=snapshot(sequence=2)
        l.recevoir(octets(s),T+120000)
        for suivant,t in ((snapshot(sequence=3,genere=T+150000,evenements=[]),T+150000),
            (snapshot(sequence=1,genere=T+180000),T+180000),({},T+600000),({},T+900000)):
            l.recevoir(octets(suivant),t)
            attendu=overlay_decision(suivant,instant_vers_iso(t),'EURUSD',last_sequence=3,
                cached_events=s['payload']['events'])
            self.assertEqual(l.evaluer('EURUSD',t).etat.value,attendu)

    def test_oracle_garde_reelle_et_financiere(self):
        for live in (False,True):
            for valide in (False,True):
                l=LecteurContexte(parametres(),PolitiqueVeto(True,live,valide));s=snapshot()
                l.recevoir(octets(s),T+120000)
                self.assertEqual(l.evaluer('EURUSD',T+120000).etat.value,
                    overlay_decision(s,instant_vers_iso(T+120000),'EURUSD',live=live,financial_gate_passed=valide))

    def test_prefixe_et_reprise_ne_retroagissent_pas(self):
        l=LecteurContexte(parametres(),PolitiqueVeto(True));l.recevoir(octets(snapshot()),T+120000)
        l.recevoir(octets(snapshot(sequence=2,genere=T+150000,
            evenements=[evenement(event_id='gbp',canonical_symbols=['GBPUSD'])])),T+150000)
        r=LecteurContexte(parametres(),PolitiqueVeto(True),l.etat)
        self.assertEqual(r.evaluer('GBPUSD',T+149999).etat.value,'NEUTRAL')
        self.assertEqual(r.evaluer('GBPUSD',T+150000).etat.value,'BLOCK')
        self.assertEqual(r.evaluer('EURUSD',T+119999).etat.value,'NEUTRAL')

    def test_liste_mixte_rejetee_contrairement_oracle_partiel(self):
        s=snapshot(evenements=[evenement(),{**evenement(event_id='bad'),'extra':True}])
        self.assertEqual(overlay_decision(s,instant_vers_iso(T+120000),'EURUSD'),'BLOCK')
        l=LecteurContexte(parametres(),PolitiqueVeto(True))
        self.assertFalse(l.recevoir(octets(s),T+120000).acceptee)
        self.assertEqual(l.evaluer('EURUSD',T+120000).etat.value,'NEUTRAL')

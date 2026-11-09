"""Catégorie 2, couche 2 : vrais snapshots, preuve de reprise et préfixes temporels."""
import unittest
from robot.outils.contexte_ia import T,evenement,octets,parametres,snapshot
from reference.llm_contracts import overlay_decision
from xpbots.noyau.c0a_temps import instant_vers_iso
from xpbots.contexte_ia.c2_cache import CacheVetos


class TestJonctionCache(unittest.TestCase):
    def test_prefixes_et_connaissance_reelle(self):
        complet=CacheVetos(parametres());prefixe=CacheVetos(parametres())
        a=octets(snapshot());b=octets(snapshot(sequence=2,genere=T+150000,
            evenements=[evenement(event_id='e2',canonical_symbols=['GBPUSD'])]))
        complet.recevoir(a,T+120000);complet.recevoir(b,T+150000)
        for t in (T+119999,T+120000,T+149999,T+150000):
            if t==T+120000:prefixe.recevoir(a,t)
            if t==T+150000:prefixe.recevoir(b,t)
            for symbole in ('EURUSD','GBPUSD'):
                self.assertEqual(complet.consulter(symbole,t),prefixe.consulter(symbole,t))

    def test_cache_et_reference_jusqu_a_echeance_sans_snapshot_frais(self):
        c=CacheVetos(parametres());s=snapshot();c.recevoir(octets(s),T+120000)
        for t in (T+120000,T+600000,T+899999,T+900000):
            attendu=overlay_decision({},instant_vers_iso(t),'EURUSD',cached_events=s['payload']['events'])
            self.assertEqual('BLOCK' if c.consulter('EURUSD',t) else 'NEUTRAL',attendu)

    def test_reprise_avec_heartbeat_vide_n_oublie_pas_preuve(self):
        c=CacheVetos(parametres());c.recevoir(octets(snapshot()),T+120000)
        c.recevoir(octets(snapshot(sequence=2,genere=T+150000,evenements=[])),T+150000)
        c.avancer(T+600000)
        r=CacheVetos(parametres(),c.etat)
        self.assertEqual(r.derniere_sequence,2)
        self.assertTrue(r.consulter('EURUSD',T+600000))
        self.assertEqual(r.consulter('EURUSD',T+900000),())
        self.assertEqual(r.etat.scelles[0].connu_ms,T+120000)

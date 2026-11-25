"""Catégorie 2, couche 1f : oracle A10 et lecteur/cache IA réels."""
import unittest
from reference.llm_contracts import make_snapshot
from robot.outils.contexte_ia import evenement
from xpbots.contexte_ia.c0_types import PolitiqueVeto, charger_parametres
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.service_ia.c0_types import decoder, iso
from xpbots.service_ia.c1f_snapshot import fabriquer_snapshot, EcrivainSnapshot
from .support import ressources, document, Memoire


class JonctionSnapshot(unittest.TestCase):
    def test_egalite_oracle_sur_sequences_et_evenements(self):
        r=ressources();t=document().collecte_ms;e=evenement(debut=t,fin=t+r.p['unscheduled_policy_veto_seconds_from_publication']*1000)
        for seq in (1,2,100):
            for events in ([],[e]):
                with self.subTest(seq=seq,events=events):
                    self.assertEqual(decoder(fabriquer_snapshot(r,seq,t,events)),make_snapshot(seq,iso(t),events))

    def test_lecteur_reel_garde_fenetre_originale_malgre_heartbeat(self):
        r=ressources();t=document().collecte_ms;fin=t+r.p['unscheduled_policy_veto_seconds_from_publication']*1000
        e=evenement(debut=t,fin=fin);m=Memoire();lecteur=LecteurContexte(charger_parametres(r.configuration),PolitiqueVeto(True))
        publication=EcrivainSnapshot(r,m,lambda b:None)
        a=publication.publier(t,[e]);self.assertTrue(lecteur.recevoir(a.octets,t).acceptee)
        self.assertEqual(lecteur.evaluer('EURUSD',t).etat.value,'BLOCK')
        b=publication.publier(fin-1,[e]);self.assertTrue(lecteur.recevoir(b.octets,fin-1).acceptee)
        self.assertEqual(lecteur.evaluer('EURUSD',fin-1).etat.value,'BLOCK')
        self.assertEqual(lecteur.evaluer('EURUSD',fin).etat.value,'NEUTRAL')

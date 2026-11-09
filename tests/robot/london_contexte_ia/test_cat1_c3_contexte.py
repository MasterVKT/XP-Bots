"""Catégorie 1, couche 3 : politique explicite, port canonique et journal causal."""
from dataclasses import replace
import json
import unittest
from robot.outils.contexte_ia import T,evenement,octets,parametres,snapshot
from xpbots.contexte_ia.c0_types import ErreurContexte,PolitiqueVeto
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.execution.c0b_controles import LecteurContexteIA
from xpbots.noyau.c1c_domaine import ContexteIA,DecisionContexteIA


class TestContexte(unittest.TestCase):
    def lecteur(self,politique=None,p=None):
        l=LecteurContexte(p or parametres(),politique or PolitiqueVeto(True))
        l.recevoir(octets(snapshot()),T+120000);return l

    def test_port_reel_et_decision_canonique(self):
        l=self.lecteur();self.assertIsInstance(l,LecteurContexteIA)
        self.assertEqual(l.evaluer('EURUSD',T+120000),DecisionContexteIA(ContexteIA.BLOCK,'evenement_1'))
        self.assertEqual(l.evaluer('GBPUSD',T+120000),DecisionContexteIA(ContexteIA.NEUTRAL))

    def test_bras_reference_neutre_meme_avec_cache(self):
        l=self.lecteur(PolitiqueVeto(False));self.assertEqual(l.evaluer('EURUSD',T+120000).etat,ContexteIA.NEUTRAL)
        self.assertEqual(len(l.description('EURUSD',T+120000)['vetos']),1)

    def test_reel_exige_validation_financiere(self):
        for valide,attendu in ((False,ContexteIA.NEUTRAL),(True,ContexteIA.BLOCK)):
            l=self.lecteur(PolitiqueVeto(True,True,valide))
            self.assertEqual(l.evaluer('EURUSD',T+120000).etat,attendu)

    def test_politique_chargee_et_papier(self):
        l=self.lecteur(PolitiqueVeto(True,True,False),replace(parametres(),validation_financiere_requise=False))
        self.assertEqual(l.evaluer('EURUSD',T+120000).etat,ContexteIA.BLOCK)
        self.assertEqual(self.lecteur().evaluer('EURUSD',T+120000).etat,ContexteIA.BLOCK)

    def test_expiration_propre_apres_snapshot_perime(self):
        l=self.lecteur();l.avancer(T+600000)
        self.assertEqual(l.evaluer('EURUSD',T+899999).etat,ContexteIA.BLOCK)
        self.assertEqual(l.prochaine_echeance_ms(T+600000),T+900000)
        l.avancer(T+900000)
        self.assertEqual(l.evaluer('EURUSD',T+900000).etat,ContexteIA.NEUTRAL)
        self.assertIsNone(l.prochaine_echeance_ms(T+900000))

    def test_absent_corrompu_sans_effacer_cache(self):
        l=LecteurContexte(parametres(),PolitiqueVeto(True))
        self.assertFalse(l.recevoir(None,T+120000).acceptee)
        self.assertEqual(l.evaluer('EURUSD',T+120000).etat,ContexteIA.NEUTRAL)
        l.recevoir(octets(snapshot()),T+120000);l.recevoir(b'{',T+120001)
        self.assertEqual(l.evaluer('EURUSD',T+120001).etat,ContexteIA.BLOCK)

    def test_reprise_exacte_sans_renouvellement(self):
        l=self.lecteur();l.avancer(T+600000)
        r=LecteurContexte(parametres(),l.politique,l.etat)
        self.assertEqual(r.etat,l.etat)
        self.assertEqual(r.description('EURUSD',T+600000),l.description('EURUSD',T+600000))
        self.assertEqual(r.evaluer('EURUSD',T+900000).etat,ContexteIA.NEUTRAL)

    def test_description_json_independante_et_sans_futur(self):
        l=self.lecteur();d=l.description('EURUSD',T+120000)
        self.assertEqual(d['vetos'][0]['connu_ms'],T+120000)
        self.assertEqual(d['dernier_snapshot']['reception_ms'],T+120000)
        self.assertEqual(d['vetos'][0]['sha256_preuve'],snapshot()['sha256'])
        json.dumps(d,allow_nan=False);d['vetos'].clear()
        self.assertEqual(len(l.description('EURUSD',T+120000)['vetos']),1)
        avant=l.description('EURUSD',T+119999)
        self.assertEqual((avant['decision'],avant['vetos'],avant['dernier_snapshot']),('NEUTRAL',[],None))

    def test_plusieurs_vetos_choix_id_stable(self):
        l=LecteurContexte(parametres(),PolitiqueVeto(True))
        l.recevoir(octets(snapshot(evenements=[evenement(event_id='z'),evenement(event_id='a')])),T+120000)
        self.assertEqual(l.evaluer('EURUSD',T+120000).evenement,'a')

    def test_appels_invalides_meme_en_neutre(self):
        with self.assertRaises(ErreurContexte):LecteurContexte(parametres(),None)
        l=self.lecteur(PolitiqueVeto(False))
        for sym,t in (('INCONNU',T),(True,T),('EURUSD',True)):
            with self.assertRaises(ErreurContexte):l.evaluer(sym,t)

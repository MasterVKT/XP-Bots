"""Coutures de décision : motifs C09, signal, résultat technique, clé d'intention, issues, contrôles."""
import unittest
from decimal import Decimal

from robot.outils import motifs_c09_de_la_specification, signal_valide
from xpbots.noyau.decisions import (MOTIFS_COMPLEMENTAIRES, CleIntention, DecisionContexteIA,
                                    DecisionFondamentale, DecisionInvalide, EtatContexteIA, MotifRefus, Refuse,
                                    Rempli, ResultatTechnique, Sens)


class TestMotifs(unittest.TestCase):
    def test_liste_fermee_identique_a_c09_plus_deux_complements(self):
        attendus = motifs_c09_de_la_specification() + [m.value for m in MOTIFS_COMPLEMENTAIRES]
        self.assertEqual([m.value for m in MotifRefus], attendus)
        self.assertEqual(len(set(attendus)), len(attendus))

    def test_complements_documentes(self):
        self.assertEqual({m.value for m in MOTIFS_COMPLEMENTAIRES}, {'AI_CONTEXT_VETO', 'ENVIRONMENT_NOT_READY'})


class TestSignal(unittest.TestCase):
    def test_signal_s01_5(self):
        signal = signal_valide()
        self.assertEqual(signal.sens * (float(signal.cloture_bid) - signal.b_sl) > 0, True)
        with self.assertRaises(TypeError):
            signal.etat_detecteur['age'] = 4

    def test_b_sl_du_cote_protecteur(self):
        with self.assertRaises(DecisionInvalide):
            signal_valide(b_sl=1.10005)
        with self.assertRaises(DecisionInvalide):
            signal_valide(b_sl=1.10000)
        signal_valide(sens=Sens.VENTE, b_sl=1.10055)
        with self.assertRaises(DecisionInvalide):
            signal_valide(sens=Sens.VENTE, b_sl=1.09945)

    def test_valeurs_strictes(self):
        for changement in ({'a_t': 0.0}, {'a_t': 5}, {'cloture_bid': 1.1}, {'multiple_objectif': 0.0},
                           {'sens': 1}, {'cloture_ms': 1.0}, {'strategie': ''}, {'b_sl': float('nan')}):
            with self.subTest(changement=changement), self.assertRaises(DecisionInvalide):
                signal_valide(**changement)


class TestResultatEtIssues(unittest.TestCase):
    def test_exactement_un_signal_ou_un_motif(self):
        ResultatTechnique(None, MotifRefus.NO_SETUP)
        ResultatTechnique(signal_valide(), None)
        with self.assertRaises(DecisionInvalide):
            ResultatTechnique(None, None)
        with self.assertRaises(DecisionInvalide):
            ResultatTechnique(signal_valide(), MotifRefus.NO_SETUP)
        with self.assertRaises(DecisionInvalide):
            ResultatTechnique(None, 'NO_SETUP')

    def test_cle_intention_c08(self):
        cle = CleIntention.du_signal('dep-1', signal_valide())
        self.assertEqual(cle.en_json(), {'deployment_id': 'dep-1', 'strategie': 'EMA_V3', 'symbole': 'EURUSD',
                                         'cloture_utc': '2026-11-04T08:15:00.000Z', 'sens': 1})
        self.assertEqual(cle.texte(), CleIntention.du_signal('dep-1', signal_valide()).texte())
        self.assertNotEqual(cle.texte(), CleIntention.du_signal('dep-2', signal_valide()).texte())

    def test_issues(self):
        Rempli(Decimal('0.1'), Decimal('1.10010'), 1)
        Refuse(MotifRefus.FUNDAMENTAL_INVALID, 1)
        with self.assertRaises(DecisionInvalide):
            Rempli(Decimal('0'), Decimal('1.1'), 1)
        with self.assertRaises(DecisionInvalide):
            Refuse('FUNDAMENTAL_INVALID', 1)


class TestDecisionsDeControle(unittest.TestCase):
    def test_decision_fondamentale(self):
        DecisionFondamentale(False, MotifRefus.NEWS_WINDOW)
        DecisionFondamentale(True, None, {'direction': 'ANY', 'risk_state': 'ALLOW'}, 'TECHNICAL_CONTROL_NEUTRAL')
        with self.assertRaises(DecisionInvalide):
            DecisionFondamentale(True, MotifRefus.NEWS_WINDOW)
        with self.assertRaises(DecisionInvalide):
            DecisionFondamentale(False, None)
        with self.assertRaises(DecisionInvalide):
            DecisionFondamentale(False, MotifRefus.SPREAD_CAP)

    def test_contexte_ia_sans_etat_allow(self):
        self.assertEqual({e.value for e in EtatContexteIA}, {'BLOCK', 'NEUTRAL'})
        DecisionContexteIA(EtatContexteIA.BLOCK, 7, ('evt-1',))
        with self.assertRaises(DecisionInvalide):
            DecisionContexteIA('NEUTRAL')
        with self.assertRaises(DecisionInvalide):
            DecisionContexteIA(EtatContexteIA.NEUTRAL, evenements=['evt-1'])


if __name__ == '__main__':
    unittest.main()

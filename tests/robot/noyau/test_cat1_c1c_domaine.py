"""Catégorie 1, couche 1c (domaine) : motifs fermés, détails énumérés, signaux, intentions, issues, décisions."""
import hashlib
import unittest

from robot.outils.specification import MOTIFS_HORS_C09, motifs_c09, table_des_motifs_document_01
from xpbots.noyau.c1c_domaine import (DETAILS_ENUMERES, MOTIFS_A_DETAIL_LIBRE, AbsenceDeSignal, CauseCloture,
                                      CleIntention, ContexteIA, DecisionContexteIA, DecisionFondamentale,
                                      ErreurDomaine, Issue, Motif, NatureIssue, Sens, SignalTechnique, verifier_motif)

CLE = CleIntention('dep-1', 'LONDON_V3', 'EURUSD', 1_800_000, Sens.ACHAT)


class TestMotifs(unittest.TestCase):
    def test_motifs_fermes_derives_de_la_specification(self):
        self.assertEqual({m.value for m in Motif}, set(motifs_c09()) | set(MOTIFS_HORS_C09))
        self.assertEqual(len(Motif), 22)
        self.assertEqual(set(DETAILS_ENUMERES) | MOTIFS_A_DETAIL_LIBRE, set(Motif))

    def test_details_identiques_au_tableau_du_document_01(self):
        cites: dict[str, set[str]] = {}
        for motifs, details in table_des_motifs_document_01():
            for motif in motifs:
                if motif in Motif.__members__:
                    cites.setdefault(motif, set()).update(details)
        for motif, admis in DETAILS_ENUMERES.items():
            with self.subTest(motif=motif):
                self.assertEqual(admis, frozenset(cites.get(motif.value, ())))
        for motif in MOTIFS_A_DETAIL_LIBRE:
            self.assertIn(motif.value, cites)

    def test_verification(self):
        self.assertEqual(verifier_motif('NO_SETUP', 'PAS_DE_CASSURE'), (Motif.NO_SETUP, 'PAS_DE_CASSURE'))
        self.assertEqual(verifier_motif(Motif.STOP_TOO_WIDE, None), (Motif.STOP_TOO_WIDE, None))
        self.assertEqual(verifier_motif('ENVIRONMENT_NOT_READY', 'tick_size'), (Motif.ENVIRONMENT_NOT_READY, 'tick_size'))
        self.assertEqual(verifier_motif('AI_CONTEXT_VETO', 'evt:2026-07-15:fed-1')[1], 'evt:2026-07-15:fed-1')
        for motif, detail in (('INCONNU', None), ('NO_SETUP', None), ('NO_SETUP', 'TROU_ACTIF'), ('SPREAD_CAP', 'X'),
                              ('ENVIRONMENT_NOT_READY', None), ('ENVIRONMENT_NOT_READY', 'champ vide'),
                              ('AI_CONTEXT_VETO', ''), ('SIGNAL_EXPIRED', 'NO_SETUP')):
            with self.subTest(motif=motif, detail=detail), self.assertRaises(ErreurDomaine):
                verifier_motif(motif, detail)


class TestSensEtCle(unittest.TestCase):
    def test_sens(self):
        self.assertEqual((Sens.ACHAT.signe, Sens.VENTE.signe, Sens.ACHAT.oppose()), (1, -1, Sens.VENTE))
        self.assertEqual(Sens('VENTE'), Sens.VENTE)

    def test_cle_intention(self):
        self.assertEqual(CLE.texte(), 'dep-1|LONDON_V3|EURUSD|1800000|ACHAT')
        self.assertEqual(CLE.empreinte(12), hashlib.sha256(CLE.texte().encode()).hexdigest()[:12])
        self.assertEqual(CleIntention('dep-1', 'LONDON_V3', 'EURUSD', 1_800_000, 'ACHAT'), CLE)
        for arguments in (('', 'S', 'X', 0, 'ACHAT'), ('d|x', 'S', 'X', 0, 'ACHAT'), ('d', 'S', 'X', -1, 'ACHAT'),
                          ('d', 'S', 'X', 0, 'LONG')):
            with self.subTest(arguments=arguments), self.assertRaises(ErreurDomaine):
                CleIntention(*arguments)
        for longueur in (0, 65, True):
            with self.subTest(longueur=longueur), self.assertRaises(ErreurDomaine):
                CLE.empreinte(longueur)


class TestResultatsTechniques(unittest.TestCase):
    def test_signal(self):
        signal = SignalTechnique('LONDON_V3', 'EURUSD', 1_800_000, 'VENTE', 1.1, 0.0005, 1.101, 2, {'range': [1, 2]})
        self.assertEqual((signal.sens, signal.multiple_objectif, signal.contexte['range']), (Sens.VENTE, 2.0, (1, 2)))
        with self.assertRaises(TypeError):
            signal.contexte['range'] = 3
        for changement in ({'stop_technique': 1.1}, {'atr_reference': 0}, {'multiple_objectif': -1},
                           {'cloture_prix': float('nan')}, {'contexte': {'x': float('inf')}}, {'contexte': {1: 'a'}},
                           {'contexte': {'x': object()}}, {'sens': 'HAUT'}):
            champs = dict(strategie='S', symbole='EURUSD', cloture_ms=0, sens='ACHAT', cloture_prix=1.1,
                          atr_reference=0.001, stop_technique=1.09, multiple_objectif=2.0)
            champs.update(changement)
            with self.subTest(changement=changement), self.assertRaises(ErreurDomaine):
                SignalTechnique(**champs)

    def test_absence_de_signal(self):
        absence = AbsenceDeSignal('LONDON_V3', 'EURUSD', 0, 'OUTSIDE_SESSION', 'HORS_FENETRE')
        self.assertIs(absence.motif, Motif.OUTSIDE_SESSION)
        with self.assertRaises(ErreurDomaine):
            AbsenceDeSignal('LONDON_V3', 'EURUSD', 0, 'OUTSIDE_SESSION', 'TROU_ACTIF')


class TestIssuesEtDecisions(unittest.TestCase):
    def test_issues(self):
        self.assertIs(Issue(CLE, 'REMPLIE', 10).nature, NatureIssue.REMPLIE)
        self.assertIs(Issue(CLE, 'REFUSEE', 10, 'MARGIN_REJECT', 'MARGE_TIERS').motif, Motif.MARGIN_REJECT)
        self.assertEqual(Issue(CLE, 'EXPIREE', 10, 'SIGNAL_EXPIRED', 'SPREAD_CAP').detail, 'SPREAD_CAP')
        self.assertIs(Issue(CLE, 'CLOTUREE', 10, cause='TAKE_PROFIT').cause, CauseCloture.TAKE_PROFIT)
        self.assertIs(Issue(CLE, 'CLOTUREE', 10, 'DAILY_LOSS_LOCK', cause='GARDE_QUOTIDIENNE').motif, Motif.DAILY_LOSS_LOCK)
        for arguments in ((CLE, 'REMPLIE', 10, 'NO_SETUP', 'PAS_DE_CASSURE'), (CLE, 'REFUSEE', 10),
                          (CLE, 'REFUSEE', 10, 'SIGNAL_EXPIRED', 'ENTRY_GAP'), (CLE, 'EXPIREE', 10, 'SPREAD_CAP'),
                          (CLE, 'CLOTUREE', 10), (CLE, 'PERDUE', 10), ('cle', 'REMPLIE', 10), (CLE, 'REMPLIE', -5),
                          (CLE, 'CLOTUREE', 10, None, 'X', 'TAKE_PROFIT'), (CLE, 'CLOTUREE', 10, None, None, 'TRAILING')):
            with self.subTest(arguments=arguments[1:]), self.assertRaises(ErreurDomaine):
                Issue(*arguments)

    def test_decision_fondamentale(self):
        self.assertTrue(DecisionFondamentale(True).admise)
        flatten = DecisionFondamentale(False, 'FUNDAMENTAL_DIRECTION', 'RISK_STATE_FLATTEN', True)
        self.assertTrue(flatten.cloture_obligatoire)
        for arguments in ((True, 'NEWS_WINDOW', 'ANNONCE_HIGH'), (True, None, None, True), (False,),
                          (False, 'MARGIN_REJECT', 'MARGE_TIERS'), ('oui',)):
            with self.subTest(arguments=arguments), self.assertRaises(ErreurDomaine):
                DecisionFondamentale(*arguments)

    def test_contexte_ia_jamais_autorisant(self):
        self.assertEqual({c.value for c in ContexteIA}, {'BLOCK', 'NEUTRAL'})
        self.assertEqual(DecisionContexteIA('BLOCK', 'fed-2026-1').motif_et_detail(), (Motif.AI_CONTEXT_VETO, 'fed-2026-1'))
        self.assertIsNone(DecisionContexteIA('NEUTRAL').motif_et_detail())
        for arguments in (('ALLOW',), ('BLOCK',), ('NEUTRAL', 'evt')):
            with self.subTest(arguments=arguments), self.assertRaises(ErreurDomaine):
                DecisionContexteIA(*arguments)


if __name__ == '__main__':
    unittest.main()

"""Catégorie 2, couche 1c (domaine) : jonction sur le bloc réel {0a, 1c}, par chemins représentatifs."""
import unittest

from xpbots.noyau.c0a_temps import aligner, instant_depuis_iso, instant_vers_iso
from xpbots.noyau.c1c_domaine import CleIntention, ErreurDomaine, Issue, Sens, SignalTechnique


class TestJonctionDomaine(unittest.TestCase):
    def test_cle_d_intention_sur_une_cloture_alignee(self):
        cloture = aligner(instant_depuis_iso('2026-07-15T08:29:59.999Z'), 900_000) + 900_000
        cle = CleIntention('dep', 'LONDON_V3', 'EURUSD', cloture, Sens.ACHAT)
        self.assertEqual(instant_vers_iso(cle.cloture_ms), '2026-07-15T08:30:00.000Z')
        self.assertEqual(len(cle.empreinte(16)), 16)
        self.assertNotEqual(cle.empreinte(16), CleIntention('dep', 'LONDON_V3', 'EURUSD', cloture, 'VENTE').empreinte(16))

    def test_issue_horodatee_apres_le_signal(self):
        cloture = instant_depuis_iso('2026-07-15T08:30:00Z')
        signal = SignalTechnique('LONDON_V3', 'EURUSD', cloture, Sens.ACHAT, 1.1, 0.0004, 1.0985, 2.0)
        cle = CleIntention('dep', signal.strategie, signal.symbole, signal.cloture_ms, signal.sens)
        issue = Issue(cle, 'EXPIREE', cloture + 5_000, 'SIGNAL_EXPIRED', 'AUCUNE_COTATION')
        self.assertEqual(issue.instant_ms - signal.cloture_ms, 5_000)
        with self.assertRaises(ErreurDomaine):
            Issue(cle, 'REMPLIE', instant_depuis_iso('2026-07-15T08:30:00Z') - 10**15)


if __name__ == '__main__':
    unittest.main()

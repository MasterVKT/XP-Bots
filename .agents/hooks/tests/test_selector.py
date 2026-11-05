"""Deterministic selector: data-driven cases, keyword forms, normalization and full routing."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REAL_ROOT  # noqa: E402

sys.path.insert(0, str(REAL_ROOT / '.agents/skills/xp-bots-request-skill-orchestrator/scripts'))
import select_skills  # noqa: E402

RULES = select_skills.load_rules()


def custom(keywords):
    rules = json.loads(json.dumps(RULES))
    rules['rules'] = [{'skill': 'xp-bots-demo', 'keywords': keywords}]
    rules['fallbacks'] = []
    return rules


class SelectorTests(unittest.TestCase):
    def test_all_data_cases_pass(self):
        self.assertEqual(select_skills.run_cases(), [])

    def test_compatibility_interface_returns_list(self):
        selection = select_skills.select('vérifier le repli EMA15/25/50 et RSI14')
        self.assertIsInstance(selection, list)
        self.assertEqual(selection[0], 'xp-bots-request-skill-orchestrator')
        self.assertEqual(selection[-1], 'xp-bots-completion-audit')

    def test_three_keyword_forms(self):
        self.assertIn('xp-bots-demo', select_skills.select('le module de risque', custom(['risque'])))
        self.assertIn('xp-bots-demo', select_skills.select('refactorisation du moteur', custom(['refactor*'])))
        self.assertIn('xp-bots-demo', select_skills.select('déployer mon-service vite', custom(['mon-service'])))
        self.assertIn('xp-bots-demo', select_skills.select("la garde d'annonces", custom(["garde d'annonces"])))
        self.assertNotIn('xp-bots-demo', select_skills.select('mon service', custom(['mon-service'])))

    def test_compound_keyword_is_never_a_single_word(self):
        rules = custom(['mon-service'])
        self.assertFalse(select_skills.analyze('mon', rules)['matched'])
        self.assertFalse(select_skills.analyze('service', rules)['matched'])

    def test_accents_and_case_are_normalized(self):
        rules = custom(['spécification'])
        self.assertIn('xp-bots-demo', select_skills.select('SPECIFICATION', rules))
        self.assertIn('xp-bots-demo', select_skills.select('Spécification', rules))

    def test_no_match_signal_and_useful_words(self):
        result = select_skills.analyze('bonjour')
        self.assertTrue(result['no_match'])
        self.assertEqual(result['useful_words'], 1)

    def test_fallback_cancelled_by_present_skill(self):
        result = select_skills.analyze('améliorer le robot EMA15/25/50')
        self.assertNotIn('xp-bots-specification-consistency', result['fallbacks'])
        result = select_skills.analyze('améliorer le robot')
        self.assertIn('xp-bots-specification-consistency', result['fallbacks'])

    def test_every_skill_is_routed_and_tested(self):
        known = {entry.name for entry in (REAL_ROOT / '.agents/skills').iterdir() if (entry / 'SKILL.md').is_file()}
        failures = select_skills.run_cases()
        self.assertEqual(failures, [])
        routed = {rule['skill'] for rule in RULES['rules']} | set(RULES['lifecycle_skills'])
        self.assertEqual(known - routed, set())

    def test_unrouted_skill_is_detected(self):
        rules = json.loads(json.dumps(RULES))
        rules['rules'] = [rule for rule in rules['rules'] if rule['skill'] != 'xp-bots-london-breakout']
        failures = select_skills.run_cases(rules)
        self.assertTrue(any('skill non routée : xp-bots-london-breakout' in item for item in failures))

    def test_documentation_request_does_not_select_everything(self):
        selection = select_skills.select('mets à jour la documentation du README')
        self.assertLessEqual(len(selection), 5)

    def test_case_file_failures_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'cases.json'
            path.write_text(json.dumps({'cases': [{'request': 'bonjour', 'includes': ['xp-bots-london-breakout']}]}),
                            encoding='utf-8')
            failures = select_skills.run_cases(cases_path=path)
        self.assertTrue(any('absent' in item for item in failures))


if __name__ == '__main__':
    unittest.main()

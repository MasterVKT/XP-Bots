"""Gap ledger and skill generator, always on a temporary copy of the repository."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import RepoCopy, clean_env  # noqa: E402

LEDGER = '.agents/skills/xp-bots-skill-gap-detector/scripts/skill_gap_ledger.py'
CREATE = '.agents/skills/xp-bots-skill-gap-detector/scripts/create_skill.py'
SELECT = '.agents/skills/xp-bots-request-skill-orchestrator/scripts/select_skills.py'
BODY = """# Journal analytique des trades

## Workflow

1. Lire la section C09 des deux spécifications et lister les champs du journal.
2. Rejouer `python tools/verify_project.py` après toute modification.

## Garde-fous

- Ne jamais recopier une valeur figée de `config/`.
"""


class LedgerGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.repo = RepoCopy(git=False)
        self.draft = self.repo.state / 'draft.md'
        self.draft.write_text(BODY, encoding='utf-8')

    def tearDown(self):
        self.repo.close()

    def run_script(self, script, *args):
        result = self.repo.python(script, *args)
        text = result.stdout.decode('utf-8')
        try:
            return result.returncode, json.loads(text)
        except ValueError:
            return result.returncode, text

    def create(self, *extra, name='xp-bots-trade-journal-analysis', keywords='journal analytique,analyse des trades'):
        return self.run_script(CREATE, '--name', name, '--description',
                               "Analyse du journal des trades C09 de XP-Bots. Utiliser pour analyser les trades clos.",
                               '--keywords', keywords, '--catalog', 'analyse du journal des trades C09',
                               '--example-request', 'fais une analyse des trades du journal analytique',
                               '--body-file', str(self.draft), *extra)

    def snapshot(self):
        return {path: path.read_bytes() for path in self.repo.root.rglob('*') if path.is_file()}

    def test_record_promotes_at_second_occurrence(self):
        # The copy carries the real ledger: count relative to its initial content, never assume it is empty.
        initial = len(self.repo.read_json('.agents/skill-gap-ledger.json')['entries'])
        code, entry = self.run_script(LEDGER, 'record', '--label', 'Analyse des slippages réels', '--evidence', 'p1')
        self.assertEqual((code, entry['decision'], entry['occurrences']), (0, 'consignee', 1))
        self.assertEqual(entry['id'], 'analyse-des-slippages-reels')
        self.assertEqual(entry['label'], 'Analyse des slippages réels')
        code, entry = self.run_script(LEDGER, 'record', '--label', 'Analyse des slippages réels', '--evidence', 'p2')
        self.assertEqual((entry['decision'], entry['occurrences']), ('promue', 2))
        code, shown = self.run_script(LEDGER, 'show', '--id', 'analyse-des-slippages-reels')
        self.assertEqual(shown['evidence'], ['p1', 'p2'])
        code, listed = self.run_script(LEDGER, 'list')
        self.assertEqual(len(listed), initial + 1)
        self.assertEqual([item['id'] for item in listed].count('analyse-des-slippages-reels'), 1)

    def test_decision_outside_vocabulary_refused(self):
        self.run_script(LEDGER, 'record', '--label', 'X')
        code, result = self.run_script(LEDGER, 'resolve', '--id', 'x', '--decision', 'peut-etre')
        self.assertEqual(code, 1)
        self.assertIn('hors vocabulaire', result['error'])

    def test_evidence_is_bounded(self):
        for index in range(8):
            self.run_script(LEDGER, 'record', '--label', 'Y', '--evidence', 'e' * 500 + str(index))
        code, entry = self.run_script(LEDGER, 'show', '--id', 'y')
        self.assertEqual(len(entry['evidence']), 5)
        self.assertTrue(all(len(item) <= 300 for item in entry['evidence']))

    def test_dry_run_writes_nothing(self):
        before = self.snapshot()
        code, result = self.create('--dry-run')
        self.assertEqual((code, result['status']), (0, 'SIMULATION'))
        self.assertEqual(before, self.snapshot())

    def test_inoperative_keywords_refused_before_any_write(self):
        before = self.snapshot()
        code, result = self.create(keywords='mot-introuvable-xyz')
        self.assertEqual(code, 1)
        self.assertIn("rien n'a été écrit", result['error'])
        self.assertEqual(before, self.snapshot())

    def test_creation_registers_everywhere_and_selector_finds_it(self):
        self.run_script(LEDGER, 'record', '--label', 'Analyse du journal des trades')
        code, result = self.create('--gap-id', 'analyse-du-journal-des-trades')
        self.assertEqual(code, 0, result)
        name = 'xp-bots-trade-journal-analysis'
        self.assertTrue(self.repo.path(f'.agents/skills/{name}/SKILL.md').is_file())
        self.assertTrue(self.repo.path(f'.claude/skills/{name}/SKILL.md').is_file())
        rules = self.repo.read_json('.agents/skills/xp-bots-request-skill-orchestrator/references/routing-rules.json')
        self.assertIn(name, [rule['skill'] for rule in rules['rules']])
        cases = self.repo.read_json('.agents/skills/xp-bots-request-skill-orchestrator/references/routing-cases.json')
        self.assertIn([name], [case.get('includes') for case in cases['cases']])
        catalog = self.repo.path('.agents/skills/xp-bots-request-skill-orchestrator/SKILL.md').read_text(encoding='utf-8')
        self.assertIn(f'- `{name}` — analyse du journal des trades C09', catalog)
        code, entry = self.run_script(LEDGER, 'show', '--id', 'analyse-du-journal-des-trades')
        self.assertEqual((entry['decision'], entry['skill']), ('creee', name))
        result = self.repo.python(SELECT, '--select', 'analyse des trades du mois')
        self.assertIn(name, json.loads(result.stdout))
        self.assertEqual(self.repo.validator()[0], 0)

    def test_one_new_skill_per_request(self):
        self.repo.engine('prompt-claude', {'session_id': 'q', 'prompt': 'crée une skill de journal'})
        code, result = self.create()
        self.assertEqual(code, 0, result)
        self.draft.write_text(BODY, encoding='utf-8')
        code, result = self.create(name='xp-bots-second-skill', keywords='seconde skill analytique,analyse des trades')
        self.assertEqual(code, 1)
        self.assertIn('par requête', result['error'])

    def test_extension_mode(self):
        code, result = self.run_script(CREATE, '--extend', 'xp-bots-london-breakout', '--keywords', 'asian range',
                                       '--example-request', "l'asian range précède-t-il le range London ?")
        self.assertEqual(code, 0, result)
        rules = self.repo.read_json('.agents/skills/xp-bots-request-skill-orchestrator/references/routing-rules.json')
        london = next(rule for rule in rules['rules'] if rule['skill'] == 'xp-bots-london-breakout')
        self.assertIn('asian range', london['keywords'])
        code, result = self.run_script(CREATE, '--extend', 'xp-bots-london-breakout', '--keywords', 'mot-absent-xyz',
                                       '--example-request', 'contrôler le range London')
        self.assertEqual(code, 1)
        self.assertIn("n'apparaît dans la requête", result['error'])

    def test_validator_failure_restores_previous_state(self):
        before = self.snapshot()
        broken = BODY + '\nVoir `docs/fichier-inexistant.md`.\n'
        self.draft.write_text(broken, encoding='utf-8')
        code, result = self.create()
        self.assertEqual(code, 1)
        self.assertIn('restauré', result['error'])
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.repo.path('.agents/skills/xp-bots-trade-journal-analysis').exists())

    def test_unregistered_skill_refused_by_validator(self):
        directory = self.repo.path('.agents/skills/xp-bots-orpheline')
        directory.mkdir()
        (directory / 'SKILL.md').write_text('---\nname: xp-bots-orpheline\ndescription: "Skill orpheline."\n---\n'
                                            '\n## Workflow\n\n1. Rien.\n\n## Garde-fous\n\n- Rien.\n', encoding='utf-8')
        self.repo.python('.agents/hooks/skill_mirrors.py', '--write')
        code, output = self.repo.validator()
        self.assertEqual(code, 1)
        for message in ('sans règle de routage : xp-bots-orpheline', 'sans ligne de catalogue : xp-bots-orpheline',
                        'sans cas de test de sélection : xp-bots-orpheline'):
            self.assertIn(message, output)


if __name__ == '__main__':
    unittest.main()

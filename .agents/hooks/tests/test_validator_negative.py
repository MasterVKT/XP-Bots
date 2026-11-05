"""Negative tests of the governance validator: every announced guarantee is violated once on a
temporary copy and must be detected; the untouched copy must pass."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import RepoCopy  # noqa: E402

LIFECYCLE = '.agents/hooks/lifecycle.json'


class ValidatorNegativeTests(unittest.TestCase):
    def setUp(self):
        self.repo = RepoCopy(git=False)

    def tearDown(self):
        self.repo.close()

    def assert_refused(self, expected: str):
        code, output = self.repo.validator()
        self.assertEqual(code, 1, output)
        self.assertIn(expected, output)

    def edit(self, relative: str, old: str, new: str):
        path = self.repo.path(relative)
        text = path.read_text(encoding='utf-8')
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding='utf-8')

    def test_copy_passes_untouched(self):
        code, output = self.repo.validator()
        self.assertEqual(code, 0, output)

    def test_removed_event_from_hook_file(self):
        hooks = self.repo.read_json('.claude/settings.json')
        del hooks['hooks']['Stop']
        self.repo.write_json('.claude/settings.json', hooks)
        self.assert_refused('claude-code : événement Stop absent')

    def test_removed_event_from_copilot_and_codex(self):
        hooks = self.repo.read_json('.github/hooks/xp-bots-lifecycle.json')
        del hooks['hooks']['userPromptSubmitted']
        self.repo.write_json('.github/hooks/xp-bots-lifecycle.json', hooks)
        hooks = self.repo.read_json('.codex/hooks.json')
        hooks['hooks']['SessionStart'][0]['hooks'][0].pop('commandWindows')
        self.repo.write_json('.codex/hooks.json', hooks)
        code, output = self.repo.validator()
        self.assertIn('copilot : événement userPromptSubmitted absent', output)
        self.assertIn('codex : SessionStart sans variante commandWindows', output)

    def test_obsolete_path_reintroduced(self):
        directory = self.repo.path('.claude/skills/mcl-matryoshka-construction-layers/references')
        directory.mkdir()
        (directory / '01-socle-commun.md').write_text('ancienne copie', encoding='utf-8')
        self.assert_refused('chemin obsolète réapparu')

    def test_obsolete_reference_in_active_file(self):
        self.edit('AGENTS.md', '## Vérifications',
                  '## Vérifications\n\nVoir .claude/skills/mcl-matryoshka-construction-layers/scripts/mcl.py.')
        self.assert_refused('référence active à un chemin obsolète')

    def test_skill_without_routing_catalog_or_case(self):
        rules = self.repo.read_json('.agents/skills/xp-bots-request-skill-orchestrator/references/routing-rules.json')
        rules['rules'] = [rule for rule in rules['rules'] if rule['skill'] != 'xp-bots-deployment-readiness']
        self.repo.write_json('.agents/skills/xp-bots-request-skill-orchestrator/references/routing-rules.json', rules)
        self.edit('.agents/skills/xp-bots-request-skill-orchestrator/SKILL.md',
                  '- `xp-bots-deployment-readiness` —', '- deployment —')
        cases = self.repo.read_json('.agents/skills/xp-bots-request-skill-orchestrator/references/routing-cases.json')
        cases['cases'] = [case for case in cases['cases'] if 'xp-bots-deployment-readiness' not in case.get('includes', [])]
        self.repo.write_json('.agents/skills/xp-bots-request-skill-orchestrator/references/routing-cases.json', cases)
        self.repo.python('.agents/hooks/skill_mirrors.py', '--write')
        code, output = self.repo.validator()
        for message in ('sans règle de routage : xp-bots-deployment-readiness',
                        'sans ligne de catalogue : xp-bots-deployment-readiness',
                        'sans cas de test de sélection : xp-bots-deployment-readiness'):
            self.assertIn(message, output)

    def test_unknown_footer_key(self):
        config = self.repo.read_json(LIFECYCLE)
        config['audit_footer']['keys'][3] = 'cle_inconnue'
        self.repo.write_json(LIFECYCLE, config)
        self.assert_refused('clés du pied inconnues ou divergentes')

    def test_no_fast_gate(self):
        config = self.repo.read_json(LIFECYCLE)
        for gate in config['gates']:
            gate['fast'] = False
        self.repo.write_json(LIFECYCLE, config)
        self.assert_refused('aucune porte rapide déclarée')

    def test_gate_with_missing_script(self):
        config = self.repo.read_json(LIFECYCLE)
        config['gates'][0]['command'] = ['{python}', '{hooks}/porte_absente.py', '{files}']
        self.repo.write_json(LIFECYCLE, config)
        self.assert_refused('script inexistant .agents/hooks/porte_absente.py')

    def test_lifecycle_skill_missing(self):
        config = self.repo.read_json(LIFECYCLE)
        config['skills']['gap'] = 'xp-bots-inexistante'
        self.repo.write_json(LIFECYCLE, config)
        self.assert_refused("skill « gap » inexistante")

    def test_frontmatter_problems(self):
        self.edit('.agents/skills/xp-bots-london-breakout/SKILL.md', 'name: xp-bots-london-breakout', 'name: autre-nom')
        long_text = 'x' * 1100
        self.edit('.agents/skills/xp-bots-ema-rsi-repli/SKILL.md', 'description: "', f'description: "{long_text}')
        self.edit('.agents/skills/xp-bots-validation-replay/SKILL.md', '## Garde-fous', '## Garde-fous\n\n- TODO compléter')
        code, output = self.repo.validator()
        self.assertIn('xp-bots-london-breakout : name « autre-nom » différent du dossier', output)
        self.assertIn('description de', output)
        self.assertIn('placeholder non résolu « TODO »', output)

    def test_missing_cited_resource(self):
        self.edit('.agents/skills/xp-bots-mcl-robot-planning/SKILL.md', 'references/cartographie-xp-bots.md',
                  'references/absente.md')
        self.assert_refused('ressource citée introuvable « references/absente.md »')

    def test_adapter_copy_or_missing_reference(self):
        self.edit('CLAUDE.md', '@AGENTS.md', 'Voir AGENTS')
        rules_line = next(line for line in self.repo.path('.agents/PROJECT_RULES.md').read_text(encoding='utf-8').splitlines()
                          if len(line.strip()) >= 70)
        path = self.repo.path('.clinerules/xp-bots-cycle.md')
        path.write_text(path.read_text(encoding='utf-8') + '\n' + rules_line + '\n', encoding='utf-8')
        code, output = self.repo.validator()
        self.assertIn('CLAUDE.md : référence obligatoire absente « @AGENTS.md »', output)
        self.assertIn('.clinerules/xp-bots-cycle.md : bloc canonique recopié', output)

    def test_mcl_preservation_and_archive(self):
        path = self.repo.path('.agents/skills/mcl-matryoshka-construction-layers/references/13-outil-mcl-py.md')
        path.write_bytes(path.read_bytes() + b'\n')
        shutil.copy(self.repo.path('livrables/skills/mcl-matryoshka-construction-layers.zip'),
                    self.repo.path('.agents/skills/mcl-matryoshka-construction-layers/copie.zip'))
        code, output = self.repo.validator()
        self.assertIn('empreinte modifiée references/13-outil-mcl-py.md', output)
        self.assertIn('archive ZIP découvrable comme skill active', output)

    def test_second_governance_detected(self):
        self.repo.path('livrables/strategies_m15/AGENTS.md').write_text('# règles parallèles\n', encoding='utf-8')
        self.assert_refused('seconde gouvernance détectée')

    def test_corrupt_ledger_detected(self):
        ledger = self.repo.read_json('.agents/skill-gap-ledger.json')
        ledger['entries'].append({'id': 'x', 'label': 'x', 'occurrences': 1, 'first_seen': '2026-11-05',
                                  'last_seen': '2026-11-05', 'evidence': [], 'decision': 'peut-etre', 'skill': None})
        self.repo.write_json('.agents/skill-gap-ledger.json', ledger)
        self.assert_refused('décision hors vocabulaire')

    def test_parasitic_artefact_detected(self):
        cache = self.repo.path('.agents/hooks/__pycache__')
        cache.mkdir()
        (cache / 'x.pyc').write_bytes(b'0')
        self.assert_refused('artefacts générés parasites')

    def test_hand_edited_mirror_detected_by_validator(self):
        path = self.repo.path('.claude/skills/xp-bots-london-breakout/SKILL.md')
        path.write_text(path.read_text(encoding='utf-8') + 'retouche\n', encoding='utf-8')
        self.assert_refused('copies générées : copie éditée à la main ou périmée')


if __name__ == '__main__':
    unittest.main()

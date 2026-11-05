"""Lifecycle engine: every tool x event output format, continuations, inheritance, end gate,
footer, two-pass bound, cross-tool duplicate guard, legacy modes, gates, encodings, fail open."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import FAST_JSON_GATE, RepoCopy, clean_env  # noqa: E402

ORCH = 'xp-bots-request-skill-orchestrator'
AUDIT = 'xp-bots-completion-audit'
FOOTER = ("Réponse.\n\nPied d'audit XP-Bots\n- completion: 3/3 exigences prouvées\n- impact: rg, aucune régression\n"
          "- verifications: validate_governance.py PASS\n- couverture_skills: couvert\n[XP-BOTS-AUDIT:OK]\n")
FAILING_GATE = {'name': 'always-fails', 'fast': False, 'indicative': False, 'timeout': 20,
                'patterns': ['notes/**'], 'command': ['{python}', '-c', 'import sys; sys.exit(3)']}
INDICATIVE_GATE = {'name': 'indicative-fails', 'fast': False, 'indicative': True, 'timeout': 20,
                   'patterns': ['notes/**'], 'command': ['{python}', '-c', 'import sys; sys.exit(4)']}
MISSING_TOOL_GATE = {'name': 'missing-tool', 'fast': False, 'indicative': True, 'timeout': 20,
                     'patterns': ['notes/**'], 'command': ['xp-bots-outil-inexistant-1234']}


def context_of(output: dict) -> str:
    return output.get('hookSpecificOutput', {}).get('additionalContext') or output.get('additionalContext') \
        or output.get('context') or ''


class LifecycleBase(unittest.TestCase):
    def setUp(self):
        self.repo = RepoCopy(git=True)
        self.repo.reduce_gates([FAST_JSON_GATE, FAILING_GATE, INDICATIVE_GATE, MISSING_TOOL_GATE])
        subprocess.run(['git', 'add', '-A'], cwd=self.repo.root, check=True, capture_output=True)
        subprocess.run(['git', '-c', 'user.email=t@e.invalid', '-c', 'user.name=t', 'commit', '-q', '-m', 'gates'],
                       cwd=self.repo.root, check=True, capture_output=True)

    def tearDown(self):
        self.repo.close()

    def prompt(self, tool, text, session='s1', **extra):
        return self.repo.engine(f'prompt-{tool}', {'session_id': session, 'prompt': text, **extra})

    def stop(self, tool, text, session='s1'):
        return self.repo.engine(f'stop-{tool}', {'session_id': session, 'last_assistant_message': text})

    def state(self, session='s1'):
        files = [path for path in self.repo.state.glob('xp-bots-*.json')
                 if not path.name.endswith(('-latest.json', '-events.json'))]
        for path in files:
            value = json.loads(path.read_text(encoding='utf-8'))
            if value.get('identity') == session:
                return value
        return None


class OutputFormatTests(LifecycleBase):
    def test_claude_and_codex_formats(self):
        for tool in ('claude', 'codex'):
            code, output = self.repo.engine(f'session-start-{tool}', {'session_id': tool, 'source': 'startup'})
            self.assertEqual(code, 0)
            self.assertEqual(set(output), {'hookSpecificOutput'})
            self.assertEqual(output['hookSpecificOutput']['hookEventName'], 'SessionStart')
            self.assertIn(f'--- .agents/skills/{ORCH}/SKILL.md ---', context_of(output))
            self.assertIn('## Catalogue', context_of(output))
            code, output = self.prompt(tool, 'contrôler le range London', session=tool)
            self.assertEqual(output['hookSpecificOutput']['hookEventName'], 'UserPromptSubmit')
            code, output = self.repo.engine(f'subagent-start-{tool}', {'session_id': tool})
            self.assertEqual(output['hookSpecificOutput']['hookEventName'], 'SubagentStart')
            code, output = self.stop(tool, 'pas de pied', session=tool)
            self.assertEqual(output['decision'], 'block')
            self.assertTrue(output['reason'].startswith('[xp-bots:passe-corrective 1/2]'))

    def test_copilot_flat_format(self):
        code, output = self.repo.engine('session-start-copilot', {'sessionId': 'c1', 'source': 'new'})
        self.assertEqual(set(output), {'additionalContext'})
        code, output = self.prompt('copilot', 'vérifier le repli EMA15/25/50', session='c1')
        self.assertEqual(set(output), {'additionalContext'})
        code, output = self.repo.engine('subagent-start-copilot', {'sessionId': 'c1'})
        self.assertIn('Ne jamais émettre', output['additionalContext'])
        code, output = self.repo.engine('stop-copilot', {'sessionId': 'c1', 'last_assistant_message': FOOTER})
        self.assertEqual(output, {})

    def test_cline_report_format(self):
        code, output = self.repo.engine('prompt-cline', extra_args=('--text', 'vérifier le repli EMA15/25/50'))
        self.assertEqual(output['decision'], 'allow')
        self.assertIn('xp-bots-ema-rsi-repli', output['context'])
        code, output = self.repo.engine('completion-cline', extra_args=('--text', 'réponse sans pied'))
        self.assertEqual(output['decision'], 'block')
        code, output = self.repo.engine('completion-cline', extra_args=('--text', FOOTER))
        self.assertEqual(output['decision'], 'allow')

    def test_session_context_size_bounded(self):
        code, output = self.repo.engine('session-start-claude', {'session_id': 'size'})
        config = self.repo.read_json('.agents/hooks/lifecycle.json')
        self.assertLessEqual(len(context_of(output)), config['session_context_max_chars'])
        self.assertNotIn('[…tronqué', context_of(output))

    def test_unknown_mode_exit_code_2(self):
        code, output = self.repo.engine('inconnu-claude', {})
        self.assertEqual(code, 2)

    def test_legacy_positional_and_alias_modes(self):
        result = self.repo.python('.agents/hooks/agent_lifecycle.py', 'session-start-claude',
                                  input_bytes=b'{"session_id":"legacy"}')
        self.assertIn('hookSpecificOutput', json.loads(result.stdout))
        code, output = self.repo.engine('claude-prompt', {'session_id': 'legacy', 'prompt': 'bonjour'})
        self.assertEqual(output['hookSpecificOutput']['hookEventName'], 'UserPromptSubmit')


class ContinuationTests(LifecycleBase):
    def test_new_request_then_continuations_keep_selection(self):
        self.prompt('claude', 'contrôler le range London 02:00–07:00')
        first = self.state()['request']
        self.assertIn('xp-bots-london-breakout', first['selection'])
        for text in ('continue', 'vas-y', 'ok', "L'utilisateur a approuvé le passage en mode action",
                     '<task-notification>tâche terminée</task-notification>',
                     '[xp-bots:passe-corrective 1/2] Audit de fin non satisfait.'):
            code, output = self.prompt('claude', text)
            current = self.state()['request']
            self.assertEqual(current['id'], first['id'], text)
            self.assertIn('xp-bots-london-breakout', current['selection'], text)
        self.assertEqual(self.state()['request']['origin'], 'brief')

    def test_notification_source_does_not_run_selector(self):
        self.prompt('claude', 'contrôler le range London')
        before = self.state()['request']
        self.prompt('claude', 'risque marge volume ordres', source='system')
        after = self.state()['request']
        self.assertEqual(before['selection'], after['selection'])
        self.assertEqual(after['origin'], 'notification')

    def test_continuation_does_not_reset_baseline_or_counter(self):
        self.prompt('claude', 'contrôler le range London')
        self.stop('claude', 'sans pied')
        self.assertEqual(self.state()['corrective_passes'], 1)
        self.prompt('claude', 'continue')
        self.assertEqual(self.state()['corrective_passes'], 1)

    def test_vague_request_inherits_and_specific_resets(self):
        self.prompt('claude', 'contrôler le range London')
        code, output = self.prompt('claude', 'lance la suite stp')
        self.assertIn('héritage', context_of(output))
        self.assertIn('xp-bots-london-breakout', self.state()['request']['selection'])
        self.prompt('claude', 'vérifier le repli EMA15/25/50 et RSI14')
        selection = self.state()['request']['selection']
        self.assertIn('xp-bots-ema-rsi-repli', selection)
        self.assertNotIn('xp-bots-london-breakout', selection)

    def test_plan_approval_recomputes_selection_same_request(self):
        self.prompt('claude', 'bonjour')
        first = self.state()['request']['id']
        code, output = self.repo.engine('post-tool-claude', {
            'session_id': 's1', 'tool_name': 'ExitPlanMode',
            'tool_input': {'plan': 'Étape 1 : dimensionner le volume et la marge du coordinateur (C07).'}})
        self.assertEqual(output['hookSpecificOutput']['hookEventName'], 'PostToolUse')
        self.assertIn('Plan approuvé', context_of(output))
        request = self.state()['request']
        self.assertEqual(request['id'], first)
        self.assertIn('xp-bots-risk-execution-contracts', request['selection'])

    def test_copilot_first_tool_injection_once_per_run(self):
        self.prompt('copilot', 'contrôler le range London', session='inj')
        code, first = self.repo.engine('post-tool-copilot', {'sessionId': 'inj', 'toolName': 'view', 'toolArgs': {}})
        self.assertIn('[XP-Bots]', first['additionalContext'])
        code, second = self.repo.engine('post-tool-copilot', {'sessionId': 'inj', 'toolName': 'view', 'toolArgs': {}})
        self.assertEqual(second, {})
        self.prompt('copilot', 'vérifier le repli EMA15/25/50', session='inj')
        code, third = self.repo.engine('post-tool-copilot', {'sessionId': 'inj', 'toolName': 'view', 'toolArgs': {}})
        self.assertIn('xp-bots-ema-rsi-repli', third['additionalContext'])

    def test_edit_of_canonical_skill_regenerates_copies(self):
        source = self.repo.path('.agents/skills/xp-bots-london-breakout/SKILL.md')
        source.write_text(source.read_text(encoding='utf-8') + '\n- Garde-fou de test.\n', encoding='utf-8')
        code, output = self.repo.engine('post-tool-claude', {'session_id': 's1', 'tool_name': 'Edit',
                                                             'tool_input': {'file_path': str(source)}})
        self.assertIn('Copies de skills régénérées', context_of(output))
        result = self.repo.python('.agents/hooks/skill_mirrors.py', '--check')
        self.assertEqual(result.returncode, 0)

    def test_subagent_context_forbids_marker(self):
        self.prompt('claude', 'contrôler le range London')
        code, output = self.repo.engine('subagent-start-claude', {'session_id': 's1'})
        text = context_of(output)
        self.assertIn('xp-bots-london-breakout', text)
        self.assertIn('Ne jamais émettre [XP-BOTS-AUDIT:OK]', text)

    def test_pointer_recalls_request_after_context_clear(self):
        self.prompt('claude', 'contrôler le range London')
        code, output = self.repo.engine('session-start-claude', {'session_id': 'nouvelle', 'source': 'clear'})
        self.assertIn('Requête en cours à reprendre', context_of(output))
        self.prompt('claude', 'continue', session='nouvelle')
        self.assertIn('xp-bots-london-breakout', self.state('nouvelle')['request']['selection'])


class EndGateTests(LifecycleBase):
    def test_marker_without_footer_blocks_and_complete_footer_allows(self):
        self.prompt('claude', 'bonjour')
        code, output = self.stop('claude', 'Fini. [XP-BOTS-AUDIT:OK]')
        self.assertEqual(output['decision'], 'block')
        self.assertIn('clés manquantes', output['reason'])
        code, output = self.stop('claude', FOOTER)
        self.assertNotIn('decision', output)
        self.assertEqual(self.state()['corrective_passes'], 0)

    def test_bold_footer_keys_accepted(self):
        self.prompt('claude', 'bonjour')
        text = FOOTER.replace('- completion:', '- **completion**:')
        code, output = self.stop('claude', text)
        self.assertNotIn('decision', output)

    def test_two_pass_limit(self):
        self.prompt('claude', 'bonjour')
        self.assertEqual(self.stop('claude', 'a')[1]['decision'], 'block')
        self.assertEqual(self.stop('claude', 'b')[1]['decision'], 'block')
        code, output = self.stop('claude', 'c')
        self.assertNotIn('decision', output)
        self.assertIn('Limite de 2 passes', output['systemMessage'])

    def test_assumed_block_marker_allows_with_summary(self):
        self.prompt('claude', 'bonjour')
        code, output = self.stop('claude', 'Blocage prouvé. [XP-BOTS-AUDIT:BLOQUE]')
        self.assertNotIn('decision', output)
        self.assertIn('Blocage assumé', output['systemMessage'])

    def test_blocking_gate_blocks_even_with_marker(self):
        self.prompt('claude', 'bonjour')
        notes = self.repo.path('notes')
        notes.mkdir()
        (notes / 'a.txt').write_text('x', encoding='utf-8')
        code, output = self.stop('claude', FOOTER)
        self.assertEqual(output['decision'], 'block')
        self.assertIn('always-fails', output['reason'])
        self.assertIn('rejouer : python -c import sys; sys.exit(3)', output['reason'])
        self.assertIn('notes/a.txt', output['reason'])

    def test_indicative_and_not_executed_gates_reported_without_blocking(self):
        config = self.repo.read_json('.agents/hooks/lifecycle.json')
        config['gates'] = [INDICATIVE_GATE, MISSING_TOOL_GATE]
        self.repo.write_json('.agents/hooks/lifecycle.json', config)
        self.prompt('claude', 'bonjour')
        notes = self.repo.path('notes')
        notes.mkdir()
        (notes / 'a.txt').write_text('x', encoding='utf-8')
        code, output = self.stop('claude', FOOTER)
        self.assertNotIn('decision', output)
        self.assertIn('indicative-fails : echec', output['systemMessage'])
        self.assertIn('missing-tool : non_executee', output['systemMessage'])

    def test_real_gate_triggered_by_invalid_json(self):
        self.prompt('claude', 'bonjour')
        self.repo.path('config/brouillon_invalide.json').write_text('{"a": 1, "a": 2}', encoding='utf-8')
        code, output = self.stop('claude', FOOTER)
        self.assertEqual(output['decision'], 'block')
        self.assertIn('json-strict', output['reason'])
        self.assertIn('clé dupliquée', output['reason'])

    def test_no_baseline_means_no_gate(self):
        notes = self.repo.path('notes')
        notes.mkdir()
        (notes / 'a.txt').write_text('x', encoding='utf-8')
        code, output = self.stop('claude', FOOTER, session='sans-base')
        self.assertNotIn('decision', output)

    def test_anti_recursion_variable_disables_gates(self):
        self.prompt('claude', 'bonjour')
        notes = self.repo.path('notes')
        notes.mkdir()
        (notes / 'a.txt').write_text('x', encoding='utf-8')
        env = clean_env(self.repo.state, XPBOTS_GATE_ACTIVE='1')
        code, output = self.repo.engine('stop-claude', {'session_id': 's1', 'last_assistant_message': FOOTER}, env=env)
        self.assertNotIn('decision', output)

    def test_cross_tool_duplicate_not_recounted_but_same_tool_counted(self):
        self.prompt('claude', 'bonjour')
        first = self.stop('claude', 'sans pied')[1]
        duplicate = self.repo.engine('stop-copilot', {'session_id': 's1', 'last_assistant_message': 'sans pied'})[1]
        self.assertEqual(first['decision'], duplicate['decision'])
        self.assertEqual(first['reason'], duplicate['reason'])
        self.assertEqual(self.state()['corrective_passes'], 1)
        self.stop('claude', 'sans pied')
        self.assertEqual(self.state()['corrective_passes'], 2)

    def test_transcript_fallback_for_tools_without_final_message(self):
        self.prompt('copilot', 'bonjour', session='tr')
        transcript = self.repo.state / 'transcript.jsonl'
        lines = [{'type': 'user', 'message': {'role': 'user', 'content': 'bonjour'}},
                 {'type': 'assistant', 'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': FOOTER}]}}]
        transcript.write_text('\n'.join(json.dumps(line, ensure_ascii=False) for line in lines), encoding='utf-8')
        code, output = self.repo.engine('stop-copilot', {'sessionId': 'tr', 'transcriptPath': str(transcript)})
        self.assertEqual(output, {})
        lines[-1]['message']['content'][0]['text'] = 'sans pied'
        transcript.write_text('\n'.join(json.dumps(line, ensure_ascii=False) for line in lines), encoding='utf-8')
        code, output = self.repo.engine('stop-copilot', {'sessionId': 'tr', 'transcriptPath': str(transcript)})
        self.assertEqual(output['decision'], 'block')

    def test_cline_completion_runs_fast_gates_only(self):
        self.repo.engine('prompt-cline', extra_args=('--text', 'bonjour'))
        notes = self.repo.path('notes')
        notes.mkdir()
        (notes / 'a.txt').write_text('x', encoding='utf-8')
        code, output = self.repo.engine('completion-cline', extra_args=('--text', FOOTER))
        self.assertEqual(output['decision'], 'allow')


class EncodingAndFailOpenTests(LifecycleBase):
    TEXT = 'Vérifier le repli EMA15/25/50 — accents éèàçù « guillemets » et RSI14'

    def assert_accents(self, raw: bytes, via_launcher: bool = False):
        if via_launcher:
            result = subprocess.run(['sh', str(self.repo.path('.agents/hooks/invoke-agent-hook.sh')), 'prompt-claude'],
                                    cwd=self.repo.root, env=clean_env(self.repo.state), input=raw,
                                    capture_output=True, timeout=60)
            output = json.loads(result.stdout)
        else:
            output = self.repo.engine('prompt-claude', raw=raw)[1]
        state = self.state('accents')
        self.assertEqual(state['request']['text'], self.TEXT)
        self.assertIn('xp-bots-ema-rsi-repli', context_of(output))

    def test_utf8_bytes_preserved_through_launcher(self):
        payload = json.dumps({'session_id': 'accents', 'prompt': self.TEXT}, ensure_ascii=False).encode('utf-8')
        self.assert_accents(payload, via_launcher=True)

    def test_utf8_bom_and_utf16(self):
        payload = json.dumps({'session_id': 'accents', 'prompt': self.TEXT}, ensure_ascii=False)
        self.assert_accents(b'\xef\xbb\xbf' + payload.encode('utf-8'))
        self.assert_accents(payload.encode('utf-16'))

    def test_output_is_ascii_json(self):
        payload = json.dumps({'session_id': 'ascii', 'prompt': self.TEXT}, ensure_ascii=False).encode('utf-8')
        result = self.repo.python('.agents/hooks/agent_lifecycle.py', '--mode', 'prompt-claude', input_bytes=payload)
        result.stdout.decode('ascii')
        self.assertIn('é', json.loads(result.stdout)['hookSpecificOutput']['additionalContext'])

    def test_input_file_deleted_and_env_input(self):
        input_file = self.repo.state / 'input.json'
        input_file.write_bytes(json.dumps({'session_id': 'f', 'prompt': 'bonjour'}).encode('utf-8'))
        code, output = self.repo.engine('prompt-claude', raw=b'', extra_args=('--input-file', str(input_file)))
        self.assertFalse(input_file.exists())
        self.assertIn('hookSpecificOutput', output)
        env = clean_env(self.repo.state, XPBOTS_HOOK_INPUT=json.dumps({'session_id': 'e', 'prompt': 'bonjour'}))
        result = subprocess.run([sys.executable, '-B', str(self.repo.path('.agents/hooks/agent_lifecycle.py')),
                                 '--mode', 'prompt-claude'], cwd=self.repo.root, env=env, capture_output=True,
                                stdin=subprocess.DEVNULL)
        self.assertIn('hookSpecificOutput', json.loads(result.stdout))

    def test_powershell_launcher_when_available(self):
        """Run the Windows launcher as the tools run it; skipped when PowerShell is not installed."""
        import shutil
        shell = shutil.which('powershell') or shutil.which('pwsh')
        if not shell:
            self.skipTest('PowerShell absent : test exécuté sur les postes qui le fournissent')
        payload = json.dumps({'session_id': 'accents', 'prompt': self.TEXT}, ensure_ascii=False).encode('utf-8')
        result = subprocess.run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                                 str(self.repo.path('.agents/hooks/invoke-agent-hook.ps1')), '-Mode', 'prompt-copilot'],
                                cwd=self.repo.root, env=clean_env(self.repo.state, POWERSHELL_TELEMETRY_OPTOUT='1'),
                                input=payload, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('xp-bots-ema-rsi-repli', json.loads(result.stdout)['additionalContext'])
        self.assertEqual(self.state('accents')['request']['text'], self.TEXT)

    def test_invalid_json_treated_as_prompt(self):
        code, output = self.repo.engine('prompt-claude', raw='contrôler le range London'.encode('utf-8'))
        self.assertIn('xp-bots-london-breakout', context_of(output))

    def test_fail_open_on_internal_error(self):
        config = self.repo.read_json('.agents/hooks/lifecycle.json')
        config['selector'] = '.agents/skills/inexistant/select.py'
        self.repo.write_json('.agents/hooks/lifecycle.json', config)
        code, output = self.prompt('claude', 'contrôler le range London')
        self.assertEqual((code, output), (0, {}))
        log = self.repo.state / 'xp-bots-lifecycle-errors.log'
        self.assertTrue(log.exists())
        self.assertIn('Traceback', log.read_text(encoding='utf-8'))


class SnapshotTests(unittest.TestCase):
    def test_exclusions_apply_to_relative_paths_only(self):
        repo = RepoCopy(git=False, parent_name='logs')
        try:
            code, output = repo.engine('prompt-claude', {'session_id': 'x', 'prompt': 'bonjour'})
            state = next(json.loads(path.read_text(encoding='utf-8')) for path in repo.state.glob('xp-bots-*.json')
                         if not path.name.endswith(('-latest.json', '-events.json')))
            self.assertGreater(len(state['snapshot']), 50)
            self.assertFalse(any(path.startswith('.git/') for path in state['snapshot']))
        finally:
            repo.close()

    def test_pattern_conversion(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import agent_lifecycle
        regex = agent_lifecycle.pattern_regex
        self.assertTrue(regex('**/*.json').match('config/a.json'))
        self.assertTrue(regex('**/*.json').match('a.json'))
        self.assertFalse(regex('docs/*.md').match('docs/sub/a.md'))
        self.assertTrue(regex('docs/**').match('docs/sub/a.md'))
        self.assertTrue(regex('a?.py').match('ab.py'))
        self.assertFalse(regex('a?.py').match('a/.py'))


if __name__ == '__main__':
    unittest.main()

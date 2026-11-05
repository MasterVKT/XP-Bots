"""Complete governance suite of XP-Bots, from the repository root.

Order: generated copies check, governance validator, selector cases, then the unittest suites of
.agents/hooks/tests (lifecycle for every tool x event, mirrors, ledger and generator, validator
negative tests). Every writing test runs on a temporary repository copy with an isolated state
directory. The inherited anti-recursion variable is neutralized for the children.

Usage:
    python .agents/skills/xp-bots-maintain-agent-skills/scripts/run_governance_suite.py [--quiet]
    python .agents/skills/xp-bots-maintain-agent-skills/scripts/run_governance_suite.py --real-repo-negative
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
TESTS = ROOT / '.agents' / 'hooks' / 'tests'
VALIDATOR = ROOT / '.agents/skills/xp-bots-maintain-agent-skills/scripts/validate_governance.py'
# First obsolete adapter path of the registry: the removed copy of MCL's references.
OBSOLETE_PROBE = ROOT / json.loads((ROOT / '.agents/agent-integrations.json').read_text(encoding='utf-8'))[
    'obsolete_paths'][0]


def child_env(state_dir: Path) -> dict:
    env = {key: value for key, value in os.environ.items()
           if key not in ('XPBOTS_GATE_ACTIVE', 'XPBOTS_HOOK_INPUT')}
    env['XPBOTS_LIFECYCLE_STATE_DIR'] = str(state_dir)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def run(label: str, command: list[str], env: dict, timeout: int = 900) -> dict:
    start = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=timeout)
    output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
    return {'step': label, 'ok': result.returncode == 0, 'code': result.returncode,
            'seconds': round(time.monotonic() - start, 1), 'tail': output[-3000:]}


def real_repo_negative() -> int:
    """Recreate briefly a removed adapter directory in the real repository: it must be refused."""
    if OBSOLETE_PROBE.exists():
        print('Le dossier obsolète existe déjà : arrêt sans modification.')
        return 1
    OBSOLETE_PROBE.mkdir()
    probe = OBSOLETE_PROBE / 'sonde.md'
    probe.write_text('sonde temporaire du test négatif\n', encoding='utf-8')
    try:
        refused = subprocess.run([sys.executable, '-B', str(VALIDATOR), '--json'], cwd=ROOT, capture_output=True)
        report = json.loads(refused.stdout)
    finally:
        probe.unlink()
        OBSOLETE_PROBE.rmdir()
    restored = subprocess.run([sys.executable, '-B', str(VALIDATOR), '--json'], cwd=ROOT, capture_output=True)
    after = json.loads(restored.stdout)
    detected = refused.returncode == 1 and any('chemin obsolète réapparu' in item for item in report['errors'])
    result = {'refused_while_present': detected, 'status_after_removal': after['status'],
              'probe_removed': not OBSOLETE_PROBE.exists()}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if detected and after['status'] == 'PASS' and result['probe_removed'] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Suite complète de gouvernance XP-Bots.')
    parser.add_argument('--quiet', action='store_true', help='Bilan seulement, détails des échecs inclus.')
    parser.add_argument('--real-repo-negative', action='store_true',
                        help='Recréer brièvement un dossier d\'adaptateurs supprimé dans le dépôt réel.')
    args = parser.parse_args(argv)
    if args.real_repo_negative:
        return real_repo_negative()
    state_dir = Path(tempfile.mkdtemp(prefix='xp-bots-suite-state-'))
    try:
        env = child_env(state_dir)
        python = [sys.executable, '-B']
        steps = [
            run('copies générées', python + [str(ROOT / '.agents/hooks/skill_mirrors.py'), '--check'], env),
            run('validateur de gouvernance', python + [str(VALIDATOR), '--quiet'], env),
            run('cas du sélecteur', python + [str(ROOT / '.agents/skills/xp-bots-request-skill-orchestrator/scripts/select_skills.py'),
                                              '--test'], env),
        ]
        for module in sorted(TESTS.glob('test_*.py')):
            steps.append(run(f'suite {module.stem}', python + ['-m', 'unittest', '-q', module.stem],
                             {**env, 'PYTHONPATH': str(TESTS)}))
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
    failed = [step for step in steps if not step['ok']]
    for step in steps:
        mark = 'OK ' if step['ok'] else 'ÉCHEC'
        print(f"{mark} {step['step']} ({step['seconds']} s)")
        if not step['ok'] or not args.quiet:
            if not step['ok']:
                print(step['tail'])
    status = 'FAIL' if failed else 'PASS'
    print(f'Suite de gouvernance XP-Bots : {status} — {len(steps) - len(failed)}/{len(steps)} étapes vertes.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())

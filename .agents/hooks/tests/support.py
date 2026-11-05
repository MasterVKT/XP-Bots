"""Shared helpers for the XP-Bots governance test suites (standard library only).

Every test that writes runs on a temporary copy of the repository with an isolated lifecycle
state directory; the real repository, its ledger and the real state directory are never written.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
REAL_ROOT = Path(__file__).resolve().parents[3]
IGNORED = shutil.ignore_patterns('.git', '.local', '__pycache__', '*.pyc', 'node_modules', '.venv', 'venv')


def clean_env(state_dir: Path | None = None, **extra) -> dict:
    """Environment for child processes: the inherited anti-recursion variable is neutralized."""
    env = {key: value for key, value in os.environ.items()
           if key not in ('XPBOTS_GATE_ACTIVE', 'XPBOTS_HOOK_INPUT', 'XPBOTS_LIFECYCLE_STATE_DIR')}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    if state_dir is not None:
        env['XPBOTS_LIFECYCLE_STATE_DIR'] = str(state_dir)
    env.update({key: str(value) for key, value in extra.items()})
    return env


class RepoCopy:
    """Temporary copy of the repository (optionally a Git repository) plus a state directory."""

    def __init__(self, git: bool = True, parent_name: str | None = None):
        self._temporary = tempfile.TemporaryDirectory(prefix='xp-bots-governance-')
        base = Path(self._temporary.name)
        if parent_name:
            base = base / parent_name
            base.mkdir(parents=True)
        self.root = base / 'XP-Bots'
        shutil.copytree(REAL_ROOT, self.root, ignore=IGNORED, symlinks=False)
        self.state = Path(self._temporary.name) / 'state'
        self.state.mkdir()
        if git:
            for command in (['git', 'init', '-q'], ['git', 'add', '-A'],
                            ['git', '-c', 'user.email=test@example.invalid', '-c', 'user.name=test',
                             'commit', '-q', '-m', 'base']):
                subprocess.run(command, cwd=self.root, check=True, capture_output=True)

    def close(self) -> None:
        self._temporary.cleanup()

    def path(self, relative: str) -> Path:
        return self.root / relative

    def read_json(self, relative: str):
        return json.loads(self.path(relative).read_text(encoding='utf-8'))

    def write_json(self, relative: str, value) -> None:
        self.path(relative).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def python(self, script: str, *args: str, env: dict | None = None, input_bytes: bytes | None = None,
               timeout: int = 300) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, '-B', str(self.path(script)), *args], cwd=self.root,
                              env=env or clean_env(self.state), input=input_bytes, capture_output=True,
                              timeout=timeout)

    def engine(self, mode: str, payload=None, raw: bytes | None = None, env: dict | None = None,
               extra_args: tuple = ()) -> tuple[int, dict | str]:
        data = raw if raw is not None else json.dumps(payload or {}, ensure_ascii=False).encode('utf-8')
        result = self.python('.agents/hooks/agent_lifecycle.py', '--mode', mode, *extra_args, env=env,
                             input_bytes=data)
        text = result.stdout.decode('utf-8', errors='replace')
        try:
            return result.returncode, json.loads(text)
        except ValueError:
            return result.returncode, text

    def validator(self) -> tuple[int, str]:
        result = self.python('.agents/skills/xp-bots-maintain-agent-skills/scripts/validate_governance.py')
        return result.returncode, result.stdout.decode('utf-8', errors='replace')

    def reduce_gates(self, gates: list[dict]) -> None:
        """Replace the gates of the copy so that tests never re-launch the governance suite."""
        config = self.read_json('.agents/hooks/lifecycle.json')
        config['gates'] = gates
        self.write_json('.agents/hooks/lifecycle.json', config)


FAST_JSON_GATE = {'name': 'json-strict', 'fast': True, 'indicative': False, 'timeout': 20,
                  'patterns': ['**/*.json'],
                  'command': ['{python}', '-B', '{hooks}/gate_checks.py', 'json', '{files}']}

"""Single lifecycle engine for every AI tool used in XP-Bots (standard library only).

Invocation from the repository root:
    python .agents/hooks/agent_lifecycle.py --mode <event>-<tool> [--input-file PATH]
    python .agents/hooks/agent_lifecycle.py <event>-<tool>            (positional form)
    python .agents/hooks/agent_lifecycle.py --run-gates [--fast-only] [--files ...]

Events: session-start, prompt, post-tool, subagent-start, stop, completion.
Tools and output formats are declared in .agents/hooks/lifecycle.json. The engine prints a
single JSON object and exits 0; exit code 2 is reserved for an unknown mode. Any internal
error is logged in the state directory and a neutral output is printed (fail open).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import unicodedata

sys.dont_write_bytecode = True  # imports below must not create __pycache__ in the repository
HOOKS_DIR = Path(__file__).resolve().parent
ROOT = HOOKS_DIR.parents[1]
CONFIG_PATH = HOOKS_DIR / 'lifecycle.json'
ENV_STATE_DIR = 'XPBOTS_LIFECYCLE_STATE_DIR'
ENV_INPUT = 'XPBOTS_HOOK_INPUT'
ENV_GATE_ACTIVE = 'XPBOTS_GATE_ACTIVE'
EVENT_NAMES = {'session-start': 'SessionStart', 'prompt': 'UserPromptSubmit', 'post-tool': 'PostToolUse',
               'subagent-start': 'SubagentStart'}
JOURNAL_MAX_BYTES = 512 * 1024


# --------------------------------------------------------------------------- utilities

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8', errors='replace')).hexdigest()


def normalize(text: str) -> str:
    text = unicodedata.normalize('NFKD', text or '')
    text = ''.join(char for char in text if not unicodedata.combining(char)).lower()
    text = text.replace('’', "'").replace('‘', "'")
    text = re.sub('[‐-―−]', '-', text)
    return re.sub(r'\s+', ' ', text).strip()


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))


def state_dir(config: dict) -> Path:
    override = os.environ.get(ENV_STATE_DIR)
    base = Path(override) if override else Path(tempfile.gettempdir()) / f"{config['state_prefix']}-agent-lifecycle"
    base.mkdir(parents=True, exist_ok=True)
    return base


def repo_slug() -> str:
    return re.sub(r'[^a-z0-9-]+', '-', ROOT.name.lower()).strip('-') or 'repo'


def atomic_write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=1)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def log_error(config: dict | None, message: str) -> None:
    try:
        prefix = (config or {}).get('state_prefix', 'xp-bots')
        directory = state_dir(config or {'state_prefix': prefix})
        with open(directory / f'{prefix}-lifecycle-errors.log', 'a', encoding='utf-8') as stream:
            stream.write(f'--- {now_iso()} ---\n{message}\n')
    except OSError:
        pass


def journal(config: dict, record: dict) -> None:
    try:
        path = state_dir(config) / f"{config['state_prefix']}-{repo_slug()}-journal.jsonl"
        if path.exists() and path.stat().st_size > JOURNAL_MAX_BYTES:
            data = path.read_bytes()[-JOURNAL_MAX_BYTES // 2:]
            path.write_bytes(data[data.find(b'\n') + 1:])
        with open(path, 'a', encoding='utf-8') as stream:
            stream.write(json.dumps({'ts': now_iso(), **record}, ensure_ascii=False) + '\n')
    except OSError:
        pass


# --------------------------------------------------------------------------- input decoding

def decode_bytes(data: bytes) -> str:
    """Decode hook input bytes without any shell text conversion (BOM aware)."""
    if data.startswith(b'\xef\xbb\xbf'):
        return data[3:].decode('utf-8', errors='replace')
    if data.startswith(b'\xff\xfe') or data.startswith(b'\xfe\xff'):
        return data.decode('utf-16', errors='replace')
    return data.decode('utf-8', errors='replace')


def read_input(input_file: str | None) -> bytes:
    if input_file:
        path = Path(input_file)
        try:
            return path.read_bytes()
        finally:
            try:
                path.unlink()
            except OSError:
                pass
    env_value = os.environ.get(ENV_INPUT)
    if env_value:
        return env_value.encode('utf-8', errors='replace')
    if sys.stdin is None or sys.stdin.isatty():
        return b''
    return sys.stdin.buffer.read()


def parse_payload(raw: bytes) -> dict:
    text = decode_bytes(raw).strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
    except ValueError:
        return {'prompt': text, '_raw_text': True}
    return value if isinstance(value, dict) else {'prompt': text, '_raw_text': True}


def field(payload: dict, *names: str):
    for name in names:
        value = payload.get(name)
        if value not in (None, '', [], {}):
            return value
    return None


def identity_of(payload: dict) -> str:
    value = field(payload, 'session_id', 'sessionId', 'task_id', 'taskId', 'conversation_id', 'conversationId')
    if value is None:
        value = field(payload, 'transcript_path', 'transcriptPath')
    return str(value) if value is not None else 'default'


# --------------------------------------------------------------------------- state

class Store:
    def __init__(self, config: dict, identity: str):
        self.config = config
        self.identity = identity
        directory = state_dir(config)
        root_key = sha(str(ROOT))[:12]
        self.path = directory / f"{config['state_prefix']}-{repo_slug()}-{sha(str(ROOT) + '|' + identity)[:16]}.json"
        self.pointer_path = directory / f"{config['state_prefix']}-{repo_slug()}-{root_key}-latest.json"
        self.events_path = directory / f"{config['state_prefix']}-{repo_slug()}-{root_key}-events.json"

    def load(self) -> dict:
        state = read_json(self.path, {})
        if not isinstance(state, dict) or state.get('schema') != 'xp-bots-lifecycle-state-v1':
            state = {'schema': 'xp-bots-lifecycle-state-v1', 'identity': self.identity, 'root': str(ROOT),
                     'request': None, 'snapshot': None, 'corrective_passes': 0, 'last_events': {},
                     'injected_runs': []}
        return state

    def save(self, state: dict) -> None:
        state['updated_at'] = now_iso()
        atomic_write_json(self.path, state)

    def pointer(self) -> dict | None:
        value = read_json(self.pointer_path, None)
        if not isinstance(value, dict):
            return None
        if time.time() - value.get('epoch', 0) > self.config['pointer_window_seconds']:
            return None
        return value

    def save_pointer(self, state: dict, tool: str, fingerprint: str) -> None:
        atomic_write_json(self.pointer_path, {'epoch': time.time(), 'tool': tool, 'identity': self.identity,
                                              'fingerprint': fingerprint, 'request': state.get('request'),
                                              'snapshot': state.get('snapshot')})

    def recent_event(self, fingerprint: str, tool: str) -> dict | None:
        events = read_json(self.events_path, {})
        entry = events.get(fingerprint) if isinstance(events, dict) else None
        if not entry:
            return None
        if time.time() - entry.get('epoch', 0) > self.config['duplicate_window_seconds']:
            return None
        return entry if entry.get('tool') != tool else None

    def remember_event(self, fingerprint: str, tool: str, output: dict, decision: str) -> None:
        """Store the decision (not a tool-specific rendering) for the cross-tool duplicate guard."""
        events = read_json(self.events_path, {})
        if not isinstance(events, dict):
            events = {}
        horizon = time.time() - max(60, self.config['duplicate_window_seconds'])
        events = {key: value for key, value in events.items() if value.get('epoch', 0) >= horizon}
        events[fingerprint] = {'epoch': time.time(), 'tool': tool, 'output': output, 'decision': decision}
        atomic_write_json(self.events_path, events)


# --------------------------------------------------------------------------- file snapshot

def excluded(relative: str, exclusions: list[str]) -> bool:
    """Apply exclusions to repository-relative paths only, never to the absolute path."""
    parts = relative.split('/')
    for item in exclusions:
        item = item.strip('/')
        if '/' in item:
            if relative == item or relative.startswith(item + '/'):
                return True
        elif item in parts:
            return True
    return False


def list_files(config: dict) -> list[str]:
    exclusions = config.get('snapshot_exclusions', [])
    try:
        result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                                cwd=ROOT, capture_output=True, timeout=30)
        if result.returncode == 0:
            names = [item.decode('utf-8', errors='replace') for item in result.stdout.split(b'\0') if item]
            return sorted({name for name in names if not excluded(name, exclusions)})
    except (OSError, subprocess.SubprocessError):
        pass
    files = []
    for directory, subdirs, names in os.walk(ROOT):
        relative_dir = Path(directory).relative_to(ROOT).as_posix()
        relative_dir = '' if relative_dir == '.' else relative_dir
        subdirs[:] = [name for name in subdirs
                      if not excluded(f'{relative_dir}/{name}'.lstrip('/'), exclusions)]
        for name in names:
            relative = f'{relative_dir}/{name}'.lstrip('/')
            if not excluded(relative, exclusions):
                files.append(relative)
    return sorted(files)


def take_snapshot(config: dict) -> dict:
    snapshot = {}
    for relative in list_files(config):
        try:
            info = (ROOT / relative).stat()
        except OSError:
            continue
        snapshot[relative] = [info.st_mtime_ns, info.st_size]
    return snapshot


def changed_files(config: dict, baseline: dict | None) -> list[str]:
    """Files added, removed or modified since the request baseline; empty without baseline."""
    if not baseline:
        return []
    current = take_snapshot(config)
    changed = {path for path, stamp in current.items() if baseline.get(path) != stamp}
    changed |= {path for path in baseline if path not in current}
    return sorted(changed)


# --------------------------------------------------------------------------- gates

def pattern_regex(pattern: str) -> re.Pattern:
    """Convert a glob to a regex: **/ and ** cross directories, * and ? never cross a separator."""
    index, out = 0, []
    while index < len(pattern):
        if pattern.startswith('**/', index):
            out.append('(?:.*/)?')
            index += 3
        elif pattern.startswith('**', index):
            out.append('.*')
            index += 2
        elif pattern[index] == '*':
            out.append('[^/]*')
            index += 1
        elif pattern[index] == '?':
            out.append('[^/]')
            index += 1
        else:
            out.append(re.escape(pattern[index]))
            index += 1
    return re.compile('^' + ''.join(out) + '$')


def gate_command(gate: dict, files: list[str], config: dict) -> tuple[list[str], bool]:
    cap = config.get('gate_files_cap', 60)
    truncated = len(files) > cap
    substitutions = {'{python}': sys.executable, '{root}': str(ROOT), '{hooks}': str(HOOKS_DIR),
                     '{skills}': str(ROOT / config['skill_library']['skills_dir'])}
    command = []
    for token in gate['command']:
        if token == '{files}':
            command.extend(files[:cap])
            continue
        for key, value in substitutions.items():
            token = token.replace(key, value)
        command.append(token)
    return command, truncated


def display_command(gate: dict) -> str:
    shown = []
    for token in gate['command']:
        token = token.replace('{python}', 'python').replace('{hooks}', '.agents/hooks').replace(
            '{skills}', '.agents/skills').replace('{root}', '.')
        shown.append('<fichiers>' if token == '{files}' else token)
    return ' '.join(shown)


def run_gates(config: dict, changed: list[str], fast_only: bool = False) -> dict:
    if os.environ.get(ENV_GATE_ACTIVE):
        return {'skipped': "anti-récursion : exécution à l'intérieur d'une porte", 'results': []}
    if not changed:
        return {'skipped': 'aucune base de comparaison ou aucun fichier modifié', 'results': []}
    existing = [path for path in changed if (ROOT / path).is_file()]
    gates = sorted(config.get('gates', []), key=lambda gate: not gate.get('fast'))
    budget = config['gate_budget_seconds']['fast' if fast_only else 'normal']
    deadline = time.monotonic() + budget
    env = {key: value for key, value in os.environ.items()}
    env[ENV_GATE_ACTIVE] = '1'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    results = []
    for gate in gates:
        if fast_only and not gate.get('fast'):
            continue
        regexes = [pattern_regex(pattern) for pattern in gate['patterns']]
        matched = [path for path in existing if any(regex.match(path) for regex in regexes)]
        if not matched:
            continue
        entry = {'name': gate['name'], 'fast': bool(gate.get('fast')), 'blocking': not gate.get('indicative'),
                 'files': len(matched), 'replay': display_command(gate)}
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            entry.update(status='non_executee', detail='budget de temps des portes épuisé')
            results.append(entry)
            continue
        command, truncated = gate_command(gate, matched, config)
        if truncated:
            entry['truncated'] = f"{len(matched)} fichiers appariés, {config.get('gate_files_cap', 60)} transmis"
        try:
            completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                       timeout=max(1, min(gate.get('timeout', 60), remaining)))
            output = (completed.stdout + completed.stderr).decode('utf-8', errors='replace')
            entry.update(status='reussie' if completed.returncode == 0 else 'echec',
                         code=completed.returncode, output=output[-1500:])
        except FileNotFoundError as error:
            entry.update(status='non_executee', detail=f'outil absent : {error}')
        except subprocess.TimeoutExpired:
            entry.update(status='non_executee', detail='délai de la porte dépassé')
        results.append(entry)
    return {'skipped': None, 'results': results}


# --------------------------------------------------------------------------- selection

def selector_module(config: dict):
    path = ROOT / config['selector']
    sys.path.insert(0, str(path.parent))
    try:
        import importlib
        return importlib.import_module(path.stem)
    finally:
        sys.path.pop(0)


def analyze_text(config: dict, text: str) -> dict:
    module = selector_module(config)
    return module.analyze(text, module.load_rules(ROOT / config['routing_rules']))


def classify(config: dict, text: str, source) -> str:
    normalized = normalize(text)
    if normalized.startswith(normalize(config['corrective_prefix'])):
        return 'corrective'
    if isinstance(source, str) and source in config.get('notification_sources', []):
        return 'notification'
    if any(normalize(marker) in normalized for marker in config.get('notification_markers', [])):
        return 'notification'
    trimmed = normalized.strip(' .!?,;:')
    if not trimmed:
        return 'empty'
    if trimmed in {normalize(item) for item in config.get('continuation_exact', [])}:
        return 'continuation'
    for prefix in config.get('continuation_prefixes', []):
        prefix = normalize(prefix)
        if trimmed == prefix or (trimmed.startswith(prefix) and not trimmed[len(prefix)].isalnum()):
            return 'continuation'
    return 'new'


def union(*lists) -> list[str]:
    merged = []
    for items in lists:
        for item in items or []:
            if item not in merged:
                merged.append(item)
    return merged


def ordered_selection(config: dict, skills: list[str]) -> list[str]:
    names = config['skills']
    head = [names['orchestrator']] if names['orchestrator'] in skills else []
    tail = [names[key] for key in ('gap', 'audit') if names[key] in skills]
    middle = [skill for skill in skills if skill not in head and skill not in tail]
    return head + middle + tail


# --------------------------------------------------------------------------- messages

def skill_path(config: dict, skill: str) -> str:
    return f"{config['skill_library']['skills_dir']}/{skill}/SKILL.md"


def orchestrator_body(config: dict) -> str:
    text = (ROOT / skill_path(config, config['skills']['orchestrator'])).read_text(encoding='utf-8')
    match = re.match(r'\A---\r?\n.*?\r?\n---[ \t]*\r?\n', text, re.S)
    return (text[match.end():] if match else text).strip()


def auxiliary_state() -> str:
    parts = ['rg disponible' if shutil.which('rg') else 'rg absent (utiliser la recherche de l’outil)']
    parts.append('outil de graphe configuré (.code-review-graph/)' if (ROOT / '.code-review-graph').exists()
                 else 'aucun outil de graphe : recherches ciblées dans la source')
    return ' ; '.join(parts)


def session_context(config: dict, tool: str, state: dict, recalled: dict | None) -> str:
    names = config['skills']
    markers = config['audit_markers']
    lines = [
        f"[XP-Bots] Cycle obligatoire : {names['orchestrator']} d'abord, {names['audit']} avant la réponse "
        f"finale (pied {', '.join(config['audit_footer']['keys'])} ; marqueur {markers['success']} ou "
        f"{markers['blocked']}). Règles : {', '.join(config['rules_files'])}.",
    ]
    request = state.get('request') or (recalled or {}).get('request')
    if request:
        lines.append(f"Requête en cours à reprendre : « {request['text'][:300]} » — sélection : "
                     f"{', '.join(request['selection'])}.")
    if tool in config.get('auxiliary_tools_session_start', []):
        lines.append(f'Outils auxiliaires : {auxiliary_state()}.')
    lines.append(f"--- {skill_path(config, names['orchestrator'])} ---")
    text = '\n'.join(lines) + '\n'
    body = orchestrator_body(config)
    limit = config.get('session_context_max_chars', 4800)
    if len(text) + len(body) > limit:
        body = body[:max(0, limit - len(text) - 80)] + f"\n[…tronqué : lire {skill_path(config, names['orchestrator'])}]"
    return text + body


ORIGINS = {'requete': 'requête', 'heritage': 'héritage de la requête précédente', 'continuation': 'continuation',
           'notification': 'notification (sélection conservée)', 'brief': 'brief correctif', 'plan': 'plan approuvé',
           'reprise': 'reprise de la requête en cours'}


def prompt_context(config: dict, request: dict) -> str:
    names = config['skills']
    selection = request['selection']
    paths = ', '.join(skill_path(config, skill) for skill in selection)
    return '\n'.join([
        f"[XP-Bots] Requête {request['id'][:8]}",
        f"1. Exécuter d'abord {names['orchestrator']} et appliquer {', '.join(config['rules_files'])}.",
        f"2. Sélection déterministe (origine : {ORIGINS.get(request['origin'], request['origin'])}) : "
        f"{', '.join(selection)} — à charger : {paths}.",
        '3. Vérifier le code réel, ajuster la sélection et annoncer la couverture tâche → skill ; '
        'signaler toute tâche sans skill.',
        f"4. Avant la réponse finale, appliquer {names['audit']} : pied d'audit "
        f"({', '.join(config['audit_footer']['keys'])}) et marqueur exact {config['audit_markers']['success']} "
        f"ou {config['audit_markers']['blocked']}.",
    ])


def plan_context(config: dict, request: dict) -> str:
    return (f"[XP-Bots] Plan approuvé : nouvelle phase d'exécution de la même requête {request['id'][:8]} "
            f"(base de comparaison et compteur conservés). Sélection recalculée sur le texte du plan : "
            f"{', '.join(request['selection'])}. Recharger {config['skills']['orchestrator']}, puis appliquer "
            f"{config['skills']['audit']} avant la réponse finale.")


def subagent_context(config: dict, request: dict | None) -> str:
    selection = (request or {}).get('selection') or [config['skills']['orchestrator']]
    markers = config['audit_markers']
    return (f"[XP-Bots] Sous-tâche déléguée. Skills retenues pour la requête parente : {', '.join(selection)}. "
            f"Charger seulement celles utiles à cette sous-tâche ({config['skill_library']['skills_dir']}/<nom>/SKILL.md). "
            f"Ne jamais émettre {markers['success']} ni {markers['blocked']} : marqueurs réservés au fil principal.")


def corrective_brief(config: dict, number: int, issues: list[str], failing: list[dict],
                     changed: list[str], request: dict | None) -> str:
    names = config['skills']
    selection = union((request or {}).get('selection'), [names['orchestrator'], names['audit'], names['gap']])
    lines = [f"{config['corrective_prefix']} {number}/{config['corrective_pass_limit']}] Audit de fin non satisfait.",
             'Constats :']
    lines += [f'- {issue}' for issue in issues]
    lines += ['Consignes :',
              f"1. Recharger {names['orchestrator']} avec la sélection de remédiation : {', '.join(ordered_selection(config, selection))}.",
              f"2. Appliquer {names['audit']} : complétion bidirectionnelle, impact et non-régression, "
              'vérification adversariale, couverture des skills.',
              '3. Dresser l\'inventaire des problèmes, puis exécuter immédiatement le plan de remédiation.',
              f"4. Terminer par le pied d'audit ({', '.join(config['audit_footer']['keys'])}) et le marqueur "
              f"{config['audit_markers']['success']} ou {config['audit_markers']['blocked']}."]
    if failing:
        lines.append('Portes bloquantes en échec :')
        for gate in failing:
            excerpt = (gate.get('output') or gate.get('detail') or '').strip().splitlines()[-6:]
            lines.append(f"- {gate['name']} ({gate['files']} fichier(s)) — rejouer : {gate['replay']}")
            lines += [f'    {line[:200]}' for line in excerpt]
    shown = changed[:40]
    lines.append(f'Fichiers modifiés depuis le début de la requête ({len(changed)}) : '
                 + (', '.join(shown) if shown else 'aucun') + (' …' if len(changed) > len(shown) else ''))
    return '\n'.join(lines)


# --------------------------------------------------------------------------- audit footer

def footer_issues(config: dict, text: str) -> list[str]:
    """Return the missing footer keys (empty list when the footer is complete)."""
    keys = config['audit_footer']['keys']
    header = normalize(config['audit_footer']['header'])
    lines = (text or '').splitlines()
    start = None
    for index, line in enumerate(lines):
        if header in normalize(line):
            start = index
    if start is None:
        return list(keys)
    found = set()
    for line in lines[start + 1:]:
        match = re.match(r'^\s*(?:[-*]\s*)?(?:\*\*|`)?([a-z_]+)(?:\*\*|`)?\s*:\s*(\S.*)$', normalize(line))
        if match and match.group(1) in keys:
            found.add(match.group(1))
    return [key for key in keys if key not in found]


def extract_final_text(payload: dict) -> str | None:
    value = field(payload, 'last_assistant_message', 'lastAssistantMessage', 'final_message', 'finalMessage',
                  'response', 'final_response')
    if isinstance(value, str):
        return value
    if payload.get('_raw_text'):
        return payload.get('prompt')
    transcript = field(payload, 'transcript_path', 'transcriptPath')
    if not transcript:
        return None
    return transcript_last_assistant(Path(str(transcript)))


def transcript_last_assistant(path: Path) -> str | None:
    try:
        with open(path, 'rb') as stream:
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            stream.seek(max(0, size - 2 * 1024 * 1024))
            data = stream.read().decode('utf-8', errors='replace')
    except OSError:
        return None

    def text_of(content) -> str | None:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [item.get('text') for item in content
                     if isinstance(item, dict) and item.get('type') in (None, 'text', 'output_text')
                     and isinstance(item.get('text'), str)]
            return '\n'.join(parts) if parts else None
        return None

    def assistant_text(node) -> str | None:
        if isinstance(node, dict):
            role = node.get('role') or node.get('type')
            if role in ('assistant', 'assistant.message', 'assistant_message'):
                for key in ('content', 'text', 'message'):
                    found = text_of(node.get(key))
                    if found:
                        return found
            for value in node.values():
                found = assistant_text(value)
                if found:
                    return found
        elif isinstance(node, list):
            for value in reversed(node):
                found = assistant_text(value)
                if found:
                    return found
        return None

    last = None
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            found = assistant_text(json.loads(line))
        except ValueError:
            continue
        if found:
            last = found
    if last is None:
        try:
            last = assistant_text(json.loads(data))
        except ValueError:
            return None
    return last


# --------------------------------------------------------------------------- outputs

def context_output(config: dict, tool: str, event: str, context: str) -> dict:
    fmt = config['tools'][tool]['format']
    if fmt == 'hook-specific':
        return {'hookSpecificOutput': {'hookEventName': EVENT_NAMES[event], 'additionalContext': context}}
    if fmt == 'flat':
        return {'additionalContext': context}
    return {'mode': f'{event}-{tool}', 'decision': 'allow', 'context': context}


def stop_output(config: dict, tool: str, decision: str, brief: str | None, summary: str | None) -> dict:
    fmt = config['tools'][tool]['format']
    if fmt == 'report':
        return {'mode': f'completion-{tool}', 'decision': decision, 'brief': brief, 'summary': summary}
    if decision == 'block':
        return {'decision': 'block', 'reason': brief}
    if summary and fmt == 'hook-specific':
        return {'systemMessage': summary}
    return {}


# --------------------------------------------------------------------------- handlers

def new_request(config: dict, state: dict, text: str, selection: list[str], origin: str, matched: list[str],
                run_id: str | None = None) -> dict:
    request = {'id': sha(f'{time.time_ns()}|{text}')[:16], 'run_id': run_id, 'text': text[:4000],
               'started_at': now_iso(), 'selection': ordered_selection(config, selection), 'origin': origin,
               'matched': matched}
    state['request'] = request
    state['snapshot'] = take_snapshot(config)
    state['corrective_passes'] = 0
    return request


def handle_prompt(config: dict, tool: str, payload: dict, store: Store, state: dict) -> tuple[dict, dict]:
    text = field(payload, 'prompt', 'user_prompt', 'userPrompt', 'message', 'text', 'initialPrompt') or ''
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    fingerprint = sha('prompt|' + text)
    duplicate = store.recent_event(fingerprint, tool)
    pointer = store.pointer()
    if duplicate and pointer and pointer.get('fingerprint') == fingerprint and pointer.get('request'):
        state['request'] = pointer['request']
        state['snapshot'] = pointer.get('snapshot')
        state['corrective_passes'] = 0
        request = state['request']
        return context_output(config, tool, 'prompt', prompt_context(config, request)), {'class': 'duplicate'}
    category = classify(config, text, field(payload, 'source'))
    request = state.get('request')
    if request is None and category != 'new' and pointer and pointer.get('request'):
        state['request'] = dict(pointer['request'], origin='reprise')
        state['snapshot'] = pointer.get('snapshot') or take_snapshot(config)
        request = state['request']
    names = config['skills']
    run_id = field(payload, 'turn_id', 'turnId', 'run_id', 'runId')
    if category == 'new' or request is None:
        analysis = analyze_text(config, text)
        previous = (request or {}).get('selection') or ((pointer or {}).get('request') or {}).get('selection')
        if (category == 'new' and analysis['no_match'] and analysis['useful_words'] < config['inherit_max_useful_words']
                and previous):
            request = new_request(config, state, text, previous, 'heritage', [], run_id)
        else:
            request = new_request(config, state, text, analysis['selection'], 'requete', analysis['matched'], run_id)
    elif category == 'continuation':
        analysis = analyze_text(config, text)
        request['selection'] = ordered_selection(config, union(request['selection'], analysis['matched'],
                                                               analysis['fallbacks']))
        request['origin'] = 'continuation'
    elif category == 'corrective':
        request['selection'] = ordered_selection(config, union(request['selection'],
                                                               [names['orchestrator'], names['audit'], names['gap']]))
        request['origin'] = 'brief'
    else:
        request['origin'] = 'notification' if category == 'notification' else 'continuation'
    state['last_events']['prompt'] = {'ts': now_iso(), 'tool': tool, 'class': category}
    output = context_output(config, tool, 'prompt', prompt_context(config, request))
    store.save_pointer(state, tool, fingerprint)
    store.remember_event(fingerprint, tool, output, 'context')
    return output, {'class': category, 'origin': request['origin'], 'selection': request['selection']}


def handle_session_start(config: dict, tool: str, payload: dict, store: Store, state: dict) -> tuple[dict, dict]:
    recalled = store.pointer() if state.get('request') is None else None
    context = session_context(config, tool, state, recalled)
    state['last_events']['session-start'] = {'ts': now_iso(), 'tool': tool, 'source': field(payload, 'source')}
    extra = {}
    initial = field(payload, 'initialPrompt', 'initial_prompt')
    if isinstance(initial, str) and initial.strip():
        prompt_output, extra = handle_prompt(config, tool, {**payload, 'prompt': initial}, store, state)
        context += '\n\n' + (prompt_output.get('additionalContext')
                             or prompt_output.get('hookSpecificOutput', {}).get('additionalContext', ''))
    return context_output(config, tool, 'session-start', context), {'chars': len(context), **extra}


def handle_post_tool(config: dict, tool: str, payload: dict, store: Store, state: dict) -> tuple[dict, dict]:
    tool_name = str(field(payload, 'tool_name', 'toolName') or '')
    tool_input = payload.get('tool_input') or payload.get('toolInput') or payload.get('toolArgs') or {}
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except ValueError:
            tool_input = {'raw': tool_input}
    notes = []
    request = state.get('request')
    if tool_name in config.get('plan_tools', []):
        plan = tool_input.get('plan') if isinstance(tool_input, dict) else None
        if request is None:
            request = new_request(config, state, plan or 'plan approuvé', [config['skills']['orchestrator']], 'plan', [])
        if isinstance(plan, str) and plan.strip():
            analysis = analyze_text(config, plan)
            if not analysis['no_match']:
                request['selection'] = ordered_selection(config, union(analysis['selection'],
                                                                       [config['skills']['audit']]))
        request['origin'] = 'plan'
        notes.append(plan_context(config, request))
    if tool_name in config.get('edit_tools', []) and isinstance(tool_input, dict):
        target = str(field(tool_input, 'file_path', 'path', 'filePath', 'notebook_path') or '')
        skills_dir = config['skill_library']['skills_dir']
        if skills_dir in target.replace('\\', '/'):
            sys.path.insert(0, str(HOOKS_DIR))
            try:
                import skill_mirrors
                result = skill_mirrors.write(ROOT)
            finally:
                sys.path.pop(0)
            if result['written'] or result['problems']:
                notes.append('[XP-Bots] Copies de skills régénérées : '
                             + (', '.join(result['written']) or 'aucune')
                             + ('. Écarts à traiter : ' + '; '.join(result['problems']) if result['problems'] else '.'))
    if config['tools'][tool].get('inject_on_first_tool'):
        # Once per run: for tool variants that ignore the session-start context.
        run_key = (request or {}).get('run_id') or (request or {}).get('id') or 'session'
        injected = state.setdefault('injected_runs', [])
        if run_key not in injected:
            if 'session-start' in state.get('last_events', {}) and request:
                notes.insert(0, prompt_context(config, request))
            else:
                notes.insert(0, session_context(config, tool, state, None))
            state['injected_runs'] = (injected + [run_key])[-20:]
    if not notes:
        return {}, {'tool_name': tool_name}
    return context_output(config, tool, 'post-tool', '\n\n'.join(notes)), {'tool_name': tool_name}


def handle_subagent(config: dict, tool: str, payload: dict, store: Store, state: dict) -> tuple[dict, dict]:
    request = state.get('request') or ((store.pointer() or {}).get('request'))
    return context_output(config, tool, 'subagent-start', subagent_context(config, request)), {}


def evaluate_end(config: dict, tool: str, payload: dict, state: dict, fast_only: bool) -> dict:
    changed = changed_files(config, state.get('snapshot'))
    gates = run_gates(config, changed, fast_only=fast_only)
    failing = [gate for gate in gates['results'] if gate['blocking'] and gate['status'] == 'echec']
    reported = [gate for gate in gates['results'] if gate['status'] != 'reussie' and gate not in failing]
    text = extract_final_text(payload)
    markers = config['audit_markers']
    issues = []
    assumed = False
    if text is None:
        text_note = 'message final indisponible pour cet outil : marqueur et pied non vérifiables'
    else:
        text_note = None
        assumed = markers['blocked'] in text
        if not assumed and markers['success'] not in text:
            issues.append(f"marqueur d'audit absent ({markers['success']} ou {markers['blocked']})")
        missing = footer_issues(config, text)
        if missing:
            issues.append("pied d'audit incomplet, clés manquantes : " + ', '.join(missing))
    for gate in failing:
        issues.append(f"porte bloquante en échec : {gate['name']}")
    return {'changed': changed, 'gates': gates, 'failing': failing, 'reported': reported, 'issues': issues,
            'assumed': assumed, 'text_note': text_note}


def handle_stop(config: dict, tool: str, payload: dict, store: Store, state: dict) -> tuple[dict, dict]:
    fast_only = bool(config['tools'][tool].get('fast_gates_only'))
    text = extract_final_text(payload) or ''
    request = state.get('request')
    fingerprint = sha(f"stop|{(request or {}).get('id', '')}|{text}")
    duplicate = store.recent_event(fingerprint, tool)
    if duplicate:
        stored = duplicate['output']
        output = stop_output(config, tool, stored['decision'], stored.get('brief'), stored.get('summary'))
        return output, {'decision': stored['decision'], 'duplicate_of': duplicate['tool']}
    result = evaluate_end(config, tool, payload, state, fast_only)
    limit = config['corrective_pass_limit']
    info = [f"{gate['name']} : {gate['status']}" + (f" ({gate.get('detail')})" if gate.get('detail') else '')
            for gate in result['reported']]
    if result['text_note']:
        info.append(result['text_note'])
    if result['gates']['skipped']:
        info.append('portes : ' + result['gates']['skipped'])
    if result['assumed']:
        decision, brief = 'allow', None
        summary = '[XP-Bots] Blocage assumé déclaré.' + (' Points ouverts : ' + '; '.join(result['issues'] + info)
                                                         if result['issues'] or info else '')
    elif not result['issues']:
        decision, brief = 'allow', None
        state['corrective_passes'] = 0
        summary = ('[XP-Bots] Audit de fin accepté. ' + '; '.join(info)) if info else None
    elif state.get('corrective_passes', 0) >= limit:
        decision, brief = 'allow', None
        summary = (f'[XP-Bots] Limite de {limit} passes correctives atteinte ; points non résolus : '
                   + '; '.join(result['issues'] + info))
    else:
        state['corrective_passes'] = state.get('corrective_passes', 0) + 1
        decision = 'block'
        brief = corrective_brief(config, state['corrective_passes'], result['issues'] + info, result['failing'],
                                 result['changed'], request)
        summary = None
    state['last_events']['stop'] = {'ts': now_iso(), 'tool': tool, 'decision': decision}
    output = stop_output(config, tool, decision, brief, summary)
    store.remember_event(fingerprint, tool, {'decision': decision, 'brief': brief, 'summary': summary}, decision)
    return output, {'decision': decision, 'issues': len(result['issues']), 'changed': len(result['changed']),
                    'gates': [(gate['name'], gate['status']) for gate in result['gates']['results']]}


HANDLERS = {'session-start': handle_session_start, 'prompt': handle_prompt, 'post-tool': handle_post_tool,
            'subagent-start': handle_subagent, 'stop': handle_stop, 'completion': handle_stop}


def resolve_mode(config: dict, mode: str) -> tuple[str, str] | None:
    mode = config.get('mode_aliases', {}).get(mode, mode)
    for event in sorted(HANDLERS, key=len, reverse=True):
        if mode.startswith(event + '-'):
            tool = mode[len(event) + 1:]
            if tool in config['tools'] and event in config['tools'][tool]['events']:
                return event, tool
    return None


def neutral_output(mode: str | None) -> dict:
    return {}


def run_mode(config: dict, mode: str, payload: dict) -> dict:
    event, tool = resolve_mode(config, mode)
    store = Store(config, identity_of(payload))
    state = store.load()
    output, details = HANDLERS[event](config, tool, payload, store, state)
    store.save(state)
    journal(config, {'mode': mode, 'identity': sha(store.identity)[:12], **details})
    return output


def manual_gates(config: dict, files: list[str] | None, fast_only: bool) -> int:
    if files is None:
        pointer = Store(config, 'default').pointer()
        if pointer and pointer.get('snapshot'):
            files = changed_files(config, pointer['snapshot'])
        else:
            status = subprocess.run(['git', 'status', '--porcelain', '-z', '--untracked-files=all'], cwd=ROOT,
                                    capture_output=True, timeout=30)
            entries = [item.decode('utf-8', errors='replace') for item in status.stdout.split(b'\0') if item]
            files = sorted({entry[3:] for entry in entries if len(entry) > 3})
    result = run_gates(config, files, fast_only=fast_only)
    print(json.dumps({'files': len(files), **result}, ensure_ascii=False, indent=2))
    return 1 if any(gate['blocking'] and gate['status'] == 'echec' for gate in result['results']) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Moteur unique du cycle de vie des agents XP-Bots.')
    parser.add_argument('positional_mode', nargs='?', help='Mode <événement>-<outil> (forme compatible).')
    parser.add_argument('--mode', help='Mode <événement>-<outil>.')
    parser.add_argument('--input-file', help="Fichier d'entrée du hook, supprimé après lecture.")
    parser.add_argument('--text', help='Texte de requête ou de réponse pour un appel manuel (Cline).')
    parser.add_argument('--run-gates', action='store_true', help='Exécuter les portes sur les fichiers modifiés.')
    parser.add_argument('--fast-only', action='store_true', help='Avec --run-gates : portes rapides seulement.')
    parser.add_argument('--files', nargs='*', help='Avec --run-gates : fichiers à contrôler.')
    args = parser.parse_args(argv)
    config = None
    try:
        config = load_config()
        if args.run_gates:
            return manual_gates(config, args.files, args.fast_only)
        mode = args.mode or args.positional_mode
        if not mode or resolve_mode(config, mode) is None:
            print(json.dumps({'error': f'mode inconnu : {mode}'}, ensure_ascii=True))
            return 2
        raw = args.text.encode('utf-8') if args.text is not None else read_input(args.input_file)
        payload = parse_payload(raw)
        if args.text is not None and resolve_mode(config, mode)[0] in ('stop', 'completion'):
            payload = {'last_assistant_message': args.text}
        output = run_mode(config, mode, payload)
    except Exception:  # fail open: never interrupt the human session
        log_error(config, traceback.format_exc())
        output = neutral_output(args.mode or args.positional_mode)
    # ASCII-only JSON (\u escapes): immune to console code pages when a shell relays the output.
    sys.stdout.write(json.dumps(output, ensure_ascii=True))
    sys.stdout.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())

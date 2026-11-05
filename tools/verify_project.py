"""Offline resource/contract audit, with an optional isolated Git merge preview."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / '.local/reports'
AUDIT_COPY = ROOT / 'docs/validation/verification_projet.json'
CHECKS = []


def check(group, label, condition):
    CHECKS.append({'pass': group, 'name': label, 'ok': bool(condition)})
    if not condition:
        raise AssertionError(label)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'Duplicate key in {path.relative_to(ROOT)}')
            result[key] = value
        return result

    def nonfinite(_):
        raise ValueError(f'Nonfinite number in {path.relative_to(ROOT)}')

    return json.loads(path.read_text(encoding='utf-8-sig'),
                      object_pairs_hook=pairs, parse_constant=nonfinite)


def git(arguments, *, env=None, input_bytes=None, accepted=(0,)):
    settings = os.environ.copy()
    settings['GIT_OPTIONAL_LOCKS'] = '0'
    if env:
        settings.update(env)
    result = subprocess.run(['git', *arguments], cwd=ROOT, env=settings,
                            input=input_bytes, capture_output=True, timeout=90)
    if result.returncode not in accepted:
        # Do not print command payloads or private environment variables.
        raise RuntimeError('Git verification failed: ' +
                           result.stderr.decode('utf-8', errors='replace').strip())
    return result.stdout


def tree_entries(tree, env=None):
    entries = {}
    for record in git(['ls-tree', '-r', '-z', tree], env=env).split(b'\0'):
        if record:
            metadata, name = record.split(b'\t', 1)
            entries[name.decode('utf-8')] = metadata.decode('ascii')
    return entries


def audit_resources():
    proof = strict_json(ROOT / 'docs/validation/conservation_ressources.json')
    for filename, relative in proof['promotions'].items():
        check(1, f'Canonical resource exists: {relative}', (ROOT / relative).is_file())

    expected_files = {
        'config/parametres_figes_v3.json': proof['frozen_technical_file_sha256'],
        'config/parametres_IA_integration_v1.json': proof['frozen_ai_file_sha256'],
        'docs/references/IA_Generative_Forex_Scalping_M15_v2.md': proof['source_reference_sha256'],
    }
    for relative, expected in expected_files.items():
        check(1, f'Original bytes preserved: {relative}', sha((ROOT / relative).read_bytes()) == expected)

    for method, name in [('ema', '01_Triple_EMA_RSI_Repli_M15_V3_IA.md'),
                         ('london', '02_London_Breakout_M15_V3_IA.md')]:
        text = (ROOT / proof['promotions'][name]).read_text(encoding='utf-8')
        body = text[text.index('## C01 '):]
        check(1, f'{method}: complete normative document body preserved',
              sha(body.encode('utf-8')) == proof['preserved_sections'][method]['complete_normative_body_sha256'])

    for relative, expected in proof['reference_function_ast_sha256'].items():
        functions = {node.name: ast.dump(node, include_attributes=False)
                     for node in ast.parse((ROOT / relative).read_text(encoding='utf-8')).body
                     if isinstance(node, ast.FunctionDef)}
        actual = sha(json.dumps(functions, sort_keys=True, separators=(',', ':')).encode('utf-8'))
        check(1, f'Function bodies preserved: {relative}', actual == expected)

    resource_files = []
    for directory in ['config', 'schemas', 'prompts', 'reference', 'tests', 'tools', 'docs', 'livrables/strategies_m15']:
        resource_files.extend(path for path in (ROOT / directory).rglob('*')
                              if path.is_file() and '__pycache__' not in path.parts)
    resource_files.extend(ROOT / name for name in
                          ['README.md', '.gitignore', '.gitattributes', '.env.example', 'requirements-dev.txt'])
    resource_files = sorted(set(resource_files))

    json_files = [path for path in resource_files if path.suffix == '.json']
    for path in json_files:
        strict_json(path)
    check(1, 'All active JSON resources parse strictly', bool(json_files))

    missing_links = []
    pending_audit_copy = False
    link_count = 0
    for path in resource_files:
        if path.suffix != '.md':
            continue
        text = path.read_text(encoding='utf-8')
        for match in re.finditer(r'\[[^\]\n]+\]\(([^)\n]+)\)', text):
            target = match.group(1).strip().strip('<>')
            if target.startswith(('http:', 'https:', '#', 'mailto:')):
                continue
            # Local links in this project have no Markdown title suffix.
            target = unquote(target.split('#', 1)[0])
            if not target:
                continue
            destination = (path.parent / target).resolve()
            link_count += 1
            if destination == AUDIT_COPY and not destination.exists():
                pending_audit_copy = True
                continue
            if not destination.exists():
                missing_links.append(f'{path.relative_to(ROOT)} -> {target}')
    check(1, 'Relative document links resolve (apart from initial audit output)', not missing_links)
    check(1, 'No obsolete active generator or raw conversation',
          not (ROOT / '.codex-artifact-work').exists() and not (ROOT / 'input_clean.md').exists())
    check(1, 'No parallel obsolete strategy distributions',
          not (ROOT / 'livrables/strategies_m15_v3').exists()
          and not (ROOT / 'livrables/enrichissement_m15').exists())
    check(1, 'New repository resources are below one MiB each',
          all(path.stat().st_size < 1024 * 1024 for path in resource_files))

    credential_pattern = re.compile(
        r'\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{24,}|gsk_[A-Za-z0-9]{24,}|AIza[A-Za-z0-9_-]{30,})\b'
        r'|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
    credential_paths = [str(path.relative_to(ROOT)) for path in resource_files
                        if credential_pattern.search(path.read_text(encoding='utf-8'))]
    check(1, 'No recognizable API key or private key in active text resources', not credential_paths)

    provenance = strict_json(ROOT / 'docs/validation/provenance_IA_v1.json')
    check(1, 'LLM reference provenance points to preserved context source',
          provenance['input']['input_file'] == 'docs/references/IA_Generative_Forex_Scalping_M15_v2.md'
          and provenance['input']['input_sha256'] == proof['source_reference_sha256'])
    return {'files_reviewed': len(resource_files),
            'bytes_reviewed': sum(path.stat().st_size for path in resource_files),
            'relative_links_checked': link_count,
            'missing_links': missing_links,
            'initial_audit_copy_pending': pending_audit_copy,
            'archive_manifest_sha256': proof['archive_manifest_sha256']}


def audit_suites():
    results = {}
    for script, report_name in [('check_llm.py', 'check_llm.json'),
                                ('check_technical.py', 'check_technical.json')]:
        report_path = REPORTS / report_name
        # A stale PASS report must never hide a failed current process.
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'tests' / script)],
                                cwd=ROOT, capture_output=True, timeout=120)
        if result.returncode:
            raise RuntimeError(f'{script}: ' + result.stderr.decode('utf-8', errors='replace').strip())
        report = strict_json(report_path)
        check(2, f'{script}: all current checks pass',
              report['status'] == 'PASS' and report['checks_total'] == len(report['checks'])
              and all(item['ok'] for item in report['checks']))
        results[script] = {key: value for key, value in report.items() if key != 'checks'}
        results[script]['test_source_sha256'] = sha((ROOT / 'tests' / script).read_bytes())
    return results


def audit_git():
    head = git(['rev-parse', 'HEAD']).decode().strip()
    remote = git(['rev-parse', 'origin/master']).decode().strip()
    base = git(['merge-base', head, remote]).decode().strip()
    index_name = git(['rev-parse', '--git-path', 'index']).decode().strip()
    real_index = Path(index_name)
    if not real_index.is_absolute():
        real_index = ROOT / real_index
    index_before = real_index.read_bytes() if real_index.exists() else b''

    git(['diff', '--check'])
    check(3, 'Tracked diff contains no whitespace errors', True)

    ignored = ['.env', '.env.production', '.local/reports/example.json',
               'data/cache/prices.parquet', 'runtime/budget.sqlite',
               'reference/__pycache__/example.pyc', '.code-review-graph/graph.db',
               'exports/example.zip']
    kept = ['.env.example', 'reference/technical.py',
            '.agents/skills/mcl-matryoshka-construction-layers/SKILL.md',
            '.claude/skills/mcl-matryoshka-construction-layers/SKILL.md',
            'livrables/skills/mcl-matryoshka-construction-layers.zip']
    ignore_output = git(['check-ignore', '--no-index', '--stdin', '-z'],
                        input_bytes=('\0'.join(ignored + kept) + '\0').encode(), accepted=(0, 1))
    ignored_actual = {path.decode() for path in ignore_output.split(b'\0') if path}
    check(3, 'Private/generated paths ignored and remote skill paths retained', ignored_actual == set(ignored))

    with tempfile.TemporaryDirectory(prefix='xp-bots-index-') as temporary:
        candidate_env = {'GIT_INDEX_FILE': str(Path(temporary) / 'candidate.index')}
        merged_env = {'GIT_INDEX_FILE': str(Path(temporary) / 'merged.index')}
        git(['read-tree', head], env=candidate_env)
        git(['add', '-A', '--', '.'], env=candidate_env)
        candidate_tree = git(['write-tree'], env=candidate_env).decode().strip()
        changed_local = {path.decode('utf-8') for path in
                         git(['diff', '--name-only', '-z', '--no-renames', base, candidate_tree]).split(b'\0') if path}
        changed_remote = {path.decode('utf-8') for path in
                          git(['diff', '--name-only', '-z', '--no-renames', base, remote]).split(b'\0') if path}
        collisions = [(local, distant) for local in changed_local for distant in changed_remote
                      if local == distant or local.startswith(distant + '/') or distant.startswith(local + '/')]
        check(3, 'Local and remote changes have no path or file/directory overlap', not collisions)

        # Resolve trivial delete/unchanged cases as an ordinary Git merge does.
        # This flag affects only the temporary index; no worktree update is used.
        git(['read-tree', '-m', '--aggressive', base, candidate_tree, remote], env=merged_env)
        check(3, 'Three-way index simulation contains no unresolved entry',
              not git(['ls-files', '-u', '-z'], env=merged_env))
        merged_tree = git(['write-tree'], env=merged_env).decode().strip()
        remote_entries = tree_entries(remote)
        combined_entries = tree_entries(merged_tree)
        check(3, 'Every remote changed path is preserved in the combined tree',
              all(combined_entries.get(path) == remote_entries.get(path) for path in changed_remote))
        candidate_entries = tree_entries(candidate_tree)
        check(3, 'Every local changed path is preserved in the combined tree',
              all(combined_entries.get(path) == candidate_entries.get(path) for path in changed_local))
        check(3, 'Prospective commit diff contains no whitespace errors',
              git(['diff', '--check', head, candidate_tree]) == b'')

    check(3, 'Real Git index byte-for-byte unchanged',
          (real_index.read_bytes() if real_index.exists() else b'') == index_before)
    check(3, 'Current branch commit unchanged', git(['rev-parse', 'HEAD']).decode().strip() == head)
    return {'status': 'PASS', 'local_head': head, 'fetched_origin_master': remote,
            'common_ancestor': base, 'local_changed_paths': len(changed_local),
            'remote_changed_paths': len(changed_remote), 'path_collisions': [],
            'remote_paths_preserved': sorted(changed_remote),
            'real_index_unchanged': True, 'merge_performed': False,
            'commit_created': False, 'push_performed': False,
            'scope': 'The fetched remote reference and the current intended local tree, including untracked, non-ignored files.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git', action='store_true', help='Include an isolated merge preview against fetched origin/master.')
    args = parser.parse_args()
    REPORTS.mkdir(parents=True, exist_ok=True)
    result = {'schema': 'xp-bots-project-audit-v1',
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'RUNNING', 'model_inference_calls': 0, 'broker_orders': 0,
              'financial_validation': False,
              'scope': 'Resource preservation, offline reference tests and optional Git preparation; not a production robot or profitability validation.'}
    try:
        result['resources'] = audit_resources()
        result['test_suites'] = audit_suites()
        if args.git:
            result['git'] = audit_git()
        else:
            result['git'] = {'status': 'NOT_REQUESTED', 'command': 'python tools/verify_project.py --git'}
        result['status'] = 'PASS'
    except Exception as error:
        result['status'] = 'FAIL'
        result['error'] = str(error)
    result['project_checks_total'] = len(CHECKS)
    result['project_passes'] = {str(group): sum(item['pass'] == group for item in CHECKS) for group in [1, 2, 3]}
    result['reference_checks_total'] = sum(item['checks_total'] for item in result.get('test_suites', {}).values())
    result['checks'] = CHECKS
    output = REPORTS / 'verification_projet.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary = {key: result[key] for key in ['status', 'project_checks_total', 'project_passes', 'reference_checks_total']}
    summary['report'] = str(output)
    if 'error' in result:
        summary['error'] = result['error']
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

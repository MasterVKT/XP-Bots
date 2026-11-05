"""Create or extend an XP-Bots skill and register it everywhere it must be known, in one command.

Order: (1) validate name, description, keywords and catalog line; (2) check BEFORE writing that the
keywords select the skill for the example request and keep every existing selection case green;
(3) create the skill; (4) add routing rule, catalog line and selection test case; (5) regenerate the
tool copies; (6) record the decision in the gap ledger; (7) run the validators and restore the
previous state if they fail.

Usage (from the repository root):
    python .agents/skills/xp-bots-skill-gap-detector/scripts/create_skill.py [--dry-run] --name xp-bots-<domaine> \
        --description "..." --keywords "a,b*,expression composée" --catalog "..." \
        --example-request "..." --body-file .local/skill-drafts/<nom>.md [--gap-id <id>]
    python .agents/skills/xp-bots-skill-gap-detector/scripts/create_skill.py [--dry-run] --extend <skill> \
        --keywords "..." --example-request "..." [--catalog "..."] [--append-file <section.md>] [--gap-id <id>]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = Path(__file__).resolve().parent
NAME = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
PLACEHOLDERS = re.compile(r'<(?:ROOT|APP|PY|ORCH|AUDIT|GAP|GOV|RULES)>|\{\{[^}]*\}\}|\bTODO\b|\bTBD\b|\bFIXME\b', re.I)
CREATED_FILE = 'created-skills.json'


class Refused(Exception):
    pass


def import_from(directory: Path, name: str):
    sys.path.insert(0, str(directory))
    try:
        import importlib
        return importlib.import_module(name)
    finally:
        sys.path.pop(0)


def load_config() -> dict:
    return json.loads((ROOT / '.agents' / 'hooks' / 'lifecycle.json').read_text(encoding='utf-8'))


def paths(config: dict) -> dict:
    library = config['skill_library']
    return {'rules': ROOT / config['routing_rules'], 'cases': ROOT / config['routing_cases'],
            'catalog': ROOT / library['catalog'], 'ledger': ROOT / library['ledger'],
            'skills': ROOT / library['skills_dir']}


def parse_keywords(raw: str) -> list[str]:
    keywords = [item.strip() for item in (raw or '').split(',') if item.strip()]
    if not keywords:
        raise Refused('au moins un mot-clé est requis')
    return keywords


def check_body(text: str, label: str) -> None:
    if text.lstrip().startswith('---'):
        raise Refused(f'{label} : pas de frontmatter dans le corps (le générateur l\'écrit)')
    for heading in ('## Workflow', '## Garde-fous'):
        if heading not in text:
            raise Refused(f'{label} : section « {heading} » obligatoire')
    match = PLACEHOLDERS.search(text)
    if match:
        raise Refused(f'{label} : placeholder non résolu « {match.group(0)} »')


def precheck(config: dict, rules: dict, skill: str, keywords: list[str], example: str) -> list[str]:
    selector = import_from(ROOT / config['selector'].rsplit('/', 1)[0], 'select_skills')
    candidate = json.loads(json.dumps(rules))
    rule = next((item for item in candidate['rules'] if item['skill'] == skill), None)
    if rule is None:
        candidate['rules'].append({'skill': skill, 'keywords': keywords})
    else:
        rule['keywords'] = rule['keywords'] + [key for key in keywords if key not in rule['keywords']]
    normalized = selector.normalize(example)
    words = set(selector.WORD.findall(normalized))
    if not any(selector.keyword_matches(keyword, normalized, words) for keyword in keywords):
        raise Refused(f'aucun des mots-clés {keywords} n\'apparaît dans la requête d\'exemple ; rien n\'a été écrit')
    analysis = selector.analyze(example, candidate)
    if skill not in analysis['matched']:
        raise Refused(f'les mots-clés {keywords} ne sélectionnent pas {skill} pour la requête d\'exemple '
                      f'(sélection obtenue : {analysis["selection"]}) ; rien n\'a été écrit')
    cases = json.loads(paths(config)['cases'].read_text(encoding='utf-8'))
    cases['cases'].append({'request': example, 'includes': [skill]})
    with tempfile.TemporaryDirectory() as temporary:
        cases_path = Path(temporary) / 'cases.json'
        cases_path.write_text(json.dumps(cases, ensure_ascii=False), encoding='utf-8')
        failures = selector.run_cases(candidate, cases_path)
    failures = [item for item in failures if skill not in item]
    if failures:
        raise Refused('les nouveaux mots-clés casseraient des cas de sélection existants : ' + '; '.join(failures))
    return candidate['rules']


def current_request_id() -> str | None:
    engine = import_from(ROOT / '.agents' / 'hooks', 'agent_lifecycle')
    config = engine.load_config()
    pointer = engine.Store(config, 'default').pointer()
    return ((pointer or {}).get('request') or {}).get('id')


def creation_registry():
    engine = import_from(ROOT / '.agents' / 'hooks', 'agent_lifecycle')
    return engine.state_dir(engine.load_config()) / CREATED_FILE


def check_creation_quota(config: dict) -> str | None:
    request_id = current_request_id()
    if not request_id:
        return None
    registry = creation_registry()
    created = json.loads(registry.read_text(encoding='utf-8')) if registry.exists() else {}
    limit = config['skill_library']['max_new_skills_per_request']
    if len(created.get(request_id, [])) >= limit:
        raise Refused(f'au plus {limit} nouvelle(s) skill(s) par requête : déjà créée(s) {created[request_id]}')
    return request_id


def remember_creation(request_id: str | None, skill: str) -> None:
    if not request_id:
        return
    registry = creation_registry()
    created = json.loads(registry.read_text(encoding='utf-8')) if registry.exists() else {}
    created.setdefault(request_id, []).append(skill)
    registry.write_text(json.dumps(created, ensure_ascii=False), encoding='utf-8')


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def set_catalog_line(config: dict, skill: str, summary: str) -> None:
    path = paths(config)['catalog']
    start, end = config['skill_library']['catalog_markers']
    text = path.read_text(encoding='utf-8')
    head, rest = text.split(start, 1)
    section, tail = rest.split(end, 1)
    lines = [line for line in section.strip('\n').splitlines() if not line.startswith(f'- `{skill}` ')]
    lines.append(f'- `{skill}` — {summary}')
    path.write_text(head + start + '\n' + '\n'.join(lines) + '\n' + end + tail, encoding='utf-8')


def run_validators(config: dict) -> list[str]:
    substitutions = {'{python}': sys.executable, '{hooks}': str(ROOT / '.agents' / 'hooks'),
                     '{skills}': str(paths(config)['skills'])}
    failures = []
    for command in config['skill_library']['validators']:
        argv = []
        for token in command:
            for key, value in substitutions.items():
                token = token.replace(key, value)
            argv.append(token)
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=300)
        if result.returncode:
            output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
            failures.append(f"{' '.join(command)} :\n{output[-2000:]}")
    return failures


def apply(args, config: dict) -> dict:
    files = paths(config)
    rules = json.loads(files['rules'].read_text(encoding='utf-8'))
    keywords = parse_keywords(args.keywords)
    skill = args.extend or args.name
    if not skill or not NAME.match(skill):
        raise Refused(f'nom de skill invalide : {skill!r} (kebab-case attendu)')
    skill_dir = files['skills'] / skill
    if args.extend:
        if not (skill_dir / 'SKILL.md').is_file():
            raise Refused(f'skill à étendre inexistante : {skill}')
        append = Path(args.append_file).read_text(encoding='utf-8') if args.append_file else None
        if append is not None and PLACEHOLDERS.search(append):
            raise Refused('section ajoutée : placeholder non résolu')
        request_id = None
    else:
        prefix = config['skill_library']['domain_prefix']
        if not skill.startswith(prefix):
            raise Refused(f'une skill de domaine commence par « {prefix} »')
        if skill_dir.exists():
            raise Refused(f'la skill existe déjà : {skill} (utiliser --extend)')
        description = (args.description or '').strip()
        if not description or len(description) > 1024:
            raise Refused('description obligatoire, 1 024 caractères au plus')
        if not args.body_file:
            raise Refused('--body-file obligatoire pour une création')
        body = Path(args.body_file).read_text(encoding='utf-8')
        check_body(body, args.body_file)
        request_id = check_creation_quota(config)
    if not (args.catalog or args.extend):
        raise Refused('--catalog obligatoire : la ligne de catalogue est le signal de routage visible')
    if not args.example_request:
        raise Refused('--example-request obligatoire')
    new_rules = precheck(config, rules, skill, keywords, args.example_request)
    plan = {'skill': skill, 'mode': 'extension' if args.extend else 'creation', 'keywords': keywords,
            'example_request': args.example_request,
            'writes': [str(skill_dir.relative_to(ROOT) / 'SKILL.md'), str(files['rules'].relative_to(ROOT)),
                       str(files['cases'].relative_to(ROOT)), str(files['catalog'].relative_to(ROOT)),
                       str(files['ledger'].relative_to(ROOT)), '.claude/skills/<copies générées>']}
    if args.dry_run:
        plan['status'] = 'SIMULATION'
        return plan
    backups = {path: path.read_bytes() for path in (files['rules'], files['cases'], files['catalog'], files['ledger'])}
    skill_backup = (skill_dir / 'SKILL.md').read_bytes() if args.extend else None
    mirrors = import_from(ROOT / '.agents' / 'hooks', 'skill_mirrors')
    ledger = import_from(SCRIPTS, 'skill_gap_ledger')
    try:
        if args.extend:
            if append is not None:
                text = (skill_dir / 'SKILL.md').read_text(encoding='utf-8').rstrip('\n')
                (skill_dir / 'SKILL.md').write_text(text + '\n\n' + append.strip('\n') + '\n', encoding='utf-8')
        else:
            skill_dir.mkdir(parents=True)
            frontmatter = f'---\nname: {skill}\ndescription: {json.dumps(description, ensure_ascii=False)}\n---\n\n'
            (skill_dir / 'SKILL.md').write_text(frontmatter + body.strip('\n') + '\n', encoding='utf-8')
        rules['rules'] = new_rules
        write_json(files['rules'], rules)
        cases = json.loads(files['cases'].read_text(encoding='utf-8'))
        cases['cases'].append({'request': args.example_request, 'includes': [skill]})
        write_json(files['cases'], cases)
        if args.catalog:
            set_catalog_line(config, skill, args.catalog.strip())
        mirror_result = mirrors.write(ROOT)
        decision = 'etendue' if args.extend else 'creee'
        if args.gap_id:
            ledger.resolve(args.gap_id, decision, skill)
        else:
            entry = ledger.record(f'{"Extension" if args.extend else "Création"} de la skill {skill}',
                                  args.example_request)
            ledger.resolve(entry['id'], decision, skill)
        failures = run_validators(config)
        if failures:
            raise Refused('validateurs en échec, état antérieur restauré :\n' + '\n'.join(failures))
    except Exception:
        for path, data in backups.items():
            path.write_bytes(data)
        if args.extend:
            (skill_dir / 'SKILL.md').write_bytes(skill_backup)
        elif skill_dir.exists():
            shutil.rmtree(skill_dir)
        mirrors.write(ROOT)
        raise
    if not args.extend:
        remember_creation(request_id, skill)
    plan.update(status='PASS', mirrors=mirror_result['written'])
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Créer ou étendre une skill XP-Bots et l\'enregistrer partout.')
    parser.add_argument('--name')
    parser.add_argument('--extend', metavar='SKILL')
    parser.add_argument('--description')
    parser.add_argument('--keywords', required=True)
    parser.add_argument('--catalog')
    parser.add_argument('--example-request', required=True)
    parser.add_argument('--body-file')
    parser.add_argument('--append-file')
    parser.add_argument('--gap-id')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    if bool(args.name) == bool(args.extend):
        print(json.dumps({'status': 'FAIL', 'error': 'indiquer --name (création) ou --extend (extension)'},
                         ensure_ascii=False))
        return 2
    try:
        result = apply(args, load_config())
    except Refused as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""Single governance validator of XP-Bots (standard library; PyYAML used only as a cross-check).

It discovers the skills instead of relying on a frozen list and checks: frontmatter, names,
descriptions, cited resources, placeholders, duplicates; generated copies; adapters; lifecycle
configuration and gates; routing rule, catalog line and test case for every skill; gap ledger;
tool hook files and their events; obsolete paths; parasitic artefacts; MCL preservation and the
historical archive; links to business resources; absence of a second governance.

Usage (from the repository root):
    python .agents/skills/xp-bots-maintain-agent-skills/scripts/validate_governance.py [--quiet] [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
NAME = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
PLACEHOLDERS = re.compile(r'<(?:ROOT|APP|PY|ORCH|AUDIT|GAP|GOV|RULES)>|\{\{[^}]*\}\}|\bTODO\b|\bTBD\b|\bFIXME\b|'
                          r'\bXXX\b|\[(?:À|A) COMPL[ÉE]TER\]|lorem ipsum', re.I)
RESOURCE = re.compile(r'(?<![A-Za-z0-9_./\\-])((?:\.\./[a-z0-9][a-z0-9-]*/)?(?:scripts|references|assets|agents)/'
                      r'[A-Za-z0-9_./-]*[A-Za-z0-9_-])')
ROOT_PATH = re.compile(r'`((?:\.agents|\.claude|\.codex|\.github|\.clinerules|config|docs|livrables|reference|'
                       r'schemas|prompts|tests|tools)/[^`\s<>*]+)`')
LINK = re.compile(r'(?<!!)\[[^\]\n]*\]\(([^)\s]+)\)')
EXPECTED_EVENTS = {'session-start', 'prompt', 'subagent-start', 'stop'}


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.checks = 0

    def check(self, condition: bool, message: str) -> bool:
        self.checks += 1
        if not condition:
            self.errors.append(message)
        return bool(condition)


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def load_json(path: Path, report: Report, label: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'clé dupliquée {key}')
            result[key] = value
        return result
    try:
        return json.loads(read(path), object_pairs_hook=pairs)
    except (OSError, ValueError) as error:
        report.check(False, f'{label} illisible ou JSON invalide : {error}')
        return None


def parse_frontmatter(text: str) -> tuple[dict | None, str, str]:
    """Strict subset parser: `key: value` lines, value plain or double-quoted (JSON escapes)."""
    match = re.match(r'\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)', text, re.S)
    if not match:
        return None, 'frontmatter absent ou non fermé', ''
    values = {}
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        item = re.match(r'^([A-Za-z][A-Za-z0-9_-]*):[ \t]*(.*)$', line)
        if not item:
            return None, f'ligne de frontmatter non conforme : {line[:80]}', ''
        key, raw = item.group(1), item.group(2).strip()
        if key in values:
            return None, f'clé de frontmatter dupliquée : {key}', ''
        if raw.startswith('"'):
            try:
                value = json.loads(raw)
            except ValueError:
                return None, f'valeur entre guillemets invalide pour {key}', ''
        elif raw.startswith(("'", '[', '{', '|', '>', '&', '*', '!')) or ': ' in raw or raw.endswith(':'):
            return None, f'valeur YAML non supportée pour {key} (utiliser une chaîne entre guillemets)', ''
        else:
            value = raw
        values[key] = value
    try:
        import yaml  # optional cross-check only
        if yaml.safe_load(match.group(1)) != values:
            return None, 'frontmatter interprété différemment par PyYAML', ''
    except ImportError:
        pass
    except Exception as error:  # noqa: BLE001 - any YAML error is a frontmatter error
        return None, f'frontmatter YAML invalide : {error}', ''
    return values, '', text[match.end():]


def skill_dirs(skills_dir: Path) -> list[Path]:
    return sorted(entry for entry in skills_dir.iterdir() if entry.is_dir()) if skills_dir.is_dir() else []


def check_skills(report: Report, config: dict) -> dict[str, str]:
    skills_dir = ROOT / config['skill_library']['skills_dir']
    bodies = {}
    seen = {}
    for directory in skill_dirs(skills_dir):
        skill_file = directory / 'SKILL.md'
        if not report.check(skill_file.is_file(), f'dossier de skill sans SKILL.md : {directory.relative_to(ROOT)}'):
            continue
        text = read(skill_file)
        meta, problem, body = parse_frontmatter(text)
        label = directory.name
        if not report.check(meta is not None, f'{label} : {problem}'):
            continue
        report.check(set(meta) == {'name', 'description'},
                     f'{label} : frontmatter minimal attendu (name, description), trouvé {sorted(meta)}')
        name = meta.get('name', '')
        report.check(name == directory.name, f'{label} : name « {name} » différent du dossier')
        report.check(bool(NAME.match(name or '')), f'{label} : name non kebab-case')
        description = meta.get('description', '')
        report.check(isinstance(description, str) and description.strip() != '', f'{label} : description vide')
        report.check(len(description) <= 1024, f'{label} : description de {len(description)} caractères (> 1024)')
        report.check(name not in seen, f'{label} : nom de skill dupliqué avec {seen.get(name)}')
        seen[name] = directory.name
        for match in PLACEHOLDERS.finditer(text):
            report.check(False, f'{label} : placeholder non résolu « {match.group(0)} »')
        for match in RESOURCE.finditer(body):
            target = (directory / match.group(1)).resolve()
            report.check(target.exists(), f'{label} : ressource citée introuvable « {match.group(1)} »')
        for match in ROOT_PATH.finditer(body):
            token = match.group(1).rstrip('.,;:)')
            if '<' in token or token.startswith(('.local/', 'mcl/')):
                continue
            report.check((ROOT / token).exists(), f'{label} : chemin de dépôt cité introuvable « {token} »')
        for path in sorted(directory.rglob('*.md')):
            for match in LINK.finditer(read(path)):
                target = match.group(1).split('#', 1)[0]
                if not target or target.startswith(('http:', 'https:', 'mailto:')):
                    continue
                report.check((path.parent / target).exists(),
                             f'{path.relative_to(ROOT)} : lien local introuvable « {target} »')
        report.check(not (directory / 'README.md').exists(), f'{label} : README auxiliaire interdit dans une skill')
        bodies[name] = body
    return bodies


def check_mirrors(report: Report) -> None:
    sys.path.insert(0, str(ROOT / '.agents' / 'hooks'))
    try:
        import skill_mirrors
        for problem in skill_mirrors.problems(skill_mirrors.inspect(ROOT)):
            report.check(False, f'copies générées : {problem}')
        report.check(True, 'copies générées synchronisées')
    finally:
        sys.path.pop(0)


def check_adapters(report: Report, registry: dict) -> None:
    canonical_lines = set()
    for relative in registry.get('canonical_blocks', []):
        path = ROOT / relative
        if report.check(path.is_file(), f'bloc canonique absent : {relative}'):
            canonical_lines |= {line.strip() for line in read(path).splitlines() if len(line.strip()) >= 70}
    for adapter in registry.get('adapters', []):
        path = ROOT / adapter['path']
        if not report.check(path.is_file(), f"adaptateur absent : {adapter['path']}"):
            continue
        data = path.read_bytes()
        report.check(len(data) <= adapter['max_bytes'],
                     f"adaptateur trop long : {adapter['path']} ({len(data)} > {adapter['max_bytes']} octets)")
        text = data.decode('utf-8')
        for needle in adapter.get('must_contain', []):
            report.check(needle in text, f"adaptateur {adapter['path']} : référence obligatoire absente « {needle} »")
        if adapter['path'] != 'AGENTS.md':
            copied = [line for line in text.splitlines() if line.strip() in canonical_lines]
            report.check(not copied, f"adaptateur {adapter['path']} : bloc canonique recopié « {(copied or [''])[0][:60]} »")


def check_lifecycle(report: Report, config: dict, bodies: dict[str, str]) -> None:
    for role, skill in config['skills'].items():
        report.check(skill in bodies, f'lifecycle.json : skill « {role} » inexistante ({skill})')
    for key in ('selector', 'routing_rules', 'routing_cases'):
        report.check((ROOT / config[key]).is_file(), f'lifecycle.json : fichier {key} absent ({config[key]})')
    for relative in config['rules_files']:
        report.check((ROOT / relative).is_file(), f'lifecycle.json : fichier de règles absent ({relative})')
    keys = config['audit_footer']['keys']
    audit_body = bodies.get(config['skills']['audit'], '')
    report.check(len(keys) == 4 and len(set(keys)) == 4, 'lifecycle.json : le pied d\'audit doit déclarer quatre clés')
    template = re.search(r'```text\n(.*?)```', audit_body, re.S)
    template_keys = re.findall(r'^- ([a-z_]+):', template.group(1), re.M) if template else []
    report.check(template_keys == keys,
                 f'clés du pied inconnues ou divergentes : lifecycle.json {keys} / skill d\'audit {template_keys}')
    for marker in config['audit_markers'].values():
        report.check(marker in audit_body, f'marqueur {marker} absent de la skill d\'audit')
    report.check(config['audit_footer']['header'] in audit_body, 'en-tête du pied absent de la skill d\'audit')
    gates = config.get('gates', [])
    report.check(any(gate.get('fast') for gate in gates), 'lifecycle.json : aucune porte rapide déclarée')
    report.check(any(gate.get('fast') and not gate.get('indicative') for gate in gates),
                 'lifecycle.json : aucune porte rapide bloquante')
    names = set()
    for gate in gates:
        label = f"porte {gate.get('name')}"
        report.check(gate.get('name') not in names, f'{label} : nom dupliqué')
        names.add(gate.get('name'))
        report.check(isinstance(gate.get('patterns'), list) and gate['patterns']
                     and all(isinstance(item, str) and item for item in gate['patterns']), f'{label} : motifs invalides')
        command = gate.get('command')
        if not report.check(isinstance(command, list) and command and all(isinstance(item, str) for item in command),
                            f'{label} : commande invalide'):
            continue
        report.check(isinstance(gate.get('timeout'), (int, float)) and gate['timeout'] > 0, f'{label} : délai invalide')
        for token in command:
            if token.endswith('.py'):
                path = token.replace('{hooks}', '.agents/hooks').replace(
                    '{skills}', config['skill_library']['skills_dir']).replace('{root}', '.')
                report.check((ROOT / path).is_file(), f'{label} : script inexistant {path}')
    library = config['skill_library']
    for command in library.get('validators', []):
        for token in command:
            if token.endswith('.py'):
                path = token.replace('{hooks}', '.agents/hooks').replace('{skills}', library['skills_dir'])
                report.check((ROOT / path).is_file(), f'validateur inexistant : {path}')
    for tool, settings in config['tools'].items():
        report.check(settings.get('format') in ('hook-specific', 'flat', 'report'), f'outil {tool} : format inconnu')


def check_library(report: Report, config: dict, bodies: dict[str, str]) -> None:
    library = config['skill_library']
    rules = load_json(ROOT / config['routing_rules'], report, 'routing-rules.json') or {}
    cases = (load_json(ROOT / config['routing_cases'], report, 'routing-cases.json') or {}).get('cases', [])
    ruled = {rule['skill'] for rule in rules.get('rules', [])}
    special = set(rules.get('default_skills', [])) | set(rules.get('lifecycle_skills', [])) \
        | set(rules.get('routing_exempt_skills', []))
    catalog_text = read(ROOT / library['catalog'])
    start, end = library['catalog_markers']
    section = catalog_text.split(start, 1)[1].split(end, 1)[0] if start in catalog_text and end in catalog_text else ''
    report.check(bool(section), 'catalogue : marqueurs de section absents')
    catalogued = set(re.findall(r'^- `([a-z0-9-]+)` — \S', section, re.M))
    tested = set()
    for case in cases:
        tested |= set(case.get('includes', [])) | set(case.get('expect_exact', []))
    for skill in bodies:
        report.check(skill in ruled or skill in special, f'skill sans règle de routage : {skill}')
        report.check(skill in catalogued, f'skill sans ligne de catalogue : {skill}')
        report.check(skill in tested, f'skill sans cas de test de sélection : {skill}')
    for skill in (ruled | catalogued | special) - set(bodies):
        report.check(False, f'skill enregistrée mais inexistante : {skill}')
    for rule in rules.get('rules', []):
        report.check(bool(rule.get('keywords')), f"règle sans mot-clé : {rule.get('skill')}")
    gap = config['skills']['gap']
    for script in ('skill_gap_ledger.py', 'create_skill.py'):
        report.check((ROOT / library['skills_dir'] / gap / 'scripts' / script).is_file(),
                     f'script de la skill de lacunes absent : {script}')
    ledger = load_json(ROOT / library['ledger'], report, 'registre des lacunes')
    if ledger is not None:
        sys.path.insert(0, str(ROOT / library['skills_dir'] / gap / 'scripts'))
        try:
            import skill_gap_ledger
            for problem in skill_gap_ledger.validate(ledger):
                report.check(False, f'registre des lacunes : {problem}')
        finally:
            sys.path.pop(0)


def hook_entries(document, fmt: str) -> dict[str, list[dict]]:
    hooks = (document or {}).get('hooks', {})
    result = {}
    for event, groups in hooks.items():
        commands = []
        for group in groups or []:
            if fmt == 'copilot-hooks-v1':
                commands.append(group)
            else:
                commands.extend(group.get('hooks', []))
        result[event] = commands
    return result


def check_tools(report: Report, registry: dict, config: dict) -> None:
    sys.path.insert(0, str(ROOT / '.agents' / 'hooks'))
    try:
        import agent_lifecycle
    finally:
        sys.path.pop(0)
    for tool in registry.get('tools', []):
        for relative in tool.get('instruction_files', []):
            report.check((ROOT / relative).is_file(), f"{tool['id']} : fichier d'instructions absent {relative}")
        if not tool.get('hook_file'):
            for mode in tool.get('manual_modes', []):
                report.check(agent_lifecycle.resolve_mode(config, mode) is not None,
                             f"{tool['id']} : mode manuel inconnu du moteur {mode}")
            continue
        path = ROOT / tool['hook_file']
        if not report.check(path.is_file(), f"{tool['id']} : fichier de hooks absent {tool['hook_file']}"):
            continue
        document = load_json(path, report, tool['hook_file'])
        if document is None:
            continue
        if tool['hook_format'] == 'copilot-hooks-v1':
            report.check(document.get('version') == 1, f"{tool['id']} : version de fichier de hooks attendue 1")
        entries = hook_entries(document, tool['hook_format'])
        declared_events = set()
        for event, mode in tool['events'].items():
            commands = entries.get(event, [])
            if not report.check(bool(commands), f"{tool['id']} : événement {event} absent de {tool['hook_file']}"):
                continue
            resolved = agent_lifecycle.resolve_mode(config, mode)
            report.check(resolved is not None, f"{tool['id']} : mode {mode} inconnu du moteur")
            if resolved:
                declared_events.add(resolved[0])
            for command in commands:
                for key in tool.get('required_command_fields', []):
                    value = command.get(key, '')
                    report.check(isinstance(value, str) and mode in value,
                                 f"{tool['id']} : {event} sans variante {key} invoquant {mode}")
                timeout = command.get('timeout', command.get('timeoutSec'))
                report.check(isinstance(timeout, (int, float)) and timeout > 0, f"{tool['id']} : {event} sans délai")
                if resolved and resolved[0] == 'stop':
                    report.check(timeout >= 300, f"{tool['id']} : délai de fin trop court ({timeout} s)")
        for event in entries:
            report.check(event in tool['events'], f"{tool['id']} : événement non déclaré au registre {event}")
        report.check(EXPECTED_EVENTS <= declared_events,
                     f"{tool['id']} : événements attendus manquants {sorted(EXPECTED_EVENTS - declared_events)}")
    hook_files = [tool['hook_file'] for tool in registry.get('tools', []) if tool.get('hook_file')]
    report.check(len(hook_files) == len(set(hook_files)), 'deux outils partagent un même fichier de hooks')
    github_hooks = sorted((ROOT / '.github' / 'hooks').glob('*.json')) if (ROOT / '.github' / 'hooks').is_dir() else []
    report.check(len(github_hooks) <= 1, 'plusieurs fichiers de hooks Copilot : une seule source par outil')


def check_paths(report: Report, registry: dict) -> None:
    for relative in registry.get('obsolete_paths', []):
        report.check(not (ROOT / relative).exists(), f'chemin obsolète réapparu : {relative}')
    allowed = set(registry.get('historical_reference_allowed', []))
    for relative in registry.get('active_governance_files', []):
        base = ROOT / relative
        files = [base] if base.is_file() else sorted(path for path in base.rglob('*') if path.is_file()) if base.is_dir() else []
        for path in files:
            rel = path.relative_to(ROOT).as_posix()
            if rel in allowed or path.suffix not in ('.md', '.json', '.py', '.ps1', '.sh'):
                continue
            if rel.startswith('.agents/hooks/tests/'):
                continue
            text = path.read_text(encoding='utf-8', errors='replace')
            for obsolete in registry.get('obsolete_references', []):
                report.check(obsolete not in text, f'référence active à un chemin obsolète dans {rel} : {obsolete}')
    parasites = [path.relative_to(ROOT).as_posix() for base in ('.agents', '.claude', '.codex', '.clinerules')
                 if (ROOT / base).exists() for path in (ROOT / base).rglob('*')
                 if path.name == '__pycache__' or path.suffix in ('.pyc', '.tmp', '.orig', '.rej', '.zip')
                 or path.name.endswith('~')]
    report.check(not parasites, f'artefacts générés parasites : {parasites[:5]}')


def check_preservation(report: Report, registry: dict) -> None:
    for source in registry.get('preserved_skill_sources', []):
        target = ROOT / source['migrated_to']
        for relative, expected in source['files_sha256'].items():
            path = target / relative
            if report.check(path.is_file(), f"{source['skill']} : fichier migré absent {relative}"):
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                report.check(actual == expected, f"{source['skill']} : empreinte modifiée {relative}")
        present = {path.relative_to(target).as_posix() for path in target.rglob('*') if path.is_file()}
        report.check(present == set(source['files_sha256']),
                     f"{source['skill']} : fichiers hors manifeste {sorted(present - set(source['files_sha256']))}")
        archive = ROOT / source['archive']['path']
        if report.check(archive.is_file(), f"archive historique absente : {source['archive']['path']}"):
            report.check(hashlib.sha256(archive.read_bytes()).hexdigest() == source['archive']['sha256'],
                         'archive historique de MCL modifiée')
    for base in ('.agents/skills', '.claude/skills'):
        zips = list((ROOT / base).rglob('*.zip')) if (ROOT / base).exists() else []
        report.check(not zips, f'archive ZIP découvrable comme skill active sous {base}')


def check_business_links(report: Report) -> None:
    rules = ROOT / '.agents' / 'PROJECT_RULES.md'
    text = read(rules)
    count = 0
    for match in LINK.finditer(text):
        target = match.group(1).split('#', 1)[0]
        if target.startswith(('http:', 'https:')):
            continue
        count += 1
        report.check((rules.parent / target).exists(), f'PROJECT_RULES.md : lien métier introuvable « {target} »')
    report.check(count >= 8, 'PROJECT_RULES.md : carte des ressources métier incomplète')


def check_single_governance(report: Report) -> None:
    extra_agents = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob('AGENTS.md')
                    if path.parent != ROOT and '.git' not in path.parts and '.local' not in path.parts]
    report.check(not extra_agents, f'seconde gouvernance détectée : {extra_agents}')
    engines = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob('*lifecycle*.py')
               if '.git' not in path.parts and '.local' not in path.parts
               and path.relative_to(ROOT).as_posix() != '.agents/hooks/agent_lifecycle.py'
               and not path.relative_to(ROOT).as_posix().startswith('.agents/hooks/tests/')]
    report.check(not engines, f'second moteur de cycle de vie : {engines}')
    nested = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob('.agents')
              if path.is_dir() and path.parent != ROOT and '.git' not in path.parts and '.local' not in path.parts]
    report.check(not nested, f'dossier .agents imbriqué : {nested}')


def validate() -> Report:
    report = Report()
    config = load_json(ROOT / '.agents' / 'hooks' / 'lifecycle.json', report, 'lifecycle.json')
    registry = load_json(ROOT / '.agents' / 'agent-integrations.json', report, 'agent-integrations.json')
    if config is None or registry is None:
        return report
    for step in (lambda: check_skills(report, config),):
        bodies = step()
    for step in (lambda: check_mirrors(report), lambda: check_adapters(report, registry),
                 lambda: check_lifecycle(report, config, bodies), lambda: check_library(report, config, bodies),
                 lambda: check_tools(report, registry, config), lambda: check_paths(report, registry),
                 lambda: check_preservation(report, registry), lambda: check_business_links(report),
                 lambda: check_single_governance(report)):
        try:
            step()
        except Exception as error:  # report every anomaly; one failing family never hides the others
            report.check(False, f'contrôle interrompu : {type(error).__name__}: {error}')
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Validateur de gouvernance XP-Bots.')
    parser.add_argument('--quiet', action='store_true', help='N\'afficher que les erreurs et le bilan.')
    parser.add_argument('--json', action='store_true', help='Sortie JSON.')
    args = parser.parse_args(argv)
    report = validate()
    status = 'FAIL' if report.errors else 'PASS'
    if args.json:
        print(json.dumps({'status': status, 'checks': report.checks, 'errors': report.errors}, ensure_ascii=False, indent=2))
    else:
        for error in report.errors:
            print(f'ERREUR : {error}')
        print(f'Gouvernance XP-Bots : {status} — {report.checks} contrôles, {len(report.errors)} erreur(s).')
    return 1 if report.errors else 0


if __name__ == '__main__':
    sys.exit(main())

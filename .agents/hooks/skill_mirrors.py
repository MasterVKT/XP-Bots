"""Generate and check the skill copies required by tools that cannot read .agents/skills.

The canonical source is .agents/skills/<name>/SKILL.md with its resources. For each mirror
directory declared in .agents/agent-integrations.json, one SKILL.md per skill is generated:
original frontmatter, a generation header, then the body with resource paths rewritten
relative to the repository root (only when the target exists). Scripts and references are
never duplicated.

Usage (from the repository root):
    python .agents/hooks/skill_mirrors.py --check
    python .agents/hooks/skill_mirrors.py --write
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = '.agents/agent-integrations.json'
GENERATOR = '.agents/hooks/skill_mirrors.py'
HEADER_MARK = 'xp-bots:generated-skill-mirror'
# Resource tokens written relative to a skill directory: scripts/, references/, assets/,
# agents/ or ../other-skill/<dir>/. A preceding path character means the token is part of
# another path (for example ".agents/skills" or "mcl/contrats") and is left untouched.
RESOURCE_TOKEN = re.compile(
    r'(?<![A-Za-z0-9_./\\-])((?:\.\./[a-z0-9][a-z0-9-]*/)?(?:scripts|references|assets|agents)/'
    r'(?:[A-Za-z0-9_./-]*[A-Za-z0-9_/-])?)')


def read_registry(root: Path) -> dict:
    return json.loads((root / REGISTRY).read_text(encoding='utf-8'))


def canonical_dir(root: Path) -> Path:
    return root / read_registry(root).get('canonical_skills_dir', '.agents/skills')


def mirror_dirs(root: Path) -> list[Path]:
    return [root / item['dir'] for item in read_registry(root).get('mirrors', [])]


def canonical_skills(root: Path) -> dict[str, Path]:
    base = canonical_dir(root)
    if not base.is_dir():
        return {}
    return {entry.name: entry / 'SKILL.md' for entry in sorted(base.iterdir())
            if entry.is_dir() and (entry / 'SKILL.md').is_file()}


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter including both --- lines and the final newline, body)."""
    match = re.match(r'\A(---\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z))', text, re.S)
    if not match:
        raise ValueError('frontmatter YAML absent ou non fermé')
    return match.group(1), text[match.end():]


def rewrite_paths(body: str, skill_dir: Path, root: Path) -> str:
    def replace(match: re.Match) -> str:
        token = match.group(1)
        clean = token.rstrip('/')
        target = Path(os.path.normpath(skill_dir / clean))
        try:
            relative = target.relative_to(root)
        except ValueError:
            return token
        if not target.exists() or '*' in token:
            return token
        rewritten = relative.as_posix()
        return rewritten + ('/' if token.endswith('/') else '')
    return RESOURCE_TOKEN.sub(replace, body)


def render_mirror(root: Path, name: str, source: Path) -> str:
    text = source.read_bytes().decode('utf-8')
    newline = '\r\n' if '\r\n' in text else '\n'
    frontmatter, body = split_frontmatter(text)
    source_rel = source.relative_to(root).as_posix()
    skill_rel = source.parent.relative_to(root).as_posix()
    header = (
        f'<!-- {HEADER_MARK} source={source_rel} generator={GENERATOR} : ne pas éditer -->{newline}'
        f'> Copie générée de `{source_rel}` par `{GENERATOR} --write`. Ne pas éditer : modifier la '
        f'source puis régénérer. Répertoire des ressources de ce skill : `{skill_rel}/` ; les chemins '
        f'de ressources ci-dessous sont relatifs à la racine du dépôt.{newline}'
    )
    return frontmatter + header + rewrite_paths(body, source.parent, root)


def is_generated(path: Path) -> bool:
    try:
        return HEADER_MARK in path.read_text(encoding='utf-8', errors='replace')[:4000]
    except OSError:
        return False


def inspect(root: Path) -> dict:
    """Compare every mirror directory with the canonical source."""
    report = {'missing': [], 'different': [], 'stale': [], 'tool_only': [], 'parasites': [],
              'expected': 0}
    skills = canonical_skills(root)
    for mirror in mirror_dirs(root):
        expected = {name: render_mirror(root, name, source) for name, source in skills.items()}
        report['expected'] += len(expected)
        for name, content in expected.items():
            target = mirror / name / 'SKILL.md'
            if not target.is_file():
                report['missing'].append(target.relative_to(root).as_posix())
            elif target.read_bytes() != content.encode('utf-8'):
                report['different'].append(target.relative_to(root).as_posix())
        if not mirror.is_dir():
            continue
        for entry in sorted(mirror.iterdir()):
            rel = entry.relative_to(root).as_posix()
            if not entry.is_dir():
                report['parasites'].append(rel)
                continue
            skill_file = entry / 'SKILL.md'
            if entry.name not in expected:
                if skill_file.is_file() and is_generated(skill_file):
                    report['stale'].append(rel)
                else:
                    report['tool_only'].append(rel)
                continue
            for item in sorted(entry.rglob('*')):
                if item.is_file() and item != skill_file:
                    report['parasites'].append(item.relative_to(root).as_posix())
    return report


def problems(report: dict) -> list[str]:
    labels = {'missing': 'copie absente', 'different': 'copie éditée à la main ou périmée',
              'stale': 'copie périmée (skill supprimée de la source)',
              'tool_only': 'skill présente seulement côté outil',
              'parasites': 'fichier parasite dans un dossier de copies'}
    return [f'{labels[key]} : {path}' for key in labels for path in report[key]]


def write(root: Path) -> dict:
    report = inspect(root)
    skills = canonical_skills(root)
    written = []
    for mirror in mirror_dirs(root):
        for name, source in skills.items():
            target = mirror / name / 'SKILL.md'
            content = render_mirror(root, name, source).encode('utf-8')
            if not target.is_file() or target.read_bytes() != content:
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name('.SKILL.md.tmp')
                temporary.write_bytes(content)
                os.replace(temporary, target)
                written.append(target.relative_to(root).as_posix())
    removed = []
    for rel in report['stale']:
        directory = root / rel
        leftovers = [item for item in directory.rglob('*') if item.is_file() and item.name != 'SKILL.md']
        if not leftovers:
            (directory / 'SKILL.md').unlink()
            directory.rmdir()
            removed.append(rel)
    after = inspect(root)
    return {'written': written, 'removed_stale': removed,
            'left_untouched': after['tool_only'] + after['parasites'] + after['stale'],
            'problems': problems(after)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true', help='Échoue en listant les écarts.')
    group.add_argument('--write', action='store_true', help='Régénère les copies.')
    parser.add_argument('--root', default=None, help='Racine du dépôt (défaut : déduite du script).')
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else ROOT
    if args.check:
        found = problems(inspect(root))
        print(json.dumps({'status': 'FAIL' if found else 'PASS', 'problems': found},
                         ensure_ascii=False, indent=2))
        return 1 if found else 0
    result = write(root)
    result['status'] = 'FAIL' if result['problems'] else 'PASS'
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['problems'] else 0


if __name__ == '__main__':
    sys.exit(main())

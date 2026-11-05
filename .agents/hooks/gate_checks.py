"""Fast deterministic file checks used as blocking gates by agent_lifecycle.py.

Usage (from the repository root, on the matched files only):
    python .agents/hooks/gate_checks.py json <files...>     strict JSON (no duplicate key, no NaN)
    python .agents/hooks/gate_checks.py python <files...>   syntax only: no import, no bytecode
    python .agents/hooks/gate_checks.py links <files...>    local Markdown links resolve

Every anomaly is reported on standard output (never only the first one); exit code 1 if any.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r'(?<!!)\[[^\]\n]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
FENCE = re.compile(r'^(```|~~~)')


def resolve(name: str) -> Path:
    path = Path(name)
    return path if path.is_absolute() else ROOT / path


def check_json(path: Path) -> list[str]:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'clé dupliquée « {key} »')
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f'nombre non fini {value}')

    try:
        json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs, parse_constant=nonfinite)
    except (ValueError, UnicodeDecodeError) as error:
        return [f'JSON invalide : {error}']
    return []


def check_python(path: Path) -> list[str]:
    try:
        ast.parse(path.read_bytes(), filename=str(path))
    except (SyntaxError, ValueError) as error:
        return [f'syntaxe Python invalide : {error}']
    return []


def check_links(path: Path) -> list[str]:
    problems = []
    in_fence = False
    for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        scrubbed = re.sub(r'`[^`]*`', '', line)
        for match in LINK.finditer(scrubbed):
            target = match.group(1).strip('<>')
            if target.startswith(('http:', 'https:', 'mailto:', '#')) or '://' in target:
                continue
            target = unquote(target.split('#', 1)[0])
            if not target:
                continue
            if not (path.parent / target).exists():
                problems.append(f'ligne {number} : lien local introuvable « {target} »')
    return problems


CHECKS = {'json': check_json, 'python': check_python, 'links': check_links}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in CHECKS:
        print('usage : gate_checks.py {json|python|links} <fichiers...>')
        return 2
    check = CHECKS[argv[0]]
    failures = 0
    for name in argv[1:]:
        path = resolve(name)
        if not path.is_file():
            continue
        for problem in check(path):
            failures += 1
            try:
                shown = path.relative_to(ROOT).as_posix()
            except ValueError:
                shown = str(path)
            print(f'{shown} : {problem}')
    print(f'{argv[0]} : {len(argv) - 1} fichier(s), {failures} anomalie(s)')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

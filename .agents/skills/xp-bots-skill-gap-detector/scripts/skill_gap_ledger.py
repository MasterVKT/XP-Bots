"""Skill gap ledger of XP-Bots: record, resolve, show and list task types not covered by a skill.

The ledger path and the promotion threshold come from .agents/hooks/lifecycle.json.
A one-off gap ("consignee") is promoted ("promue") at its second occurrence.

Usage (from the repository root):
    python .agents/skills/xp-bots-skill-gap-detector/scripts/skill_gap_ledger.py record --label "..." [--evidence "..."]
    python .agents/skills/xp-bots-skill-gap-detector/scripts/skill_gap_ledger.py resolve --id <id> --decision <decision> [--skill <nom>]
    python .agents/skills/xp-bots-skill-gap-detector/scripts/skill_gap_ledger.py show --id <id>
    python .agents/skills/xp-bots-skill-gap-detector/scripts/skill_gap_ledger.py list
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
DECISIONS = ('consignee', 'proposee', 'promue', 'creee', 'etendue', 'rejetee')
MAX_EVIDENCE = 5
MAX_EVIDENCE_CHARS = 300
ENTRY_KEYS = {'id', 'label', 'occurrences', 'first_seen', 'last_seen', 'evidence', 'decision', 'skill'}


def config() -> dict:
    return json.loads((ROOT / '.agents' / 'hooks' / 'lifecycle.json').read_text(encoding='utf-8'))


def ledger_path() -> Path:
    return ROOT / config()['skill_library']['ledger']


def normalize_id(label: str) -> str:
    text = unicodedata.normalize('NFKD', label)
    text = ''.join(char for char in text if not unicodedata.combining(char)).lower()
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')[:80]


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def empty_ledger() -> dict:
    return {'schema_version': 1, 'description': 'Registre des lacunes de skills XP-Bots.', 'entries': []}


def load() -> dict:
    path = ledger_path()
    if not path.exists():
        return empty_ledger()
    return json.loads(path.read_text(encoding='utf-8'))


def save(ledger: dict) -> None:
    problems = validate(ledger)
    if problems:
        raise ValueError('registre non conforme : ' + '; '.join(problems))
    path = ledger_path()
    handle, temporary = tempfile.mkstemp(prefix='ledger.', suffix='.tmp', dir=str(path.parent))
    with os.fdopen(handle, 'w', encoding='utf-8') as stream:
        stream.write(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')
    os.replace(temporary, path)


def validate(ledger) -> list[str]:
    problems = []
    if not isinstance(ledger, dict) or ledger.get('schema_version') != 1 or not isinstance(ledger.get('entries'), list):
        return ['structure attendue {schema_version: 1, entries: [...]}']
    seen = set()
    for index, entry in enumerate(ledger['entries'], 1):
        label = f'entrée {index}'
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
            problems.append(f'{label} : clés attendues {sorted(ENTRY_KEYS)}')
            continue
        if entry['id'] != normalize_id(entry['label']) or not entry['id']:
            problems.append(f"{label} : identifiant non normalisé « {entry['id']} »")
        if entry['id'] in seen:
            problems.append(f"{label} : identifiant dupliqué « {entry['id']} »")
        seen.add(entry['id'])
        if entry['decision'] not in DECISIONS:
            problems.append(f"{label} : décision hors vocabulaire « {entry['decision']} »")
        if not isinstance(entry['occurrences'], int) or entry['occurrences'] < 1:
            problems.append(f'{label} : occurrences invalides')
        if not isinstance(entry['evidence'], list) or len(entry['evidence']) > MAX_EVIDENCE \
                or any(not isinstance(item, str) or len(item) > MAX_EVIDENCE_CHARS for item in entry['evidence']):
            problems.append(f'{label} : preuves non bornées')
        if entry['decision'] in ('creee', 'etendue') and not entry['skill']:
            problems.append(f'{label} : décision {entry["decision"]} sans skill associée')
        for key in ('first_seen', 'last_seen'):
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(entry[key])):
                problems.append(f'{label} : date {key} invalide')
    return problems


def find(ledger: dict, identifier: str) -> dict | None:
    return next((entry for entry in ledger['entries'] if entry['id'] == identifier), None)


def record(label: str, evidence: str | None) -> dict:
    ledger = load()
    identifier = normalize_id(label)
    if not identifier:
        raise ValueError('libellé vide')
    entry = find(ledger, identifier)
    if entry is None:
        entry = {'id': identifier, 'label': label, 'occurrences': 0, 'first_seen': today(), 'last_seen': today(),
                 'evidence': [], 'decision': 'consignee', 'skill': None}
        ledger['entries'].append(entry)
    entry['occurrences'] += 1
    entry['last_seen'] = today()
    if evidence:
        entry['evidence'] = (entry['evidence'] + [evidence[:MAX_EVIDENCE_CHARS]])[-MAX_EVIDENCE:]
    threshold = config()['skill_library']['promotion_threshold']
    if entry['decision'] == 'consignee' and entry['occurrences'] >= threshold:
        entry['decision'] = 'promue'
    save(ledger)
    return entry


def resolve(identifier: str, decision: str, skill: str | None) -> dict:
    if decision not in DECISIONS:
        raise ValueError(f'décision hors vocabulaire : {decision} (attendu : {", ".join(DECISIONS)})')
    ledger = load()
    entry = find(ledger, identifier)
    if entry is None:
        raise ValueError(f'lacune inconnue : {identifier}')
    entry['decision'] = decision
    entry['skill'] = skill or entry['skill']
    entry['last_seen'] = today()
    save(ledger)
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Registre des lacunes de skills XP-Bots.')
    sub = parser.add_subparsers(dest='command', required=True)
    rec = sub.add_parser('record', help='Consigner une occurrence de lacune.')
    rec.add_argument('--label', required=True)
    rec.add_argument('--evidence')
    res = sub.add_parser('resolve', help='Enregistrer une décision.')
    res.add_argument('--id', required=True)
    res.add_argument('--decision', required=True)
    res.add_argument('--skill')
    show = sub.add_parser('show', help='Afficher une lacune.')
    show.add_argument('--id', required=True)
    sub.add_parser('list', help='Lister les lacunes.')
    args = parser.parse_args(argv)
    try:
        if args.command == 'record':
            result = record(args.label, args.evidence)
        elif args.command == 'resolve':
            result = resolve(args.id, args.decision, args.skill)
        elif args.command == 'show':
            result = find(load(), args.id)
            if result is None:
                raise ValueError(f'lacune inconnue : {args.id}')
        else:
            result = load()['entries']
    except ValueError as error:
        print(json.dumps({'status': 'FAIL', 'error': str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())

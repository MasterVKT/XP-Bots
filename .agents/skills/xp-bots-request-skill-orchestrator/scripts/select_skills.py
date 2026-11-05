"""Deterministic skill selector for XP-Bots (standard library only).

Rules and test cases are data (references/routing-rules.json, references/routing-cases.json).
Keyword forms: single word (compared with the words of the text), prefix ending with "*",
and compound expression (space, hyphen, apostrophe, slash, dot or colon) compared with the
whole normalized text.

Usage:
    python select_skills.py --explain "vérifier le repli EMA15/25/50 et RSI14"
    python select_skills.py --test
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import unicodedata

SKILL_DIR = Path(__file__).resolve().parents[1]
RULES_PATH = SKILL_DIR / 'references' / 'routing-rules.json'
CASES_PATH = SKILL_DIR / 'references' / 'routing-cases.json'
WORD = re.compile(r'[a-z0-9_]+')
COMPOUND = re.compile(r"[\s\-'/.:]")
STOPWORDS = frozenset('''
a ai au aux avec ce ces cet cette dans de des du elle en est et etre il ils je la le les leur lui ma mais
me mes moi mon ne nos notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une
vos votre vous y ca cela ceci tout tous toute toutes fait faire faut peux peut veux voudrais merci stp svp
plus moins bien tres aussi donc alors ici the and for with this that from into your you are was were be is
it of to in on an or as at by if not do does can please
'''.split())


def normalize(text: str) -> str:
    text = unicodedata.normalize('NFKD', text or '')
    text = ''.join(char for char in text if not unicodedata.combining(char)).lower()
    text = text.replace('’', "'").replace('‘', "'")
    text = re.sub('[‐-―−]', '-', text)
    return re.sub(r'\s+', ' ', text).strip()


def load_rules(path: Path | None = None) -> dict:
    return json.loads((path or RULES_PATH).read_text(encoding='utf-8'))


def keyword_matches(keyword: str, text: str, words: set[str]) -> bool:
    key = normalize(keyword)
    if not key:
        return False
    if key.endswith('*'):
        stem = key[:-1]
        if COMPOUND.search(stem):
            return re.search(r'(?<![a-z0-9_])' + re.escape(stem), text) is not None
        return any(word.startswith(stem) for word in words)
    if COMPOUND.search(key):
        return re.search(r'(?<![a-z0-9_])' + re.escape(key) + r'(?![a-z0-9_])', text) is not None
    return key in words


def useful_word_count(text: str) -> int:
    return sum(1 for word in WORD.findall(normalize(text)) if len(word) >= 3 and word not in STOPWORDS)


def analyze(text: str, rules: dict | None = None) -> dict:
    """Return the selection plus matched skills, triggered fallbacks and a no-match signal."""
    rules = rules or load_rules()
    normalized = normalize(text)
    words = set(WORD.findall(normalized))
    matched, keywords_hit = [], {}
    for rule in rules.get('rules', []):
        hits = [keyword for keyword in rule.get('keywords', []) if keyword_matches(keyword, normalized, words)]
        if hits and rule['skill'] not in matched:
            matched.append(rule['skill'])
            keywords_hit[rule['skill']] = hits
    fallbacks = []
    for fallback in rules.get('fallbacks', []):
        if fallback['skill'] in matched:
            continue
        if any(skill in matched for skill in fallback.get('unless_selected', [])):
            continue
        if any(keyword_matches(trigger, normalized, words) for trigger in fallback.get('triggers', [])):
            fallbacks.append(fallback['skill'])
    defaults = list(rules.get('default_skills', []))
    leading = defaults[:1]
    trailing = [skill for skill in defaults[1:] if skill not in matched and skill not in fallbacks]
    selection = []
    for skill in leading + matched + fallbacks + trailing:
        if skill not in selection:
            selection.append(skill)
    return {'selection': selection, 'matched': matched, 'fallbacks': fallbacks,
            'keywords': keywords_hit, 'no_match': not matched and not fallbacks,
            'useful_words': useful_word_count(text)}


def select(text: str, rules: dict | None = None) -> list[str]:
    """Compatibility interface: only the ordered list of skills."""
    return analyze(text, rules)['selection']


def run_cases(rules: dict | None = None, cases_path: Path | None = None,
              skills_dir: Path | None = None) -> list[str]:
    rules = rules or load_rules()
    cases = json.loads((cases_path or CASES_PATH).read_text(encoding='utf-8'))['cases']
    failures = []
    for index, case in enumerate(cases, 1):
        result = analyze(case['request'], rules)
        chosen = result['selection']
        label = f"cas {index} « {case['request'][:60]} »"
        if 'expect_exact' in case and chosen != case['expect_exact']:
            failures.append(f'{label} : attendu {case["expect_exact"]}, obtenu {chosen}')
        for skill in case.get('includes', []):
            if skill not in chosen:
                failures.append(f'{label} : {skill} absent de {chosen}')
        for skill in case.get('excludes', []):
            if skill in chosen:
                failures.append(f'{label} : {skill} ne devait pas être sélectionnée')
        if 'expect_no_match' in case and result['no_match'] != case['expect_no_match']:
            failures.append(f'{label} : signal no_match {result["no_match"]} au lieu de {case["expect_no_match"]}')
        if 'max_selected' in case and len(chosen) > case['max_selected']:
            failures.append(f'{label} : {len(chosen)} skills au lieu de {case["max_selected"]} au plus')
    skills_dir = skills_dir or SKILL_DIR.parent
    known = {entry.name for entry in skills_dir.iterdir() if (entry / 'SKILL.md').is_file()}
    routed = (set(rules.get('default_skills', [])) | set(rules.get('lifecycle_skills', []))
              | set(rules.get('routing_exempt_skills', [])) | {rule['skill'] for rule in rules.get('rules', [])}
              | {fallback['skill'] for fallback in rules.get('fallbacks', [])})
    for skill in sorted(known - routed):
        failures.append(f'skill non routée : {skill}')
    tested = set()
    for case in cases:
        tested |= set(case.get('includes', [])) | set(case.get('expect_exact', []))
    for skill in sorted(known - tested):
        failures.append(f'skill sans cas de test de sélection : {skill}')
    for skill in sorted(routed - known):
        failures.append(f'règle de routage vers une skill inexistante : {skill}')
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Sélecteur déterministe des skills XP-Bots.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--explain', metavar='REQUETE', help='Afficher la sélection et ses raisons.')
    group.add_argument('--select', metavar='REQUETE', help='Afficher seulement la liste sélectionnée.')
    group.add_argument('--test', action='store_true', help='Exécuter les cas de test de sélection.')
    parser.add_argument('--rules', default=None, help='Fichier de règles (défaut : celui du skill).')
    parser.add_argument('--cases', default=None, help='Fichier de cas (défaut : celui du skill).')
    args = parser.parse_args(argv)
    rules = load_rules(Path(args.rules)) if args.rules else load_rules()
    if args.test:
        failures = run_cases(rules, Path(args.cases) if args.cases else None)
        print(json.dumps({'status': 'FAIL' if failures else 'PASS', 'failures': failures},
                         ensure_ascii=False, indent=2))
        return 1 if failures else 0
    if args.select:
        print(json.dumps(select(args.select, rules), ensure_ascii=False))
        return 0
    print(json.dumps(analyze(args.explain, rules), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())

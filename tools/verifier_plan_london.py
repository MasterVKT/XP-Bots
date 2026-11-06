"""Contrôle mécanique de couverture du plan du robot London (docs/architecture/robot_london_v3).

Sans réseau ni dépendance. Vérifie que le document 06 rattache chaque paramètre figé, chaque section de la
spécification 02 et chaque consigne d'expert à un emplacement du plan ; que les motifs minimaux de C09 sont
traités par le document 01 ; que les cas d'acceptation C11, S02.6 et A14 sont affectés par le document 03 ; que
les décisions du plan directeur sont toutes arrêtées ; que chaque action humaine a sa procédure (document 07) ;
que chaque étape et chaque garde-fou de la skill de planification a sa preuve (document 06, §8) ; que les phases
0 à 12 n'exigent aucune action humaine et que les actions H-02 et suivantes se situent en phase 13 (plan
directeur, documents 04 et 07) ; que chaque frontière du document 02 a son contrat au document 08, et réciproquement.
Les listes attendues sont dérivées des sources (spécification, exports, skill), jamais recopiées ici.
Code de sortie 0 si tout est couvert, 1 sinon.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'docs' / 'architecture' / 'robot_london_v3'
SPEC = ROOT / 'livrables' / 'strategies_m15' / '02_London_Breakout_M15_Specification_IA.md'
CONFIG = ROOT / 'config' / 'parametres_figes_v3.json'
CONFIG_IA = ROOT / 'config' / 'parametres_IA_integration_v1.json'
SKILL_PLANIFICATION = ROOT / '.agents' / 'skills' / 'xp-bots-mcl-robot-planning' / 'SKILL.md'
VERDICTS = ('aligné', 'écart figé', 'instrumenté', 'hors robot')
STATUTS_ARRETES = ('Arrêtée', 'Autorisée', 'Note')


def identifiants_contigus(ids: list[str], prefixe: str) -> bool:
    return ids == [f'{prefixe}{i:02d}' for i in range(1, len(ids) + 1)]


def lire(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def json_strict(path: Path):
    def paires(items):
        resultat = {}
        for cle, valeur in items:
            if cle in resultat:
                raise ValueError(f'clé dupliquée « {cle} » dans {path.name}')
            resultat[cle] = valeur
        return resultat
    return json.loads(lire(path), object_pairs_hook=paires)


def section(texte: str, debut_titre: str) -> str:
    """Section Markdown dont le titre commence par debut_titre, jusqu'au titre de niveau égal ou supérieur."""
    lignes = texte.splitlines()
    for i, ligne in enumerate(lignes):
        if not ligne.startswith('#'):
            continue
        niveau = len(ligne) - len(ligne.lstrip('#'))
        if not ligne[niveau:].strip().startswith(debut_titre):
            continue
        fin = len(lignes)
        for j in range(i + 1, len(lignes)):
            autre = lignes[j]
            if autre.startswith('#') and len(autre) - len(autre.lstrip('#')) <= niveau:
                fin = j
                break
        return '\n'.join(lignes[i:fin])
    raise ValueError(f'section introuvable : « {debut_titre} »')


def lignes_tableau(texte: str) -> list[list[str]]:
    """Cellules des lignes de données des tableaux Markdown (en-têtes et séparateurs exclus)."""
    resultat, apres_separateur = [], False
    for ligne in texte.splitlines():
        brute = ligne.strip()
        if not brute.startswith('|'):
            apres_separateur = False
            continue
        cellules = [cellule.strip() for cellule in brute.strip('|').split('|')]
        if all(re.fullmatch(r':?-{3,}:?', cellule) for cellule in cellules):
            apres_separateur = True
        elif apres_separateur:
            resultat.append(cellules)
    return resultat


def verifier() -> tuple[dict, list[str]]:
    problemes: list[str] = []
    resume: dict = {}
    doc01 = lire(PLAN / '01_architecture.md')
    doc03 = lire(PLAN / '03_acceptation_et_tests.md')
    doc06 = lire(PLAN / '06_verification_exhaustive.md')
    spec = lire(SPEC)
    config = json_strict(CONFIG)
    config_ia = json_strict(CONFIG_IA)

    # 1. Chaque clé des exports figés est rattachée à une unité dans le document 06.
    for nom, cles, debut in (('common', list(config['common']), '2.1'),
                             ('london', list(config['london']), '2.2'),
                             ('IA', list(config_ia), '3.')):
        texte = section(doc06, debut)
        annonce = re.search(r'\((\d+) clés\)', texte.splitlines()[0])
        if not annonce or int(annonce.group(1)) != len(cles):
            problemes.append(f'document 06, §{debut} : nombre de clés annoncé différent de {len(cles)}')
        manquantes = [cle for cle in cles if f'`{cle}`' not in texte]
        problemes += [f'clé {nom} « {cle} » non rattachée (document 06, §{debut})' for cle in manquantes]
        resume[f'cles_{nom}'] = {'total': len(cles), 'rattachees': len(cles) - len(manquantes)}

    # 2. Chaque motif minimal de C09 figure dans la table de correspondance du document 01.
    trouve = re.search(r'Motifs minimaux : (.*?)\.\n', spec)
    if not trouve:
        problemes.append('spécification : liste des motifs minimaux de C09 introuvable')
        codes = []
    else:
        codes = [code.strip() for code in trouve.group(1).split(',')]
    table_motifs = section(doc01, '9.3')
    problemes += [f'motif C09 « {code} » absent du document 01, §9.3' for code in codes
                  if f'`{code}`' not in table_motifs]
    resume['motifs_c09'] = len(codes)

    # 3. Chaque cas d'acceptation est affecté dans le document 03.
    for titre_spec, motif_ligne, prefixe, debut_doc03 in (
            ('C11 ', r'^\d+\. ', 'C11.', '5.1'),
            ('S02.6 ', r'^- ', 'S02.6-', '5.2'),
            ('A14 ', r'^- ', 'A14-', '5.3')):
        nombre = len(re.findall(motif_ligne, section(spec, titre_spec), re.M))
        affectes = {ligne[0] for ligne in lignes_tableau(section(doc03, debut_doc03))}
        manquants = [f'{prefixe}{i}' for i in range(1, nombre + 1) if f'{prefixe}{i}' not in affectes]
        problemes += [f'cas « {cas} » non affecté (document 03, §{debut_doc03})' for cas in manquants]
        resume[f'cas_{titre_spec.strip()}'] = {'total': nombre, 'affectes': nombre - len(manquants)}

    # 4. Chaque section de la spécification figure dans la matrice du document 06, §4.
    matrice = lignes_tableau(section(doc06, '4.'))
    ids_lignes = [ligne[0] for ligne in matrice]
    for doublon in sorted({i for i in ids_lignes if ids_lignes.count(i) > 1}):
        problemes.append(f'matrice du document 06 : identifiant en double « {doublon} »')
    attendues = re.findall(r'^#{2,3} (C\d\d|A\d\d|S02(?:\.\d)?|R)(?= —)', spec, re.M)
    points_c03 = re.findall(r'^(\d+)\. ', section(spec, 'C03 '), re.M)
    attendues += [f'C03.{point}' for point in points_c03]
    for ident in attendues:
        exact = ident.startswith('C03.')
        couvert = any(ligne == ident or (not exact and (ligne.startswith(ident + '-')
                                                         or ligne.startswith(ident + '.')))
                      for ligne in ids_lignes)
        if not couvert:
            problemes.append(f'section « {ident} » de la spécification absente de la matrice (document 06, §4)')
    problemes += [f'matrice : la ligne « {ligne[0]} » ne désigne aucun emplacement du plan'
                  for ligne in matrice if len(ligne) < 4 or not ligne[2] or ligne[2] == '—']
    resume['sections_specification'] = {'attendues': len(attendues), 'lignes_matrice': len(matrice)}

    # 5. Chaque consigne d'expert a un identifiant contigu, un verdict reconnu et un traitement.
    consignes = lignes_tableau(section(doc06, '5.'))
    ids_consignes = [ligne[0] for ligne in consignes]
    attendus = [f'E-{i:02d}' for i in range(1, len(consignes) + 1)]
    if ids_consignes != attendus:
        problemes.append('table des consignes d\'expert : identifiants non contigus ou en double')
    for ligne in consignes:
        if len(ligne) < 5 or not any(v in ligne[3].lower() for v in VERDICTS) or not ligne[4]:
            problemes.append(f'consigne « {ligne[0]} » : verdict non reconnu ou traitement vide')
    resume['consignes_expert'] = len(consignes)

    # 6. Les décisions du plan directeur sont toutes arrêtées, autorisées ou de simple note.
    plan_directeur = lire(PLAN / 'README.md')
    decisions = lignes_tableau(section(plan_directeur, '3.'))
    if not identifiants_contigus([ligne[0] for ligne in decisions], 'D-'):
        problemes.append('plan directeur, §3 : identifiants de décision non contigus ou en double')
    for ligne in decisions:
        statut = ligne[2].replace('*', '').strip() if len(ligne) > 2 else ''
        if not statut.startswith(STATUTS_ARRETES):
            problemes.append(f'décision « {ligne[0]} » non arrêtée (statut : « {statut[:40]} »)')
    resume['decisions'] = len(decisions)

    # 7. Chaque action humaine du plan directeur a sa procédure dans le document 07, et réciproquement.
    actions = [ligne[0] for ligne in lignes_tableau(section(plan_directeur, '5.'))]
    if not identifiants_contigus(actions, 'H-'):
        problemes.append('plan directeur, §5 : identifiants d\'action humaine non contigus ou en double')
    procedures = re.findall(r'^## (H-\d\d) — ', lire(PLAN / '07_procedures_humaines.md'), re.M)
    problemes += [f'action « {a} » sans procédure (document 07)' for a in actions if a not in procedures]
    problemes += [f'procédure « {p} » absente du plan directeur, §5' for p in procedures if p not in actions]
    resume['actions_humaines'] = {'plan_directeur': len(actions), 'procedures': len(procedures)}

    # 8. Chaque étape et chaque garde-fou de la skill de planification a sa preuve (document 06, §8).
    skill = lire(SKILL_PLANIFICATION)
    etapes = len(re.findall(r'^\d+\. ', section(skill, 'Workflow'), re.M))
    garde_fous = len(re.findall(r'^- ', section(skill, 'Garde-fous'), re.M))
    application = {ligne[0]: ligne for ligne in lignes_tableau(section(doc06, '8.'))}
    attendus_skill = ([f'M-{i:02d}' for i in range(1, etapes + 1)]
                      + [f'G-{i:02d}' for i in range(1, garde_fous + 1)])
    for ident in attendus_skill:
        ligne = application.get(ident)
        if not ligne or len(ligne) < 4 or not ligne[2] or not ligne[3]:
            problemes.append(f'skill de planification : « {ident} » sans application ni preuve (document 06, §8)')
    resume['skill_planification'] = {'etapes': etapes, 'garde_fous': garde_fous,
                                     'lignes': len(application)}

    # 9. Les phases 0 à 12 n'exigent aucune action humaine ; plan directeur et document 04 ont les mêmes phases.
    derniere_phase_autonome = 12
    phases = [ligne for ligne in lignes_tableau(section(plan_directeur, '2.3')) if re.fullmatch(r'\d+', ligne[0])]
    doc04 = lire(PLAN / '04_phases.md')
    fiches = re.findall(r'^## Phase (\d+) — ', doc04, re.M)
    if [ligne[0] for ligne in phases] != fiches:
        problemes.append('phases du plan directeur (§2.3) et du document 04 différentes')
    for ligne in phases:
        if int(ligne[0]) <= derniere_phase_autonome and (len(ligne) < 4 or ligne[3] != '—'):
            problemes.append(f'plan directeur, §2.3 : la phase {ligne[0]} exige une action humaine')
    for numero in fiches:
        if int(numero) <= derniere_phase_autonome:
            citees = sorted(set(re.findall(r'\bH-(?:0[2-9]|1\d)\b', section(doc04, f'Phase {numero} '))))
            if citees:
                problemes.append(f'document 04, phase {numero} : actions humaines citées ({", ".join(citees)})')
    resume['phases'] = {'total': len(phases),
                        'sans_action_humaine': sum(int(ligne[0]) <= derniere_phase_autonome for ligne in phases)}

    # 10. Les actions humaines autres que H-01 se situent toutes en phase 13 (plan directeur, §5, et document 07).
    en_phase_13 = re.compile(r'\b13\.\d')
    for ligne in lignes_tableau(section(plan_directeur, '5.')):
        if ligne[0] != 'H-01' and (len(ligne) < 2 or not en_phase_13.search(ligne[1])):
            problemes.append(f'action « {ligne[0]} » hors de la phase 13 (plan directeur, §5)')
    doc07 = lire(PLAN / '07_procedures_humaines.md')
    for ident in procedures:
        if ident == 'H-01':
            continue
        quand = re.search(r'^- \*\*Quand\*\* : (.*)$', section(doc07, ident + ' '), re.M)
        if not quand or not en_phase_13.search(quand.group(1)):
            problemes.append(f'procédure « {ident} » : moment hors de la phase 13 (document 07)')
    resume['actions_en_phase_13'] = len([a for a in actions if a != 'H-01'])

    # 11. Chaque frontière du document 02, §7, a son contrat au document 08, §1, et réciproquement ; chaque
    #     paragraphe cité par la table existe et chaque contrat a une vérification réelle.
    frontieres = [ligne[0] for ligne in lignes_tableau(section(lire(PLAN / '02_cartographie_mcl.md'), '7.'))]
    doc08 = lire(PLAN / '08_contrats_frontieres.md')
    contrats = {ligne[0]: ligne for ligne in lignes_tableau(section(doc08, '1.'))}
    problemes += [f'frontière « {f} » sans contrat (document 08, §1)' for f in frontieres if f not in contrats]
    problemes += [f'contrat « {c} » sans frontière (document 02, §7)' for c in contrats if c not in frontieres]
    paragraphes = set(re.findall(r'^#{2,3} (\d+(?:\.\d+)?)\.? ', doc08, re.M))
    for nom, ligne in contrats.items():
        cites = re.findall(r'§(\d+(?:\.\d+)?)', ligne[1]) if len(ligne) > 1 else []
        if not cites:
            problemes.append(f'contrat « {nom} » : aucun paragraphe cité (document 08, §1)')
        problemes += [f'contrat « {nom} » : paragraphe §{ref} absent du document 08'
                      for ref in cites if ref not in paragraphes]
        if len(ligne) < 3 or not ligne[2] or ligne[2] == '—':
            problemes.append(f'contrat « {nom} » sans vérification réelle (document 08, §1)')
    resume['frontieres'] = {'document_02': len(frontieres), 'document_08': len(contrats)}
    return resume, problemes


def main() -> int:
    try:
        resume, problemes = verifier()
    except (OSError, ValueError, KeyError) as erreur:
        print(json.dumps({'statut': 'ECHEC', 'erreur': str(erreur)}, ensure_ascii=False, indent=2))
        return 1
    statut = 'PASS' if not problemes else 'ECHEC'
    print(json.dumps({'statut': statut, 'resume': resume, 'problemes': problemes},
                     ensure_ascii=False, indent=2))
    return 0 if statut == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())

"""Vérification adversariale déterministe de la phase 4, exclusivement sur copies temporaires.

Chaque motif doit exister exactement une fois. La suite intégrale passe d'abord sur la copie saine, puis
chaque variante syntaxiquement valide doit la faire échouer. Une variante survivante est signalée, jamais
ignorée. Aucun fichier source du dépôt n'est muté. Les rapports courants restent dans .local/reports/.
"""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOSSIERS = ('src', 'tests', 'tools', 'config', 'schemas', 'prompts', 'reference', 'docs', 'mcl', 'livrables', '.agents')


def variante(nom, paquet, avant, apres, couche):
    return {'nom': nom, 'fichier': f'src/xpbots/london/{paquet}/_impl.py',
            'avant': avant, 'apres': apres, 'couche': couche}


MUTATIONS = [
    variante('0a_effectif_range_ignore', 'c0a_parametres',
             'or (fin - debut) != self.expected_range_m15_bars * duree', 'or False', '0a'),
    variante('0b_largeur_additionnee', 'c0b_types', 'return self.haut - self.bas', 'return self.haut + self.bas', '0b'),
    variante('1a_extreme_superieur_minimum', 'c1a_range',
             'haut = max(b.haut for b in retenues.values())', 'haut = min(b.haut for b in retenues.values())', '1a'),
    variante('1a_bougies_apres_range_lues', 'c1a_range',
             'if enrichie.bougie.debut_ms not in attendues:', 'if False and enrichie.bougie.debut_ms not in attendues:', '1a'),
    variante('1b_plus_ancienne_h1', 'c1b_gel_atr_h1', 'candidate = max(candidates,', 'candidate = min(candidates,', '1b'),
    variante('1b_age_exact_refuse', 'c1b_gel_atr_h1', 'fin_gel - b.fin_ms > duree', 'fin_gel - b.fin_ms >= duree', '1b'),
    variante('1c_egalite_buffer_admise', 'c1c_cassure', 'b.cloture > range_.haut + buffer',
             'b.cloture >= range_.haut + buffer', '1c'),
    variante('1c_corps_exact_refuse', 'c1c_cassure', 'corps < parametres.signal_body_fraction_min',
             'corps <= parametres.signal_body_fraction_min', '1c'),
    variante('1c_cloture_exacte_refusee', 'c1c_cassure', 'fraction < parametres.signal_close_location_min',
             'fraction <= parametres.signal_close_location_min', '1c'),
    variante('1c_tr_exact_refuse', 'c1c_cassure', 'i.tr > parametres.commun.maximum_signal_true_range_atr * i.a',
             'i.tr >= parametres.commun.maximum_signal_true_range_atr * i.a', '1c'),
    variante('1d_stop_achat_maximum', 'c1d_stop', 'niveau = min(composantes)', 'niveau = max(composantes)', '1d'),
    variante('1d_maximum_exact_refuse', 'c1d_stop', 'distance > parametres.commun.maximum_chart_stop_atr * a',
             'distance >= parametres.commun.maximum_chart_stop_atr * a', '1d'),
    variante('1d_guard_minimum', 'c1d_stop', 'guard = max(tick, parametres.commun.structural_buffer_atr * a)',
             'guard = min(tick, parametres.commun.structural_buffer_atr * a)', '1d'),
    variante('1e_remplissage_compte_plusieurs_fois', 'c1e_quotas', 'issue.cle not in self._etat.remplissages',
             'True', '1e'),
    variante('1e_jour_utc_au_lieu_de_londres', 'c1e_quotas', 'self._calendrier.jour_local(issue.instant_ms)',
             'self._calendrier.jour_utc(issue.instant_ms)', '1e'),
    variante('2_prechargement_m15_borne_exclue', 'c2_moteur', 'i.rang < self._p.commun.warmup_closed_m15_bars - 1',
             'i.rang <= self._p.commun.warmup_closed_m15_bars - 1', '2'),
    variante('2_largeur_minimale_exclue', 'c2_moteur', 'self._p.range_min_h1_atr * self._gel.atr <= self._range.largeur',
             'self._p.range_min_h1_atr * self._gel.atr < self._range.largeur', '2'),
    variante('2_disponibilite_du_gel_ignoree', 'c2_moteur', 'if self._gel.disponible_ms > b.fin_ms:',
             'if False and self._gel.disponible_ms > b.fin_ms:', '2'),
    variante('2_position_possedee_ignoree', 'c2_moteur', 'if self.position_ouverte:', 'if False and self.position_ouverte:', '2'),
    variante('2_meme_bougie_reemise', 'c2_moteur', 'b.fin_ms <= self._dernier_m15', 'b.fin_ms < self._dernier_m15', '2'),
    variante('2_quota_ignore', 'c2_moteur', 'refus = self._quotas.refus(cassure.sens)', 'refus = None', '2'),
    {'nom': 'S4_issue_non_transmise', 'fichier': 'src/xpbots/orchestration/squelette.py', 'couche': 'S4',
     'avant': 'self._strategie.sur_issue(issue)', 'apres': 'pass  # mutation : issue perdue'},
    {'nom': 'S7_taille_absente_admise_au_demarrage', 'fichier': 'src/xpbots/app/rejeu_squelette.py', 'couche': 'S7',
     'avant': 'if set(tailles) != symboles:', 'apres': 'if False and set(tailles) != symboles:'},
]


def executer(racine, nom):
    execution = subprocess.run([sys.executable, '-B', 'tools/run_london_tests.py'], cwd=racine,
                               env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                               capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
    rapport = json.loads((racine / '.local/reports/robot_tests.json').read_text(encoding='utf-8'))
    return {'nom': nom, 'code': execution.returncode, 'tests': rapport['tests'],
            'echecs': rapport['echecs'], 'erreurs': rapport['erreurs'], 'en_defaut': rapport['en_defaut'],
            'extrait': (execution.stdout+execution.stderr)[-5000:]}


def probe_range(racine):
    """Preuve de changement observable pour l'éventuelle survivante max→min du range."""
    code = '''from dataclasses import replace
from robot.outils.london import JOUR,bougies_range,parametres
from xpbots.london.c1a_range import construire_range
p=parametres(); s=bougies_range(p)
s[0]=replace(s[0],bougie=replace(s[0].bougie,haut=101))
print(construire_range(JOUR,s,p).haut)
'''
    execution = subprocess.run([sys.executable, '-B', '-c', code], cwd=racine,
                               env={**os.environ, 'PYTHONPATH': os.pathsep.join(str(racine/p) for p in ('src', 'tests')),
                                    'PYTHONDONTWRITEBYTECODE': '1'}, capture_output=True, text=True, check=True)
    return execution.stdout.strip()


def lot(racine, mutations):
    resultats = []
    for mutation in mutations:
        fichier = racine / mutation['fichier']
        original = fichier.read_text(encoding='utf-8')
        if original.count(mutation['avant']) != 1:
            raise ValueError(f"{mutation['nom']} : motif non unique ou absent")
        probe_avant = probe_range(racine) if mutation['nom'] == '1a_extreme_superieur_minimum' else None
        modifie = original.replace(mutation['avant'], mutation['apres'])
        ast.parse(modifie)
        try:
            fichier.write_text(modifie, encoding='utf-8')
            resultat = executer(racine, mutation['nom'])
            resultat.update(couche=mutation['couche'], fichier=mutation['fichier'])
            if probe_avant is not None:
                resultat['preuve_observable'] = {'avant': probe_avant, 'apres': probe_range(racine)}
                if resultat['preuve_observable']['avant'] == resultat['preuve_observable']['apres']:
                    raise ValueError('mutation de range sans effet : harnais invalide')
            if resultat['code'] and not resultat['en_defaut']:
                raise ValueError('échec de harnais sans test en défaut')
            resultats.append(resultat)
            print(json.dumps({k: resultat[k] for k in ('nom', 'code', 'echecs', 'erreurs')}, ensure_ascii=True), flush=True)
        finally:
            fichier.write_text(original, encoding='utf-8')
    return resultats


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument('--ouvriers', type=int, default=3, choices=(1, 2, 3))
    analyseur.add_argument('--rapport', default='.local/reports/mutations_london_phase4.json')
    arguments = analyseur.parse_args()
    with tempfile.TemporaryDirectory(prefix='xpbots_m4_') as temporaire:
        racine_temp = Path(temporaire).resolve()
        # Le nettoyage récursif de TemporaryDirectory est borné à ce répertoire créé pour cette exécution.
        if (not racine_temp.is_relative_to(Path(tempfile.gettempdir()).resolve())
                or racine_temp.is_relative_to(ROOT) or not racine_temp.name.startswith('xpbots_m4_')):
            raise ValueError('répertoire jetable hors des bornes attendues')
        saine = racine_temp / 'saine'
        saine.mkdir()
        for nom in DOSSIERS:
            shutil.copytree(ROOT/nom, saine/nom, ignore=shutil.ignore_patterns('__pycache__', '.env', '.local'))
        for nom in ('AGENTS.md', 'README.md', '.gitattributes', '.gitignore', 'requirements-dev.txt'):
            shutil.copyfile(ROOT/nom, saine/nom)
        baseline = executer(saine, 'copie_saine')
        if baseline['code']:
            print(json.dumps(baseline, ensure_ascii=True))
            return 2
        print(json.dumps({'copie_saine': 'PASS', 'tests': baseline['tests']}, ensure_ascii=True), flush=True)
        copies = []
        for i in range(arguments.ouvriers):
            destination = racine_temp/f'ouvrier{i}'
            shutil.copytree(saine, destination, ignore=shutil.ignore_patterns('.local'))
            copies.append(destination)
        resultats = []
        with ThreadPoolExecutor(max_workers=arguments.ouvriers) as executeur:
            travaux = [executeur.submit(lot, racine, MUTATIONS[i::arguments.ouvriers]) for i, racine in enumerate(copies)]
            for travail in as_completed(travaux):
                resultats.extend(travail.result())
    resultats.sort(key=lambda r: r['nom'])
    survivantes = [r['nom'] for r in resultats if r['code'] == 0]
    rapport = {'statut': 'ECHEC' if survivantes else 'PASS', 'copie_saine': baseline,
               'mutations': len(resultats), 'detectees': len(resultats)-len(survivantes),
               'survivantes': survivantes, 'resultats': resultats}
    chemin = ROOT/arguments.rapport
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(rapport, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: rapport[k] for k in ('statut', 'mutations', 'detectees', 'survivantes')}, ensure_ascii=True))
    return 1 if survivantes else 0


if __name__ == '__main__':
    raise SystemExit(main())

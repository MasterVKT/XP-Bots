"""Règles transverses du plan maître (section 4.2) vérifiées sur tout `src/` : aucune valeur normative
recopiée, aucune horloge ni bibliothèque de frontière hors infrastructure, lanceur de tests fiable."""
import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path

from robot.outils import RACINE, SRC
from robot.outils.lignees import LONDON, appartient

# Valeurs autorisées malgré une égalité fortuite avec une valeur de config/, avec leur justification.
NOMBRES_AUTORISES = {
    0: 'neutre arithmétique', 1: 'unité, départ de numérotation', -1: 'sens de vente',
}
NOMBRES_AUTORISES_PAR_FICHIER = {
    ('noyau/temps.py', 1000): 'conversions d\'unités ms/s et µs/ms, seules constantes temporelles du code',
    ('app/rejeu.py', 2): 'code de sortie d\'usage invalide (convention argparse)',
    ('donnees_temps/c1c_indicateurs.py', 2): 'coefficient 2/(n+1) de la définition de l\'EMA (C03 point 8)',
    ('donnees_temps/c1c_indicateurs.py', 50): 'RSI neutre de la définition (C03 point 9)',
    ('donnees_temps/c1c_indicateurs.py', 100): 'bornes de la définition du RSI (C03 point 9)',
}
NOMBRES_AUTORISES_PAR_FONCTION = {
    ('service_ia/c0_types/_impl.py', '_entetes', 2): 'cardinalité d’une paire nom-valeur HTTP, hors seuil métier',
    ('infra/c2a_specifications/_impl.py', '_valider_export', 7): 'cardinalite des sept jours de la semaine native, hors seuil de strategie',
    ('infra/c2a_specifications/_impl.py', '_horaires', 7): 'conversion ISO lundi=1 vers dimanche=0, hors horaire de strategie',
    ('orchestration/c2_moteur/_impl.py', '_intervalles_marche', 2): 'cardinalité d’un intervalle UTC reçu, pas un seuil de stratégie',
    ('infra/c1_session/_impl.py', 'actualiser', 3): 'trois champs du tuple version natif : version, build et date',
    ('infra/c0a_types/_impl.py', 'utc_de_serveur', 1000): 'conversion exacte de l’offset secondes vers millisecondes',
    ('infra/c0a_types/_impl.py', 'serveur_de_utc', 1000): 'conversion exacte de l’offset secondes vers millisecondes',
    ('infra/c0b_horloge/_impl.py', 'attendre_ms', 1000): 'conversion exacte de millisecondes vers secondes pour sleep',
    ('orchestration/c3_codec/_impl.py', '_registre', 2): 'cardinalité d’un couple (nom public, classe), hors règle de trading',
    ('orchestration/c3_codec/_impl.py', '_decoder', 2): 'cardinalité d’une paire clé-valeur, hors règle de trading',
    ('execution/c4_cycle/_impl.py', '_ms', 1000): 'conversion exacte des secondes en millisecondes',
    ('execution/c4_cycle/_impl.py', 'identifier_courtier', 8): 'huit octets du SHA-256 pour un magic entier sur 63 bits (D-08)',
}
TEXTES_AUTORISES = {
    'PAPER': 'nom du mode (code) ; la valeur par défaut reste lue dans common.default_mode',
    'UTC': 'fuseau déclaré par un manifeste de fixture ; variante d\'alignement implémentée',
}
TEXTES_AUTORISES_PAR_FICHIER = {
    ('donnees_temps/c0_parametres_seances.py', 'BID'): 'variante implémentée : refus de démarrer sinon',
    ('donnees_temps/c0_parametres_seances.py', 'WILDER'): 'variante implémentée : refus de démarrer sinon',
    ('donnees_temps/c0_parametres_seances.py', 'PREVIOUS_CLOSED_M15'): 'variante implémentée : refus de démarrer sinon',
    ('moteur_ema/c0_parametres.py', 'SMA_N'): 'variante implémentée : refus de démarrer sinon',
    ('moteur_ema/c0_parametres.py', 'WILDER'): 'variante implémentée : refus de démarrer sinon',
    ('moteur_ema/c0_parametres.py', 'EMA15_TO_EMA50'): 'variante implémentée : refus de démarrer sinon',
}
TEXTES_AUTORISES_PAR_AFFECTATION = {
    ('fondamental/c0_types/_impl.py', '_DEVISES', valeur)
    for valeur in ('EURUSD', 'GBPUSD', 'XAUUSD', 'EUR', 'GBP', 'USD')
}  # C05 et plan London §6.5 : table de devises explicitement codée, pas un paramètre recopié.
TEXTES_AUTORISES_PAR_AFFECTATION.update(
    ('rejeu/c2_executeur/_impl.py', '_FOREX_C09', valeur) for valeur in ('EURUSD', 'GBPUSD'))
TEXTES_AUTORISES_PAR_AFFECTATION.add(
    ('orchestration/c3_codec/_impl.py', '_ZONES_SUPPORTEES', 'Europe/London'))  # variantes du codec, pas fuseau de décision
TEXTES_AUTORISES_PAR_AFFECTATION.add(
    ('infra/c1_session/_impl.py', '_MODES', 'PAPER_AB'))  # modes pris en charge ; aucun choix de défaut
TEXTES_AUTORISES_PAR_AFFECTATION.add(
    ('infra/c0d_journal/_impl.py', '_MODE_DOUBLE_COMPTE', 'PAPER_AB'))  # variante C09 des deux livres, aucun défaut
TEXTES_AUTORISES_PAR_AFFECTATION.add(
    ('service_ia/c1d_budget/_impl.py', '_PROFIL_GRATUIT_VERIFIE', 'FREE_CONFIRMED'))  # variante A08 vérifiée, aucun compte supposé gratuit
TEXTES_AUTORISES_PAR_AFFECTATION.update(
    ('service_ia/c1e_fournisseurs/_impl.py','_FORMATS_FOURNISSEURS',v)
    for v in ('GROQ_FREE','GEMINI_FREE','OPENAI_PAID_OPTIONAL'))  # protocoles explicitement implémentés, modèles lus dans l’export
NOMBRES_AUTORISES_PAR_AFFECTATION = {
    ('rejeu/c0b_protocole/_impl.py', nom, valeur)
    for nom, valeurs in {
        '_BORNES': (2019, 12, 2, 2020, 2023, 2025, 2026, 5, 11, 4),
        '_SEUILS_TEXTUELS_C10': (200, 100, 50),
        '_PROSPECTIF_C10': (2026, 11, 5, 2027, 2, 100),
        '_SCENARIOS_C10': (250, 1000, 2),
        '_DEBUT_DIAGNOSTIC_V3': (2026, 5, 11),
        '_CENT_POUR_CENT': (100,),  # définition mathématique d'un percentile
    }.items() for valeur in valeurs
}  # Plan London §6.8 : constantes exclusivement textuelles C10, hors exports.
NOMBRES_AUTORISES_PAR_AFFECTATION.add(
    ('rejeu/c1d_bootstrap/_impl.py', '_CENT_POUR_CENT', 100))  # définition du percentile
NOMBRES_AUTORISES_PAR_AFFECTATION.add(
    ('infra/c2c_calculs/_impl.py', '_CENT_POUR_CENT', 100))  # Conversion mathematique d'un ratio en pourcentage.
NOMBRES_AUTORISES_PAR_AFFECTATION.add(
    ('service_ia/c0_types/_impl.py', '_STATUT_HTTP_MINIMUM', 100))  # Classe de statut HTTP, hors valeur de compte.
NOMBRES_AUTORISES_PAR_AFFECTATION.add(
    ('service_ia/c1e_fournisseurs/_impl.py', '_HTTP_SUCCES', 200))  # Statut HTTP, hors effectif financier.
NOMBRES_AUTORISES_PAR_AFFECTATION.add(
    ('service_ia/c2c_collecteur/_impl.py', '_HTTP_SUCCES', 200))  # Statut HTTP, hors effectif financier.
NOMBRES_AUTORISES_PAR_AFFECTATION.add(
    ('service_ia/c2c_collecteur/_impl.py', '_REDIRECTIONS_RSS_MAXIMUM', 3))  # A04 documentaire, sans champ exporté.
APPELS_D_HORLOGE = {('datetime', 'now'), ('datetime', 'utcnow'), ('datetime', 'today'), ('date', 'today'),
                    ('time', 'time'), ('time', 'time_ns'), ('time', 'monotonic'), ('time', 'monotonic_ns'),
                    ('time', 'perf_counter'), ('time', 'perf_counter_ns')}
BIBLIOTHEQUES_DE_FRONTIERE = {'MetaTrader5', 'sqlite3', 'urllib', 'http', 'ssl', 'socket', 'time', 'msvcrt', 'fcntl'}
INFRASTRUCTURE = SRC / 'xpbots' / 'infrastructure'
INFRA_COMMUNE = SRC / 'xpbots' / 'infra'
INFRA_SERVICE_IA = SRC / 'xpbots' / 'service_ia' / 'c4_service'


def horloge_autorisee(chemin):
    return INFRASTRUCTURE / 'horloge' in chemin.parents or INFRA_COMMUNE / 'c0b_horloge' in chemin.parents


def frontiere_autorisee(chemin):
    return (INFRASTRUCTURE in chemin.parents or INFRA_COMMUNE in chemin.parents
            or INFRA_SERVICE_IA in chemin.parents)


def import_frontiere_autorise(chemin, nom):
    # urllib.parse ne réalise aucune entrée-sortie ; urllib.request reste physique.
    return (frontiere_autorisee(chemin) or nom == 'urllib.parse'
            and SRC/'xpbots'/'service_ia' in chemin.parents)


def feuilles(valeur):
    if isinstance(valeur, dict):
        for element in valeur.values():
            yield from feuilles(element)
    elif isinstance(valeur, list):
        for element in valeur:
            yield from feuilles(element)
    else:
        yield valeur


def valeurs_normatives():
    nombres, textes = set(), set()
    for nom in ('parametres_figes_v3.json', 'parametres_IA_integration_v1.json'):
        for valeur in feuilles(json.loads((RACINE / 'config' / nom).read_text(encoding='utf-8'))):
            if type(valeur) in (int, float):
                nombres.add(valeur)
            elif type(valeur) is str:
                textes.add(valeur)
    return nombres, textes


def fichiers_source():
    """Sources du robot 1 : les fichiers propres au robot London (registre `robot.outils.lignees`) sont ignorés."""
    return sorted(p for p in (SRC / 'xpbots').rglob('*.py')
                  if '__pycache__' not in p.parts and not appartient(p.relative_to(RACINE).as_posix(), LONDON))


def litteraux_interdits(source, relatif, nombres, textes):
    arbre = ast.parse(source)
    parents = {enfant: parent for parent in ast.walk(arbre) for enfant in ast.iter_child_nodes(parent)}
    violations = []
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Constant) or type(noeud.value) is bool:
            continue
        parent = noeud
        fonction = None
        affectation = None
        while parent in parents:
            parent = parents[parent]
            if (isinstance(parent, ast.Assign) and isinstance(parents.get(parent), ast.Module)
                    and len(parent.targets) == 1 and isinstance(parent.targets[0], ast.Name)):
                affectation = parent.targets[0].id
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fonction = parent.name
                break
        v = noeud.value
        if type(v) in (int, float) and v in nombres and v not in NOMBRES_AUTORISES \
                and (relatif, v) not in NOMBRES_AUTORISES_PAR_FICHIER \
                and (relatif, fonction, v) not in NOMBRES_AUTORISES_PAR_FONCTION \
                and (relatif, affectation, v) not in NOMBRES_AUTORISES_PAR_AFFECTATION:
            violations.append(f'{relatif}:{noeud.lineno} nombre {v!r}')
        if type(v) is str and v in textes and v not in TEXTES_AUTORISES \
                and (relatif, v) not in TEXTES_AUTORISES_PAR_FICHIER \
                and (relatif, affectation, v) not in TEXTES_AUTORISES_PAR_AFFECTATION:
            violations.append(f'{relatif}:{noeud.lineno} texte {v!r}')
    return violations


class TestReglesTransverses(unittest.TestCase):
    def test_constantes_http_et_redirections_rss_limitees_aux_affectations(self):
        s='_HTTP_SUCCES=200\n_REDIRECTIONS_RSS_MAXIMUM=3\n_AUTRE=3\ndef risque():\n    return 200, 3\n'
        self.assertEqual(len(litteraux_interdits(s,'service_ia/c2c_collecteur/_impl.py',{200,3},set())),3)
        self.assertEqual(len(litteraux_interdits(s,'autre.py',{200,3},set())),5)

    def test_formats_fournisseurs_et_http_limites_aux_variantes(self):
        s="_HTTP_SUCCES=200\n_AUTRE=200\n_FORMATS_FOURNISSEURS={'GROQ_FREE':'GROQ'}\ndef risque():\n    return 200, 'GROQ_FREE'\n"
        self.assertEqual(len(litteraux_interdits(s,'service_ia/c1e_fournisseurs/_impl.py',{200},{'GROQ_FREE'})),3)
        self.assertEqual(len(litteraux_interdits(s,'autre.py',{200},{'GROQ_FREE'})),5)

    def test_profil_gratuit_limite_a_la_variante_de_facturation(self):
        s="_PROFIL_GRATUIT_VERIFIE='FREE_CONFIRMED'\n_AUTRE='FREE_CONFIRMED'\ndef budget():\n    return 'FREE_CONFIRMED'\n"
        self.assertEqual(len(litteraux_interdits(s,'service_ia/c1d_budget/_impl.py',set(),{'FREE_CONFIRMED'})),2)
        self.assertEqual(len(litteraux_interdits(s,'autre.py',set(),{'FREE_CONFIRMED'})),3)

    def test_exceptions_service_ia_limitees_aux_formats(self):
        source = ('_STATUT_HTTP_MINIMUM=100\n_AUTRE=100\n'
                  'def _entetes():\n    return 2\n'
                  'def risque():\n    return 100, 2\n')
        self.assertEqual(len(litteraux_interdits(source,'service_ia/c0_types/_impl.py',{100,2},set())),3)
        self.assertEqual(len(litteraux_interdits(source,'autre.py',{100,2},set())),5)
        pur=SRC/'xpbots'/'service_ia'/'c0_types'/'_impl.py'
        self.assertTrue(import_frontiere_autorise(pur,'urllib.parse'))
        self.assertFalse(import_frontiere_autorise(pur,'urllib.request'))
        self.assertFalse(import_frontiere_autorise(SRC/'xpbots'/'noyau'/'pur.py','urllib.parse'))
        self.assertTrue(frontiere_autorisee(INFRA_SERVICE_IA/'_http.py'))
        self.assertFalse(frontiere_autorisee(pur))

    def test_mode_double_compte_borne_a_la_variante_du_journal(self):
        source="_MODE_DOUBLE_COMPTE='PAPER_AB'\n_AUTRE='PAPER_AB'\ndef risque():\n    return 'PAPER_AB'\n"
        self.assertEqual(len(litteraux_interdits(source,'infra/c0d_journal/_impl.py',set(),{'PAPER_AB'})),2)
        self.assertEqual(len(litteraux_interdits(source,'autre.py',set(),{'PAPER_AB'})),3)

    def test_exceptions_natives_bornees_aux_jours_et_au_pourcentage(self):
        source = 'def _valider_export():\n    return 7\ndef _horaires():\n    return 7\ndef risque():\n    return 7\n'
        self.assertEqual(len(litteraux_interdits(source, 'infra/c2a_specifications/_impl.py', {7}, set())), 1)
        self.assertEqual(len(litteraux_interdits(source, 'autre.py', {7}, set())), 3)
        source = '_CENT_POUR_CENT=100\n_AUTRE=100\ndef risque():\n    return 100\n'
        self.assertEqual(len(litteraux_interdits(source, 'infra/c2c_calculs/_impl.py', {100}, set())), 2)
        self.assertEqual(len(litteraux_interdits(source, 'autre.py', {100}, set())), 3)

    def test_frontieres_communes_et_horloge_restant_bornees(self):
        self.assertTrue(frontiere_autorisee(INFRA_COMMUNE/'c0c_sqlite'/'_impl.py'))
        self.assertTrue(horloge_autorisee(INFRA_COMMUNE/'c0b_horloge'/'_impl.py'))
        self.assertFalse(horloge_autorisee(INFRA_COMMUNE/'c2b_flux'/'_impl.py'))
        self.assertFalse(frontiere_autorisee(SRC/'xpbots'/'app'/'direct.py'))
        self.assertFalse(horloge_autorisee(SRC/'xpbots'/'app'/'horloge'/'_impl.py'))

    def test_exceptions_codec_bornees_aux_paires_et_zones(self):
        chemin = 'orchestration/c3_codec/_impl.py'
        source = ("_ZONES_SUPPORTEES = ('Europe/London',)\n"
                  "def _registre():\n    return 2\n"
                  "def risque():\n    return 2, 'Europe/London'\n")
        self.assertEqual(len(litteraux_interdits(source, chemin, {2}, {'Europe/London'})), 2)
        self.assertEqual(len(litteraux_interdits(source, 'autre.py', {2}, {'Europe/London'})), 4)

    def test_table_forex_c09_bornee_au_denommateur_du_module(self):
        source = "_FOREX_C09 = {'EURUSD', 'GBPUSD'}\n_AUTRE = 'EURUSD'\n"
        fichier = 'rejeu/c2_executeur/_impl.py'
        self.assertEqual(len(litteraux_interdits(source, fichier, set(), {'EURUSD', 'GBPUSD'})), 1)
        self.assertEqual(len(litteraux_interdits(source, 'autre.py', set(), {'EURUSD', 'GBPUSD'})), 3)

    def test_exception_c10_limitee_aux_constantes_textuelles_du_module(self):
        source = ('_SCENARIOS_C10 = ((250, 1000, 2),)\n'
                  '_AUTRE = 1000\n'
                  'def risque():\n    _SCENARIOS_C10 = 1000\n    return 2\n')
        chemin = 'rejeu/c0b_protocole/_impl.py'
        self.assertEqual(len(litteraux_interdits(source, chemin, {250, 1000, 2}, set())), 3)
        self.assertEqual(len(litteraux_interdits(source, 'autre.py', {250, 1000, 2}, set())), 6)

    def test_exception_table_c05_limitee_a_l_affectation_du_module(self):
        source = ("_DEVISES = {'EURUSD': ('EUR', 'USD')}\n"
                  "_AUTRE = 'USD'\n"
                  "def risque():\n    _DEVISES = {'USD': 'EUR'}\n    return 'EURUSD'\n")
        fichier = 'fondamental/c0_types/_impl.py'
        violations = litteraux_interdits(source, fichier, set(), {'EURUSD', 'EUR', 'USD'})
        self.assertEqual(len(violations), 4)
        self.assertEqual(len(litteraux_interdits(source, 'autre_module.py', set(), {'EURUSD', 'EUR', 'USD'})), 7)

    def test_aucune_valeur_normative_recopiee(self):
        nombres, textes = valeurs_normatives()
        violations = []
        for chemin in fichiers_source():
            relatif = chemin.relative_to(SRC / 'xpbots').as_posix()
            violations.extend(litteraux_interdits(chemin.read_text(encoding='utf-8'), relatif, nombres, textes))
        self.assertEqual(violations, [], 'valeurs de config/ recopiées dans le code')

    def test_exceptions_techniques_limitees_au_fichier_et_a_la_fonction(self):
        source = ('def _ms(secondes):\n    return secondes * 1000\n'
                  'def identifier_courtier(octets):\n    return octets[:8]\n'
                  'def calculer_risque(volume):\n    return volume * 1000 + 8\n')
        chemin = 'execution/c4_cycle/_impl.py'
        violations = litteraux_interdits(source, chemin, {1000, 8}, set())
        self.assertEqual(len(violations), 2)
        self.assertEqual({v.rsplit(' ', 1)[-1] for v in violations}, {'1000', '8'})
        self.assertTrue(all(':6 ' in v for v in violations))
        self.assertEqual(len(litteraux_interdits(source, 'autre_module.py', {1000, 8}, set())), 4)

    def test_aucune_horloge_hors_infrastructure(self):
        violations = []
        for chemin in fichiers_source():
            if horloge_autorisee(chemin):
                continue
            for noeud in ast.walk(ast.parse(chemin.read_text(encoding='utf-8'))):
                if isinstance(noeud, ast.Attribute):
                    base = noeud.value.attr if isinstance(noeud.value, ast.Attribute) else getattr(noeud.value, 'id', None)
                    if (base, noeud.attr) in APPELS_D_HORLOGE:
                        violations.append(f'{chemin.relative_to(RACINE)}:{noeud.lineno} {base}.{noeud.attr}')
        self.assertEqual(violations, [])

    def test_bibliotheques_de_frontiere_confinees_a_l_infrastructure(self):
        violations = []
        for chemin in fichiers_source():
            if frontiere_autorisee(chemin):
                continue
            for noeud in ast.walk(ast.parse(chemin.read_text(encoding='utf-8'))):
                noms = []
                if isinstance(noeud, ast.Import):
                    noms = [alias.name for alias in noeud.names]
                elif isinstance(noeud, ast.ImportFrom) and noeud.level == 0:
                    noms = [noeud.module or '']
                for nom in noms:
                    if nom.split('.')[0] in BIBLIOTHEQUES_DE_FRONTIERE and not import_frontiere_autorise(chemin,nom):
                        violations.append(f'{chemin.relative_to(RACINE)}:{noeud.lineno} import {nom}')
        self.assertEqual(violations, [])


class TestLanceur(unittest.TestCase):
    def lancer(self, *arguments):
        return subprocess.run([sys.executable, str(RACINE / 'tools' / 'run_robot_tests.py'), *arguments],
                              cwd=RACINE, capture_output=True, text=True, timeout=120)

    def test_filtre_sans_test_signale_par_le_code_5(self):
        resultat = self.lancer('--artefact', 'noyau', '--couche', '9z', '--categorie', '1')
        self.assertEqual(resultat.returncode, 5, resultat.stderr)

    def test_artefact_inconnu(self):
        self.assertEqual(self.lancer('--artefact', 'inexistant').returncode, 2)

    def test_motif_des_fichiers(self):
        sys.path.insert(0, str(RACINE / 'tools'))
        try:
            from run_robot_tests import motif_fichiers
        finally:
            sys.path.remove(str(RACINE / 'tools'))
        self.assertEqual(motif_fichiers(None, None), 'test_*.py')
        self.assertEqual(motif_fichiers('2', '1'), 'test_c2_cat1_*.py')
        self.assertEqual(motif_fichiers('1a', None), 'test_c1a_cat*_*.py')
        self.assertEqual(motif_fichiers(None, '2'), 'test_c*_cat2_*.py')


if __name__ == '__main__':
    unittest.main()

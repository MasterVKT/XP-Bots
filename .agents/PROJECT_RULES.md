# Règles transversales de gouvernance XP-Bots

Règles communes à tous les agents et à toutes les skills. Elles décrivent la gouvernance et renvoient aux
sources métier sans les remplacer. Une skill ne recopie pas ces règles : elle y renvoie.

## 1. Carte des ressources et autorité métier

| Ressource | Rôle | Règle d'usage |
|---|---|---|
| [Spécification 01 EMA](../livrables/strategies_m15/01_Triple_EMA_RSI_Repli_M15_Specification_IA.md) | C01–C11, S01, A01–A15, version 3.1.0 | Autorité de la méthode Triple EMA + RSI + repli |
| [Spécification 02 London](../livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md) | C01–C11, S02, A01–A15, version 3.1.0 | Autorité de la méthode London breakout |
| [Paramètres techniques](../config/parametres_figes_v3.json), [paramètres IA](../config/parametres_IA_integration_v1.json) | Exports figés | Les citer, ne jamais recopier ni modifier leurs valeurs |
| [Schémas](../schemas/), [prompts](../prompts/prompts_IA_v1.json) | Contrats JSON et prompts exacts de l'IA métier | Concordance obligatoire avec les deux spécifications |
| [Fonctions de référence](../reference/README.md) | Calculs et contrats de comparaison hors ligne | Vérifier le code et ses limites avant de guider un portage |
| `tests/check_technical.py`, `tests/check_llm.py`, `tools/verify_project.py` | Contrôles techniques, IA et documentaires des ressources de référence | Ce ne sont pas des tests du robot |
| `tools/run_robot_tests.py`, `tests/robot/` | Suite du robot en construction (squelette, gardes transverses, puis tests MCL de chaque couche) | Rejouée à chaque gate MCL, à chaque fin de phase et avant chaque commit (D-10) |
| [Guide](../docs/architecture/GUIDE_IMPLEMENTATION.md), [données](../docs/data/03_Donnees_Historiques_Requises_et_Validation.md), [décision](../docs/decisions/00_Decision_Conception_et_Faisabilite_V3.md) | Construction, données requises, décisions | Orientent conception et validation |
| [Plan du robot London](../docs/architecture/robot_london_v3/README.md), [plan MCL composite](../mcl/robot-london-v3/PLAN-MCL.md) | Implémentation de `LONDON_V3` et des composants partagés par phases MCL ; décisions D-01 à D-18 | Une phase à la fois, sur demande explicite ; n'ajoute ni ne modifie aucune règle métier |
| [Preuves conservées](../docs/validation/README.md) | Empreintes, provenance, diagnostics datés | Historique intouchable ; nouveaux rapports dans `.local/reports/` |
| [Références de contexte](../docs/references/README.md) | Textes historiques | Jamais des instructions normatives |

Le dépôt contient des spécifications, des exports et des fonctions de référence. Les robots de plateforme,
l'adaptateur courtier, le service HTTP LLM et l'analyse fondamentale externe restent à implémenter. Pour le
robot London (`LONDON_V3`) et les composants partagés, le langage et la plateforme sont arrêtés depuis le
05/11/2026 : Python 3.13 et MT5 par le paquet officiel `MetaTrader5`, sources dans `src/xpbots/` (décisions D-01
et D-02 du [plan](../docs/architecture/robot_london_v3/README.md)) ; le robot EMA n'est pas encore planifié. Ne
jamais présenter un composant comme existant sans l'avoir vu dans le code.

## 2. Invariants métier à préserver

- Les deux méthodes restent indépendantes ; seul le coordinateur de compte partage risque et marge (C07, C08).
- Les limites communes de risque, de positions et de pertes sont celles de C07 ; aucune skill ne les ajuste.
- La permission fondamentale externe (C05) est obligatoire ; le complément LLM (A01–A15) est facultatif,
  ne produit jamais de permission et sa panne vaut `NEUTRAL` (A12).
- Mode initial `PAPER_AB`, API distantes exclusivement, aucune inférence locale, plafonds IA partagés (A09).
- Toute modification de règle, de seuil ou de coût crée une autre version : jamais de retouche silencieuse.
- Réussir les contrôles hors ligne ne prouve ni la rentabilité ni le comportement d'un robot réel.

## 3. Règles de gouvernance

1. **Source unique** : les skills vivent dans `.agents/skills/` ; les copies de `.claude/skills/` sont
   générées par `.agents/hooks/skill_mirrors.py` et ne s'éditent jamais à la main.
2. **Frontmatter minimal** : `name` identique au dossier, en kebab-case, et `description` (ce que fait la skill
   et quand l'utiliser), 1 024 caractères au plus.
3. **Déterminisme d'abord** : routage, cas de test et portes sont des données
   (`routing-rules.json`, `routing-cases.json`, `.agents/hooks/lifecycle.json`).
4. **Hooks en renfort** : ils n'abrogent pas les instructions permanentes ; un outil sans hook fiable reste
   couvert par `AGENTS.md` et sa règle d'outil.
5. **Échec ouvert** : un hook défaillant journalise l'erreur dans son dossier d'état et laisse la session
   continuer.
6. **Bornage** : deux passes correctives au plus par requête.
7. **Tout est vérifiable** : chaque composant de gouvernance a son test et un test négatif.
8. **Pas de seconde gouvernance** : un seul moteur, un seul jeu de validateurs et de générateurs pour les deux
   stratégies et tous les outils ; les différences passent par la configuration.

## 4. Actions interdites sans demande explicite

- Modifier un paramètre figé, une section normative des spécifications, un schéma ou un prompt métier.
- Réécrire une empreinte de conservation, une preuve de `docs/validation/` ou l'archive ZIP de MCL pour faire
  passer un contrôle.
- Ajouter une dépendance ou un framework ; appeler une API LLM, un courtier ou passer un ordre depuis un
  contrôle ; afficher un secret de `.env`.
- Supprimer un fichier sans l'avoir ouvert ; une ressource réelle n'est jamais traitée comme un pointeur.

## 5. Vérification et preuves

- Gouvernance : `python .agents/skills/xp-bots-maintain-agent-skills/scripts/run_governance_suite.py`.
- Métier : `python tools/verify_project.py` ; si les dépendances manquent,
  `python -m pip install -r requirements-dev.txt` (versions déjà déclarées, aucun ajout).
- `python tools/verify_project.py --git` n'est lancé que sur besoin Git explicite.
- Les traces du cycle de vie des agents vivent dans le dossier temporaire du système ; elles ne se mélangent
  ni aux journaux de trading ni aux preuves de `docs/validation/`.
- Un échec préexistant est documenté avec sa preuve ; il n'est jamais masqué.

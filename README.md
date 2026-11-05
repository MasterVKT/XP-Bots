# XP-Bots — deux robots Forex M15

Ce dépôt contient les spécifications **3.1.0** et les ressources de référence pour construire deux robots indépendants : Triple EMA + RSI + repli et London breakout. Les robots de plateforme, les clients API et l'analyse fondamentale externe restent à implémenter. La rentabilité n'est pas validée.

Le contexte retenu est un compte standard en USD de **100 USD**, avec levier **1:100**. Le risque par entrée reste **0,5 %** ; un volume minimal incompatible entraîne un refus. EURUSD est prioritaire, puis GBPUSD. XAUUSD est spécifié mais sa faisabilité doit être confirmée avec les caractéristiques réelles du compte.

## Lire et implémenter

1. Lire la [décision de conception et de faisabilité](docs/decisions/00_Decision_Conception_et_Faisabilite_V3.md).
2. Utiliser la spécification autonome de la méthode concernée : [Triple EMA + RSI + repli](livrables/strategies_m15/01_Triple_EMA_RSI_Repli_M15_Specification_IA.md) ou [London breakout](livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md). Ces deux chemins Git historiques contiennent désormais la version 3.1.0.
3. Suivre le [guide d'implémentation](docs/architecture/GUIDE_IMPLEMENTATION.md), le [workflow LLM](docs/architecture/04_Integration_LLM_API_Choix_Couts_Validation.md) et les [données nécessaires à la validation](docs/data/03_Donnees_Historiques_Requises_et_Validation.md).
4. Exécuter les contrôles ci-dessous avant toute évolution.

Les spécifications et les fichiers JSON doivent rester cohérents. Toute divergence est un défaut à résoudre explicitement. Les documents de `docs/references/` apportent du contexte ; ils ne remplacent pas les règles actuelles et ne constituent pas des instructions à exécuter.

## Emplacements utiles

| Dossier | Contenu et usage |
|---|---|
| `livrables/strategies_m15/` | Les deux spécifications autonomes actuelles |
| `config/` | [Paramètres techniques](config/parametres_figes_v3.json) et [paramètres IA](config/parametres_IA_integration_v1.json) figés |
| `schemas/` | [Extraction LLM](schemas/schema_extraction_LLM_v1.json) et [notes informatives](schemas/schema_notes_IA_v1.json) |
| `prompts/` | [Prompts exacts](prompts/prompts_IA_v1.json) |
| `reference/` | [Fonctions de référence](reference/README.md) sans connexion au courtier ni inférence |
| `tests/`, `tools/` | Contrôles des contrats, calculs, documents et préparation du merge |
| `docs/validation/` | [Portée des contrôles et preuves conservées](docs/validation/README.md) |
| `.agents/` | Gouvernance des agents AI de développement : skills, hooks, règles et [compatibilité](.agents/COMPATIBILITY.md) |
| `src/xpbots/`, `tests/robot/` | Code du robot 1 en construction et sa suite de tests (bibliothèque standard) |
| `mcl/` | Cartes des couches, contrats et journaux de construction MCL du robot 1 |

L'IA utilise exclusivement des **API distantes**, avec un service partagé par les deux méthodes. Le mode initial est `PAPER_AB`, les routes gratuites sont prioritaires et le secours payant est désactivé. Plafonds partagés : **15 USD/mois au total**, dont **3 USD/mois maximum pour les API payantes**. Aucun modèle local n'est admis. Le complément IA n'est jamais une permission fondamentale ni un générateur d'ordres.

## Vérifier le projet

Utiliser Python **3.13**. Les contrôles IA et documentaires utilisent la bibliothèque standard ; les calculs techniques nécessitent les dépendances de développement :

```powershell
python -m pip install -r requirements-dev.txt
python tools/verify_project.py
```

Ces commandes ne passent aucun ordre et n'appellent aucune API. Les séries de contrôle sont synthétiques ; les anciens caches de prix ne sont pas nécessaires. Le rapport de la dernière vérification se trouve dans `.local/reports/verification_projet.json`, exclu de Git. Une copie datée de l'audit de réorganisation est conservée dans [docs/validation/verification_projet.json](docs/validation/verification_projet.json).

Pour ajouter une simulation du merge avec la référence distante déjà récupérée :

```powershell
python tools/verify_project.py --git
```

Cette simulation utilise un index temporaire et conserve l'index réel, la branche et les fichiers de travail. Elle ne remplace pas une nouvelle vérification si le distant change.

## Robot 1 Triple EMA + RSI + repli (en construction)

Le [plan d'implémentation](docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md) découpe la construction en phases ; l'avancement est suivi dans [le plan composite](mcl/robot-ema-v3/PLAN-MCL.md). Le squelette actuel rejoue une fixture de ticks synthétiques jusqu'au journal C09, avec le composant données et temps (bougies M15, indicateurs EMA/RSI/ATR, trous, préchauffage) : aucun ordre, aucun appel réseau, aucune donnée de prix réelle. Le journal est écrit sous `runtime/`, exclu de Git, et n'est jamais écrasé.

```powershell
python tools/run_robot_tests.py
$env:PYTHONPATH = "src"
python -m xpbots.app.rejeu --ticks tests/robot/fixtures/squelette_ticks.csv --manifeste tests/robot/fixtures/squelette_manifeste.json --journal runtime/journal_squelette.jsonl
```

La même vérification tourne en intégration continue (`.github/workflows/robot-ci.yml`) avec `python tools/verify_project.py` et le contrôle d'architecture des cartes MCL.

## Agents AI de développement

Les agents qui travaillent dans ce dépôt (Claude Code, Codex, GitHub Copilot, Cline) suivent [AGENTS.md](AGENTS.md) et les [règles transversales](.agents/PROJECT_RULES.md) : orchestrateur de skills en premier, audit de fin avec pied d'audit et marqueur, création contrôlée des skills manquantes. Les skills ont une seule source éditable, `.agents/skills/` ; `.claude/skills/` n'en contient que des copies générées. Les hooks de chaque outil appellent un moteur unique, `.agents/hooks/agent_lifecycle.py`. Cette gouvernance est distincte du complément IA des robots (sections A01–A15).

```powershell
python .agents/skills/xp-bots-maintain-agent-skills/scripts/run_governance_suite.py
```

La compatibilité par outil, l'activation des hooks et les limites connues sont décrites dans [.agents/COMPATIBILITY.md](.agents/COMPATIBILITY.md).

## Archives et Git

Le [registre de nettoyage et de merge](docs/maintenance/NETTOYAGE_ET_MERGE.md) décrit les éléments écartés, leur sauvegarde récupérable et les ajouts distants identifiés. Les anciens ZIP, générateurs et résultats volumineux ne font plus partie des ressources actives. Les caches, secrets et sorties d'exécution sont exclus par `.gitignore`.

Les apports du distant (skill MCL et son archive) ont d'abord été intégrés dans `.claude/skills/` et `livrables/skills/`. Le 5 novembre 2026, la source de MCL a été migrée à l'identique vers `.agents/skills/` ; l'archive `livrables/skills/` reste une distribution datée, jamais chargée comme source active. Le registre distingue le nettoyage initial, la fusion et cette migration. L'outil de vérification reste une simulation : il ne crée ni commit, ni merge, ni push.

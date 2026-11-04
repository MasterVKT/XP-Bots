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

## Archives et Git

Le [registre de nettoyage et de merge](docs/maintenance/NETTOYAGE_ET_MERGE.md) décrit les éléments écartés, leur sauvegarde récupérable et les ajouts distants identifiés. Les anciens ZIP, générateurs et résultats volumineux ne font plus partie des ressources actives. Les caches, secrets et sorties d'exécution sont exclus par `.gitignore`.

Les ajouts distants `.claude/skills/` et `livrables/skills/` seront apportés par le futur merge. Leurs chemins sont préservés. Aucun merge, commit ou push n'est réalisé par le nettoyage ni par l'outil de vérification.

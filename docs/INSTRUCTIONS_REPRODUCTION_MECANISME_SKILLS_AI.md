# Instructions de reproduction pour XP-Bots : mécanisme de skills et de cycle de vie multi-agents

Document destiné à un **agent AI** (tout modèle, tout fournisseur, toute extension) chargé
d'installer, dans le **dépôt unique XP-Bots**, le mécanisme complet de gouvernance AI
décrit ici : source unique de skills, orchestrateur lancé en premier pour toute requête,
audit de fin vérifié par la machine, et
création dynamique des skills manquantes.

Les principes, mécanismes, processus et concepts restent ceux du dispositif : routage
déterministe, cycle de vie multi-outils et multi-agents, audit à quatre contrôles,
remédiation bornée, détection des lacunes, génération contrôlée et validation positive et
négative. Leur application est adaptée à l'architecture et aux ressources de XP-Bots.

Le document est **auto-suffisant pour ce projet** : les chemins, domaines, commandes et
précautions ci-dessous correspondent à XP-Bots. Les variables de la section A.3 donnent les
valeurs retenues ; seuls la racine locale, l'interpréteur et les capacités des outils doivent
être revérifiés à l'étape de découverte.

**État de référence au 5 novembre 2026** : le dépôt contient les spécifications 3.1.0 de
deux robots Forex M15 indépendants, leurs paramètres, schémas et prompts, ainsi que des
fonctions Python de référence et des contrôles hors ligne. Les robots de plateforme,
l'adaptateur courtier, le service HTTP LLM et l'analyse fondamentale externe restent à
implémenter. Le langage et la plateforme des futurs robots ne sont pas arrêtés.

Ce fichier décrit **une mise en place à réaliser**. Sa présence ne prouve pas que
l'orchestrateur, les hooks ou l'audit sont déjà installés. Une demande d'adaptation de ce
document porte sur son contenu ; l'exécution des phases exige une demande de mise en place
du mécanisme. La gouvernance des agents de développement et le complément IA distant des
robots sont deux systèmes distincts.

---

## A. Mode d'emploi

### A.1 Ce que tu dois produire

À la fin de la mise en place, XP-Bots doit satisfaire les **quatre exigences** suivantes
dans **un seul dépôt**, pour les deux stratégies et toutes les ressources communes :

1. **Exigence 1 — Localisation des skills.** Toutes les skills vivent dans un seul dossier
   canonique `.agents/skills/`. Chaque outil AI y accède selon **ses propres normes** ; on ne
   duplique le contenu que là où l'outil l'impose, et alors la copie est **générée et
   contrôlée automatiquement**, jamais écrite à la main.
2. **Exigence 2 — Orchestrateur d'abord, sans exception.** Une skill d'orchestration
   (routeur) s'exécute en premier pour **chaque requête**, qu'elle soit tapée par l'humain ou
   non : validation d'un plan, notification système, passe corrective, sous-tâche déléguée,
   reprise de session, compaction de contexte. Elle sélectionne le plus petit ensemble de
   skills pertinentes.
3. **Exigence 3 — Audit de fin automatique.** Une skill d'audit s'exécute à la fin de
   **chaque requête**, sans exception. Elle vérifie erreurs, régressions, écarts et omissions
   au moyen de quatre contrôles, produit un inventaire des problèmes et un plan de
   remédiation, puis **exécute** ce plan (ce qui relance l'orchestrateur), dans une boucle
   bornée.
4. **Exigence 4 — Création dynamique de skills.** Un mécanisme vérifie à chaque requête si
   des types de tâches effectués ne sont couverts par aucune skill, puis crée ou étend la
   skill adéquate **et met à jour l'orchestrateur** pour que ce type de tâche soit désormais
   routé.

### A.2 Règles de conduite non négociables

- **Travaille depuis la racine de XP-Bots dans une même exécution.** Couvre les deux
  stratégies et les ressources communes sans créer de dépôt jumeau ni de gouvernance par
  robot. Les deux robots restent des méthodes indépendantes dans le même projet.
- **Ne commite rien.** Ne crée ni branche, ni tag, ni stash. Laisse l'arbre de travail tel
  quel, à l'exception des fichiers que ce document demande de créer ou modifier.
- **Préserve les modifications locales** sans rapport avec cette tâche. Ne répare aucune dette
  hors périmètre.
- **Vérifie le code réel** avant de croire une documentation : un fichier de règles peut
  décrire un mécanisme qui n'existe plus.
- **Préserve les contrats métier et les preuves conservées.** La gouvernance ne modifie ni
  les paramètres figés, ni les sections normatives des stratégies, ni les schémas et prompts
  métier. Ne réécris pas les empreintes de conservation pour faire passer un contrôle.
- **Utilise les validations hors ligne.** La mise en place n'exige ni clé API métier, ni
  inférence du complément LLM, ni connexion au courtier, ni ordre. N'introduis pas de
  framework ou de dépendance métier.
- **Ne remplace jamais une vérification par une supposition.** Si une vérification est
  impossible, déclare-la explicitement comme limite.
- **Avance par phases** (section F). À la fin de chaque phase : exécute ses validations, rends
  compte en quelques lignes (fichiers touchés, validations passées, écarts), **puis enchaîne**.
  N'entame pas une phase tant que les validations de la précédente ne passent pas.
- **Aucune action destructive** hors de ce qui est explicitement listé. Avant de supprimer un
  fichier, ouvre-le : s'il contient autre chose qu'un pointeur obsolète, signale-le au lieu de
  le supprimer.

### A.3 Variables résolues pour XP-Bots

| Variable | Signification | Valeur retenue |
|---|---|---|
| `<ROOT>` | Racine Git de XP-Bots, à résoudre localement | `D:\PROJETS\XP-Bots` sur le poste de référence |
| `<APP>` | Nom court du projet, en kebab-case | `xp-bots` |
| `<PY>` | Interpréteur des contrôles et hooks, à vérifier | Python **3.13**, invoqué par `python` sur le poste de référence |
| `<ORCH>` | Nom cible de la skill d'orchestration | `xp-bots-request-skill-orchestrator` |
| `<AUDIT>` | Nom cible de la skill d'audit de fin | `xp-bots-completion-audit` |
| `<GAP>` | Nom cible de la skill de détection de lacunes | `xp-bots-skill-gap-detector` |
| `<GOV>` | Nom cible de la skill de gouvernance des skills | `xp-bots-maintain-agent-skills` |
| `<RULES>` | Fichier cible des règles transversales de gouvernance | `.agents/PROJECT_RULES.md` |

Les noms de cycle de vie ci-dessus sont à créer si aucun équivalent n'existe au moment de
l'exécution. La skill existante **`mcl-matryoshka-construction-layers` conserve son nom**.
Tous les chemins du document sont relatifs à `<ROOT>`, sauf indication contraire ; les
liens Markdown sont relatifs au présent fichier. Aucun chemin absolu propre au poste ne
doit être figé dans les scripts ou configurations livrés.

---

## B. Phase 0 — Découverte et fiche de contexte

Objectif : savoir exactement où tu es, ce qui existe déjà, et avec quels outils.

### B.1 Identifier le dépôt et son périmètre réel

1. Résous `<ROOT>` avec `git rev-parse --show-toplevel` ; confirme l'identité XP-Bots avec
   le [README](../README.md) et les ancres de B.2. Depuis un sous-dossier, reviens à cette racine.
2. Lis la [décision de conception](decisions/00_Decision_Conception_et_Faisabilite_V3.md),
   les deux spécifications de `livrables/strategies_m15/`, le
   [guide d'implémentation](architecture/GUIDE_IMPLEMENTATION.md) et la
   [notice des fonctions de référence](../reference/README.md).
3. Distingue ce qui existe de ce qui reste à construire : `reference/` contient des calculs
   et contrats de comparaison, sans robot opérationnel, client HTTP ou passage d'ordres.
   Ne déduis aucune architecture de production de la seule présence de Python.
4. Relève `git status --short` avant toute écriture. Si la racine ne correspond pas à
   XP-Bots ou n'est pas accessible en écriture, arrête la mise en place et explique le
   problème. Aucun second dépôt n'est requis.

### B.2 Garde d'identité

Utilise ces quatre **ancres**, puis vérifie leur contenu :

- `livrables/strategies_m15/01_Triple_EMA_RSI_Repli_M15_Specification_IA.md` ;
- `livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md` ;
- `config/parametres_figes_v3.json` ;
- `tools/verify_project.py`.

Elles serviront dans les instructions permanentes pour éviter qu'un agent applique ces règles
à un autre projet ouvert en parallèle. Un nom de dossier seul ne suffit pas.

### B.3 Relever l'environnement

- Système d'exploitation et shell réellement disponibles : **Windows / PowerShell** sur
  le poste de référence ; conserver un repli POSIX si une exécution distante le nécessite.
- Interpréteur `<PY>` : `python --version` doit confirmer Python **3.13** ; relever aussi
  `sys.executable`. Ne suppose pas la présence d'un environnement virtuel.
- Dépendances de `requirements-dev.txt` : `numpy`, `pandas`, `tzdata` ; elles servent aux
  calculs synthétiques existants. Le moteur de gouvernance doit rester en bibliothèque
  standard. Vérifie les bibliothèques utiles déjà présentes (`yaml`, `tomllib`) avant de
  les employer pour les autres validations.
- Outils disponibles : `git`, `python`, éventuellement `py`, `powershell` ou `pwsh`, `rg`,
  et un outil de graphe de code ou serveur MCP déjà configuré. Aucun SDK de plateforme de
  trading ni outillage web ou mobile n'est requis pour cette tâche.
- Extensions et versions des agents AI installés. Sur un poste, on les lit dans le dossier
  d'extensions de l'éditeur. **Note les versions** : les normes de ces outils changent vite.

### B.4 Inventorier la gouvernance AI existante

À la racine de XP-Bots, liste le contenu de : `.agents/`, `.claude/`, `.codex/`, `.github/`,
`.clinerules/`, `.cline/`, `.cursor/`, `.vscode/`, et les fichiers racine du type `AGENTS.md`,
`CLAUDE.md`, `GEMINI.md`, fichiers de règles. Pour chacun, conclus : **source canonique**,
**adaptateur** (pointeur vers la source), ou **copie obsolète**.

**État initial constaté** : `.claude/skills/mcl-matryoshka-construction-layers/` contient
une vraie skill, son script `scripts/mcl.py`, ses références et ses gabarits. Ce n'est ni
un pointeur ni une copie générée. Son archive distribuable se trouve dans
`livrables/skills/mcl-matryoshka-construction-layers.zip`.

À cette date, le dépôt ne contient pas de `.agents/`, d'`AGENTS.md` ni de moteur de cycle de
vie partagé. Il est donc **partiellement outillé** : la phase 1 doit préserver et migrer MCL,
puis créer la gouvernance et les skills manquantes. Revérifie cet état avant d'agir ; si des
équivalents ont été ajoutés depuis, conserve leurs noms et fais porter les différences par
la configuration. Ne traite jamais le ZIP historique comme une seconde source éditable.

### B.5 Produire la fiche de contexte

Rends compte d'un tableau compact : racine XP-Bots, interpréteur, OS, outils AI et versions,
état de la gouvernance et de MCL, noms retenus pour `<APP>` et les skills de cycle de vie,
résultat initial de `python tools/verify_project.py`. Distingue les contrôles existants de
ceux à construire. **Cette fiche conditionne toutes les phases suivantes.**

### B.6 Carte des ressources et autorité métier

| Ressource existante | Rôle dans XP-Bots | Conséquence pour les skills |
|---|---|---|
| `livrables/strategies_m15/01_Triple_EMA_RSI_Repli_M15_Specification_IA.md` | Spécification autonome EMA + RSI + repli, version 3.1.0 | Couvrir C01–C11, S01 et A01–A15 |
| `livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md` | Spécification autonome London breakout, version 3.1.0 | Couvrir C01–C11, S02 et A01–A15 |
| `config/parametres_figes_v3.json`, `config/parametres_IA_integration_v1.json` | Exports figés des paramètres techniques et IA | Les citer sans recopier leurs valeurs dans les skills |
| `schemas/`, `prompts/prompts_IA_v1.json` | Contrats JSON et prompts exacts de l'IA métier | Préserver leur concordance avec les deux spécifications |
| `reference/technical.py`, `reference/llm_contracts.py` | Fonctions de comparaison et contrats hors ligne | Vérifier le code et ses limites avant de guider un portage |
| `tests/check_technical.py`, `tests/check_llm.py`, `tools/verify_project.py` | Contrôles techniques, IA et documentaires | Réutiliser les vraies commandes, sans annoncer des tests de production |
| `docs/architecture/`, `docs/data/`, `docs/decisions/` | Construction, données requises et décisions | Orienter les workflows de conception et de validation |
| `docs/validation/` | Empreintes, provenance et preuves datées | Conserver l'historique ; écrire les nouveaux rapports dans `.local/reports/` |
| `docs/references/` | Contexte documentaire historique | Ne pas traiter ces textes comme des instructions normatives |
| `.claude/skills/`, `livrables/skills/` | Source MCL initiale et archive distribuée | Migrer la source avec ses ressources ; conserver la provenance |

Les deux spécifications et leurs exports doivent rester cohérents ; toute contradiction
doit être signalée et résolue explicitement. `<RULES>` décrit la gouvernance et renvoie à
ces sources métier, sans les remplacer. Préserve notamment l'indépendance des méthodes,
les limites communes de risque, la séparation entre permissions fondamentales obligatoires
et complément LLM facultatif, le mode initial `PAPER_AB`, les API distantes exclusivement
et les plafonds IA partagés. La réussite des contrôles hors ligne ne prouve pas la rentabilité.

---

## C. Invariants d'architecture

1. **Une seule source éditable de skills** : `.agents/skills/<nom>/SKILL.md`, avec ses
   ressources (`references/`, `scripts/`, `assets/`, `agents/`). Tout le reste n'est qu'adaptateur ou
   copie générée.
2. **Frontmatter minimal** : `name` (identique au nom du dossier, kebab-case) et `description`
   (ce que fait la skill **et quand l'utiliser** : déclencheurs, vocabulaire réel du projet),
   1024 caractères au maximum pour rester compatible avec tous les outils.
3. **Pas de duplication des règles communes** dans les skills ni dans les adaptateurs. Seule
   exception tolérée : une copie **générée** pour un outil qui ne sait pas lire la source
   canonique, jamais éditée à la main, contrôlée par un validateur.
4. **Déterminisme d'abord** : tout ce qui peut être décidé par des données (règles de routage,
   cas de test, portes de vérification) l'est, plutôt que laissé au jugement du modèle.
5. **Les hooks ne remplacent pas les instructions permanentes** : ils les renforcent. Un outil
   sans hook fiable doit rester couvert par une règle toujours active.
6. **Tout mécanisme doit échouer « ouvert »** : si un hook casse, la session de l'humain
   continue ; l'erreur est journalisée, jamais silencieuse au point d'être introuvable.
7. **Bornage** : toute boucle corrective automatique a une limite dure (2 passes), afin de ne
   jamais enfermer une session.
8. **Tout est vérifiable** : chaque composant livré possède un test ou un validateur, et un
   test négatif prouvant qu'il détecte bien la régression qu'il prétend détecter.

---

## D. Vérification des normes de chaque outil (à refaire, ne pas croire ce tableau)

Les outils AI évoluent de mois en mois. **Tu dois revérifier** avant d'implémenter.

### D.1 Méthode de vérification, par ordre de fiabilité

1. **Le code de la version installée** : c'est la seule vérité pour le poste cible. Cherche,
   dans le binaire ou le bundle de l'extension, les chaînes de caractères qui révèlent les
   chemins scannés et les schémas acceptés (`skills`, `hooks`, noms d'événements, noms de
   champs JSON). Un simple outil de recherche plein texte suffit.
2. **La documentation officielle de l'éditeur** de l'outil, à la date du jour.
3. **Le journal des versions** (changelog) de l'outil : il annonce souvent les champs acceptés
   et les comportements corrigés.
4. **Les tickets publics**, utiles pour connaître les limites et les comportements non
   documentés ; à considérer comme incertains.

Consigne les conclusions avec leur source et leur niveau de certitude. Ce qui n'est pas
vérifié doit être signalé comme tel dans la documentation finale.

### D.2 Questions auxquelles tu dois répondre, pour chaque outil

- **Skills** : quels dossiers sont scannés, dans quel ordre ? Comment sont résolus deux
  fichiers de même nom (premier trouvé ? dernier trouvé ?) ? Quelles clés de frontmatter sont
  acceptées ? Quelle limite de longueur pour la description ? Les liens symboliques sont-ils
  suivis ?
- **Hooks** : existent-ils ? Où se déclarent-ils ? Quels événements (début de session, soumission
  de prompt, avant/après outil, sous-agent, fin de tour) ? Quel format d'entrée et **surtout**
  de sortie (comment injecter du contexte, comment bloquer une fin) ? Y a-t-il un champ
  spécifique à Windows ? Faut-il approuver les hooks, et que se passe-t-il sinon ?
- **Instructions permanentes** : quels fichiers sont lus automatiquement (`AGENTS.md` et ses
  variantes), et avec quels réglages ?
- **Requêtes non tapées** : qu'arrive-t-il lors de la validation d'un plan, d'une reprise, d'une
  compaction, d'une sous-tâche ? Quel événement se déclenche, s'il y en a un ?

### D.3 Matrice à établir pour XP-Bots

La présence d'un dossier `.claude/skills/` n'atteste ni la version d'une extension, ni son
activation. Aucune version d'outil ni capacité de hook n'est certifiée par ce document.
Établis la matrice suivante pour les outils effectivement disponibles ; pour un outil
absent, consigne « non installé / non testé » sans prétendre à une validation réelle.

| Outil à examiner | Découverte des skills à vérifier | Cycle de vie et points de vigilance à vérifier |
|---|---|---|
| Claude Code | Lecture de `.agents/skills/` ou nécessité d'un miroir `.claude/skills/` ; priorité des homonymes | Événements disponibles, formats JSON, import des instructions communes, rechargement des skills et hooks |
| Codex | Lecture de `.agents/skills/`, portée de découverte depuis un sous-dossier, métadonnées | Événements réellement exposés, commande Windows, activation et éventuelle approbation par empreinte |
| GitHub Copilot, selon les variantes utilisées | Dossiers scannés et priorité des homonymes | Différences éditeur/CLI/cloud, prise en compte des sorties de hooks, shell distant et visibilité des fichiers commités |
| Cline, selon la variante utilisée | Dossiers scannés et ordre de résolution | Hooks de fichiers par OS, prise en compte du contexte injecté, contrôle de l'outil de complétion si aucun hook de fin n'existe |

Consigne versions, date, sources, résultats et replis dans `.agents/COMPATIBILITY.md`.
Les comportements évoqués en H et J sont des cas à tester lorsqu'ils s'appliquent à la
version observée. N'impose ni copie, ni événement, ni approbation sur la seule base d'une
convention issue d'un autre projet.

---

## E. Architecture cible

### E.1 Arborescence cible dans le dépôt unique

Les fichiers de gouvernance ci-dessous sont **à créer**, sauf ressources déjà présentes
signalées. Les dossiers métier existants restent à leur place. Les adaptateurs et fichiers
de hooks propres aux outils ne sont ajoutés qu'après vérification de leurs conventions.

```
XP-Bots/
├─ AGENTS.md                         # point d'entrée commun, autorité et priorités
├─ <adaptateur par outil>            # pointeurs courts, jamais de copie de règles
├─ .agents/
│  ├─ PROJECT_RULES.md               # règles de gouvernance ; renvois aux contrats métier
│  ├─ COMPATIBILITY.md               # matrice par outil, activation, limites connues
│  ├─ agent-integrations.json        # registre machine des adaptateurs, hooks, miroirs (facultatif mais recommandé)
│  ├─ skill-gap-ledger.json          # registre des lacunes de skills
│  ├─ hooks/
│  │  ├─ agent_lifecycle.py          # moteur unique du cycle de vie
│  │  ├─ lifecycle.json              # configuration unique XP-Bots
│  │  ├─ invoke-agent-hook.ps1       # lanceur (Windows) ; équivalent shell si besoin
│  │  ├─ skill_mirrors.py            # génération et contrôle des copies pour l'outil qui l'exige
│  │  └─ gate_checks.py              # contrôles déterministes de fichiers
│  └─ skills/
│     ├─ xp-bots-request-skill-orchestrator/
│     ├─ xp-bots-completion-audit/
│     ├─ xp-bots-skill-gap-detector/
│     ├─ xp-bots-maintain-agent-skills/
│     ├─ mcl-matryoshka-construction-layers/  # source existante à migrer avec ses ressources
│     └─ <skills de domaine XP-Bots>/
├─ .claude/skills/                   # miroir généré si nécessaire, après migration de MCL
├─ config/                          # existant : paramètres figés des deux méthodes et de l'IA
├─ schemas/                         # existant : contrats JSON métier
├─ prompts/                         # existant : prompts métier exacts
├─ reference/                       # existant : fonctions Python de comparaison
├─ tests/                           # existant : contrôles techniques et IA hors ligne
├─ tools/                           # existant : verify_project.py
├─ docs/                            # existant : architecture, décisions, données, preuves
├─ livrables/
│  ├─ strategies_m15/               # existant : les deux spécifications autonomes
│  └─ skills/                       # existant : ZIP MCL historique, non éditable
├─ .local/reports/                  # rapports courants ignorés par Git
└─ <fichiers de hooks par outil>     # un par outil, au format qu'il impose
```

### E.2 Principe de fonctionnement, en une phrase par étage

- **Début de session** : le hook injecte un rappel du cycle **et le corps de l'orchestrateur**,
  pour qu'il soit présent sans relecture à chaque requête.
- **Chaque requête** : le hook calcule une sélection déterministe de skills et l'injecte ;
  l'orchestrateur l'ajuste selon le code réel et annonce la couverture tâche → skill.
- **Chaque requête non tapée** : même traitement, en **conservant** la sélection de la requête
  en cours (une notification ne doit pas réinitialiser le travail).
- **Fin de requête** : le hook vérifie le marqueur d'audit, un **pied d'audit** structuré, et
  des **portes machine** sur les seuls fichiers modifiés ; sinon il impose une passe corrective
  avec un brief exploitable.
- **À chaque requête encore** : la couverture des skills est évaluée ; une lacune réutilisable
  devient une skill, enregistrée dans tout ce qui la rend découvrable.

---

## F. Phases d'exécution

Chaque phase se termine par ses validations et un compte rendu, puis enchaîne.

### Phase 1 — Source unique des skills et copies générées

**Objectif** : exigence 1 satisfaite.

#### 1.a Variante « projet vierge » : constituer la bibliothèque canonique

Pour XP-Bots, cette étape complète la bibliothèque après la migration de MCL décrite en
1.b. Ne repars pas de zéro et ne remplace pas la méthode existante.

1. Inventorie les **domaines réels** de XP-Bots à partir de la carte B.6 : les deux
   stratégies, les calculs de référence, les contrats communs de risque et d'exécution,
   les permissions fondamentales, le complément LLM distant, les données causales et les
   contrôles de validation. Pour les composants futurs, couvre leurs spécifications et
   leur qualification sans annoncer une implémentation inexistante.
2. Regroupe-les en **8 à 14 skills de domaine dans le dépôt**, ni plus ni moins : une skill doit
   correspondre à un domaine qu'une requête réelle vise, pas à un fichier.
3. Écris chaque `SKILL.md` : `## Workflow` numéroté et vérifiable (commandes réelles du
   projet), puis `## Garde-fous` (pièges constatés dans ce projet). Interdits : placeholders
   non résolus, règles communes recopiées, README auxiliaires.
4. Crée les skills de cycle de vie : `<ORCH>`, `<AUDIT>`, `<GAP>`, `<GOV>`.
5. Crée `AGENTS.md` (autorité, ancres d'identité, ordre de priorité des instructions, cycle
   obligatoire) et `<RULES>`, avec renvois aux sources métier de B.6.

Découpage initial proposé, à confirmer par les types de requêtes réels ; les quatre skills
de cycle de vie et MCL ne sont pas comptées dans ces huit domaines :

| Skill de domaine proposée | Couverture et ressources principales |
|---|---|
| `xp-bots-ema-rsi-repli` | S01, états de tendance/repli/reprise, spécification 01, `reference/technical.py` |
| `xp-bots-london-breakout` | S02, range, cassure, quotas, horaires Londres/UTC, spécification 02 |
| `xp-bots-risk-execution-contracts` | C03 et C06–C09, risque et marge partagés, contrats courtier à implémenter |
| `xp-bots-fundamental-permissions` | C05, permissions fondamentales externes obligatoires et validité causale |
| `xp-bots-llm-integration-contracts` | A01–A12, `reference/llm_contracts.py`, configuration IA, schémas et prompts |
| `xp-bots-market-data-causality` | Données historiques, Bid/Ask, provenance, synchronisation et absence d'anticipation |
| `xp-bots-validation-replay` | C10–C11 et A13–A15, tests synthétiques, rejeu et protocole A/B à réaliser |
| `xp-bots-specification-consistency` | Cohérence des deux spécifications, exports JSON, versions, liens et preuves conservées |

Le catalogue de l'orchestrateur doit aussi référencer MCL pour les tâches de conception,
construction et refactorisation auxquelles sa méthode s'applique. MCL structure la
construction ; les skills métier apportent les contrats de XP-Bots.

#### 1.b Variante « projet déjà outillé » : rationaliser

1. **Commence par MCL** : inventorie et relève les empreintes de tous les fichiers de
   `.claude/skills/mcl-matryoshka-construction-layers/`. Migre la skill complète vers
   `.agents/skills/mcl-matryoshka-construction-layers/`, en conservant nom, contenu,
   script, références et gabarits. Vérifie l'égalité des empreintes avant de remplacer
   l'ancien emplacement. N'efface aucune ressource originale sans cette preuve.
2. Pour chaque dossier de skills propre à un outil, détermine s'il est **nécessaire** d'après
   la section D : si l'outil lit la source canonique, ces fichiers sont à supprimer (après
   avoir vérifié qu'ils ne contiennent que des pointeurs). Dans le cas MCL, l'ancien
   contenu réel n'est remplacé qu'après la migration et sa validation.
3. Pour l'outil qui ne lit pas la source canonique, remplace les pointeurs par des **copies
   générées** (spécification G.2).
4. Mets à jour le fichier d'entrée de cet outil pour qu'il **importe** la source commune selon
   la convention de l'outil, plutôt que de la paraphraser.
5. Conserve `livrables/skills/mcl-matryoshka-construction-layers.zip` et sa provenance
   historique. Documente qu'il s'agit d'une distribution datée, jamais chargée comme
   source active. Ne régénère pas cette archive pendant la mise en place.
6. Vérifie les références actives à l'ancien chemin, y compris le README et les contrôles
   Git de `tools/verify_project.py`. N'interdis pas aveuglément `.claude/skills/` si ce
   chemin reste le miroir requis d'un outil. Conserve les chemins historiques dans les
   registres de provenance en les distinguant des instructions courantes.

#### 1.c Contrôles de la phase

- Les frontmatters des skills et des copies sont du YAML valide ; `name` = nom du dossier ;
  description non vide et sous la limite.
- Le contrôle de synchronisation des copies passe.
- MCL conserve tous ses fichiers et leurs empreintes dans la source canonique ; les
  ressources citées depuis son éventuel miroir se résolvent vers cette source.
- Aucun dossier d'adaptateurs devenu inutile ne subsiste.
- Le validateur de gouvernance passe (il est adapté en phase 1, pas seulement en phase 5).

#### 1.d Tests négatifs exigés

Sur une **copie temporaire** du dépôt : une copie éditée à la main, une copie périmée (skill
supprimée de la source), une skill présente seulement côté outil, un fichier parasite dans un
dossier de copie, et une modification de la source non répercutée. Les cinq doivent être
détectés. Puis, **dans le dépôt réel**, recrée brièvement un dossier d'adaptateurs supprimé :
le validateur doit le refuser ; supprime-le ensuite.

---

### Phase 2 — Orchestrateur lancé en premier, sans exception

**Objectif** : exigence 2 satisfaite.

1. **Moteur unique** (spécification G.1) : un seul script traite tous les événements de tous
   les outils, piloté par la configuration XP-Bots. Il remplace les scripts de hooks
   disparates éventuellement présents.
2. **Lanceur** (G.1.9) : il relaie l'entrée de l'outil **octet par octet** et n'altère aucun
   encodage.
3. **Sélecteur déterministe** (G.3) : règles et cas de test en données, pas en code.
4. **Configuration de chaque outil** (section H) : déclare les événements disponibles, avec les
   formats de sortie propres à chacun.
5. **Instructions permanentes** : filet de sécurité pour les outils dont les hooks n'injectent
   rien.
6. **`SKILL.md` de l'orchestrateur** : ajoute l'étape « annoncer la couverture tâche → skill et
   signaler toute tâche sans skill », et une section « requêtes non tapées ».

**Contrôles** : la suite du cycle de vie (G.6) passe pour chaque couple outil × événement ;
les anciens modes de hooks éventuellement utilisés par d'autres outils du projet fonctionnent
toujours ; un prompt accentué conserve ses accents de bout en bout.

**Tests négatifs exigés** : retirer un événement d'un fichier de hooks, réintroduire un chemin
obsolète, déclarer une skill sans règle de routage — chaque cas doit être refusé par un
validateur.

---

### Phase 3 — Audit de fin et remédiation automatique

**Objectif** : exigence 3 satisfaite.

1. **Crée ou complète la skill d'audit** (G.4) : quatre contrôles, inventaire, plan de remédiation
   exécuté immédiatement, pied d'audit, marqueurs, mention des portes machine.
2. **Implémente la porte de fin** dans le moteur (G.1.7) : marqueur + pied + portes sur les
   seuls fichiers modifiés depuis le début de la requête ; blocage même si le marqueur est
   présent mais qu'une porte bloquante échoue ; deux passes maximum.
3. **Déclare les portes** (G.1.8) dans la configuration : rapides d'abord, lourdes ensuite,
   indicatives séparées des bloquantes.
4. **Couvre l'outil sans hook de fin** : applique la même porte à son outil de complétion, avec
   les seules vérifications rapides.

**Contrôles** : un marqueur sans pied est refusé ; un pied complet est accepté ; une porte
bloquante en échec impose une passe ; une porte indicative ne bloque pas mais est rapportée ;
sans base de comparaison, aucune porte ne s'exécute.

**Tests négatifs exigés** : clé de pied inconnue, absence de porte rapide, porte pointant un
script inexistant, et une **vraie** porte déclenchée par un fichier volontairement invalide.

---

### Phase 4 — Détection des lacunes et création dynamique de skills

**Objectif** : exigence 4 satisfaite.

1. **Crée la skill `<GAP>`** (G.5) : inventaire des types de tâches, classement en quatre
   catégories, registre, et procédure de création chargée seulement quand c'est nécessaire.
2. **Registre** : un fichier de données, avec promotion d'une lacune ponctuelle en skill à la
   deuxième occurrence.
3. **Générateur de skills** : une seule commande crée la skill **et** l'enregistre partout où
   elle doit être connue (routage, catalogue, cas de test, copies générées), puis relance les
   validateurs. Il refuse, **avant toute écriture**, des mots-clés qui ne sélectionneraient pas
   la skill pour sa propre requête d'exemple.
4. **Relie l'audit** : son quatrième contrôle délègue à `<GAP>` et déclare le résultat dans le
   pied d'audit.
5. **Rends les validateurs dynamiques** : ils découvrent les skills au lieu de s'appuyer sur une
   liste figée, et exigent pour chacune une règle de routage, une ligne de catalogue, un cas de
   test et, pour chaque outil qui l'exige, une copie à jour.

**Contrôles** : la suite du registre et du générateur passe ; une skill non enregistrée est
refusée ; le sélecteur trouve une skill fraîchement créée.

---

### Phase 5 — Documentation finale et vérification de bout en bout

**Objectif** : le mécanisme est documenté, activable et prouvé.

1. **Documente** : matrice par outil, mécanisme commun, activation pas à pas, commandes de
   vérification, **limites connues**. Mets à jour les index et journaux de gouvernance du
   projet, et supprime de la documentation toute affirmation devenue fausse.
2. **Exécute la suite complète** à la racine de XP-Bots : gouvernance et contrôles existants
   de I.1. Les deux stratégies doivent rester couvertes.
3. **Teste en conditions réelles**, outil par outil, avec une requête minimale et en lecture
   seule (section I.3).
4. **Fournis la checklist manuelle** pour les outils sans exécution non interactive.
5. **Rends compte** selon les critères d'acceptation (section K).

---

## G. Spécifications détaillées des composants

### G.1 Moteur du cycle de vie

Un seul fichier `.agents/hooks/agent_lifecycle.py`, sans dépendance hors bibliothèque
standard, **commun à tous les outils et domaines de XP-Bots**. Les différences entre outils
et contrôles sont déclarées dans `.agents/hooks/lifecycle.json` ; aucun moteur distinct
par stratégie, par outil ou par futur langage de robot.

#### G.1.1 Interface

- Invocation depuis `<ROOT>` : `<PY> .agents/hooks/agent_lifecycle.py --mode <événement>-<outil> [--input-file <chemin>]`.
- Accepte aussi un mode en argument positionnel, pour rester compatible avec des
  configurations existantes.
- Entrée : fichier passé par `--input-file` (supprimé après lecture), sinon variable
  d'environnement dédiée, sinon entrée standard.
- Sortie : **un seul objet JSON** sur la sortie standard, au format attendu par l'outil.
- Code de sortie : 0 en fonctionnement normal ; 2 seulement pour un mode inconnu.

#### G.1.2 Décodage de l'entrée

Lis des **octets**, puis décode : marque d'ordre d'octets UTF-8 et UTF-16 détectées, sinon
UTF-8 tolérant. **Ne fais jamais transiter l'entrée par une conversion de texte du shell** :
c'est ainsi que les accents sont détruits, ce qui dégrade ensuite la sélection des skills.
Si le JSON est invalide, traite le texte brut comme un prompt.

#### G.1.3 Identité de session et état

- Identité : premier champ non vide parmi identifiant de session, identifiant de tâche,
  identifiant de conversation ; à défaut, chemin de transcription ; sinon une valeur par défaut.
- Fichier d'état : dans le dossier temporaire du système, nommé d'après le dépôt et une
  empreinte de `racine | identité`. Un **pointeur** « dernière requête du dépôt » permet de
  retrouver la sélection après un effacement de contexte (fenêtre de l'ordre de 30 minutes).
- Contenu : texte de la requête, identifiants de requête et de run, sélection de skills,
  instantané de fichiers, compteur de passes correctives, trace du dernier événement par type,
  marqueur d'injection par run.
- Écriture **atomique** (fichier temporaire puis remplacement).
- Un réglage d'environnement permet de rediriger ce dossier : indispensable pour les tests.

Utilise un préfixe d'état propre à `xp-bots`. Les traces du cycle de vie des agents ne sont
ni les journaux de trading ni les snapshots du complément IA métier ; ne les mélange pas
avec les preuves conservées dans `docs/validation/`.

#### G.1.4 Instantané de fichiers

Liste les fichiers suivis **et** non suivis mais non ignorés par Git, puis relève pour chacun
date de modification et taille. En l'absence de Git, parcours le dépôt en excluant les dossiers
déclarés dans la configuration. **N'applique les exclusions qu'aux chemins relatifs** au dépôt,
jamais au chemin absolu : un dossier parent nommé comme une exclusion ferait disparaître tout
le dépôt.

Pour XP-Bots, aligne les exclusions sur `.gitignore` : `.git/`, `.local/`,
`.code-review-graph/`, environnements virtuels, caches Python, `data/raw/`, `data/cache/`,
`data/private/`, `runtime/`, `logs/`, `reports/` et `exports/`. Préserve le suivi des
ressources actives, des futurs fichiers de gouvernance et de
`livrables/skills/mcl-matryoshka-construction-layers.zip` ; ce dernier reste une archive,
pas une skill supplémentaire à découvrir.

#### G.1.5 Classement du prompt

Cinq catégories, dans cet ordre de priorité :

1. **passe corrective** : le texte commence par le préfixe du brief correctif ;
2. **notification système** : le texte contient un marqueur de notification de l'outil ;
3. **continuation** : le texte normalisé appartient à une liste de formules
   (« continue », « vas-y », « ok », « implémente le plan », « l'utilisateur a approuvé le
   passage en mode action »…) ou commence par l'une d'elles ;
4. **vide** ;
5. **nouvelle requête**.

Pour les catégories 1 à 4 : **ne réinitialise ni l'instantané ni le compteur**, et conserve la
sélection de la requête en cours. Pour une notification, **n'exécute pas le sélecteur sur son
texte** : il est bruité et provoque une sur-sélection.

#### G.1.6 Sélection et héritage

Appelle le sélecteur (G.3) et récupère la sélection, les skills réellement appariées et un
signal d'absence de correspondance. Pour une **nouvelle requête vague** — aucune correspondance,
aucune règle de repli, et peu de mots utiles (seuil configurable, de l'ordre de 15) — **hérite**
de la sélection précédente et annonce explicitement cet héritage. Une requête spécifique, elle,
repart de zéro.

#### G.1.7 Fin de requête

1. Calcule les fichiers modifiés depuis le début de la requête. **Sans instantané de
   référence, renvoie une liste vide** : on ne juge pas des modifications appartenant à une
   requête antérieure, et cela évite des exécutions de portes inutiles.
2. Exécute les portes (G.1.8).
3. Constitue la liste des problèmes : marqueur absent, pied incomplet (avec les clés
   manquantes), portes bloquantes en échec.
4. Décide :
   - marqueur de blocage assumé ⇒ autoriser, avec un message récapitulatif ;
   - aucun problème ⇒ autoriser, remise à zéro du compteur ;
   - limite de passes atteinte ⇒ autoriser, en listant les points non résolus ;
   - sinon ⇒ **bloquer** avec le brief correctif (G.1.10) et incrémenter le compteur.
5. **Anti-doublon inter-outils** : si le même événement, avec la même empreinte, a déjà été
   traité par une **autre** configuration d'outil dans une fenêtre courte (une vingtaine de
   secondes), renvoie la même décision sans recompter. Un même outil qui répète l'événement est
   traité normalement, sinon la limite de passes serait contournée.

#### G.1.8 Portes machine

- Déclaration par porte : nom, motifs de chemins, commande, délai, et deux drapeaux :
  **rapide** (utilisable là où le temps est très contraint) et **indicative** (échec rapporté
  sans blocage).
- **Ne porte que sur les fichiers modifiés** : une porte ne doit jamais pouvoir échouer à cause
  d'un problème préexistant ailleurs. Les contrôles globaux du projet (conservation des
  ressources, cohérence documentaire et suites de référence) sont déclarés **indicatifs**, car ils peuvent échouer
  pour une cause antérieure.
- Substitutions dans la commande : interpréteur, racine du dépôt, dossier des hooks, dossier des
  skills, et la **liste des fichiers appariés** (plafonnée, avec mention de la troncature).
- Appariement des motifs : implémente un convertisseur motif → expression régulière gérant
  `**/`, `**`, `*` et `?`, en interdisant à `*` de franchir un séparateur de chemin.
- Budget global de temps, portes rapides en premier ; au-delà du budget, les portes restantes
  sont **rapportées comme non exécutées**, jamais silencieusement ignorées.
- Une porte qui dépasse son délai, ou dont l'outil est absent, est rapportée comme non exécutée.
- **Anti-récursion** : le moteur pose une variable d'environnement dans le sous-processus de
  chaque porte ; quand elle est présente, aucune porte ne s'exécute. Sans cela, une porte qui
  lance la suite de tests relance des portes, indéfiniment.

**Application à XP-Bots** : les commandes existantes ci-dessous s'exécutent depuis `<ROOT>`.
Elles ne prennent actuellement aucun argument de sélection de fichiers ; ne leur invente
pas une option `--files` et ne les présente pas comme des contrôles ciblés.

| Fichiers modifiés déclenchant le contrôle | Commande existante | Statut dans le hook de fin |
|---|---|---|
| `reference/technical.py`, `tests/check_technical.py`, `config/parametres_figes_v3.json` | `python tests/check_technical.py` | Indicatif : suite technique globale |
| `reference/llm_contracts.py`, `tests/check_llm.py`, paramètres IA, `schemas/**`, `prompts/**`, spécifications | `python tests/check_llm.py` | Indicatif : suite globale des contrats IA |
| `README.md`, `docs/**`, `livrables/strategies_m15/**`, `config/**`, `schemas/**`, `prompts/**`, `reference/**`, `tests/**`, `tools/**` | `python tools/verify_project.py` | Indicatif : conservation, liens et deux suites de référence |
| Fichiers de gouvernance et d'adaptateurs créés par ces phases | Validateurs de gouvernance prévus en G.6 | Bloquant seulement sur le périmètre modifié et les dépendances nécessaires au contrat vérifié |

Développe les libellés « paramètres IA » et « spécifications » en chemins explicites dans
la configuration. Ajoute au moins une **porte rapide bloquante** à `gate_checks.py` : par
exemple JSON strict, syntaxe Python vérifiée sans import ni production de bytecode, liens
locaux Markdown ou contrats des adaptateurs, sur les seuls fichiers appariés. Ce script
est à construire ; `tools/verify_project.py` ne fournit pas déjà cette interface.

Une suite globale indicative dans un hook reste une validation de non-régression à réussir
en fin de phase ; l'échec préexistant est documenté avec sa preuve. Les contrôles de
gouvernance complètent les suites métier. `python tools/verify_project.py --git` est réservé
à une vérification Git explicitement nécessaire, sans fetch ni merge réel ; ne l'ajoute pas
comme porte automatique. Aucun de ces contrôles ne doit appeler une API ni un courtier.

#### G.1.9 Lanceur spécifique à l'OS

Sous Windows, un script PowerShell : il résout `<PY>` (interpréteur explicitement configuré,
venv du dépôt ou parent s'il existe, puis interpréteur système), vérifie sa compatibilité
Python 3.13, copie l'entrée **en octets** dans un fichier temporaire, appelle le moteur avec
`--input-file`, puis supprime ce fichier. Le poste de référence utilise `python` sans venv
de dépôt ; ne fige aucun chemin utilisateur. Hors Windows, appelle directement le moteur :
l'entrée standard suffit. Conserve les anciens noms de modes si le projet en utilise déjà,
afin de ne pas casser les outils hors périmètre.

#### G.1.10 Gabarits de messages

- **Contexte de début de session** : rappel du cycle (orchestrateur d'abord, audit à la fin,
  fichiers de règles), reprise éventuelle de la requête en cours, état des outils auxiliaires,
  puis **le corps de l'orchestrateur**. Viser un millier de tokens au maximum : certains outils
  plafonnent le contexte injecté.
- **Contexte de prompt** : quatre lignes numérotées — exécuter l'orchestrateur et appliquer les
  règles ; sélection déterministe avec son **origine** (requête, héritage, continuation, brief) et
  les chemins à charger ; vérifier le code réel et annoncer la couverture ; appliquer l'audit
  avant la réponse finale.
- **Contexte de plan approuvé** : signale une nouvelle phase d'exécution de la **même** requête,
  avec une sélection recalculée sur le texte du plan.
- **Contexte de sous-tâche** : skills retenues pour la requête parente, consigne de ne charger
  que l'utile, et **interdiction d'émettre le marqueur d'audit** (réservé au fil principal).
- **Brief correctif** : préfixe numéroté de passe, liste des constats, consigne de recharger
  l'orchestrateur avec la sélection de remédiation, rappel des quatre contrôles, exigence d'un
  inventaire puis d'un plan exécuté, détail des portes en échec **avec la commande à rejouer**,
  et liste des chemins modifiés.

#### G.1.11 Échec ouvert

Enveloppe tout le traitement : en cas d'exception, journalise l'horodatage et la trace dans le
dossier d'état, puis émets une sortie neutre valide pour l'outil. Une session humaine ne doit
jamais être interrompue par ce mécanisme.

### G.2 Copies générées pour l'outil qui ne lit pas la source canonique

- Pour chaque skill canonique, génère un fichier unique reprenant **tel quel** le frontmatter,
  puis un **en-tête de génération** explicite (source, générateur, interdiction d'éditer), puis
  le corps.
- **Réécris les chemins relatifs** du corps (`scripts/…`, `references/…`, `assets/…`,
  `../autre-skill/…`) en chemins relatifs à la racine du dépôt, **uniquement si la cible
  existe** : une mention générique (« ajouter un fichier de métadonnées ») ne doit pas être
  transformée en chemin.
- Ne duplique **ni** les scripts **ni** les références : seules les instructions le sont.
- Deux modes : contrôle (échoue en listant les écarts) et écriture (régénère, supprime les
  copies périmées reconnaissables à leur en-tête, **laisse intactes** et signale les skills
  présentes seulement côté outil).
- Préserve les fins de ligne du fichier source, pour que le contrôle d'égalité soit stable.

Pour MCL, ces règles s'appliquent **après** la migration complète de 1.b. L'éventuel
`.claude/skills/mcl-matryoshka-construction-layers/SKILL.md` généré renvoie aux ressources
de `.agents/skills/mcl-matryoshka-construction-layers/`. Conserve l'archive distribuée
hors du périmètre de découverte des skills actives. Les nouveaux fichiers Markdown suivent
les fins de ligne LF de `.gitattributes` ; les octets d'origine des ressources migrées
restent préservés jusqu'à une évolution explicitement justifiée.

### G.3 Sélecteur déterministe

- **Règles en données** : skills par défaut, liste des skills de cycle de vie (dispensées de
  mots-clés), skills dispensées de routage, règles `skill → mots-clés`, règles de repli
  conditionnelles.
- **Normalisation** : minuscules, accents retirés. Trois formes de mots-clés : mot isolé
  (comparé aux mots du texte), préfixe terminé par `*`, et **expression composée** (espace,
  trait d'union, apostrophe) comparée au texte entier. Sans cette troisième forme, un mot-clé
  comme `mon-service` ne correspond jamais à rien.
- **Deux interfaces** : une fonction renvoyant la liste des skills (compatibilité) et une
  fonction d'analyse renvoyant aussi les skills appariées, les replis déclenchés et un signal
  d'absence de correspondance.
- **Cas de test en données** : requêtes réalistes du projet avec, pour chacune, la sélection
  exacte attendue ou des appartenances et exclusions. Un test vérifie en plus que **toute**
  skill est routée (par règle, défaut, repli, cycle de vie ou dispense).

Les requêtes de test doivent employer le vocabulaire du dépôt, par exemple « vérifier
le repli EMA15/25/50 et RSI14 », « contrôler le range London 02:00–07:00 », « auditer le
contrat de veto IA et son budget partagé », « vérifier la cohérence entre les deux
spécifications et les paramètres JSON », ou « construire le moteur par couches MCL ».
Inclure les accents, `PAPER_AB`, les noms des fichiers et les expressions composées ;
ne sélectionne pas toutes les skills pour une simple demande documentaire.

### G.4 Skill d'audit de fin

Contenu obligatoire :

1. **Double contrôle de complétion, bidirectionnel** : chaque exigence de la requête pointe vers
   un résultat, un fichier, une commande, une observation ou une limite déclarée ; et chaque
   fichier modifié pointe vers une exigence autorisée. Tout élément non relié est une omission
   ou un écart de périmètre jusqu'à preuve du contraire.
2. **Impact et non-régression** : outil de graphe ou de recherche d'abord, puis **vérification
   dans la source courante** ; exécution des validations les plus proches du risque ;
   distinction explicite entre échec préexistant et régression introduite.
3. **Vérification indépendante et adversariale** : tenter de **réfuter** le résultat par une voie
   différente de celle de l'implémentation ; relecture à contexte vierge si l'outil le permet,
   sinon grille de réfutation (structure, liens, schémas, artefacts générés, contrats,
   permissions, configuration, documentation) ; comparaison finale avec la requête d'origine,
   pas seulement avec le plan suivi.
4. **Couverture des skills** : délègue à `<GAP>`.

Puis : **inventaire** des problèmes sous forme de tableau (identifiant, type, preuve, fichier ou
symbole, gravité, correction, validation), **plan de remédiation** ordonné et **exécuté
immédiatement** après rechargement de l'orchestrateur, dans la limite de deux passes, sans
jamais ajouter de dépendance, de migration métier, d'action destructive ni de changement hors périmètre
pour faire passer l'audit. Après deux échecs : livrer les blocages avec leurs preuves.

Dans XP-Bots, vérifie aussi la cohérence entre les deux spécifications et leurs exports,
la conservation des ressources protégées et la distinction entre code de référence et
composant opérationnel. Ne change ni paramètre figé, ni empreinte attendue, ni preuve
historique pour masquer un échec. La migration de la source MCL prévue en phase 1 est une
opération de gouvernance autorisée par cette mise en place, pas une correction métier.

Enfin : **pied d'audit** et **marqueurs**.

- Le pied est un bloc inséré en fin de réponse, contenant quatre clés dont les noms sont
  **vérifiés par la machine** : complétion (exigences prouvées, écarts), impact (méthode,
  régressions), vérifications exécutées, couverture des skills.
- Deux marqueurs exacts : succès et blocage assumé. Le hook de fin les reconnaît littéralement :
  ils ne doivent jamais changer de forme sans mise à jour simultanée du moteur et des tests.

### G.5 Détection de lacunes et création dynamique

**Skill `<GAP>`**, corps court (elle est chargée à chaque requête) :

1. inventaire des **types de tâches** réellement effectués, jamais des fichiers ;
2. classement : couvert ; partiellement couvert (étendre) ; non couvert et réutilisable (créer) ;
   non couvert et ponctuel (consigner) ;
3. registre, avec la commande exacte ;
4. création ou extension : **charge la procédure détaillée seulement à ce moment** ; hors mode
   écriture (planification, lecture seule), n'écris rien et déclare la skill envisagée.

Garde-fous : préférer l'extension à la création ; au plus une nouvelle skill par requête ; pas
de skill pour une commande unique ni pour une règle déjà canonique ; nom de dossier = champ de
nom ; validateurs verts avant la fin de la requête.

**Registre** : entrées avec identifiant normalisé, libellé d'origine **conservé**, nombre
d'occurrences, dates, preuves (bornées), décision et skill associée. Une lacune ponctuelle est
promue au seuil configuré (deuxième occurrence). Outil en ligne de commande : enregistrer,
résoudre, consulter, lister ; toute décision hors vocabulaire est refusée.

**Générateur de skills** : une commande qui, dans l'ordre, (1) valide le nom, la description,
les mots-clés et la présence d'un signal de catalogue ; (2) **vérifie par avance** que les
mots-clés sélectionnent bien la skill pour la requête d'exemple fournie, et refuse sinon
**sans rien écrire** ; (3) crée la skill et ses métadonnées ; (4) ajoute la règle de routage, la
ligne de catalogue et le cas de test ; (5) régénère les copies ; (6) enregistre la décision au
registre ; (7) **relance les validateurs** et échoue bruyamment s'ils échouent. Un mode
simulation et un mode extension d'une skill existante sont exigés.

### G.6 Validateurs et suites de tests

**Validateur de gouvernance** (unique pour XP-Bots, adapté à ses conventions) :

- skills : frontmatter conforme, nom = dossier, description présente et sous la limite,
  ressources citées existantes, aucun placeholder non résolu, pas de doublon de nom ;
- copies générées : synchronisation, absence de copie périmée ou de fichier parasite ;
- adaptateurs : présence, taille bornée, références obligatoires, absence de blocs canoniques
  recopiés ;
- configuration du cycle de vie : skills citées existantes, sélecteur et fichiers de règles
  présents, clés du pied d'audit déclarées, portes valides (motifs, commande, scripts existants,
  au moins une porte rapide) ;
- bibliothèque de skills : skill de lacunes et ses scripts, registre lisible et conforme, et
  **pour chaque skill** une règle de routage, une ligne de catalogue et un cas de test ;
- configurations d'outils : fichiers présents, événements attendus déclarés, modes invoqués
  présents, réglages d'éditeur cohérents ;
- chemins obsolètes : leur réapparition est un échec ;
- absence d'artefacts générés parasites.

Ajoute les vérifications propres au dépôt : conservation complète de MCL pendant sa
migration, absence de découverte du ZIP historique comme skill active, validité des liens
vers les ressources métier de B.6 et absence de seconde gouvernance pour l'une des deux
stratégies. La détection des anciens chemins distingue références actives et provenance
historique. Les contrôles de conservation métier existants restent assurés par
`tools/verify_project.py` ; le nouveau validateur ne remplace pas leurs preuves.

**Suite du cycle de vie** : pour chaque couple outil × événement, vérifie l'injection de
l'orchestrateur et le **format exact** de sortie ; les continuations (notification,
« continue », plan, brief) conservent la sélection ; l'héritage d'une requête vague ;
la validation de plan ; le contexte de sous-tâche ; la borne de deux passes ; l'anti-doublon
inter-outils ; les anciens modes ; le pied d'audit (absent ⇒ blocage, complet ⇒ autorisation) ;
les portes (bloquante en échec, indicative, non exécutée, absence de base de comparaison) ; la
porte de l'outil sans hook de fin ; et, sur Windows, le lanceur et les hooks de fichier
**exécutés comme l'outil les exécute**, avec un prompt accentué.

**Suite du registre et du générateur** : tout s'exécute sur une **copie temporaire** du dépôt,
afin de ne jamais écrire dans le registre réel.

**Règle impérative pour les suites de tests** : une suite qui exerce les portes doit **neutraliser
la variable d'anti-récursion** héritée d'une porte parente, sinon elle se contredira quand elle
sera elle-même exécutée comme porte.

---

## H. Configuration par outil

Pour chaque outil, applique ce que la section D a établi **pour la version installée**.

### H.1 Règles générales

- Un **seul fichier de hooks par outil**, sans doublon de source : deux sources actives pour le
  même outil signifient des événements traités deux fois.
- Déclare les variantes de commande par système d'exploitation quand l'outil le permet.
- Délais : courts pour le début de session et le prompt ; **largement dimensionné pour la fin de
  requête**, car les portes peuvent exécuter des tests (prévoir plusieurs minutes).
- Pour l'outil dont les hooks sont approuvés par empreinte : **documente la ré-approbation**
  comme une action humaine obligatoire après toute modification.
- Pour l'outil qui ignore la sortie du hook de prompt : appuie-toi sur le début de session et
  les instructions permanentes.
- Pour l'outil dont une variante ignore le contexte des hooks de début : **injecte au premier
  appel d'outil du run**, une seule fois, grâce au marqueur d'injection de l'état.
- Pour l'outil sans hook de fin : applique la porte à son **outil de complétion**, avec les
  seules vérifications rapides, et dis-le dans sa règle permanente.

### H.2 Événements à couvrir, par ordre d'importance

| Besoin | Événement typique | Repli si absent |
|---|---|---|
| Charger l'orchestrateur une fois par session | début de session (toutes sources) | instruction permanente |
| Sélection par requête | soumission de prompt | début de session + instruction permanente |
| Reprise après validation d'un plan | après outil, filtré sur l'outil de sortie de planification | formule de continuation détectée sur le prompt suivant |
| Sous-tâche déléguée | démarrage de sous-agent | rien (documenter la limite) |
| Fraîcheur des copies générées et des outils auxiliaires | après outil d'édition | début de session |
| Audit de fin | fin de tour | porte sur l'outil de complétion, sinon règle permanente |

### H.3 Instructions permanentes

- `AGENTS.md` : autorité, ancres d'identité, démarrage obligatoire, ordre de priorité,
  règles de maintenance, exception des copies générées, mention de la couverture des skills.
- Fichier d'entrée propre à chaque outil : **pointeur court**, jamais une copie. Quand l'outil
  offre une syntaxe d'import, utilise-la pour inclure `AGENTS.md` au lieu de le paraphraser.
- Règle toujours active pour l'outil sans hook fiable : cycle complet, pied d'audit et
  marqueurs, et mention explicite de ce que ses hooks peuvent ou ne peuvent pas faire.

---

## I. Vérification

### I.1 Suite automatique

Exécute, depuis **la racine de XP-Bots** : contrôle des copies générées, validateur de gouvernance, tests
du sélecteur, suite du cycle de vie, suite du registre et du générateur, et tout audit
documentaire existant. Exécute les validations déjà disponibles à chaque phase ; à la fin,
tous les composants prescrits doivent être couverts. Tout doit être vert **à la fin de
chaque phase**, pas seulement à la fin.

Les commandes métier et documentaires existantes sont :

```powershell
python --version
python tests/check_technical.py
python tests/check_llm.py
python tools/verify_project.py
```

La dernière commande relance déjà les deux suites ; pour une vérification globale, elle
suffit sans les rejouer séparément. Si les dépendances techniques manquent, utiliser
`python -m pip install -r requirements-dev.txt` pour installer les versions déjà déclarées,
sans ajouter de dépendance au projet. Les résultats courants vont dans `.local/reports/` ;
`docs/validation/verification_projet.json` reste la copie d'audit historique.

Les scripts de vérification de la nouvelle gouvernance sont à créer au sein de ses skills
ou hooks et leurs commandes exactes sont à documenter après implémentation. Ne présente
pas `tools/verify_project.py` comme un validateur de hooks, de routage ou de miroirs : ce
n'est pas son rôle actuel.

### I.2 Tests négatifs

Pour chaque garantie annoncée, prouve qu'elle est détectée quand elle est violée. Au minimum :
copie éditée à la main, copie périmée, skill sans routage ni catalogue ni cas de test, événement
retiré d'une configuration, chemin obsolète réintroduit, clé de pied inconnue, porte sans script,
porte bloquante en échec, mots-clés inopérants. **Restaure systématiquement l'état initial** et
prouve-le.

### I.3 Tests en conditions réelles

Pour chaque outil disposant d'une exécution non interactive, lance une requête **minimale et en
lecture seule** dans XP-Bots, et cherche quatre preuves :

1. le contexte du début de session contient le cycle et l'orchestrateur ;
2. l'état de requête écrit par le hook de prompt existe, avec la requête et la base de
   comparaison ;
3. une fin sans pied d'audit est **bloquée**, avec un brief exploitable ;
4. la réponse finale conforme est acceptée.

Vérifie aussi, par comparaison avant/après, que le dépôt n'a pas été modifié. Quand l'outil
n'expose pas d'exécution non interactive, rabats-toi sur la checklist manuelle et **dis-le**.

Utilise par exemple « indique en lecture seule où sont définies les deux stratégies et
leurs validations ». Ce test n'implique ni exécution des robots, ni appel LLM métier, ni
connexion au courtier. Isole l'état du cycle de vie et les registres de test ; compare les
fichiers versionnables avant/après, indépendamment des rapports locaux ignorés.

### I.4 Checklist manuelle à livrer

Pour chaque outil : comment ouvrir le projet, où vérifier que les skills sont détectées, où
approuver ou activer les hooks, comment constater l'injection de l'orchestrateur, et comment
provoquer puis lever un blocage de fin. Ajoute la contrainte propre aux exécutions distantes :
elles ne voient que des fichiers **commités**.

---

## J. Pièges du mécanisme à prévenir

Ces cas guident les validations de XP-Bots ; ils ne constituent pas un historique
d'incidents constatés dans ce dépôt. Pour les comportements propres aux outils, applique
les résultats de la vérification de version décrite en D.

1. **Encodage de l'entrée des hooks** : faire transiter le JSON par une conversion de texte du
   shell détruit les accents, donc la sélection des skills. Relaye les octets.
2. **Notifications et continuations** : sans classement du prompt, une notification
   réinitialise la requête en cours et sur-sélectionne les skills.
3. **Requêtes vagues** : « continue », « lance l'étape suivante » ne contiennent aucun signal ;
   sans héritage, la sélection s'effondre sur le minimum.
4. **Mots-clés composés** : un mot-clé avec trait d'union ou apostrophe n'est jamais un mot
   isolé du texte. Traite-le comme une expression.
5. **Générateur trop permissif** : des mots-clés qui ne sélectionnent pas la skill créent une
   skill morte. Vérifie la sélection avant d'écrire.
6. **Exclusions de chemins appliquées au chemin absolu** : un dossier parent homonyme d'une
   exclusion vide l'instantané.
7. **Récursion des portes** : une porte qui lance la suite de tests relance des portes. Pose
   une variable d'anti-récursion, et neutralise-la dans les suites qui doivent exercer les
   portes.
8. **Portes jugeant des modifications antérieures** : sans base de comparaison, n'exécute
   aucune porte.
9. **Contrôles globaux du projet** : ils échouent pour des causes préexistantes. Déclare-les
   indicatifs.
10. **Sortie d'erreur d'un script de validation** : selon le shell, écrire sur la sortie
    d'erreur peut interrompre le script et masquer toutes les anomalies suivantes. Rends compte
    de **toutes** les anomalies.
11. **Hooks approuvés par empreinte** : après modification, ils sont ignorés **sans
    avertissement**. Documente la ré-approbation.
12. **Copies générées homonymes de la source** : vérifie l'ordre de résolution de chaque outil,
    et neutralise le risque (réglage d'éditeur, ou confiance dans l'ordre constaté).
13. **Disque saturé** : à zéro octet libre, les hooks échouent ouvert et **n'injectent plus
    rien**, sans que l'humain s'en aperçoive. Avant de soupçonner le code devant un
    comportement erratique, vérifie l'espace disque et le journal d'erreurs du moteur.
14. **Deux sources de hooks pour un même outil** : événements traités deux fois, compteurs
    faussés. D'où l'anti-doublon inter-outils et la source unique.

---

## K. Critères d'acceptation et compte rendu final

Tu ne peux déclarer le travail terminé que si **tous** les points suivants sont vrais, preuves
à l'appui :

1. Les quatre exigences de la section A.1 sont satisfaites **dans le dépôt XP-Bots**, pour
   les deux stratégies et les ressources communes.
2. Il n'existe qu'une source éditable de skills ; toute copie est générée, contrôlée, et
   justifiée par une norme d'outil documentée en section D.
3. L'orchestrateur est déclenché pour chaque type de requête listé en H.2, ou la limite est
   documentée quand l'outil ne le permet pas.
4. La fin de requête vérifie marqueur, pied d'audit et portes, et **bloque réellement** : tu
   dois l'avoir constaté au moins une fois, y compris sur ta propre réponse.
5. Une lacune de skill est détectée, consignée, et une skill peut être créée **et routée** par
   une seule commande, validateurs inclus.
6. Les validateurs refusent toute skill non enregistrée et toute configuration incomplète.
7. Les suites automatiques de gouvernance et les contrôles existants de XP-Bots sont verts,
   et chaque garantie du mécanisme a son test négatif.
8. Un **seul exemplaire canonique** du moteur, du lanceur, des générateurs, des validateurs
   et des schémas de gouvernance sert tous les outils et domaines. Les miroirs sont
   contrôlés ; la migration de MCL conserve les empreintes de tous ses fichiers et
   l'archive historique reste intacte. Les différences passent par la configuration.
9. La documentation décrit le mécanisme, l'activation et les **limites connues** ; aucune
   affirmation fausse ne subsiste dans les documents de gouvernance.
10. Aucun commit, aucune modification hors périmètre, aucun artefact de test résiduel.

**Compte rendu final attendu** : ce qui a été mis en place par exigence ; les preuves
(validations, tests négatifs, tests réels, avec leurs résultats) ; les défauts trouvés et
corrigés en route ; les **limites connues** et les actions humaines restantes (approbations,
activations, commit éventuel) ; et le pied d'audit avec son marqueur.

---

## L. Annexes

### L.1 Conventions de nommage

- Dossiers et noms de skills en kebab-case, préfixés par `<APP>` pour les skills de domaine ;
  les skills de cycle de vie peuvent garder un nom générique si le projet en utilise déjà.
  La skill importée `mcl-matryoshka-construction-layers` garde son nom et sa provenance.
- Une skill = un domaine qu'une requête réelle vise. Ni une skill par fichier, ni une skill
  fourre-tout.
- Les noms de fichiers et de modes de hooks doivent être **déductibles** : `<événement>-<outil>`.

### L.2 Schéma de la configuration du cycle de vie

Clés attendues : version de schéma ; nom du projet ; préfixe d'état ; noms des skills
d'orchestration, d'audit, de lacunes et de gouvernance ; fichiers de règles ; chemin du
sélecteur ; exclusions de l'instantané ; limite de passes correctives ; seuil de mots pour
l'héritage ; outils pour lesquels le début de session consulte les outils auxiliaires ;
formules de continuation additionnelles ; clés du pied d'audit ; budgets de temps des portes
(normal et rapide) ; liste des portes ; bibliothèque de skills (catalogue, registre, seuil de
promotion, nombre maximal de créations par requête, validateurs).

### L.3 Schéma des règles de routage

Clés : version de schéma ; description ; skills par défaut ; skills de cycle de vie ; skills
dispensées de routage ; règles (`skill`, `mots-clés`) dans l'ordre de chargement souhaité ;
replis (`skill`, mots déclencheurs, skills dont la présence annule le repli).

### L.4 Schéma des cas de test de sélection

Liste de cas : requête réaliste, et soit la sélection exacte attendue, soit des appartenances et
des exclusions, plus éventuellement le signal d'absence de correspondance attendu.

### L.5 Schéma du registre de lacunes

Liste d'entrées : identifiant normalisé, libellé d'origine, nombre d'occurrences, première et
dernière observation, preuves bornées, décision (consignée, proposée, promue, créée, étendue,
rejetée) et skill associée.

### L.6 Adaptations possibles sans trahir le mécanisme

- **Langue** des messages et des skills : celle du projet. En revanche, les **noms des clés du
  pied d'audit et les marqueurs** doivent rester stables, car ils sont vérifiés par la machine.
- **Noms des skills de cycle de vie** : ceux du projet.
- **Emplacement du fichier de règles transversales** : celui du projet.
- **Outils supplémentaires** (autres extensions, autres fournisseurs) : ajoute un mode et un
  format de sortie par outil ; n'ajoute jamais un second moteur.
- **Absence d'outil de graphe de code** : remplace-le par des recherches ciblées dans la source,
  et dis-le dans la documentation.
- **Projet sans Git** : l'instantané de fichiers se rabat sur un parcours du dépôt ; signale la
  dégradation.
- **Différences entre domaines ou outils de XP-Bots** : mots-clés de routage, ressources
  chargées, formats de sortie et portes peuvent différer. Le moteur, le lanceur, les
  générateurs, les validateurs et les schémas de gouvernance restent **uniques** (critère K.8).
  Toute différence légitime passe par la configuration ; ne sépare pas les stratégies en
  dépôts artificiels et ne crée pas un moteur par plateforme future.

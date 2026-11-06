# Rapport de passation — robot 1 `EMA_V3` (Triple EMA + RSI + repli M15), après la phase 3

> Destinataire : l'agent AI qui reprend l'implémentation du **plan maître**
> `docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md`, à partir de la **phase 4**, dans une autre session.
> Objectif : continuer exactement comme l'agent précédent l'aurait fait — même méthode (MCL), mêmes contrats,
> mêmes contrôles, même façon de clore une phase et de rendre compte.
> Rédigé le 2026-11-06. État de référence : branche `claude/epic-edison-4lurlt`, commit `d8c3f2a` (plus le commit
> qui ajoute ce rapport), arbre propre, CI `robot-ci` verte.

## 0. Résumé en dix lignes

1. Le dépôt XP-Bots contient les spécifications 3.1.0 de deux robots Forex M15 ; on construit le **robot 1**
   (méthode S01 « Triple EMA + RSI + repli », identifiant `EMA_V3`) en **Python 3.13 + MetaTrader 5**.
2. La construction suit le plan maître (phases 0 à 11) et la méthode **MCL** (couches inside-out, gate puis gel).
3. **Phases 0, 1, 2 et 3 terminées** : cadrage, squelette composite, artefact `donnees-temps` (bougies M15,
   indicateurs, trous) et artefact `moteur-ema` (méthode S01) **construits, figés et branchés**.
4. Le rejeu `python -m xpbots.app.rejeu` produit un journal C09 complet ; les signaux S01 sont émis puis refusés
   (`FUNDAMENTAL_INVALID`, ou `ENVIRONMENT_NOT_READY` avec le scénario `TECHNICAL_CONTROL_NEUTRAL`), car
   l'exécution (phases 4–5), le fondamental (6) et l'IA (7) n'existent pas encore.
5. 249 tests verts ; signaux strictement identiques à `reference.technical.ema_setups`.
6. **Prochaine étape : phase 4** = artefact `execution-coordinateur`, couches 0 à 3 (types, cotation, prix,
   gardes de compte, réservations, risque all-in, arbitrage, dimensionnement). Plan proposé en §8.
7. L'utilisateur **arrête chaque phase** et ne lance la suivante que par une demande explicite
   (« Commence et achève intégralement la phase N »).
8. L'utilisateur a **délégué les décisions d'interprétation** avec le critère « le plus fort potentiel de
   rentabilité », borné par la spécification (jamais `config/`, jamais le texte normatif).
9. Chaque réponse finale se termine par le **pied d'audit XP-Bots** et un marqueur exact (§3).
10. La rentabilité n'est **pas** démontrée (aucune évaluation C10) : ne jamais la présenter comme acquise.

## 1. Comment utiliser ce rapport

- Lire dans l'ordre : ce rapport (§0 à §6), puis `AGENTS.md`, `.agents/PROJECT_RULES.md`, le plan maître
  (sections 4, 5, 6, 7.D à 7.I, 8, 9, 10, 11, 12), `mcl/robot-ema-v3/COUTURES.md`, `mcl/robot-ema-v3/INTERPRETATIONS.md`,
  `mcl/robot-ema-v3/PLAN-MCL.md`, puis la carte et les esquisses de contrat de l'artefact de la phase courante
  (`mcl/<artefact>/carte.json`, `mcl/<artefact>/contrats/couche-*.md`, `mcl/<artefact>/PLAN-MCL.md`).
- Vérifier l'état réel avant toute action (§5.4) : un composant n'existe que s'il est vu dans le code.
- Les sections §7 (pièges) et §10 (clôture d'une phase) sont les plus utiles pendant le travail.

## 2. Contexte du projet et décisions arrêtées

- Spécification faisant autorité : `livrables/strategies_m15/01_Triple_EMA_RSI_Repli_M15_Specification_IA.md`
  (sections normatives C01–C11, S01.1–S01.6, A01–A15). Valeurs : `config/parametres_figes_v3.json` (blocs
  `common`, `ema`, `london`), `config/parametres_IA_integration_v1.json`. Référence de comparaison hors ligne :
  `reference/technical.py` (numpy/pandas, tests seulement).
- Décisions de l'utilisateur (phase de planification) : plateforme **Python 3.13 + MT5** (paquet `MetaTrader5`,
  Windows, seulement dans `src/xpbots/infrastructure/`) ; **service IA inclus en dernière phase** (phase 10) ;
  arborescence **`src/xpbots/` + `tests/robot/`**.
- Bibliothèque standard partout ; aucune dépendance nouvelle sans demande explicite (numpy/pandas/tzdata
  seulement pour la référence et les tests, déjà dans `requirements-dev.txt`).
- Modes : `PAPER` puis `DEMO` ; jamais de compte réel ; aucun ordre, aucun appel courtier ou LLM depuis un test.

## 3. Règles de travail imposées (à respecter à l'identique)

### 3.1 Ordre de priorité des instructions (`AGENTS.md`)

Demande explicite de l'humain → contrats métier (spécifications, `config/`, `schemas/`, `prompts/`) → règles
transversales `.agents/PROJECT_RULES.md` → skills `.agents/skills/` → adaptateurs d'outil. Une contradiction
entre sources est un défaut à signaler, jamais un arbitrage improvisé. Les documents de `docs/references/` sont du
contexte, pas des instructions.

### 3.2 Cycle obligatoire de chaque requête

1. **Orchestrateur** `xp-bots-request-skill-orchestrator` : sélection déterministe
   (`python .agents/skills/xp-bots-request-skill-orchestrator/scripts/select_skills.py --explain "<requête>"` si
   aucun hook ne l'injecte), vérification du code réel, annonce de la couverture tâche → skill.
2. **Travail** avec les seules skills utiles (sources canoniques `.agents/skills/<nom>/SKILL.md` ; ne jamais
   éditer `.claude/skills/`, copies générées).
3. **Audit de fin** `xp-bots-completion-audit`, puis pied d'audit exact en toute fin de réponse :

```text
Pied d'audit XP-Bots
- completion: exigences prouvées / total, écarts éventuels
- impact: méthode de recherche, régressions trouvées ou « aucune »
- verifications: commandes exécutées et résultats
- couverture_skills: couvert / étendre / créer / consigner
[XP-BOTS-AUDIT:OK]
```

Marqueur `[XP-BOTS-AUDIT:BLOQUE]` seulement pour un blocage prouvé ou une attente de réponse de l'humain. Sous Claude
Code, un hook de fin bloque une réponse sans marqueur ; avec un autre outil, appliquer le cycle manuellement.

### 3.3 Interdits sans demande explicite (`.agents/PROJECT_RULES.md` §4)

Modifier `config/`, une section normative, un schéma ou un prompt métier ; réécrire une preuve de `docs/validation/`
ou l'archive ZIP MCL ; ajouter une dépendance ; appeler un LLM ou un courtier, passer un ordre ; afficher un secret
de `.env` ; supprimer un fichier sans l'avoir ouvert.

### 3.4 Préférences et consignes de l'utilisateur

- Langue : **français**. Réponses économes en mots sans perte de qualité ; questions de clarification seulement si
  indispensables. Dans la documentation, décrire et expliquer plutôt qu'écrire du code, sauf nécessité.
- **Une phase à la fois** : exécuter intégralement la phase demandée, puis **s'arrêter** et attendre une demande
  explicite pour la suivante. Ne jamais enchaîner de soi-même.
- **Délégation des décisions** (consigne donnée pour la phase 3 et appliquée depuis) : pour toute question ou
  décision d'interprétation, choisir soi-même la réponse la plus pertinente qui augmente le plus le potentiel de
  rentabilité, **dans les bornes de la spécification** (aucune valeur de `config/` ni section normative touchée ;
  une lecture peut préserver des occasions de trade conformes, jamais créer un avantage hors texte). Chaque
  décision est inscrite au registre `mcl/robot-ema-v3/INTERPRETATIONS.md` avec son effet, devient un test nommé,
  et est résumée à l'utilisateur.
- Git : travailler sur la branche désignée par la session (historique sur `claude/epic-edison-4lurlt`) ;
  `git push -u origin <branche>` avec reprise sur erreur réseau (2, 4, 8, 16 s) ; **aucune pull request** sans
  demande ; messages de commit en français, détaillés ; lignes d'attribution celles imposées par votre propre
  environnement ; **aucun identifiant de modèle** dans le code, les commits ou les documents.
- Après chaque push, vérifier la CI `robot-ci` (outils GitHub MCP `actions_list` / `actions_get` /
  `get_job_logs`) jusqu'au statut `completed` et `success` du **run** (pas seulement du job) avant d'annoncer « CI
  verte ».
- La réponse finale commence par le résultat, en langage simple ; elle signale les limites (rentabilité non
  démontrée) et se termine par le pied d'audit.

## 4. La méthode MCL telle qu'appliquée

- Outil : `M=.agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py` (référence d'usage :
  `.agents/skills/mcl-matryoshka-construction-layers/references/13-outil-mcl-py.md`). Mode **composite** : carte des
  artefacts `mcl/robot-ema-v3/carte.json` ; un dossier MCL par artefact (`mcl/<artefact>/`).
- Pour chaque couche, dans l'ordre donné par `python $M --dossier mcl/<a> statut` (« constructible maintenant ») :
  1. **Avant d'écrire le code**, mettre à jour `depend_de` de l'unité dans `mcl/<a>/carte.json` avec ses imports
     réels (y compris `amont-noyau`, `amont-donnees-temps`, unités internes), puis `python $M --dossier mcl/<a>
     analyser` → « Aucune divergence ».
  2. Écrire le module `src/xpbots/<paquet>/c<id>_<nom>.py` et ses tests `tests/robot/<paquet>/test_c<id>_cat1_<sujet>.py`
     (catégorie 1 : unité sur dépendances réelles déjà figées) et, si prévu, `test_c<id>_cat2_<sujet>.py`
     (catégorie 2 : bloc réel intégré, comparaison à la référence, bout en bout).
  3. **Finaliser le contrat** `mcl/<a>/contrats/couche-<id>.md` (statut « finalisé », consommateurs, dépendances,
     module, sources normatives, puis Unité / Responsabilité / Signature / Entrée / Sortie / Effets de bord /
     Erreurs, spécification exécutable, comportements documentés). Exemples complets :
     `mcl/moteur-ema/contrats/couche-2.md`, `mcl/moteur-ema/contrats/couche-3.md`.
  4. Gate : `python $M --dossier mcl/<a> gate --couche <id> --unitaire "python tools/run_robot_tests.py --artefact
     <paquet> --couche <id> --categorie 1" [--integration "python tools/run_robot_tests.py --artefact <paquet>
     --couche <id> --categorie 2"] --regression "python tools/run_robot_tests.py" --regression "python
     tools/verify_project.py"` → `== GATE VERT ==` ; puis **immédiatement** `python $M --dossier mcl/<a> figer
     --couche <id>` (rien ne doit changer dans l'arbre entre gate et figer). Couches parallèles (1a, 1b…) : gate
     et gel séparés, l'un après l'autre.
  5. **Checkpoint** quand `statut` l'annonce (tous les deux niveaux figés) : `python $M --dossier mcl/<a>
     checkpoint --par <vous> --notes "<revue : responsabilités, duplications, interfaces ; révisions ou aucune>"`.
- Fin d'artefact ou de phase : `python $M --dossier mcl/<a> gate --global --regression "python
  tools/run_robot_tests.py" --regression "python tools/verify_project.py"` (artefact et `mcl/robot-ema-v3`), `python
  $M --dossier <d> verifier --mode strict` sur les **neuf** dossiers `mcl/*/`, `python $M --dossier mcl/<a> rapport`
  pour le bilan (§12 du `PLAN-MCL.md` de l'artefact).
- **Défigeage** (changement du contrat d'une couche figée) : `python $M --dossier mcl/<a> defiger --couche <id>
  --nature extension|modification|correction --motif "<raison>" --par <vous>` ; fiche ADR
  `mcl/<a>/defigeages/AAAA-MM-JJ-couche-<id>-<sujet>.md` (gabarit
  `.agents/skills/mcl-matryoshka-construction-layers/assets/gabarits/defigeage-adr.md`, exemple
  `mcl/donnees-temps/defigeages/2026-11-05-couche-3-r6.md`) ; contrat et tests mis à jour ; gate puis re-gel.
- **Fichiers de contrat figés** = `mcl/<a>/contrats/couche-<id>.md` **et tous les fichiers correspondant au motif**
  `tests/robot/<paquet>/test_c<id>_*.py`. Ajouter ou modifier un tel fichier après le gel viole
  `contrats_figes` : placer les nouveaux tests d'intégration au niveau `tests/robot/app/` (non figé) ou défiger.
- Coutures du squelette : toute extension d'un type ou d'un port du noyau, et tout remplacement de segment, est
  tracé dans `mcl/robot-ema-v3/COUTURES.md` §5 (phase, changement, nature, raison) ; un port arrive avec son
  premier consommateur.

## 5. État livré (phases 0 à 3)

### 5.1 Journal des phases

| Phase | Commit | Résultat |
|---|---|---|
| 0 — Cadrage | `70462c1` | Neuf cartes MCL sans divergence, esquisses de contrat, coutures, registre R1–R17 |
| 1 — Squelette | `91e9bc6`, `baeb2a7` | Noyau, segments minimaux, rejeu CLI, lanceur, CI `robot-ci` |
| 2 — Données et temps | `acedb96` | `donnees-temps` figé (couches 0, 1a, 1b, 1c, 2, 3) et branché |
| 3 — Moteur EMA | `1dfc515`, `d8c3f2a` | Décisions R1–R18 ; défigeage R6′ ; `moteur-ema` figé (0, 1a, 1b, 1c, 1d, 2, 3) et branché ; preuves de bout en bout |

Statut MCL : `donnees-temps` et `moteur-ema` entièrement figés ; `execution-coordinateur` (11 couches),
`controles-fondamentaux`, `contexte-ia`, `journal-rejeu`, `infrastructure`, `service-ia` **à construire** ;
composite `robot-ema-v3` à compléter au fil des phases.

### 5.2 Code existant (API utiles aux phases suivantes)

**Noyau `src/xpbots/noyau/`** (coutures ; modifier seulement par extension tracée) :
- `temps` : `Instant(ms, sequence=0)` ordonné ; `MS_PAR_SECONDE` ; `iso_depuis_ms`, `ms_depuis_iso`
  (`AAAA-MM-JJTHH:MM:SS.mmmZ`).
- `marche` : `Tick(symbole, symbole_courtier, instant, bid, ask)` (Decimal > 0 ; le croisement relève de C06) ;
  `Bougie(symbole, periode_s, ouverture_ms, o, h, l, c, nb_ticks, valide)` et `cloture_ms` ; `StatutBougie` (`OK`,
  `WARMUP`, `DATA_GAP`) ; `BougieEnrichie(bougie, statut, indicateurs, a_t, jour_londres)` ;
  `NatureEvenementDonnees` (`TROU`, `RECUPERATION`, `RECALCUL`, `REINITIALISATION`, `PRECHARGEMENT`) ;
  `EvenementDonnees(symbole, nature, instant_ms, debut_ms, fin_ms, details)`.
- `decisions` : `MotifRefus` (liste C09 + `AI_CONTEXT_VETO` + `ENVIRONMENT_NOT_READY`, liste fermée) ;
  `Sens` (`ACHAT`=1, `VENTE`=−1) ; `Signal(strategie, symbole, cloture_ms, sens, cloture_bid: Decimal, a_t: float,
  b_sl: float, multiple_objectif: float, etat_detecteur)` ; `ResultatTechnique(signal, motif, etat_detecteur)` ;
  `CleIntention(deployment_id, strategie, symbole, cloture_ms, sens)` avec `du_signal`, `en_json`, `texte` ;
  `Rempli(volume, prix_moyen, instant_ms)`, `Refuse(motif, instant_ms)`, `IssueSignal` ;
  `DecisionFondamentale`, `EtatContexteIA` (`BLOCK`, `NEUTRAL` ; aucun `ALLOW`), `DecisionContexteIA`.
- `journal_schema` : enregistrements `INITIALISATION`, `CLOTURE_BOUGIE`, `INTENTION`, `DONNEES` ;
  `ConstructeurEnregistrements(deployment_id, mode, bundle)` dont `intention(...)` accepte déjà les champs
  optionnels `calendrier`, `bras_ab`, `cout_api_alloue_usd`, `courtier`, `cotation`, `frais`, `risque`, `volume` ;
  `valider_enregistrement` ; `en_json` (Decimal en texte exact, énumérations par valeur, dates ISO).
- `json_canonique` : `charger_strict` (doublons, NaN, infinis refusés), `serialiser`, `empreinte`.
- `config` : `charger_bundle_technique()` → `BundleTechnique(donnees, empreinte)` et `valeur(bloc, cle)` ;
  `ConfigurationInvalide` ; `figer`.
- `ports` (Protocols) : `SourceTicksHistoriques` (dont `seances`, `tick_size`), `Stockage` (`lire`/`ecrire` en
  octets), `Journal`, `Strategie` (`strategie_id`, `sur_cloture`, `appliquer_issue`, `notifier_sortie`,
  `sur_evenement_donnees`), `ControleFondamental`, `ContexteIA`. À ajouter avec leur premier consommateur :
  `CalculCourtier` (phase 4), `Courtier`, `FluxTicks`, `Horloge` (phase 5), `SourcePermissions`,
  `SourceCalendrier` (6), `LecteurSnapshotIA` (7), `TransportHTTP` (10).

**`donnees-temps` `src/xpbots/donnees_temps/`** (figé) : `charger_parametres_techniques(bundle)` →
`ParametresTechniques` (bloc `common` validé, 73 clés ; `valeur(cle)`, `periode_m15_s`, `prechauffage_m15`, …) ;
`GENRES`, `FonctionNonImplementee`, `analyser_heure`, `CalendrierSeances` ; `SessionsLondres` (`jour_londres`,
`jour_utc`, `dans_fenetre(ouverture, cloture, debut, fin_exclue)`, `instant_local`, `dans_blackout`) ;
`ConstructeurBougies` ; indicateurs et clés `cle_ema`, `cle_ema_decalee`, `cle_rsi`, `cle_atr`, `CLE_TR` ;
`SpecIndicateurs`, `EtatIndicateursSymbole` ; `PipelineMarche` (ticks + couverture + horloge → bougies enrichies
et événements ; trous, récupération ou recalcul R6′, préchargement, reprise).

**`moteur-ema` `src/xpbots/moteur_ema/`** (figé) : `charger_parametres_ema(bundle)` → `ParametresEMA` ;
`sens_tendance` ; `contexte_armement`, `repli_valide`, `contact` ; `est_reprise` ; `stop_technique` →
`StopTechnique(b_sl, tampon, distance, trop_large)` ; `MachineEtatsEMA` (états `IDLE`, `ARMED_*`, `PULLBACK_*`,
`COOLDOWN`, `OWNED_POSITION`, `ATTENTE_ISSUE`) ; `MoteurEMA(parametres, sessions, ticks, stockage)` (port
`Strategie` ; motifs `OUTSIDE_SESSION`, `WARMUP`, `DATA_GAP`, `NO_SETUP`, `STOP_TOO_WIDE`, `DAILY_ENTRY_CAP`,
`SYMBOL_BUSY`, `UNKNOWN_ORDER_STATE` ; état persisté sous `moteur_ema/<strategie>/<symbole>`).

**`app` `src/xpbots/app/`** : `rejeu.py` (`executer_rejeu(ticks, manifeste, journal, deployment_id,
scenario_fondamental, fabrique_strategies=strategies_par_defaut, racine)`, `MarcheRejoue`, CLI `main`) ;
`segments_minimaux.py` : `LecteurFixtureCSV` (manifeste `xp-fixture-manifeste-v3` : couverture, séances,
`tick_size`), `EcrivainJournalJSONL`, `StockageMemoire`, `FondamentalAbsent` (+ scénario
`TECHNICAL_CONTROL_NEUTRAL`, interdit en `DEMO`), `ContexteIANeutre`, `ExecutionPapierMinimale`,
`CoordinateurRefus`. Segments encore à remplacer : voir `COUTURES.md` §4.

**Tests `tests/robot/`** : lanceur `python tools/run_robot_tests.py [--artefact <paquet>] [--couche <id>]
[--categorie 1|2] [-v]` (code 5 si aucun test) ; `outils.py` (`RACINE`, `SRC`, `FIXTURES`, `signal_valide`) ;
`fixtures/series.py` (`ticks_bougies`, `bougies_directes`, `bougies_tendances(symbole, debut, nb, graine,
pointes=0.0)`, `ticks_depuis_bougies`) ; `fixtures/generateur_ticks.py` (`ProfilSynthetique`, `manifeste_v3`,
`ecrire_ticks`, régénération des fixtures versionnées vérifiée octet pour octet) ; `doublures/stockage_memoire.py` ;
`moteur_ema/reference_ema.py` (pont vers la référence pandas) ; `test_squelette_regles.py` (règles transverses).

### 5.3 Preuves au moment du passage

249 tests verts ; 7 + 6 gates de couche verts, gates globaux verts (moteur-ema, donnees-temps, robot-ema-v3) ;
`verifier --mode strict` vert sur les neuf cartes ; `tools/verify_project.py` PASS (30 contrôles projet, 288 de
référence) ; suite de gouvernance 8/8 ; CI runs 42093397291 et 42094101881 `completed`/`success` ; rejeu CLI d'une
série de 2 600 bougies : 19 signaux refusés, 6 `STOP_TOO_WIDE`, cooldown visible.

### 5.4 Vérification d'état à faire en arrivant

`git status --short` (vide attendu), `git log --oneline -3`, `python tools/run_robot_tests.py`, `python
tools/verify_project.py`, `python $M --dossier mcl/execution-coordinateur statut`. Si `numpy`/`pandas` manquent :
`python -m pip install -r requirements-dev.txt`.

## 6. Registre d'interprétation (état)

`mcl/robot-ema-v3/INTERPRETATIONS.md` fait foi. R1, R2, R3, R4, R5, R6′, R7–R18 **décidés** (R4, R5, R6′, R1, R2, R18
déjà appliqués et testés). Points à appliquer dans les phases à venir : R3 (Bid ≤ Ask admis), R7
(`PROTECTION_ERROR` sur contrainte native SL/TP), R8 (`ENVIRONMENT_NOT_READY` si positions externes non
coordonnables), R17 (coordinateur générique testé avec des signaux `LONDON_V3` synthétiques) en phases 4–5 ; R10,
R12 (exportateur MQL5 du calendrier natif MT5 ; calendrier du module fondamental en alternative), R13 en phase 6 ;
R9, R11, R16 en phase 8 ; R14, R15 en phase 9.

## 7. Pièges et conventions appris (à lire avant de coder)

1. **Anti-recopie** (`tests/robot/test_squelette_regles.py`) : tout littéral numérique ou texte de `src/` égal à
   une valeur de `config/` (les deux fichiers) échoue, y compris de petits entiers (2, 3, 4, 5, 6, 8, 14…), des
   fractions (0.25, 0.65…) et des textes (`'EMA_V3'`, `'USD'`, `'WILDER'`…). Seuls 0, 1, −1 sont libres. Lire les
   valeurs dans `config/` ; dépaqueter plutôt que tester `len(x) == 3` ; une exception justifiée s'ajoute aux
   listes `NOMBRES_AUTORISES_PAR_FICHIER` / `TEXTES_AUTORISES_PAR_FICHIER` (ex. noms de variantes implémentées).
2. **Horloge et frontières** : aucun `time.time`, `datetime.now`, etc. hors `infrastructure/horloge/` ;
   `MetaTrader5`, `sqlite3`, `urllib`/`http`/`ssl`/`socket` seulement en infrastructure (tests de règles + carte).
3. **Nombres** : indicateurs en `float` ; prix, volumes, argent en `Decimal` ; conversion d'un flottant par
   `Decimal(repr(x))` ; arrondi au tick avec la tolérance de `rounded_levels` (1e-8 tick) ; inégalités exactement
   celles du texte.
4. **Variantes de configuration** : une valeur non implémentée doit faire refuser le démarrage
   (`FonctionNonImplementee`), jamais être ignorée.
5. **Énumérations** `StrEnum` : comparer par `==` aux textes (pas `is`) ; le journal sérialise par valeur.
6. **Tests** : toujours via `tools/run_robot_tests.py` (il ajoute `src` et `tests` au chemin ; les tests importent
   `robot.*`) ; `python -m unittest` direct échoue sans chemin. Les comparaisons à la référence sont protégées par
   `skipUnless(REFERENCE_DISPONIBLE)`.
7. **Équivalence avec la référence** : nourrir le composant des mêmes flottants (cadre `reference.technical
   .add_indicators`) pour une égalité exacte ; à travers le vrai pipeline, comparer instants/sens/âge exactement et
   les flottants à 1e-12 relatif.
8. **Fixtures** : synthétiques, déterministes, < 1 Mio, LF, aucun prix réel ; les longues séries se génèrent en
   dossier temporaire (`tempfile`) ; `runtime/` est ignoré par Git (journaux de démonstration).
9. **Ordre gate → figer** sans aucune modification entre les deux ; mettre à jour la carte avant le gate.
10. **Persistance** : tout état à survivre au redémarrage passe par `Stockage` (JSON canonique, clé préfixée par
    l'artefact) ; idempotence par `CleIntention`.
11. **Hooks Claude Code** : sous un autre outil, les hooks ne s'exécutent pas ; rejouer les portes à la main :
    `python .agents/hooks/agent_lifecycle.py --run-gates`.

## 8. Phase 4 — plan proposé (non encore exécuté)

Plan maître §7.D et §9 : « Exécution, partie 1 (D 0–3) : types, cotation, prix, gardes de compte, risque,
réservations, dimensionnement, arbitrage. Critère : chiffres S01.5 reproduits ; C11.2/5/6/7/10/13 (cat. 1)
verts. » Skills : `xp-bots-risk-execution-contracts`, `xp-bots-broker-account-qualification`, MCL. Paquet
`src/xpbots/execution/`, carte `mcl/execution-coordinateur/carte.json` (couches 0, 1a, 1b, 1c, 1d, 2a, 2b, 3 en
phase 4 ; 4, 5, 6 en phase 5). Aucun segment du squelette n'est remplacé en phase 4.

### 8.1 Couture (extension additive, tracée dans `COUTURES.md`)

Port `CalculCourtier` dans `noyau/ports.py` : `profit(symbole, sens, volume, prix_ouverture, prix_cloture) ->
Decimal` (USD, équivalent `OrderCalcProfit`) et `marge(symbole, sens, volume, prix) -> Decimal` (équivalent
`OrderCalcMargin`) ; exception `CalculIndisponible` traduite en `ENVIRONMENT_NOT_READY`. Doublure
`tests/robot/doublures/calcul_courtier.py` : formules déterministes contrat USD (profit = sens × (clôture −
ouverture) × taille × volume ; marge = volume × taille × prix / levier) et mode « indisponible ».

### 8.2 Couches

| Couche | Module | Contenu | Cas clés (cat. 1) |
|---|---|---|---|
| 0 | `c0_types.py` | `ParametresExecution` bâti sur `ParametresTechniques` (TTL, âge de cotation, plafonds de spread par symbole, écart d'entrée, g, fractions de risque, positions max, marge max, priorités, gardes ; `allow_*` à faux et `risk_day_timezone` UTC sinon `FonctionNonImplementee`) ; `decimal_de` ; `ProfilInstrument` (tous les champs C04 : symbole courtier, taille de contrat, tick, digits, valeur du tick, volumes min/max/pas/limite agrégée, distance minimale et gel, commission et minimum par ordre, barème, frais confirmés, mode de compte, levier, protections attachables ; clé absente ou invalide → `ProfilIncomplet`) ; `PositionCompte`, `EtatCompte`, `Reservation` | profil incomplet → `ENVIRONMENT_NOT_READY` |
| 1a | `c1a_cotation.py` | `controler_cotation(signal, tick, maintenant, p, plafond)` → `Conforme` / `Attendre(motif)` / `Expire(motif)` : TTL `[T, T+5 s)`, tick ≥ T, âge ≤ 2 s, Bid ≤ Ask (R3), spread ≤ plafond inclus, \|Bid − C\| ≤ 0,25 A inclus | spread au plafond admis ; TTL 5 s expiré (C11.2) ; première cotation après clôture seule utilisable (C11.3) |
| 1b | `c1b_prix.py` | `niveaux_executables` : E = Ask/Bid ; SL achat = plancher de B_SL au tick ; SL vente = plafond de B_SL + S ; D > 0 ; TP = E + sens·k·D (plafond achat, plancher vente) ; distance minimale native (convention MT5 : achat contre Bid, vente contre Ask) → `PROTECTION_ERROR` (R7) ; `tp_apres_fill` | S01.5 : E 1,10010, SL 1,09945, D 0,00065, TP 1,10108 ; vente SL 1,10065, TP 1,09902 ; spread compté une fois (C11.5) ; concordance `rounded_levels` |
| 1c | `c1c_gardes_compte.py` | `GardesCompte(p, stockage)` : base au premier relevé du jour UTC ; ≤ 98 % → `DAILY_LOSS_LOCK` jusqu'au jour UTC suivant (demande de clôture) ; pic depuis activation ; ≤ 90 % → `GLOBAL_DRAWDOWN_HALT` persistant, levé seulement par une décision de déploiement tracée ; neutralisation des flux externes ; persistance | seuils inclus, pertes flottantes et frais compris, redémarrage sans remise à zéro (C11.13) |
| 1d | `c1d_reservations.py` | `RegistreReservations(stockage)` : `reserver` idempotent par clé C08, `attacher_position`, `liberer`, totaux, occupation par symbole ; document unique écrit atomiquement | message répété sans doublon ; reprise après redémarrage |
| 2a | `c2a_risque.py` | `reserve_glissement` g = max(tick, 0,05 A) ; `risque_all_in` = perte via `CalculCourtier` entre E+sens·g et SL−sens·g + frais aller-retour ; `frais_aller_retour` (barème par paliers, minimum par ordre, par jambe) ; `risque_apres_remplissage` (seule réserve de sortie) | g = 0,000025, distance 0,00070, 0,70 USD à 0,01 lot standard (S01.5) ; frais non linéaires (C11.7) |
| 2b | `c2b_arbitrage.py` | `ordonner` (même instant : `simultaneous_strategy_priority` puis `universe_priority` ; ni fusion ni couverture) ; `symbole_libre` (positions et réservations de tout propriétaire) | signaux `LONDON_V3` synthétiques simultanés (C11.10, R17) |
| 3 | `c3_dimensionnement.py` | `dimensionner(...)` → `Dimensionnement` ou `RefusDimensionnement(motif)` : gardes, positions externes (R8), occupation, B = 0,5 % Eqt gelé, plus grand volume de la grille (min, pas, max, limite agrégée) respectant les cinq contraintes C07, arrondi vers le bas (balayage descendant borné par la perte prix, monotone en volume ; les frais à paliers peuvent ne pas l'être) ; motifs `MIN_VOLUME_OR_RISK_REJECT`, `ACCOUNT_RISK_CAP`, `MARGIN_REJECT`, `SYMBOL_BUSY`, `ENVIRONMENT_NOT_READY` dans un ordre d'évaluation documenté | 0,70 USD > 0,50 refusé (C11.6) ; micro 1 000 unités, min 0,1 lot → 0,07 USD admis ; marge cumulée ≤ Eqt/3 ; positions externes ; deux robots simultanés |

Catégorie 2 en couche 3 : bloc réel {0 → 3} (chaîne S01.5 complète : signal → cotation → niveaux → g → risque →
volume ; concordance de 1b avec `rounded_levels` sur des cas aléatoires ; LONDON puis EMA sur le registre réel).
Checkpoints après les profondeurs 1 et 3.

### 8.3 Points d'interprétation proposés pour la phase 4 (à décider sous la même délégation et à inscrire au registre)

- R19 : motif d'un signal non exécuté à l'échéance du TTL = dernière garde violée par une cotation utilisable
  (`SPREAD_CAP`, `ENTRY_GAP`), sinon `SIGNAL_EXPIRED`.
- R20 : base quotidienne = premiers fonds propres relevés du jour UTC (00:00 UTC ou activation en cours de jour).
- R21 : plus de deux positions ou réservations sur le compte → `ACCOUNT_RISK_CAP` ; symbole occupé → `SYMBOL_BUSY`.
- R22 : tolérance d'erreur flottante avant arrondi = 1e-8 tick (celle de `rounded_levels`).
- R23 : frais = commission par lot et par jambe selon un barème par paliers, avec minimum par ordre, à l'entrée et à
  la sortie ; commission nulle admise seulement si confirmée ; swaps hors risque (positions closes avant le
  blackout de 21:00 UTC).

## 9. Phases 5 à 11 — feuille de route (détail : plan maître §7 et §9)

| Phase | Contenu | Remplace dans le squelette | Points d'attention |
|---|---|---|---|
| 5 | `execution` couches 4 (cycle d'ordre), 5 (sorties obligatoires), 6 (coordinateur) ; ports `Courtier`, `FluxTicks`, `Horloge` ; courtier scripté ; intégration A+B+D | `ExecutionPapierMinimale`, `CoordinateurRefus` (rejeu avec `TECHNICAL_CONTROL_NEUTRAL` : cycle signal → ordre → fill → TP/SL/16:00/7 200 s) | C11.10–13 ; accusé ambigu (R2 côté moteur : `ATTENTE_ISSUE`) ; `notifier_sortie` du moteur ; septième entrée refusée ; second contrôle fondamental et IA juste avant envoi |
| 6 | `fondamental` couches 0 → {1a, 1b} → 2 → 3 ; ports `SourcePermissions`, `SourceCalendrier` | `FondamentalAbsent` | R12, R13 ; C11.8/9 ; FLATTEN prioritaire |
| 7 | `contexte_ia` couches 0 → 3 ; insertion A07 ; port `LecteurSnapshotIA` | `ContexteIANeutre` | A14 côté robot ; le veto n'ajoute qu'un refus |
| 8 | `journal_rejeu` couches 0 → 4 ; import des ticks et manifeste | `LecteurFixtureCSV` (partiellement) | R9, R11, R16 ; C11.12/14 ; rapport sous `.local/reports/` |
| 9 | `infrastructure` (MT5, SQLite, fichiers, horloge, IPC, sources fondamentales), qualification C04, `app.paper`/`app.demo` | `EcrivainJournalJSONL`, `StockageMemoire`, lecteurs | lacune de skill « adaptateur MetaTrader5 » à évaluer (`xp-bots-skill-gap-detector`) ; R14, R15 ; procédure démo remise à l'utilisateur (poste Windows) |
| 10 | `service_ia` (logique puis adaptateurs HTTP/RSS/SQLite), `app.service_ia` | — | aucun appel d'API en test ; procédure de conformité manuelle avec les clés de l'utilisateur |
| 11 | Procédures C10 et PAPER_AB, checklists go/no-go | — | aucune conclusion économique sans données réelles et V1 (R11) |

## 10. Clôture d'une phase (liste à dérouler à chaque fois)

1. Toutes les couches prévues figées ; checkpoints faits ; carte sans divergence.
2. Branchement sur le squelette si la phase en prévoit un (segment retiré, `SEGMENTS_MINIMAUX` mis à jour, tests du
   squelette adaptés, nouveau test de bout en bout dans `tests/robot/app/`).
3. Documentation : `mcl/robot-ema-v3/COUTURES.md` (§1 à §5), `INTERPRETATIONS.md`, `mcl/<a>/PLAN-MCL.md` (statuts
   « figée (phase N) », dépendances, bilan via `rapport`), `mcl/robot-ema-v3/PLAN-MCL.md` (ligne du journal des
   phases), plan maître (ligne « Avancement », registre §10 si nouveaux points), `README.md` (section robot 1).
4. Vérifications : suite complète, gates globaux (artefact et composite), `verifier --mode strict` ×9,
   `tools/verify_project.py`, suite de gouvernance, `agent_lifecycle.py --run-gates`, rejeu CLI démontrant le
   comportement nouveau (série longue écrite sous `runtime/` si besoin).
5. Commit détaillé, push, CI `robot-ci` jusqu'à `completed`/`success`.
6. Réponse finale en français : résultat d'abord, décisions prises (avec leur effet), preuves, limites, arrêt en
   attente de la phase suivante, pied d'audit et marqueur.

## 11. Limites et risques connus

- Rentabilité non démontrée ; verdict par défaut « non validé » jusqu'à C10 (données réelles à fournir par
  l'utilisateur : ticks Bid/Ask des symboles exacts, conditions de contrat, calendrier avec `known_at`, permissions
  historiques, spécification V1).
- À 100 USD et 0,5 % de risque, le contrat standard est infinançable (S01.5) : contrats micro vérifiés nécessaires.
- MT5 Python : Windows seulement, scrutation, aucun calendrier natif côté Python ; aucun test MT5 réel possible sous
  Linux.
- Les refus `STOP_TOO_WIDE` n'apparaissent que sur des séries à mèches extrêmes (`pointes`) ; les séries
  synthétiques ne disent rien du marché réel.

## Annexe A — Prompt de reprise (à coller dans la nouvelle session, avec ce rapport en pièce jointe)

```text
Tu reprends l'implémentation du plan maître du robot 1 « Triple EMA RSI Repli M15 » (identifiant EMA_V3) du dépôt
XP-Bots, décrit dans docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md. Les phases 0 à 3 sont terminées ; tu
continues à partir de la phase 4 exactement comme l'agent précédent l'aurait fait. Le rapport de passation joint
(aussi versionné sous docs/handoff/HANDOFF_ROBOT1_EMA_V3_APRES_PHASE3.md) décrit l'état, la méthode, les règles et
le plan proposé de la phase 4 : lis-le en entier avant toute action, puis les fichiers qu'il désigne (AGENTS.md,
.agents/PROJECT_RULES.md, plan maître, mcl/robot-ema-v3/COUTURES.md, INTERPRETATIONS.md, PLAN-MCL.md, carte et
esquisses de contrat de l'artefact execution-coordinateur).

Règles impératives, identiques à celles de la session précédente :
1. Applique le cycle obligatoire d'AGENTS.md à chaque requête : orchestrateur de skills d'abord
   (xp-bots-request-skill-orchestrator), skills utiles ensuite (pour la phase 4 : xp-bots-risk-execution-contracts,
   xp-bots-broker-account-qualification, mcl-matryoshka-construction-layers, xp-bots-mcl-robot-planning,
   xp-bots-validation-replay), audit de fin (xp-bots-completion-audit) et pied d'audit exact avec le marqueur
   [XP-BOTS-AUDIT:OK] ou [XP-BOTS-AUDIT:BLOQUE] en toute fin de réponse.
2. Construis chaque artefact au protocole MCL complet décrit au §4 du rapport : carte mise à jour avant le code,
   tests de catégorie 1 et 2, contrat de couche finalisé, gate vert puis gel immédiat, checkpoints, défigeage tracé
   avec fiche ADR si un contrat figé doit changer, gates globaux et vérification stricte des neuf cartes en fin de
   phase.
3. Ne modifie jamais config/, les sections normatives des spécifications, les schémas, les prompts, les preuves de
   docs/validation/ ni l'archive MCL ; aucune dépendance nouvelle ; aucun appel de LLM ou de courtier, aucun ordre ;
   aucune valeur normative recopiée dans src/ (test anti-recopie) ; aucun identifiant de modèle dans le code, les
   commits ou les documents.
4. Décisions d'interprétation : je te délègue le choix ; retiens chaque fois la réponse la plus pertinente qui
   augmente le plus le potentiel de rentabilité du robot, dans les bornes de la spécification, inscris-la au
   registre mcl/robot-ema-v3/INTERPRETATIONS.md, transforme-la en test nommé et résume-la-moi.
5. Exécute intégralement une seule phase à la fois, puis arrête-toi et attends que je te demande explicitement de
   passer à la suivante.
6. Git : travaille sur la branche désignée par ta session (l'historique est sur claude/epic-edison-4lurlt, à partir
   de laquelle tu continues) ; commits en français détaillés ; push avec reprise sur erreur réseau ; aucune pull
   request sans demande ; vérifie la CI robot-ci jusqu'à ce que le run soit terminé en succès avant de l'annoncer.
7. Réponds en français, de façon concise sans perte de qualité ; commence par le résultat ; signale les limites
   (la rentabilité n'est pas démontrée tant que C10 n'est pas exécuté). Ne pose de question que si c'est
   indispensable. Dans la documentation, décris et explique plutôt que d'écrire du code, sauf nécessité.

Commence par vérifier l'état réel du dépôt (§5.4 du rapport), puis : commence et achève intégralement la phase 4.
```

# Coutures du squelette composite — robot 1 `EMA_V3`

Statut : **finalisé en phase 1** (2026-11-05), changements tracés en section 5 (phases 2 et 3). Code : `src/xpbots/noyau/` (coutures) et
`src/xpbots/app/segments_minimaux.py` (segments minimaux). Toute modification d'une couture est un changement de
contrat tracé (règle de couture 4) ; une extension additive (nouveau type, nouveau port, nouvelle clé optionnelle
documentée) accompagne le premier artefact qui en a besoin. Plan maître :
`docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md`, sections 5 et 6.

## 1. Chemin minimal de bout en bout

ticks de fixture → `donnees-temps` (bougies M15 enrichies, trous, préchargement ; depuis la phase 2) →
`moteur-ema` (méthode S01 ; depuis la phase 3) → coordinateur (refus explicite) → exécution papier → journal C09.

- Point d'entrée : `python -m xpbots.app.rejeu --ticks <csv> --manifeste <json> --journal <jsonl>` (avec `src`
  dans `PYTHONPATH`) ; option `--scenario-fondamental TECHNICAL_CONTROL_NEUTRAL` (C05, explicitement nommée).
- Fixture versionnée : `tests/robot/fixtures/squelette_ticks.csv` et `squelette_manifeste.json`, synthétiques,
  régénérables à l'octet près par `tests/robot/fixtures/generateur_ticks.py`.
- Gate du squelette = sa CI (`.github/workflows/robot-ci.yml`) : `python tools/run_robot_tests.py`,
  `python tools/verify_project.py`, `mcl.py --dossier mcl/<dossier> verifier --mode strict` pour les neuf dossiers ;
  gate global tracé dans `mcl/robot-ema-v3/journal.jsonl`.

## 2. Types de couture (`src/xpbots/noyau/`)

| Module | Type | Contenu | Invariants vérifiés |
|---|---|---|---|
| `temps` | `Instant` | ms UTC depuis l'époque + séquence | entiers stricts, séquence ≥ 0, ordre total (ms, séquence) ; ISO `AAAA-MM-JJTHH:MM:SS.mmmZ` exact, arithmétique entière |
| `marche` | `Tick` | symbole canonique, symbole courtier, `Instant`, Bid, Ask | prix `Decimal` finis > 0 ; le croisement Bid/Ask relève de C06 (R3) |
| `marche` | `Bougie` | symbole, période, ouverture, O, H, L, C Bid, nombre de ticks, validité | ouverture alignée sur l'époque UTC, L ≤ O, C ≤ H, au moins un tick |
| `marche` | `BougieEnrichie` | bougie, `StatutBougie` (OK, WARMUP, DATA_GAP), indicateurs, `A_t`, jour Londres | bougie invalide ⇒ DATA_GAP ; indicateurs flottants finis, figés ; `A_t` > 0 |
| `marche` | `EvenementDonnees` (phase 2) | symbole, nature (`TROU`, `RECUPERATION`, `RECALCUL` — phase 3, R6′ —, `REINITIALISATION`, `PRECHARGEMENT`), instant, bornes, détails | instants entiers, détails figés |
| `decisions` | `MotifRefus` | liste C09 + `AI_CONTEXT_VETO` + `ENVIRONMENT_NOT_READY` | identique, dans l'ordre, à la ligne « Motifs minimaux » du texte normatif |
| `decisions` | `Sens`, `Signal` | stratégie, symbole, clôture, sens, clôture Bid, `A_t`, `B_SL`, k, état du détecteur | `A_t` > 0, k > 0, 0 < sens × (C − B_SL) (C06) |
| `decisions` | `ResultatTechnique` | signal ou motif, état du détecteur | exactement l'un des deux |
| `decisions` | `CleIntention` | `(deployment_id, strategy_id, symbole, cloture_M15_UTC, sens)` | forme canonique stable (C08) |
| `decisions` | `Rempli`, `Refuse` | issue d'un signal | volume et prix > 0 ; motif de la liste fermée |
| `decisions` | `DecisionFondamentale` | autorisation ou refus, permission connue, scénario | refus seulement `FUNDAMENTAL_INVALID`, `FUNDAMENTAL_DIRECTION`, `NEWS_WINDOW` |
| `decisions` | `DecisionContexteIA` | `BLOCK` ou `NEUTRAL`, séquence du snapshot, événements | aucun état `ALLOW` n'existe (A12) |
| `journal_schema` | enregistrements C09 | `INITIALISATION`, `CLOTURE_BOUGIE`, `INTENTION`, `DONNEES` (phase 2) | clés exactes par type, numérotation sans trou, version et empreinte des règles dans chaque ligne, décimaux en texte exact, refus sans ordre |
| `json_canonique` | JSON | lecture stricte, écriture canonique, SHA-256 | doublons, NaN, Infinity et débordements refusés ; empreinte = `reference.llm_contracts.digest` |
| `config` | `BundleTechnique` | `config/parametres_figes_v3.json` figé | trois blocs, lecture seule, clé absente = erreur ; empreinte `dab01fb4…7c05` égale à celle publiée par la spécification |

## 3. Ports (`src/xpbots/noyau/ports.py`)

| Port | Méthodes | Disponible depuis | Implémenté par |
|---|---|---|---|
| `SourceTicksHistoriques` | `symboles()`, `ticks()`, `couverture(s)`, `seances(s)` (phase 2), `tick_size(s)` (phase 3), `fin_donnees_ms()`, `empreintes()` | phase 1 | lecteur de fixture (squelette), puis `journal-rejeu` 1c / `infrastructure` 0a |
| `Stockage` | `lire(cle)`, `ecrire(cle, valeur)` | phase 2 | doublure mémoire (tests), segment `StockageMemoire` (rejeu, phase 3), puis `infrastructure` 0b (SQLite) |
| `Journal` | `ajouter(enregistrement)` | phase 1 | écrivain JSONL (squelette), puis `infrastructure` 0a |
| `Strategie` | `strategie_id`, `sur_cloture(bougie)`, `appliquer_issue(cle, issue)`, `notifier_sortie(symbole, instant_ms)` et `sur_evenement_donnees(evenement)` (phase 3) | phase 1 | stratégie neutre (phases 1–2), `moteur-ema` 3 depuis la phase 3 |
| `ControleFondamental` | `autoriser(symbole, sens, instant_ms)` | phase 1 | fondamental absent, puis `controles-fondamentaux` 3 (ajout prévu : demandes de sortie, phase 6) |
| `ContexteIA` | `decision(symbole, instant_ms)` | phase 1 | contexte neutre, puis `contexte-ia` 3 |
| `FluxTicks`, `Horloge`, `Courtier`, `CalculCourtier` | — | phases 4 et 5 (premier consommateur) | doublures puis `infrastructure` |
| `SourcePermissions`, `SourceCalendrier`, `LecteurSnapshotIA` | — | phases 6 et 7 | doublures puis `infrastructure` 0a |
| `TransportHTTP` | — | phase 10 | doublure puis `infrastructure` 0d |

## 4. Segments minimaux et artefacts remplaçants

| Segment (`app/segments_minimaux.py`) | Comportement conforme à la spécification | Remplacé par | Phase |
|---|---|---|---|
| `LecteurFixtureCSV` | format du cahier de données §2 ; ordre (ms, séquence) strictement croissant ; manifeste `xp-fixture-manifeste-v3` (couverture, séances natives et `tick_size` déclarés, aucun seuil inventé, R5) | `journal-rejeu` 1c + `infrastructure` 0a | 8, 9 |
| `EcrivainJournalJSONL` | JSONL canonique LF, ajout seul, valide chaque ligne, refuse d'écraser un journal | `infrastructure` 0a | 9 |
| ~~`AgregateurM15Minimal`~~ | **remplacé en phase 2** par `PipelineMarche` (`donnees-temps` 3), câblé dans `app/rejeu.py` (`MarcheRejoue`) | `donnees-temps` 3 | 2 (fait) |
| ~~`StrategieNeutre`~~ | **remplacée en phase 3** par `MoteurEMA` (`moteur-ema` 3), câblé dans `app/rejeu.py` (`strategies_par_defaut`) | `moteur-ema` 3 | 3 (fait) |
| `StockageMemoire` | port `Stockage` en mémoire pour le rejeu (état du moteur, clé `moteur_ema/<stratégie>/<symbole>`) | `infrastructure` 0b | 9 |
| `FondamentalAbsent` | `FUNDAMENTAL_INVALID` ; scénario `TECHNICAL_CONTROL_NEUTRAL` seulement s'il est nommé, journalisé, interdit en `DEMO` | `controles-fondamentaux` 3 | 6 |
| `ContexteIANeutre` | `NEUTRAL` (A12) ; n'autorise jamais rien | `contexte-ia` 3 | 7 |
| `ExecutionPapierMinimale` | aucun ordre ; un refus devient une issue `Refuse` | `execution-coordinateur` 4 + `journal-rejeu` 1b, `infrastructure` 1a | 5, 8, 9 |
| `CoordinateurRefus` | clôture journalisée pour chaque méthode ; événement de données journalisé (`DONNEES`, phase 2) puis transmis aux méthodes (phase 3) ; signal : fondamental, puis contexte IA, puis environnement d'exécution absent (`ENVIRONMENT_NOT_READY`) ; premier refus retenu ; issue rendue à la méthode (cooldown du moteur) | `execution-coordinateur` 6 | 4–5 |

Chaque remplacement est un incrément démontrable : le point d'entrée du squelette continue de produire un journal
C09 complet et la CI reste verte.

## 5. Journal des changements de couture

| Phase | Changement | Nature | Raison |
|---|---|---|---|
| 2 | Port `Stockage` (`lire`, `ecrire`) | extension additive | premier consommateur : `donnees-temps` 2 (C03 point 7) |
| 2 | Type `EvenementDonnees` et enregistrement C09 `DONNEES` | extension additive | journaliser trous, récupérations, réinitialisations et préchargement (C03 points 6 et 7) |
| 2 | `SourceTicksHistoriques.seances(s)` | extension additive | distinguer fermeture officielle et trou (C03 point 5, C04) |
| 2 | Manifeste de fixture `xp-fixture-manifeste-v1` → `v2` (clé `seances` obligatoire par symbole) | modification de contrat du segment lecteur | même raison ; aucun champ manquant ne vaut une valeur par défaut (C02) ; fixture régénérée |
| 2 | `CoordinateurRefus.sur_evenement_donnees` | extension additive | journal des événements de données |
| 2 | Retrait de `AgregateurM15Minimal` | remplacement de segment | enveloppe `donnees-temps` 3 figée et branchée |
| 3 | Nature `RECALCUL` de `EvenementDonnees` | extension additive | R6′ : trou irrécupérable recalculé sur les seules bougies valides (défigeage de `donnees-temps` 3) |
| 3 | `Strategie.notifier_sortie`, `Strategie.sur_evenement_donnees` | extension additive | premier consommateur : `moteur-ema` 3 (S01.2 point 1, C03.6) |
| 3 | `SourceTicksHistoriques.tick_size(s)` et manifeste `v2` → `v3` (clé `tick_size` obligatoire, décimal en texte) | extension du port, modification de contrat du segment lecteur | tampon structurel S01.4 ; aucune valeur par défaut (C02) ; fixture régénérée (ticks inchangés) |
| 3 | `CoordinateurRefus.sur_evenement_donnees` transmet l'événement aux méthodes | extension du segment | un trou efface armements et replis (C03.6) |
| 3 | Segment `StockageMemoire` ; retrait de `StrategieNeutre` ; `executer_rejeu(fabrique_strategies=strategies_par_defaut)` reçoit `(bundle, source, symboles)` | remplacement de segment | enveloppe `moteur-ema` 3 figée et branchée |

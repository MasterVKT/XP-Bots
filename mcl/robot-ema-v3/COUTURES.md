# Coutures du squelette composite — robot 1 `EMA_V3`

Statut : **finalisé en phase 1** (2026-11-05). Code : `src/xpbots/noyau/` (coutures) et
`src/xpbots/app/segments_minimaux.py` (segments minimaux). Toute modification d'une couture est un changement de
contrat tracé (règle de couture 4) ; une extension additive (nouveau type, nouveau port, nouvelle clé optionnelle
documentée) accompagne le premier artefact qui en a besoin. Plan maître :
`docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md`, sections 5 et 6.

## 1. Chemin minimal de bout en bout

ticks de fixture → bougie M15 → stratégie neutre (`NO_SETUP`) → coordinateur (refus explicite) → exécution
papier → journal C09.

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
| `decisions` | `MotifRefus` | liste C09 + `AI_CONTEXT_VETO` + `ENVIRONMENT_NOT_READY` | identique, dans l'ordre, à la ligne « Motifs minimaux » du texte normatif |
| `decisions` | `Sens`, `Signal` | stratégie, symbole, clôture, sens, clôture Bid, `A_t`, `B_SL`, k, état du détecteur | `A_t` > 0, k > 0, 0 < sens × (C − B_SL) (C06) |
| `decisions` | `ResultatTechnique` | signal ou motif, état du détecteur | exactement l'un des deux |
| `decisions` | `CleIntention` | `(deployment_id, strategy_id, symbole, cloture_M15_UTC, sens)` | forme canonique stable (C08) |
| `decisions` | `Rempli`, `Refuse` | issue d'un signal | volume et prix > 0 ; motif de la liste fermée |
| `decisions` | `DecisionFondamentale` | autorisation ou refus, permission connue, scénario | refus seulement `FUNDAMENTAL_INVALID`, `FUNDAMENTAL_DIRECTION`, `NEWS_WINDOW` |
| `decisions` | `DecisionContexteIA` | `BLOCK` ou `NEUTRAL`, séquence du snapshot, événements | aucun état `ALLOW` n'existe (A12) |
| `journal_schema` | enregistrements C09 | `INITIALISATION`, `CLOTURE_BOUGIE`, `INTENTION` | clés exactes par type, numérotation sans trou, version et empreinte des règles dans chaque ligne, décimaux en texte exact, refus sans ordre |
| `json_canonique` | JSON | lecture stricte, écriture canonique, SHA-256 | doublons, NaN, Infinity et débordements refusés ; empreinte = `reference.llm_contracts.digest` |
| `config` | `BundleTechnique` | `config/parametres_figes_v3.json` figé | trois blocs, lecture seule, clé absente = erreur ; empreinte `dab01fb4…7c05` égale à celle publiée par la spécification |

## 3. Ports (`src/xpbots/noyau/ports.py`)

| Port | Méthodes | Disponible depuis | Implémenté par |
|---|---|---|---|
| `SourceTicksHistoriques` | `symboles()`, `ticks()`, `couverture(s)`, `fin_donnees_ms()`, `empreintes()` | phase 1 | lecteur de fixture (squelette), puis `journal-rejeu` 1c / `infrastructure` 0a |
| `Journal` | `ajouter(enregistrement)` | phase 1 | écrivain JSONL (squelette), puis `infrastructure` 0a |
| `Strategie` | `strategie_id`, `sur_cloture(bougie)`, `appliquer_issue(cle, issue)` | phase 1 | stratégie neutre, puis `moteur-ema` 3 (ajout prévu : `notifier_sortie`, phase 3) |
| `ControleFondamental` | `autoriser(symbole, sens, instant_ms)` | phase 1 | fondamental absent, puis `controles-fondamentaux` 3 (ajout prévu : demandes de sortie, phase 6) |
| `ContexteIA` | `decision(symbole, instant_ms)` | phase 1 | contexte neutre, puis `contexte-ia` 3 |
| `FluxTicks`, `Horloge`, `Courtier`, `CalculCourtier`, `Stockage` | — | phases 2 à 5 (premier consommateur) | doublures puis `infrastructure` |
| `SourcePermissions`, `SourceCalendrier`, `LecteurSnapshotIA` | — | phases 6 et 7 | doublures puis `infrastructure` 0a |
| `TransportHTTP` | — | phase 10 | doublure puis `infrastructure` 0d |

## 4. Segments minimaux et artefacts remplaçants

| Segment (`app/segments_minimaux.py`) | Comportement conforme à la spécification | Remplacé par | Phase |
|---|---|---|---|
| `LecteurFixtureCSV` | format du cahier de données §2 ; ordre (ms, séquence) strictement croissant ; manifeste `xp-fixture-manifeste-v1` (couverture déclarée, aucun seuil inventé, R5) | `journal-rejeu` 1c + `infrastructure` 0a | 8, 9 |
| `EcrivainJournalJSONL` | JSONL canonique LF, ajout seul, valide chaque ligne, refuse d'écraser un journal | `infrastructure` 0a | 9 |
| `AgregateurM15Minimal` | bougies Bid `[T, T+900 s)` ; tick de frontière dans la bougie suivante ; clôture quand l'horloge de rejeu atteint T+900 s ; validité = intervalle entièrement couvert ; bougie non terminée jamais close | `donnees-temps` 3 | 2 |
| `StrategieNeutre` | aucun signal ; `NO_SETUP`, `WARMUP` ou `DATA_GAP` selon le statut | `moteur-ema` 3 | 3 |
| `FondamentalAbsent` | `FUNDAMENTAL_INVALID` ; scénario `TECHNICAL_CONTROL_NEUTRAL` seulement s'il est nommé, journalisé, interdit en `DEMO` | `controles-fondamentaux` 3 | 6 |
| `ContexteIANeutre` | `NEUTRAL` (A12) ; n'autorise jamais rien | `contexte-ia` 3 | 7 |
| `ExecutionPapierMinimale` | aucun ordre ; un refus devient une issue `Refuse` | `execution-coordinateur` 4 + `journal-rejeu` 1b, `infrastructure` 1a | 5, 8, 9 |
| `CoordinateurRefus` | clôture journalisée pour chaque méthode ; signal : fondamental, puis contexte IA, puis environnement d'exécution absent (`ENVIRONMENT_NOT_READY`) ; premier refus retenu ; issue rendue à la méthode | `execution-coordinateur` 6 | 4–5 |

Chaque remplacement est un incrément démontrable : le point d'entrée du squelette continue de produire un journal
C09 complet et la CI reste verte.

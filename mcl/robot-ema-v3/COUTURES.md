# Coutures du squelette composite — robot 1 `EMA_V3`

Statut : **esquisse** (phase 0, 2026-11-05). Les coutures sont finalisées en phase 1 avec le noyau, puis
modifiées seulement par changement de contrat tracé (règle de couture 4). Plan maître :
`docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md`, sections 5 et 6.

## 1. Chemin minimal de bout en bout

ticks de fixture → bougie M15 → stratégie neutre (`NO_SETUP`) → coordinateur (refus explicite) → exécution
papier → journal C09. Point d'entrée : `python -m xpbots.app.rejeu --ticks <csv> --manifeste <json> --journal <jsonl>`.
Gate du squelette = sa CI : `python tools/run_robot_tests.py`, `python tools/verify_project.py`,
`mcl.py --dossier mcl/robot-ema-v3 verifier --mode strict`.

## 2. Types de couture (`src/xpbots/noyau/`)

| Type | Contenu | Invariants |
|---|---|---|
| `Instant` | entier ms UTC depuis l'époque + séquence de départage | ordre total stable ; conversion ISO `…Z` à la milliseconde |
| `Tick` | symbole canonique, symbole courtier, instant, séquence, Bid, Ask | Bid et Ask finis et positifs ; aucune règle de croisement ici (C06, R3) |
| `Bougie` | symbole, période (900 ou 3600 s), ouverture T, O, H, L, C Bid, validité, nombre de ticks | intervalle `[T, T+période)` aligné sur l'époque UTC ; L ≤ O, C ≤ H |
| `BougieEnrichie` | bougie + indicateurs + `A_t` + jour Londres + statut `OK`/`WARMUP`/`DATA_GAP` | indicateurs absents tant que la graine n'est pas atteinte |
| `Signal` | stratégie, symbole, clôture UTC, sens, clôture Bid, `A_t`, `B_SL`, k, état du détecteur | émis seulement à une clôture admissible |
| `IssueSignal` | `REMPLI(volume, prix_moyen, instant)` ou `REFUS(motif, instant)` | une issue par signal |
| `CleIntention` | `(deployment_id, strategy_id, symbole, cloture_M15_UTC, sens)` | unique et persistante (C08) |
| `MotifRefus` | liste C09 + `AI_CONTEXT_VETO` (A07) + `ENVIRONMENT_NOT_READY` (C04) | énumération fermée, testée contre le texte de la spécification |
| `Enregistrement` C09 | types `CLOTURE_BOUGIE`, `INTENTION`, `ORDRE_REQUETE`, `ORDRE_REPONSE`, `EXECUTION`, `PROTECTION`, `SORTIE`, `GARDE_COMPTE`, `ALERTE`, `INITIALISATION`, `RAPPROCHEMENT` | version et empreinte des règles dans chaque ligne ; aucun secret |
| JSON canonique | tri des clés, séparateurs sans espace, UTF-8 ; lecture stricte | doublons et non-finis refusés ; empreinte = `reference.technical.canonical_hash` |
| Chargeur de configuration | lecture stricte de `config/`, `schemas/`, `prompts/` | aucune valeur recopiée dans le code |

## 3. Ports (protocoles)

`FluxTicks`, `Horloge`, `Courtier`, `CalculCourtier`, `Stockage`, `Journal`, `SourcePermissions`,
`SourceCalendrier`, `LecteurSnapshotIA`, `SourceTicksHistoriques`, `TransportHTTP`, et les ports internes de
couture `Strategie`, `ControleFondamental`, `ContexteIA`. Le coordinateur ne connaît la méthode, le fondamental et
l'IA qu'à travers ces trois derniers ports.

## 4. Segments minimaux et artefacts remplaçants

| Segment minimal (`app/segments_minimaux.py`) | Comportement conforme à la spécification | Remplacé par | Phase |
|---|---|---|---|
| Lecteur de fixture CSV et écrivain JSONL | lecture du format du cahier de données §2, écriture en ajout seul | `infrastructure` 0a | 9 |
| Agrégateur M15 sans gestion de trou | couverture lue dans le manifeste de fixture ; bougies Bid `[T, T+900)` | `donnees-temps` 3 | 2 |
| Stratégie neutre | `NO_SETUP` à chaque clôture | `moteur-ema` 3 | 3 |
| Coordinateur de refus | journalise chaque clôture ; tout signal injecté reçoit un refus explicite | `execution-coordinateur` 6 | 4–5 |
| Exécution papier minimale | aucun ordre émis (aucun signal admis) | `journal-rejeu` 1b (rejeu), `infrastructure` 1a (démo) | 8, 9 |
| Fondamental absent | `FUNDAMENTAL_INVALID` ; scénario nommé `TECHNICAL_CONTROL_NEUTRAL` (C05) seulement s'il est explicitement configuré, journalisé, interdit en `DEMO` | `controles-fondamentaux` 3 | 6 |
| Contexte IA neutre | `NEUTRAL` (A12) | `contexte-ia` 3 | 7 |

Chaque remplacement est un incrément démontrable : le point d'entrée du squelette continue de produire un
journal C09 complet, CI verte.

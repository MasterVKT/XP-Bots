# Plan MCL — donnees-temps

> Artefact de chair du composite `robot-ema-v3`. Plan maître : `docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md`, section 7.A ; registre d'interprétation : `mcl/robot-ema-v3/INTERPRETATIONS.md`. Aucun code avant la section 9.

## 0. Périmètre de l'artefact

- **Artefact** : `donnees-temps` (paquet `src/xpbots/donnees_temps/`) — Temps UTC et Londres, bougies M15 Bid, indicateurs EMA/RSI/ATR et état récursif (C03).
- **Échelle** : composant autonome ; **mode** : pur (chair du composite).
- **Règle de périmètre** : livré en phase(s) 2 du plan maître ; MCL ne gouverne que la construction du code de cet artefact.

## 1. Test d'applicabilité

| Question | Réponse | Justification |
|---|---|---|
| Structure connaissable ? | oui | Contrats normatifs C03 (points 1 à 12), C11.1, C11.3, C11.4 |
| Contrats stabilisables tôt ? | oui | Seuils figés dans `config/`, fonctions de référence |
| Construire pour comprendre ? | non | Aucune recherche de variante |

- **Verdict** : applicable.
- **Bénéfice dégradé** : frontières externes stockage-etat, horloge-os doublées.
- **Signaux de mauvais domaine** : divergences répétées, défigeages en chaîne → suspendre et re-cartographier.

## 2. Étape 1 — Comprendre la cible

1. Finalité : Transformer un flux de ticks Bid/Ask horodatés en bougies M15 clôturées et valides, enrichies des indicateurs C03 et du contexte de session Londres, sans aucune information future.
2. Entrées : ticks ordonnés (instant ms UTC, séquence, Bid, Ask), événements de couverture du flux, calendrier de séances du symbole, bloc common de la configuration figée, état persisté. Sorties : BougieEnrichie (OHLC Bid, validité, E15/E25/E50, E50(t−4), RSI14, ATR14, A_t, jour Londres, statut OK/WARMUP/DATA_GAP) et événements de trou.
3. Contraintes : Python 3.13, bibliothèque standard (sauf adaptateurs réels en infrastructure), valeurs normatives lues dans `config/`, instants en ms UTC, prix en `Decimal`, aucune horloge ni réseau hors infrastructure.
4. Projet neuf (greenfield).

Point d'insertion dans le squelette : agrégateur M15 minimal du squelette (app/segments_minimaux.py) (voir `mcl/robot-ema-v3/COUTURES.md`).

## 3. Étape 2 — Unités fonctionnelles

- 2.1 Entrées : ticks ordonnés (instant ms UTC, séquence, Bid, Ask), événements de couverture du flux, calendrier de séances du symbole, bloc common de la configuration figée, état persisté ; sorties : BougieEnrichie (OHLC Bid, validité, E15/E25/E50, E50(t−4), RSI14, ATR14, A_t, jour Londres, statut OK/WARMUP/DATA_GAP) et événements de trou.
- 2.2 Workflow : tick → bougie en formation → clôture (tick de frontière ou horloge) → validité/trou → mise à jour des états EMA, RSI, ATR → A_t (ATR de t−1) → contexte Londres → BougieEnrichie.

| Unité | Responsabilité | Entrée → sortie | Dépend de |
|---|---|---|---|
| `parametres_techniques` | Charger et valider le bloc common de la configuration figée en objet immuable, avec l'empreinte canonique du bundle. | bundle JSON strict fourni par le chargeur du noyau (config/parametres_figes_v3.json) → objet immuable typé de tous les champs de common ; empreinte SHA-256 canonique du bundle | amont-noyau |
| `calendrier_seances` | Représenter les séances de cotation natives d'un symbole et dire si un instant est en séance. | intervalles UTC versionnés lus de l'environnement courtier (C04), jamais devinés → appartenance à une séance ; instant de la prochaine fermeture ou pause | amont-noyau |
| `sessions_londres` | Calculer jours Londres et UTC, appartenance aux fenêtres de méthode, heures locales de sortie et blackout de rollover via Europe/London. | Instant ms UTC ; heures locales lues dans la configuration de la méthode → dates et booléens exacts selon zoneinfo Europe/London, jours 0–4 seulement | parametres_techniques |
| `constructeur_bougies` | Agréger les ticks en bougies M15/H1 Bid clôturées sur [T,T+d) aligné UTC et signaler les trous. | ticks ordonnés (instant, séquence) ; événements de couverture ; calendrier de séances → bougies clôturées OHLC Bid avec validité et nombre de ticks ; événements de trou | parametres_techniques, calendrier_seances, amont-noyau |
| `indicateurs` | Calculer de façon incrémentale EMA graine SMA, RSI et ATR Wilder, TR et A_t = ATR de t−1. | clôtures et OHLC Bid de bougies valides, dans l'ordre → valeurs float64, None avant la graine ; historique EMA50 sur 4 bougies | parametres_techniques |
| `etat_indicateurs` | Précharger, persister et restaurer les états récursifs par symbole et en tracer l'empreinte. | au moins warmup_closed_m15_bars bougies M15 clôturées ; port Stockage → indicateurs courants ; empreinte (premier horodatage, SHA-256) ; statut WARMUP | indicateurs, stockage-etat, amont-noyau |
| `pipeline_marche` | Produire par symbole les bougies enrichies et les événements de trou à partir des ticks, de la couverture et de l'horloge. | ticks, événements de couverture, instants d'horloge → BougieEnrichie (bougie, indicateurs, A_t, jour Londres, statut) ou EvenementTrou | sessions_londres, constructeur_bougies, etat_indicateurs |

Question-test : « constructible et testable si rien d'autre n'existait ? »

| Unité | Réponse | A besoin de | Profondeur |
|---|---|---|---|
| `parametres_techniques` | oui (feuille interne) | — | 0 |
| `calendrier_seances` | oui (feuille interne) | — | 0 |
| `sessions_londres` | non | parametres_techniques | 1 |
| `constructeur_bougies` | non | parametres_techniques, calendrier_seances | 1 |
| `indicateurs` | non | parametres_techniques | 1 |
| `etat_indicateurs` | non | indicateurs | 2 |
| `pipeline_marche` | non | sessions_londres, constructeur_bougies, etat_indicateurs | 3 |

## 4. Étape 3 — Graphe de dépendances

- `parametres_techniques` → amont-noyau
- `calendrier_seances` → amont-noyau
- `sessions_londres` → parametres_techniques
- `constructeur_bougies` → parametres_techniques, calendrier_seances, amont-noyau
- `indicateurs` → parametres_techniques
- `etat_indicateurs` → indicateurs, stockage-etat, amont-noyau
- `pipeline_marche` → sessions_londres, constructeur_bougies, etat_indicateurs

- **Contrôle de divergence** : `mcl.py analyser --ecrire` puis `analyser` (2026-11-05) : profondeurs proposées identiques aux profondeurs déclarées, zéro divergence.
- Regroupements retenus (unités indépendantes de même profondeur réunies dans une couche) : `parametres_techniques` : proposé `0a`, retenu `0`; `calendrier_seances` : proposé `0b`, retenu `0`.
- **Amont figé** (artefacts antérieurs, déclarés comme frontières autorisées partout) : amont-noyau.
- **Frontières externes** : stockage-etat, horloge-os.
- **Cycles** : aucun entre unités ; la machine à états éventuelle est condensée dans une seule unité.

## 5. Étape 4 — Carte des couches

| Couche | Unités | Dépend de | Module |
|---|---|---|---|
| 0 — parametres-et-seances | `parametres_techniques`, `calendrier_seances` | amont-noyau | `src/xpbots/donnees_temps/c0_parametres_seances.py` |
| 1a — sessions-londres | `sessions_londres` | 0 | `src/xpbots/donnees_temps/c1a_sessions.py` |
| 1b — constructeur-bougies | `constructeur_bougies` | 0, amont-noyau | `src/xpbots/donnees_temps/c1b_bougies.py` |
| 1c — indicateurs | `indicateurs` | 0 | `src/xpbots/donnees_temps/c1c_indicateurs.py` |
| 2 — etat-indicateurs | `etat_indicateurs` | 1c, amont-noyau | `src/xpbots/donnees_temps/c2_etat_indicateurs.py` |
| 3 — pipeline-marche | `pipeline_marche` | 1a, 1b, 2 | `src/xpbots/donnees_temps/c3_pipeline.py` |

- **Groupes parallèles** : 1a, 1b, 1c (contrats finalisés ensemble, gates et gels séparés).

## 6. Encodage de la carte

- Outil : convention « une couche = un module nommé » + `mcl.py verifier --mode strict` en CI et revue de code (aucun outil d'architecture ajouté).
- Règle : dépendances autorisées vers toute couche plus interne, à profondeur quelconque.

## 7. Étape 5 — Contrats

- Esquisses : `mcl/donnees-temps/contrats/couche-<id>.md` (2026-11-05) ; finalisation couche par couche.

## 8. Étape 6 — Frontières externes

| Frontière | Imports réels | Couches autorisées | Doublure |
|---|---|---|---|
| stockage-etat | sqlite3 | aucune (port du noyau) | `tests/robot/doublures/` |
| horloge-os | time | aucune (port du noyau) | `tests/robot/doublures/` |

## 9. Étape 7 — Plan de construction

| Couche | Tests cat. 1 | Tests cat. 2 | Gate | Statut |
|---|---|---|---|---|
| 0 | clés manquantes/en trop, types, valeurs nulles, empreinte égale à reference.technical.canonical_hash ; séances : en séance, pause, fermeture exceptionnelle, instant inconnu | — | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/donnees-temps gate --couche 0 --unitaire "python tools/run_robot_tests.py --artefact donnees_temps --couche 0 --categorie 1" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 0` | à construire |
| 1a | changements d'heure 2025/2026, 08:15 première clôture, 15:45 dernière, 16:00 exclue, week-end exclu, jour UTC ≠ jour Londres, blackout [21:00,23:00) UTC, concordance local_decision_in_window | avec 1b et 1c via la couche 3 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/donnees-temps gate --couche 1a --unitaire "python tools/run_robot_tests.py --artefact donnees_temps --couche 1a --categorie 1" --integration "python tools/run_robot_tests.py --artefact donnees_temps --couche 1a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1a` | à construire |
| 1b | tick à T+900 dans la bougie suivante (C11.3), égalités de ms par séquence, minute inchangée ≠ trou, fermeture officielle ≠ trou, interruption inexpliquée = trou, H1 invisible avant clôture, clôture par horloge, bougie sans Bid (R4) | via la couche 3 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/donnees-temps gate --couche 1b --unitaire "python tools/run_robot_tests.py --artefact donnees_temps --couche 1b --categorie 1" --integration "python tools/run_robot_tests.py --artefact donnees_temps --couche 1b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1b` | à construire |
| 1c | égalité à reference.technical (ema, wilder, rsi, add_indicators) à 1e-12 près et mêmes comparaisons de seuil ; graines ; RSI 50/100/0 ; TR de la première bougie = H−L | via les couches 2 et 3 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/donnees-temps gate --couche 1c --unitaire "python tools/run_robot_tests.py --artefact donnees_temps --couche 1c --categorie 1" --integration "python tools/run_robot_tests.py --artefact donnees_temps --couche 1c --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1c` | à construire |
| 2 | préchargement insuffisant = WARMUP ; empreinte ; sauvegarde/restauration via doublure de Stockage ; préchargement différent journalisé | reprise après redémarrage identique au flux continu | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/donnees-temps gate --couche 2 --unitaire "python tools/run_robot_tests.py --artefact donnees_temps --couche 2 --categorie 1" --integration "python tools/run_robot_tests.py --artefact donnees_temps --couche 2 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 2` | à construire |
| 3 | statuts OK/WARMUP/DATA_GAP, ordre des émissions, effacement après trou (R5, R6) | C11.1 préfixe causal sur ticks synthétiques ; trou puis récupération ; changement d'heure de bout en bout | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/donnees-temps gate --couche 3 --unitaire "python tools/run_robot_tests.py --artefact donnees_temps --couche 3 --categorie 1" --integration "python tools/run_robot_tests.py --artefact donnees_temps --couche 3 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 3` | à construire |

## 10. Étape 8 — Checkpoints

- Tous les deux niveaux figés (`checkpoint_tous_les` = 2), signalés par `mcl.py statut`.

## 11. Gouvernance

- Profil : solo assisté par agent ; gardien de la carte et décideur des défigeages : l'utilisateur.
- Modification de contrat : défigeage tracé (`mcl.py defiger`) et ADR ; rayon via `mcl.py rayon`.

## 12. Bilan

- À compléter à la clôture de l'artefact (`mcl.py rapport`).

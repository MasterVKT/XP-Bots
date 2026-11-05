# Registre des points d'interprétation — robot 1 `EMA_V3`

Statut global : **décidé par délégation de l'utilisateur** (2026-11-05, phase 3). L'utilisateur a délégué le choix
avec pour critère le plus fort potentiel de rentabilité ; garde-fou appliqué : aucune décision ne touche une valeur
figée de `config/` ni une section normative, une lecture ne peut que préserver des occasions de trade conformes à la
spécification. La rentabilité reste non démontrée tant que C10 n'est pas exécuté. R6 est révisé en R6′ (défigeage
tracé de `donnees-temps` 3).

Règle (C02) : une contradiction ou un flou relevé pendant l'implémentation est signalé ici, jamais arbitré en
silence. Chaque point validé devient un test nommé dans la couche indiquée ; un point refusé reçoit la lecture
choisie par l'utilisateur. Aucun de ces points ne modifie une valeur figée de `config/`.

| Id | Source | Point | Lecture retenue | Couche qui la fixe | Statut |
|---|---|---|---|---|---|
| R1 | S01.2 point 1 | Sortie de position exactement à un instant de clôture M15 | Cette clôture n'est pas « strictement postérieure » : ni préparation ni entrée ; la clôture suivante est ignorée ; `IDLE` ensuite (lecture littérale, neutre pour la rentabilité) | moteur-ema 2 | décidé (phase 3) |
| R2 | S01.2 point 8, C08 | Issue d'un signal encore inconnue à la clôture suivante (accusé ambigu) | Sous-état technique d'attente, sans préparation de repli ; fill confirmé → `OWNED_POSITION` ; refus → `COOLDOWN` d'une clôture à partir de la résolution ; sous-état `ATTENTE_ISSUE`, motif `UNKNOWN_ORDER_STATE` à chaque clôture d'attente | moteur-ema 2 | décidé (phase 3) |
| R3 | C06 | « Cotation non croisée » | Bid ≤ Ask (spread nul admis) ; Bid > Ask refusé (davantage de cotations exécutables, risque inchangé) | execution-coordinateur 1a | décidé (phase 4) |
| R4 | C03 point 5 | Bougie sans aucun Bid en séance alors que la couverture est établie | Bougie invalide traitée comme un trou (`DATA_GAP`) | donnees-temps 1b (`test_intervalle_attendu_sans_bid_r4`), 3 (`test_intervalle_sans_bid_r4`) | appliqué (phase 2) |
| R5 | C03 points 5–6 | Détection des trous en rejeu (aucun seuil de silence dans la spécification) | Couverture déclarée par le manifeste des données ; sans manifeste, rejeu refusé ; aucun seuil inventé | donnees-temps 1b (`test_interruption_inexpliquee`), app (`test_manifestes_refuses`), journal-rejeu 1c | appliqué (phase 2) |
| R6′ | C03 point 6 | Reprise après un trou inexpliqué (R6 révisé) | Récupération des ticks manquants ; à défaut, **recalcul** sur les seules bougies valides (reconstructions complètes appliquées, aucune bougie inventée), événement `RECALCUL` ; entrées bloquées et replis effacés pendant le trou ; plus de nouveau préchauffage de 1 000 bougies (≈ 10 jours de marché sans décision évités par trou) ; même convention que la référence, qui calcule ses indicateurs sur les seules bougies valides | donnees-temps 3 (défigeage du 2026-11-05, `TestRecuperation`) | décidé (phase 3) |
| R7 | C06 | Motif quand une contrainte native SL/TP (distance minimale, gel) invalide le plan | `PROTECTION_ERROR` | execution-coordinateur 1b | décidé (phase 4) |
| R8 | C07 | Motif quand des positions externes empêchent la coordination fiable du risque | `ENVIRONMENT_NOT_READY` | execution-coordinateur 3 | décidé (phase 4) |
| R9 | C10 | « Un tick adverse » du scénario de référence | Un `tick_size` défavorable ajouté au prix du premier tick après le délai (évaluation prudente) | journal-rejeu 1b | décidé (phase 8) |
| R10 | C05, A06 | Devises par symbole et symboles par issuer, absents des exports JSON | Table codée depuis le texte de la spécification, avec test de concordance sur ce texte | controles-fondamentaux 0, service-ia 2a | décidé (phases 6, 10) |
| R11 | C10 | Comparaison à la V1 : spécification V1 absente du dépôt | Rétention `N/A` jusqu'à fourniture de la V1 ; aucune conclusion économique | journal-rejeu 2a | décidé (phase 8) |
| R12 | A04, C05 | Calendrier HIGH : le paquet Python MetaTrader5 n'expose aucune fonction Calendar | Exportateur MQL5 minimal du calendrier natif MT5 (sans coût, même source horaire que le courtier) ; calendrier livré par le module fondamental admis en alternative | controles-fondamentaux 1b, infrastructure 0a | décidé (phase 6) |
| R13 | C05 | Transport des permissions fondamentales (non spécifié) | Fichiers JSONL écrits atomiquement dans un dossier dédié ; à confirmer avec le module externe | controles-fondamentaux 2, infrastructure 0a | décidé (phase 6) |
| R14 | C03 point 1, C04 | Heure des ticks MT5 : documentation officielle UTC, rapports contradictoires (heure serveur) | Contrôle empirique obligatoire en qualification (écart entre le tick et l'horloge UTC système) ; écart non expliqué → `ENVIRONMENT_NOT_READY` | infrastructure 1a et 2 | décidé (phase 9) |
| R15 | — | Réglages d'exploitation non normatifs (scrutation ≤ 250 ms, chemins, `deployment_id`, magic) | Hors `config/` figé : gabarit `deploiement/environnement.exemple.json`, valeurs réelles sous `runtime/` | app, infrastructure | décidé |
| R16 | C10 | Six perturbations de voisinage | Scénarios nommés réservés au rejeu, refusés en `PAPER` et `DEMO` | journal-rejeu 0 | décidé (phase 8) |
| R17 | C08 | Priorité LONDON avant EMA alors que le robot 2 n'existe pas | Coordinateur générique, testé avec des signaux `LONDON_V3` synthétiques | execution-coordinateur 2b | décidé (phase 4) |
| R18 | S01.2 point 4, S01.3 | Seuil RSI d'armement (50) sans clé dédiée dans le bloc `ema` | Clés `long_signal_rsi_min` / `short_signal_rsi_max` (même valeur écrite par les deux sections), jamais recopiées | moteur-ema 1b (`test_seuil_armement_r18`) | décidé (phase 3) |

## Constats de cohérence relevés en phase 0 (sans défaut)

- Le bloc JSON de la spécification nomme `strategy` le bloc que l'export nomme `ema` ; `tests/check_technical.py`
  vérifie déjà leur identité.
- `common.default_mode = PAPER` (robot) et `ai_integration.default_evaluation_mode = PAPER_AB` (comparaison IA)
  portent sur deux objets distincts et sont compatibles.

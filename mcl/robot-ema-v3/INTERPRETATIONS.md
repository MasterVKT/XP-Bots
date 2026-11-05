# Registre des points d'interprétation — robot 1 `EMA_V3`

Statut global : **proposé — en attente de validation de l'utilisateur** (phase 0, 2026-11-05).

Règle (C02) : une contradiction ou un flou relevé pendant l'implémentation est signalé ici, jamais arbitré en
silence. Chaque point validé devient un test nommé dans la couche indiquée ; un point refusé reçoit la lecture
choisie par l'utilisateur. Aucun de ces points ne modifie une valeur figée de `config/`.

| Id | Source | Point | Lecture proposée | Couche qui la fixe | Statut |
|---|---|---|---|---|---|
| R1 | S01.2 point 1 | Sortie de position exactement à un instant de clôture M15 | Cette clôture n'est pas « strictement postérieure » : ni préparation ni entrée ; la clôture suivante est ignorée ; `IDLE` ensuite | moteur-ema 2 | proposé |
| R2 | S01.2 point 8, C08 | Issue d'un signal encore inconnue à la clôture suivante (accusé ambigu) | Sous-état technique d'attente, sans préparation de repli ; fill confirmé → `OWNED_POSITION` ; refus → `COOLDOWN` d'une clôture à partir de la résolution | moteur-ema 2 | proposé |
| R3 | C06 | « Cotation non croisée » | Bid ≤ Ask (spread nul admis) ; Bid > Ask refusé | execution-coordinateur 1a | proposé |
| R4 | C03 point 5 | Bougie sans aucun Bid en séance alors que la couverture est établie | Bougie invalide traitée comme un trou (`DATA_GAP`) | donnees-temps 1b | proposé |
| R5 | C03 points 5–6 | Détection des trous en rejeu (aucun seuil de silence dans la spécification) | Couverture déclarée par le manifeste des données ; sans manifeste, rejeu refusé ; aucun seuil inventé | donnees-temps 3, journal-rejeu 1c | proposé |
| R6 | C03 point 6 | Reprise après un trou inexpliqué | Récupération des ticks manquants puis recalcul depuis le préchargement ; à défaut, nouvelle initialisation journalisée | donnees-temps 2 et 3 | proposé |
| R7 | C06 | Motif quand une contrainte native SL/TP (distance minimale, gel) invalide le plan | `PROTECTION_ERROR` | execution-coordinateur 1b | proposé |
| R8 | C07 | Motif quand des positions externes empêchent la coordination fiable du risque | `ENVIRONMENT_NOT_READY` | execution-coordinateur 3 | proposé |
| R9 | C10 | « Un tick adverse » du scénario de référence | Un `tick_size` défavorable ajouté au prix du premier tick après le délai | journal-rejeu 1b | proposé |
| R10 | C05, A06 | Devises par symbole et symboles par issuer, absents des exports JSON | Table codée depuis le texte de la spécification, avec test de concordance sur ce texte | controles-fondamentaux 0, service-ia 2a | proposé |
| R11 | C10 | Comparaison à la V1 : spécification V1 absente du dépôt | Rétention `N/A` jusqu'à fourniture de la V1 ; aucune conclusion économique | journal-rejeu 2a | proposé |
| R12 | A04, C05 | Calendrier HIGH : le paquet Python MetaTrader5 n'expose aucune fonction Calendar | À choisir en phase 6 : exportateur MQL5 minimal (CSV versionné vers `Common/Files`, compilé par l'utilisateur) ou calendrier livré par le module fondamental | controles-fondamentaux 1b, infrastructure 0a | décision en phase 6 |
| R13 | C05 | Transport des permissions fondamentales (non spécifié) | Fichiers JSONL écrits atomiquement dans un dossier dédié ; à confirmer avec le module externe | controles-fondamentaux 2, infrastructure 0a | décision en phase 6 |
| R14 | C03 point 1, C04 | Heure des ticks MT5 : documentation officielle UTC, rapports contradictoires (heure serveur) | Contrôle empirique obligatoire en qualification (écart entre le tick et l'horloge UTC système) ; écart non expliqué → `ENVIRONMENT_NOT_READY` | infrastructure 1a et 2 | proposé |
| R15 | — | Réglages d'exploitation non normatifs (scrutation ≤ 250 ms, chemins, `deployment_id`, magic) | Hors `config/` figé : gabarit `deploiement/environnement.exemple.json`, valeurs réelles sous `runtime/` | app, infrastructure | proposé |
| R16 | C10 | Six perturbations de voisinage | Scénarios nommés réservés au rejeu, refusés en `PAPER` et `DEMO` | journal-rejeu 0 | proposé |
| R17 | C08 | Priorité LONDON avant EMA alors que le robot 2 n'existe pas | Coordinateur générique, testé avec des signaux `LONDON_V3` synthétiques | execution-coordinateur 2b | proposé |

## Constats de cohérence relevés en phase 0 (sans défaut)

- Le bloc JSON de la spécification nomme `strategy` le bloc que l'export nomme `ema` ; `tests/check_technical.py`
  vérifie déjà leur identité.
- `common.default_mode = PAPER` (robot) et `ai_integration.default_evaluation_mode = PAPER_AB` (comparaison IA)
  portent sur deux objets distincts et sont compatibles.

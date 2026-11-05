# Plan MCL — moteur-ema

> Artefact de chair du composite `robot-ema-v3`. Plan maître : `docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md`, section 7.B ; registre d'interprétation : `mcl/robot-ema-v3/INTERPRETATIONS.md`. Aucun code avant la section 9.

## 0. Périmètre de l'artefact

- **Artefact** : `moteur-ema` (paquet `src/xpbots/moteur_ema/`) — Méthode S01 : tendance, armement, repli, reprise, stop structurel, machine à états, compteur journalier.
- **Échelle** : composant autonome ; **mode** : pur (chair du composite).
- **Règle de périmètre** : livré en phase(s) 3 du plan maître ; MCL ne gouverne que la construction du code de cet artefact.

## 1. Test d'applicabilité

| Question | Réponse | Justification |
|---|---|---|
| Structure connaissable ? | oui | Contrats normatifs S01.1 à S01.6, C03.8–C03.11, C06 (conversion), A07 |
| Contrats stabilisables tôt ? | oui | Seuils figés dans `config/`, fonctions de référence |
| Construire pour comprendre ? | non | Aucune recherche de variante |

- **Verdict** : applicable.
- **Bénéfice dégradé** : frontières externes stockage-etat doublées.
- **Signaux de mauvais domaine** : divergences répétées, défigeages en chaîne → suspendre et re-cartographier.

## 2. Étape 1 — Comprendre la cible

1. Finalité : À chaque clôture M15 admissible, produire un signal EMA_V3 (sens, B_SL, A_t, k) ou un motif technique, puis appliquer l'issue reçue (fill ou refus définitif) à l'état du symbole.
2. Entrées : BougieEnrichie, tick_size du profil, issues des signaux, notifications de sortie de position. Sorties : ResultatTechnique (signal ou motif OUTSIDE_SESSION, WARMUP, DATA_GAP, NO_SETUP, STOP_TOO_WIDE, DAILY_ENTRY_CAP) et état du détecteur pour C09.
3. Contraintes : Python 3.13, bibliothèque standard (sauf adaptateurs réels en infrastructure), valeurs normatives lues dans `config/`, instants en ms UTC, prix en `Decimal`, aucune horloge ni réseau hors infrastructure.
4. Projet neuf (greenfield).

Point d'insertion dans le squelette : stratégie neutre NO_SETUP du squelette (voir `mcl/robot-ema-v3/COUTURES.md`).

## 3. Étape 2 — Unités fonctionnelles

- 2.1 Entrées : BougieEnrichie, tick_size du profil, issues des signaux, notifications de sortie de position ; sorties : ResultatTechnique (signal ou motif OUTSIDE_SESSION, WARMUP, DATA_GAP, NO_SETUP, STOP_TOO_WIDE, DAILY_ENTRY_CAP) et état du détecteur pour C09.
- 2.2 Workflow : réinitialisations (fenêtre, jour, trou) → cooldown/position possédée → tendance → armement → validité du repli → contact et âge → reprise → stop → signal → issue → transition.

| Unité | Responsabilité | Entrée → sortie | Dépend de |
|---|---|---|---|
| `parametres_ema` | Charger et valider le bloc ema de la configuration figée. | bundle JSON strict → objet immuable du bloc ema | amont-noyau |
| `tendance_ema` | Évaluer l'ordre EMA15/25/50 et la pente de l'EMA50 sur quatre bougies. | quatre flottants disponibles → 1 long, −1 court, 0 aucune tendance (égalités comprises) | parametres_ema |
| `conditions_repli` | Tester le contexte d'armement, la validité du repli et le contact avec la zone EMA15–EMA50. | valeurs de la bougie et indicateurs, A_t > 0 → booléens selon S01.2 points 4 à 6 | parametres_ema |
| `bougie_reprise` | Tester la bougie de reprise de S01.3. | OHLC Bid, TR, E15, RSI, A_t > 0 → vrai seulement si toutes les conditions S01.3 du sens sont vraies | parametres_ema |
| `stop_objectif_ema` | Calculer buffer, B_SL non arrondi, refus au-delà de 2,50 A et multiple d'objectif. | sens, clôture, extrême du repli signal compris, A_t, tick_size Decimal → B_SL sur l'échelle Bid, distance sens·(C−B_SL), drapeau trop large ; k = 1,5 | parametres_ema |
| `machine_etats_ema` | Gérer armement, contact, repli de 1 à 8 bougies, cooldown, position possédée et compteur journalier par symbole. | BougieEnrichie au statut OK ; issues ; instants de sortie → état (IDLE, ARMED_*, PULLBACK_*, COOLDOWN, OWNED_POSITION) et événement AUCUN ou REPRISE(sens, extrêmes, âge) | tendance_ema, conditions_repli, bougie_reprise, amont-noyau |
| `moteur_ema` | Produire à chaque clôture admissible un signal ou un motif technique et appliquer l'issue reçue. | BougieEnrichie, tick_size, issues → Signal ou motif, état du détecteur et niveaux structurels | machine_etats_ema, stop_objectif_ema, amont-donnees-temps, stockage-etat |

Question-test : « constructible et testable si rien d'autre n'existait ? »

| Unité | Réponse | A besoin de | Profondeur |
|---|---|---|---|
| `parametres_ema` | oui (feuille interne) | — | 0 |
| `tendance_ema` | non | parametres_ema | 1 |
| `conditions_repli` | non | parametres_ema | 1 |
| `bougie_reprise` | non | parametres_ema | 1 |
| `stop_objectif_ema` | non | parametres_ema | 1 |
| `machine_etats_ema` | non | tendance_ema, conditions_repli, bougie_reprise | 2 |
| `moteur_ema` | non | machine_etats_ema, stop_objectif_ema | 3 |

## 4. Étape 3 — Graphe de dépendances

- `parametres_ema` → amont-noyau
- `tendance_ema` → parametres_ema
- `conditions_repli` → parametres_ema
- `bougie_reprise` → parametres_ema
- `stop_objectif_ema` → parametres_ema
- `machine_etats_ema` → tendance_ema, conditions_repli, bougie_reprise, amont-noyau
- `moteur_ema` → machine_etats_ema, stop_objectif_ema, amont-donnees-temps, stockage-etat

- **Contrôle de divergence** : `mcl.py analyser --ecrire` puis `analyser` (2026-11-05) : profondeurs proposées identiques aux profondeurs déclarées, zéro divergence.
- Regroupements retenus (unités indépendantes de même profondeur réunies dans une couche) : aucun.
- **Amont figé** (artefacts antérieurs, déclarés comme frontières autorisées partout) : amont-noyau, amont-donnees-temps.
- **Frontières externes** : stockage-etat.
- **Cycles** : aucun entre unités ; la machine à états éventuelle est condensée dans une seule unité.

## 5. Étape 4 — Carte des couches

| Couche | Unités | Dépend de | Module |
|---|---|---|---|
| 0 — parametres-ema | `parametres_ema` | amont-noyau | `src/xpbots/moteur_ema/c0_parametres.py` |
| 1a — tendance | `tendance_ema` | 0 | `src/xpbots/moteur_ema/c1a_tendance.py` |
| 1b — conditions-repli | `conditions_repli` | 0 | `src/xpbots/moteur_ema/c1b_repli.py` |
| 1c — bougie-reprise | `bougie_reprise` | 0 | `src/xpbots/moteur_ema/c1c_reprise.py` |
| 1d — stop-objectif | `stop_objectif_ema` | 0 | `src/xpbots/moteur_ema/c1d_stop.py` |
| 2 — machine-etats | `machine_etats_ema` | 1a, 1b, 1c, amont-noyau | `src/xpbots/moteur_ema/c2_machine_etats.py` |
| 3 — moteur | `moteur_ema` | 1d, 2, amont-donnees-temps | `src/xpbots/moteur_ema/c3_moteur.py` |

- **Groupes parallèles** : 1a, 1b, 1c, 1d (contrats finalisés ensemble, gates et gels séparés).

## 6. Encodage de la carte

- Outil : convention « une couche = un module nommé » + `mcl.py verifier --mode strict` en CI et revue de code (aucun outil d'architecture ajouté).
- Règle : dépendances autorisées vers toute couche plus interne, à profondeur quelconque.

## 7. Étape 5 — Contrats

- Esquisses : `mcl/moteur-ema/contrats/couche-<id>.md` (2026-11-05) ; finalisation couche par couche.

## 8. Étape 6 — Frontières externes

| Frontière | Imports réels | Couches autorisées | Doublure |
|---|---|---|---|
| stockage-etat | sqlite3 | aucune (port du noyau) | `tests/robot/doublures/` |

## 9. Étape 7 — Plan de construction

| Couche | Tests cat. 1 | Tests cat. 2 | Gate | Statut |
|---|---|---|---|---|
| 0 | clés du bloc ema, drapeaux non implémentés refusés | — | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/moteur-ema gate --couche 0 --unitaire "python tools/run_robot_tests.py --artefact moteur_ema --couche 0 --categorie 1" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 0` | à construire |
| 1a | EMA égales ou pente EMA50 nulle : aucun armement (C11.2, S01.6) ; inégalités strictes | via 2 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/moteur-ema gate --couche 1a --unitaire "python tools/run_robot_tests.py --artefact moteur_ema --couche 1a --categorie 1" --integration "python tools/run_robot_tests.py --artefact moteur_ema --couche 1a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1a` | à construire |
| 1b | RSI de repli 40 admis ; clôture à EMA50−0,25A exactement admise ; mèche sous EMA50 sans clôture au-delà n'annule pas ; contact aux bornes | via 2 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/moteur-ema gate --couche 1b --unitaire "python tools/run_robot_tests.py --artefact moteur_ema --couche 1b --categorie 1" --integration "python tools/run_robot_tests.py --artefact moteur_ema --couche 1b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1b` | à construire |
| 1c | RSI 49,999 refusé, 50 admis ; O=C refusé ; TR > 2,5A refusé ; 0,65 exactement admis ; R = 0 refusé | via 2 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/moteur-ema gate --couche 1c --unitaire "python tools/run_robot_tests.py --artefact moteur_ema --couche 1c --categorie 1" --integration "python tools/run_robot_tests.py --artefact moteur_ema --couche 1c --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1c` | à construire |
| 1d | S01.5 : B_SL 1,09945 et 1,10055 ; extrême de la bougie de signal inclus ; plancher 0,80A ; STOP_TOO_WIDE au-delà de 2,5A | via 3 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/moteur-ema gate --couche 1d --unitaire "python tools/run_robot_tests.py --artefact moteur_ema --couche 1d --categorie 1" --integration "python tools/run_robot_tests.py --artefact moteur_ema --couche 1d --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1d` | à construire |
| 2 | transitions T1 à T12 une par une (plan maître 7.B), R1, R2 | équivalence avec reference.technical.ema_setups sur séries synthétiques | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/moteur-ema gate --couche 2 --unitaire "python tools/run_robot_tests.py --artefact moteur_ema --couche 2 --categorie 1" --integration "python tools/run_robot_tests.py --artefact moteur_ema --couche 2 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 2` | à construire |
| 3 | motifs et ordre des traitements ; compteur de six fills (T11) ; persistance | bloc A+B réel : S01.6 complet, C11.4, causalité | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/moteur-ema gate --couche 3 --unitaire "python tools/run_robot_tests.py --artefact moteur_ema --couche 3 --categorie 1" --integration "python tools/run_robot_tests.py --artefact moteur_ema --couche 3 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 3` | à construire |

## 10. Étape 8 — Checkpoints

- Tous les deux niveaux figés (`checkpoint_tous_les` = 2), signalés par `mcl.py statut`.

## 11. Gouvernance

- Profil : solo assisté par agent ; gardien de la carte et décideur des défigeages : l'utilisateur.
- Modification de contrat : défigeage tracé (`mcl.py defiger`) et ADR ; rayon via `mcl.py rayon`.

## 12. Bilan

- À compléter à la clôture de l'artefact (`mcl.py rapport`).

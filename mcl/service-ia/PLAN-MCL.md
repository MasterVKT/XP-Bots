# Plan MCL — service-ia

> Artefact de chair du composite `robot-ema-v3`. Plan maître : `docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md`, section 7.G ; registre d'interprétation : `mcl/robot-ema-v3/INTERPRETATIONS.md`. Aucun code avant la section 9.

## 0. Périmètre de l'artefact

- **Artefact** : `service-ia` (paquet `src/xpbots/service_ia/`) — Service IA distant partagé (A04–A11) : collecte, validation, veto, budget, routeur, snapshot.
- **Échelle** : composant autonome ; **mode** : pur (chair du composite).
- **Règle de périmètre** : livré en phase(s) 10 du plan maître ; MCL ne gouverne que la construction du code de cet artefact.

## 1. Test d'applicabilité

| Question | Réponse | Justification |
|---|---|---|
| Structure connaissable ? | oui | Contrats normatifs A02, A04 à A11, A14 |
| Contrats stabilisables tôt ? | oui | Seuils figés dans `config/`, fonctions de référence |
| Construire pour comprendre ? | non | Aucune recherche de variante |

- **Verdict** : applicable.
- **Bénéfice dégradé** : frontières externes stockage-ia, transport-llm, collecte-rss, ipc-ecriture, horloge-os doublées.
- **Signaux de mauvais domaine** : divergences répétées, défigeages en chaîne → suspendre et re-cartographier.

## 2. Étape 1 — Comprendre la cible

1. Finalité : Collecter les textes officiels, les classer par API distantes sous budget, construire les vetos A06 et publier un snapshot atomique consommé par les robots.
2. Entrées : flux RSS officiels, calendrier, clés API de l'environnement, horloge. Sorties : snapshot xp-ai-context-v1, briefings et journaux informatifs séparés, registre de budget.
3. Contraintes : Python 3.13, bibliothèque standard (sauf adaptateurs réels en infrastructure), valeurs normatives lues dans `config/`, instants en ms UTC, prix en `Decimal`, aucune horloge ni réseau hors infrastructure.
4. Projet neuf (greenfield).

Point d'insertion dans le squelette : aucun : processus distinct ; remplace l'absence de snapshot (NEUTRAL) (voir `mcl/robot-ema-v3/COUTURES.md`).

## 3. Étape 2 — Unités fonctionnelles

- 2.1 Entrées : flux RSS officiels, calendrier, clés API de l'environnement, horloge ; sorties : snapshot xp-ai-context-v1, briefings et journaux informatifs séparés, registre de budget.
- 2.2 Workflow : collecte → normalisation → borne de tokens → réservation de budget → routeur → validation → événement de veto → snapshot ; planification des briefings et journaux.

| Unité | Responsabilité | Entrée → sortie | Dépend de |
|---|---|---|---|
| `parametres_ia` | Charger l'export IA, les schémas et les prompts exacts. | config/, schemas/, prompts/ → objet immuable | amont-noyau |
| `normalisation_textes` | Normaliser et dédoublonner les textes officiels collectés. | texte brut et métadonnées de collecte → TexteSource daté ou marqué non daté | parametres_ia |
| `borne_tokens` | Calculer la borne conservatrice de tokens d'une requête. | corps sérialisé → borne ≤ 4 096 ou refus | parametres_ia |
| `validateurs_sorties` | Valider strictement les sorties d'extraction et informatives. | réponse brute, texte transmis → objet validé ou refus (aucun veto) | parametres_ia |
| `registre_budget` | Réserver et rapprocher coûts, tentatives et tokens de façon transactionnelle. | route, bornes de tokens et de coût → réservation Decimal ou refus | parametres_ia, stockage-ia |
| `evenement_veto` | Construire un événement OFFICIAL_UNSCHEDULED_POLICY selon A06. | extraction validée, texte, calendrier valide → veto daté et symboles concernés ou rien | validateurs_sorties, normalisation_textes, amont-contexte-ia |
| `routeur_fournisseurs` | Choisir et appeler les fournisseurs dans l'ordre et les délais A08. | job de classification ou informatif → résultat validé ou NEUTRAL | borne_tokens, registre_budget, validateurs_sorties, transport-llm |
| `ecrivain_snapshot` | Publier atomiquement le snapshot et son heartbeat. | vetos valides, séquence persistée → fichier remplacé atomiquement | evenement_veto, ipc-ecriture |
| `planificateur` | Planifier collectes, classifications, briefings, journaux et revues. | horloge Londres, file, budget → travaux ordonnés par priorité A09 | routeur_fournisseurs, normalisation_textes, collecte-rss |
| `service` | Exécuter le service : collecteur, worker unique, heartbeat. | environnement configuré → snapshot et journaux informatifs | planificateur, ecrivain_snapshot |

Question-test : « constructible et testable si rien d'autre n'existait ? »

| Unité | Réponse | A besoin de | Profondeur |
|---|---|---|---|
| `parametres_ia` | oui (feuille interne) | — | 0 |
| `normalisation_textes` | non | parametres_ia | 1 |
| `borne_tokens` | non | parametres_ia | 1 |
| `validateurs_sorties` | non | parametres_ia | 1 |
| `registre_budget` | non | parametres_ia | 1 |
| `evenement_veto` | non | validateurs_sorties, normalisation_textes | 2 |
| `routeur_fournisseurs` | non | borne_tokens, registre_budget, validateurs_sorties | 2 |
| `ecrivain_snapshot` | non | evenement_veto | 3 |
| `planificateur` | non | routeur_fournisseurs, normalisation_textes | 3 |
| `service` | non | planificateur, ecrivain_snapshot | 4 |

## 4. Étape 3 — Graphe de dépendances

- `parametres_ia` → amont-noyau
- `normalisation_textes` → parametres_ia
- `borne_tokens` → parametres_ia
- `validateurs_sorties` → parametres_ia
- `registre_budget` → parametres_ia, stockage-ia
- `evenement_veto` → validateurs_sorties, normalisation_textes, amont-contexte-ia
- `routeur_fournisseurs` → borne_tokens, registre_budget, validateurs_sorties, transport-llm
- `ecrivain_snapshot` → evenement_veto, ipc-ecriture
- `planificateur` → routeur_fournisseurs, normalisation_textes, collecte-rss
- `service` → planificateur, ecrivain_snapshot

- **Contrôle de divergence** : `mcl.py analyser --ecrire` puis `analyser` (2026-11-05) : profondeurs proposées identiques aux profondeurs déclarées, zéro divergence.
- Regroupements retenus (unités indépendantes de même profondeur réunies dans une couche) : aucun.
- **Amont figé** (artefacts antérieurs, déclarés comme frontières autorisées partout) : amont-noyau, amont-contexte-ia.
- **Frontières externes** : stockage-ia, transport-llm, collecte-rss, ipc-ecriture, horloge-os.
- **Cycles** : aucun entre unités ; la machine à états éventuelle est condensée dans une seule unité.

## 5. Étape 4 — Carte des couches

| Couche | Unités | Dépend de | Module |
|---|---|---|---|
| 0 — parametres-ia | `parametres_ia` | amont-noyau | `src/xpbots/service_ia/c0_parametres.py` |
| 1a — normalisation | `normalisation_textes` | 0 | `src/xpbots/service_ia/c1a_normalisation.py` |
| 1b — tokens | `borne_tokens` | 0 | `src/xpbots/service_ia/c1b_tokens.py` |
| 1c — validateurs | `validateurs_sorties` | 0 | `src/xpbots/service_ia/c1c_validateurs.py` |
| 1d — budget | `registre_budget` | 0 | `src/xpbots/service_ia/c1d_budget.py` |
| 2a — veto | `evenement_veto` | 1a, 1c, amont-contexte-ia | `src/xpbots/service_ia/c2a_veto.py` |
| 2b — routeur | `routeur_fournisseurs` | 1b, 1c, 1d | `src/xpbots/service_ia/c2b_routeur.py` |
| 3a — ecrivain-snapshot | `ecrivain_snapshot` | 2a | `src/xpbots/service_ia/c3a_ecrivain_snapshot.py` |
| 3b — planificateur | `planificateur` | 1a, 2b | `src/xpbots/service_ia/c3b_planificateur.py` |
| 4 — service | `service` | 3a, 3b | `src/xpbots/service_ia/c4_service.py` |

- **Groupes parallèles** : 1a, 1b, 1c, 1d; 2a, 2b; 3a, 3b (contrats finalisés ensemble, gates et gels séparés).

## 6. Encodage de la carte

- Outil : convention « une couche = un module nommé » + `mcl.py verifier --mode strict` en CI et revue de code (aucun outil d'architecture ajouté).
- Règle : dépendances autorisées vers toute couche plus interne, à profondeur quelconque.

## 7. Étape 5 — Contrats

- Esquisses : `mcl/service-ia/contrats/couche-<id>.md` (2026-11-05) ; finalisation couche par couche.

## 8. Étape 6 — Frontières externes

| Frontière | Imports réels | Couches autorisées | Doublure |
|---|---|---|---|
| stockage-ia | sqlite3 | aucune (port du noyau) | `tests/robot/doublures/` |
| transport-llm | urllib, http, ssl, socket | aucune (port du noyau) | `tests/robot/doublures/` |
| collecte-rss | — (port du noyau) | aucune (port du noyau) | `tests/robot/doublures/` |
| ipc-ecriture | — (port du noyau) | aucune (port du noyau) | `tests/robot/doublures/` |
| horloge-os | time | aucune (port du noyau) | `tests/robot/doublures/` |

## 9. Étape 7 — Plan de construction

| Couche | Tests cat. 1 | Tests cat. 2 | Gate | Statut |
|---|---|---|---|---|
| 0 | export IA, schémas et prompts exacts | — | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/service-ia gate --couche 0 --unitaire "python tools/run_robot_tests.py --artefact service_ia --couche 0 --categorie 1" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 0` | à construire |
| 1a | item_id, URL canonique, SHA-256, dates absentes ou futures, dédoublonnage | via 2a | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/service-ia gate --couche 1a --unitaire "python tools/run_robot_tests.py --artefact service_ia --couche 1a --categorie 1" --integration "python tools/run_robot_tests.py --artefact service_ia --couche 1a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1a` | à construire |
| 1b | borne octets + 512 ≤ 4 096 ; raccourcissement sans perte de négation | via 2b | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/service-ia gate --couche 1b --unitaire "python tools/run_robot_tests.py --artefact service_ia --couche 1b --categorie 1" --integration "python tools/run_robot_tests.py --artefact service_ia --couche 1b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1b` | à construire |
| 1c | clés en trop, doublons, enums, citation inventée, item_id étranger, tronqué (A14) | via 2a | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/service-ia gate --couche 1c --unitaire "python tools/run_robot_tests.py --artefact service_ia --couche 1c --categorie 1" --integration "python tools/run_robot_tests.py --artefact service_ia --couche 1c --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1c` | à construire |
| 1d | 24, 18, 150 000, 3 USD, 15 USD aux bornes ; coût inconnu conservé ; Gemini payant jamais gratuit | concurrence via 0e | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/service-ia gate --couche 1d --unitaire "python tools/run_robot_tests.py --artefact service_ia --couche 1d --categorie 1" --integration "python tools/run_robot_tests.py --artefact service_ia --couche 1d --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1d` | à construire |
| 2a | conditions A06 ; calendrier POLICY_DECISION ±3 600 s ; fenêtre [réception, publication+900 s) | via 3a | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/service-ia gate --couche 2a --unitaire "python tools/run_robot_tests.py --artefact service_ia --couche 2a --categorie 1" --integration "python tools/run_robot_tests.py --artefact service_ia --couche 2a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 2a` | à construire |
| 2b | ordre des fournisseurs, délais, pauses, échéance 75 s, 401/429/5xx | transport factice | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/service-ia gate --couche 2b --unitaire "python tools/run_robot_tests.py --artefact service_ia --couche 2b --categorie 1" --integration "python tools/run_robot_tests.py --artefact service_ia --couche 2b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 2b` | à construire |
| 3a | remplacement atomique, réessais, heartbeat 30 s, séquence persistée | lu par contexte-ia | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/service-ia gate --couche 3a --unitaire "python tools/run_robot_tests.py --artefact service_ia --couche 3a --categorie 1" --integration "python tools/run_robot_tests.py --artefact service_ia --couche 3a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 3a` | à construire |
| 3b | 07:45, 16:15, vendredi 16:45 Londres ; priorités A09 | via 4 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/service-ia gate --couche 3b --unitaire "python tools/run_robot_tests.py --artefact service_ia --couche 3b --categorie 1" --integration "python tools/run_robot_tests.py --artefact service_ia --couche 3b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 3b` | à construire |
| 4 | worker unique, file bornée, heartbeat indépendant | A14 côté service de bout en bout sans API réelle | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/service-ia gate --couche 4 --unitaire "python tools/run_robot_tests.py --artefact service_ia --couche 4 --categorie 1" --integration "python tools/run_robot_tests.py --artefact service_ia --couche 4 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 4` | à construire |

## 10. Étape 8 — Checkpoints

- Tous les deux niveaux figés (`checkpoint_tous_les` = 2), signalés par `mcl.py statut`.

## 11. Gouvernance

- Profil : solo assisté par agent ; gardien de la carte et décideur des défigeages : l'utilisateur.
- Modification de contrat : défigeage tracé (`mcl.py defiger`) et ADR ; rayon via `mcl.py rayon`.

## 12. Bilan

- À compléter à la clôture de l'artefact (`mcl.py rapport`).

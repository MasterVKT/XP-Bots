# Plan MCL — contexte-ia

> Artefact de chair du composite `robot-ema-v3`. Plan maître : `docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md`, section 7.F ; registre d'interprétation : `mcl/robot-ema-v3/INTERPRETATIONS.md`. Aucun code avant la section 9.

## 0. Périmètre de l'artefact

- **Artefact** : `contexte-ia` (paquet `src/xpbots/contexte_ia/`) — Lecture du snapshot IA, cache persistant des vetos, décision BLOCK ou NEUTRAL (A07, A10, A12).
- **Échelle** : composant autonome ; **mode** : pur (chair du composite).
- **Règle de périmètre** : livré en phase(s) 7 du plan maître ; MCL ne gouverne que la construction du code de cet artefact.

## 1. Test d'applicabilité

| Question | Réponse | Justification |
|---|---|---|
| Structure connaissable ? | oui | Contrats normatifs A03, A07, A10, A12, A14 |
| Contrats stabilisables tôt ? | oui | Seuils figés dans `config/`, fonctions de référence |
| Construire pour comprendre ? | non | Aucune recherche de variante |

- **Verdict** : applicable.
- **Bénéfice dégradé** : frontières externes ipc-snapshot, stockage-etat doublées.
- **Signaux de mauvais domaine** : divergences répétées, défigeages en chaîne → suspendre et re-cartographier.

## 2. Étape 1 — Comprendre la cible

1. Finalité : Fournir au coordinateur, en mémoire et sans attente, un contexte IA BLOCK ou NEUTRAL par symbole et instant à partir du snapshot écrit par le service IA.
2. Entrées : fichier context_latest.json, état persisté (dernière séquence, cache des vetos), instant. Sorties : BLOCK ou NEUTRAL, jamais ALLOW ; identifiant du snapshot et des preuves pour C09.
3. Contraintes : Python 3.13, bibliothèque standard (sauf adaptateurs réels en infrastructure), valeurs normatives lues dans `config/`, instants en ms UTC, prix en `Decimal`, aucune horloge ni réseau hors infrastructure.
4. Projet neuf (greenfield).

Point d'insertion dans le squelette : segment « contexte IA neutre » du squelette (voir `mcl/robot-ema-v3/COUTURES.md`).

## 3. Étape 2 — Unités fonctionnelles

- 2.1 Entrées : fichier context_latest.json, état persisté (dernière séquence, cache des vetos), instant ; sorties : BLOCK ou NEUTRAL, jamais ALLOW ; identifiant du snapshot et des preuves pour C09.
- 2.2 Workflow : timer 1 s → lecture du fichier → validation → ajout des nouveaux vetos au cache → décision en mémoire au signal et avant l'ordre.

| Unité | Responsabilité | Entrée → sortie | Dépend de |
|---|---|---|---|
| `format_snapshot` | Définir le format canonique xp-ai-context-v1 et les paramètres de lecture du snapshot. | payload JSON → octets canoniques et SHA-256 identiques à reference.llm_contracts.digest | amont-noyau |
| `snapshot` | Valider un snapshot lu du fichier d'IPC. | octets du fichier (≤ 32 Kio), instant, dernière séquence persistée → snapshot accepté ou motif de rejet | format_snapshot, ipc-snapshot |
| `cache_vetos` | Conserver les vetos validés jusqu'à leur échéance propre, redémarrage compris. | snapshots acceptés → vetos actifs | snapshot, stockage-etat |
| `contexte` | Rendre BLOCK ou NEUTRAL pour un symbole et un instant, jamais ALLOW. | symbole, instant, bras PAPER_AB, mode → décision et identifiants de preuve | cache_vetos |

Question-test : « constructible et testable si rien d'autre n'existait ? »

| Unité | Réponse | A besoin de | Profondeur |
|---|---|---|---|
| `format_snapshot` | oui (feuille interne) | — | 0 |
| `snapshot` | non | format_snapshot | 1 |
| `cache_vetos` | non | snapshot | 2 |
| `contexte` | non | cache_vetos | 3 |

## 4. Étape 3 — Graphe de dépendances

- `format_snapshot` → amont-noyau
- `snapshot` → format_snapshot, ipc-snapshot
- `cache_vetos` → snapshot, stockage-etat
- `contexte` → cache_vetos

- **Contrôle de divergence** : `mcl.py analyser --ecrire` puis `analyser` (2026-11-05) : profondeurs proposées identiques aux profondeurs déclarées, zéro divergence.
- Regroupements retenus (unités indépendantes de même profondeur réunies dans une couche) : aucun.
- **Amont figé** (artefacts antérieurs, déclarés comme frontières autorisées partout) : amont-noyau.
- **Frontières externes** : ipc-snapshot, stockage-etat.
- **Cycles** : aucun entre unités ; la machine à états éventuelle est condensée dans une seule unité.

## 5. Étape 4 — Carte des couches

| Couche | Unités | Dépend de | Module |
|---|---|---|---|
| 0 — format-snapshot | `format_snapshot` | amont-noyau | `src/xpbots/contexte_ia/c0_format.py` |
| 1 — snapshot | `snapshot` | 0 | `src/xpbots/contexte_ia/c1_snapshot.py` |
| 2 — cache-vetos | `cache_vetos` | 1 | `src/xpbots/contexte_ia/c2_cache_vetos.py` |
| 3 — contexte | `contexte` | 2 | `src/xpbots/contexte_ia/c3_contexte.py` |

- **Groupes parallèles** : aucun (contrats finalisés ensemble, gates et gels séparés).

## 6. Encodage de la carte

- Outil : convention « une couche = un module nommé » + `mcl.py verifier --mode strict` en CI et revue de code (aucun outil d'architecture ajouté).
- Règle : dépendances autorisées vers toute couche plus interne, à profondeur quelconque.

## 7. Étape 5 — Contrats

- Esquisses : `mcl/contexte-ia/contrats/couche-<id>.md` (2026-11-05) ; finalisation couche par couche.

## 8. Étape 6 — Frontières externes

| Frontière | Imports réels | Couches autorisées | Doublure |
|---|---|---|---|
| ipc-snapshot | — (port du noyau) | aucune (port du noyau) | `tests/robot/doublures/` |
| stockage-etat | sqlite3 | aucune (port du noyau) | `tests/robot/doublures/` |

## 9. Étape 7 — Plan de construction

| Couche | Tests cat. 1 | Tests cat. 2 | Gate | Statut |
|---|---|---|---|---|
| 0 | JSON canonique, paramètres IA, empreinte d'intégration | — | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/contexte-ia gate --couche 0 --unitaire "python tools/run_robot_tests.py --artefact contexte_ia --couche 0 --categorie 1" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 0` | à construire |
| 1 | taille, doublons, hash, schéma, séquence en recul, futur, âge 90 s, événement mal formé ; concordance overlay_decision | via 2 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/contexte-ia gate --couche 1 --unitaire "python tools/run_robot_tests.py --artefact contexte_ia --couche 1 --categorie 1" --integration "python tools/run_robot_tests.py --artefact contexte_ia --couche 1 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1` | à construire |
| 2 | échéance propre, snapshot périmé sans révocation, reprise après redémarrage sans réinférence | via 3 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/contexte-ia gate --couche 2 --unitaire "python tools/run_robot_tests.py --artefact contexte_ia --couche 2 --categorie 1" --integration "python tools/run_robot_tests.py --artefact contexte_ia --couche 2 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 2` | à construire |
| 3 | BLOCK/NEUTRAL jamais ALLOW, bras A/B, réel sans validation financière = NEUTRAL, publication+900 s | avec moteur-ema et execution-coordinateur : insertion A07 (AI_CONTEXT_VETO, cooldown, aucun fill) | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/contexte-ia gate --couche 3 --unitaire "python tools/run_robot_tests.py --artefact contexte_ia --couche 3 --categorie 1" --integration "python tools/run_robot_tests.py --artefact contexte_ia --couche 3 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 3` | à construire |

## 10. Étape 8 — Checkpoints

- Tous les deux niveaux figés (`checkpoint_tous_les` = 2), signalés par `mcl.py statut`.

## 11. Gouvernance

- Profil : solo assisté par agent ; gardien de la carte et décideur des défigeages : l'utilisateur.
- Modification de contrat : défigeage tracé (`mcl.py defiger`) et ADR ; rayon via `mcl.py rayon`.

## 12. Bilan

- À compléter à la clôture de l'artefact (`mcl.py rapport`).

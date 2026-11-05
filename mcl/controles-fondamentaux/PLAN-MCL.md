# Plan MCL — controles-fondamentaux

> Artefact de chair du composite `robot-ema-v3`. Plan maître : `docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md`, section 7.E ; registre d'interprétation : `mcl/robot-ema-v3/INTERPRETATIONS.md`. Aucun code avant la section 9.

## 0. Périmètre de l'artefact

- **Artefact** : `controles-fondamentaux` (paquet `src/xpbots/fondamental/`) — Contrat C05 : permissions fondamentales externes et garde d'annonces HIGH.
- **Échelle** : composant autonome ; **mode** : pur (chair du composite).
- **Règle de périmètre** : livré en phase(s) 6 du plan maître ; MCL ne gouverne que la construction du code de cet artefact.

## 1. Test d'applicabilité

| Question | Réponse | Justification |
|---|---|---|
| Structure connaissable ? | oui | Contrats normatifs C05, C08 point 2, C11.8, C11.9 |
| Contrats stabilisables tôt ? | oui | Seuils figés dans `config/`, fonctions de référence |
| Construire pour comprendre ? | non | Aucune recherche de variante |

- **Verdict** : applicable.
- **Bénéfice dégradé** : frontières externes stockage-etat, source-permissions, source-calendrier doublées.
- **Signaux de mauvais domaine** : divergences répétées, défigeages en chaîne → suspendre et re-cartographier.

## 2. Étape 1 — Comprendre la cible

1. Finalité : Dire, pour un symbole, un sens et un instant, si une nouvelle entrée est autorisée par le module fondamental externe et le calendrier, et produire les sorties FLATTEN et d'annonce.
2. Entrées : messages fundamental-permission-v1 avec heure de réception, versions de calendrier avec known_at. Sorties : Autorisation(direction) ou refus FUNDAMENTAL_INVALID, FUNDAMENTAL_DIRECTION, NEWS_WINDOW ; demandes de sortie.
3. Contraintes : Python 3.13, bibliothèque standard (sauf adaptateurs réels en infrastructure), valeurs normatives lues dans `config/`, instants en ms UTC, prix en `Decimal`, aucune horloge ni réseau hors infrastructure.
4. Projet neuf (greenfield).

Point d'insertion dans le squelette : segment « fondamental absent » du squelette (refus FUNDAMENTAL_INVALID ou scénario nommé TECHNICAL_CONTROL_NEUTRAL) (voir `mcl/robot-ema-v3/COUTURES.md`).

## 3. Étape 2 — Unités fonctionnelles

- 2.1 Entrées : messages fundamental-permission-v1 avec heure de réception, versions de calendrier avec known_at ; sorties : Autorisation(direction) ou refus FUNDAMENTAL_INVALID, FUNDAMENTAL_DIRECTION, NEWS_WINDOW ; demandes de sortie.
- 2.2 Workflow : réception → validation du message → état par symbole → contrôle du calendrier → combinaison → autorisation ou refus ; sorties FLATTEN et N−900 s.

| Unité | Responsabilité | Entrée → sortie | Dépend de |
|---|---|---|---|
| `types_fondamentaux` | Représenter messages de permission, événements et versions de calendrier et la table devises par symbole. | JSON strict ; paramètres news_* et fundamental_* → objets immuables | amont-noyau, amont-donnees-temps |
| `message_permission` | Valider un message fundamental-permission-v1 et ses heures. | texte JSON reçu et instant de réception locale → message valide ou motif d'invalidité | types_fondamentaux |
| `garde_annonces` | Contrôler fraîcheur et couverture du calendrier et les fenêtres HIGH par devise. | versions de calendrier connues à l'instant → verdict et demandes de clôture à N−900 s | types_fondamentaux, source-calendrier |
| `etat_permissions` | Conserver la dernière permission valide par symbole avec séquence, expiration et heartbeat. | messages validés → permission courante ; événements de heartbeat manqué | message_permission, stockage-etat, source-permissions |
| `permissions` | Combiner direction, état de risque et annonces en autorisation ou motif de refus. | symbole, sens, instant → autorisation ou FUNDAMENTAL_INVALID, FUNDAMENTAL_DIRECTION, NEWS_WINDOW ; demandes FLATTEN et annonce | etat_permissions, garde_annonces |

Question-test : « constructible et testable si rien d'autre n'existait ? »

| Unité | Réponse | A besoin de | Profondeur |
|---|---|---|---|
| `types_fondamentaux` | oui (feuille interne) | — | 0 |
| `message_permission` | non | types_fondamentaux | 1 |
| `garde_annonces` | non | types_fondamentaux | 1 |
| `etat_permissions` | non | message_permission | 2 |
| `permissions` | non | etat_permissions, garde_annonces | 3 |

## 4. Étape 3 — Graphe de dépendances

- `types_fondamentaux` → amont-noyau, amont-donnees-temps
- `message_permission` → types_fondamentaux
- `garde_annonces` → types_fondamentaux, source-calendrier
- `etat_permissions` → message_permission, stockage-etat, source-permissions
- `permissions` → etat_permissions, garde_annonces

- **Contrôle de divergence** : `mcl.py analyser --ecrire` puis `analyser` (2026-11-05) : profondeurs proposées identiques aux profondeurs déclarées, zéro divergence.
- Regroupements retenus (unités indépendantes de même profondeur réunies dans une couche) : aucun.
- **Amont figé** (artefacts antérieurs, déclarés comme frontières autorisées partout) : amont-noyau, amont-donnees-temps.
- **Frontières externes** : stockage-etat, source-permissions, source-calendrier.
- **Cycles** : aucun entre unités ; la machine à états éventuelle est condensée dans une seule unité.

## 5. Étape 4 — Carte des couches

| Couche | Unités | Dépend de | Module |
|---|---|---|---|
| 0 — types-fondamentaux | `types_fondamentaux` | amont-donnees-temps, amont-noyau | `src/xpbots/fondamental/c0_types.py` |
| 1a — message-permission | `message_permission` | 0 | `src/xpbots/fondamental/c1a_message.py` |
| 1b — garde-annonces | `garde_annonces` | 0 | `src/xpbots/fondamental/c1b_annonces.py` |
| 2 — etat-permissions | `etat_permissions` | 1a | `src/xpbots/fondamental/c2_etat_permissions.py` |
| 3 — permissions | `permissions` | 1b, 2 | `src/xpbots/fondamental/c3_permissions.py` |

- **Groupes parallèles** : 1a, 1b (contrats finalisés ensemble, gates et gels séparés).

## 6. Encodage de la carte

- Outil : convention « une couche = un module nommé » + `mcl.py verifier --mode strict` en CI et revue de code (aucun outil d'architecture ajouté).
- Règle : dépendances autorisées vers toute couche plus interne, à profondeur quelconque.

## 7. Étape 5 — Contrats

- Esquisses : `mcl/controles-fondamentaux/contrats/couche-<id>.md` (2026-11-05) ; finalisation couche par couche.

## 8. Étape 6 — Frontières externes

| Frontière | Imports réels | Couches autorisées | Doublure |
|---|---|---|---|
| stockage-etat | sqlite3 | aucune (port du noyau) | `tests/robot/doublures/` |
| source-permissions | — (port du noyau) | aucune (port du noyau) | `tests/robot/doublures/` |
| source-calendrier | — (port du noyau) | aucune (port du noyau) | `tests/robot/doublures/` |

## 9. Étape 7 — Plan de construction

| Couche | Tests cat. 1 | Tests cat. 2 | Gate | Statut |
|---|---|---|---|---|
| 0 | schéma, énumérations, table devises par symbole (R10) | — | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/controles-fondamentaux gate --couche 0 --unitaire "python tools/run_robot_tests.py --artefact fondamental --couche 0 --categorie 1" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 0` | à construire |
| 1a | ordre des heures, durée ≤ 900 s, futur refusé, réception ≥ known_at (C11.8) | via 2 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/controles-fondamentaux gate --couche 1a --unitaire "python tools/run_robot_tests.py --artefact fondamental --couche 1a --categorie 1" --integration "python tools/run_robot_tests.py --artefact fondamental --couche 1a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1a` | à construire |
| 1b | [N−900, N+900) début inclus fin exclue, fraîcheur 86 400 s, couverture 172 800 s, annonce tardive, calendrier révisé sans réécriture (C11.9) | via 3 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/controles-fondamentaux gate --couche 1b --unitaire "python tools/run_robot_tests.py --artefact fondamental --couche 1b --categorie 1" --integration "python tools/run_robot_tests.py --artefact fondamental --couche 1b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1b` | à construire |
| 2 | séquence strictement croissante, expiration, heartbeat 60 s, persistance | via 3 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/controles-fondamentaux gate --couche 2 --unitaire "python tools/run_robot_tests.py --artefact fondamental --couche 2 --categorie 1" --integration "python tools/run_robot_tests.py --artefact fondamental --couche 2 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 2` | à construire |
| 3 | direction incompatible, NO_NEW, FLATTEN, TECHNICAL_CONTROL_NEUTRAL seulement nommé | avec execution-coordinateur : FLATTEN prioritaire, contrôle au signal puis avant l'ordre | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/controles-fondamentaux gate --couche 3 --unitaire "python tools/run_robot_tests.py --artefact fondamental --couche 3 --categorie 1" --integration "python tools/run_robot_tests.py --artefact fondamental --couche 3 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 3` | à construire |

## 10. Étape 8 — Checkpoints

- Tous les deux niveaux figés (`checkpoint_tous_les` = 2), signalés par `mcl.py statut`.

## 11. Gouvernance

- Profil : solo assisté par agent ; gardien de la carte et décideur des défigeages : l'utilisateur.
- Modification de contrat : défigeage tracé (`mcl.py defiger`) et ADR ; rayon via `mcl.py rayon`.

## 12. Bilan

- À compléter à la clôture de l'artefact (`mcl.py rapport`).

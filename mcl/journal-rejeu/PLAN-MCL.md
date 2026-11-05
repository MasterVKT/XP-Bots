# Plan MCL — journal-rejeu

> Artefact de chair du composite `robot-ema-v3`. Plan maître : `docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md`, section 7.H ; registre d'interprétation : `mcl/robot-ema-v3/INTERPRETATIONS.md`. Aucun code avant la section 9.

## 0. Périmètre de l'artefact

- **Artefact** : `journal-rejeu` (paquet `src/xpbots/journal_rejeu/`) — Journal C09, simulateur d'exécution de référence et de stress, rejeu, métriques, bootstrap, PAPER_AB.
- **Échelle** : composant autonome ; **mode** : pur (chair du composite).
- **Règle de périmètre** : livré en phase(s) 8 du plan maître ; MCL ne gouverne que la construction du code de cet artefact.

## 1. Test d'applicabilité

| Question | Réponse | Justification |
|---|---|---|
| Structure connaissable ? | oui | Contrats normatifs C09, C10, C11.12, C11.14, A13, A14 |
| Contrats stabilisables tôt ? | oui | Seuils figés dans `config/`, fonctions de référence |
| Construire pour comprendre ? | non | Aucune recherche de variante |

- **Verdict** : applicable.
- **Bénéfice dégradé** : frontières externes journal-persistant, ticks-historiques doublées.
- **Signaux de mauvais domaine** : divergences répétées, défigeages en chaîne → suspendre et re-cartographier.

## 2. Étape 1 — Comprendre la cible

1. Finalité : Rejouer causalement des ticks à travers le même moteur de décision et produire journaux, métriques et incertitudes selon C10 et A13.
2. Entrées : ticks historiques et manifeste, profils, permissions et calendriers historiques, réponses IA archivées, scénarios nommés. Sorties : journaux C09, résultats par bloc et en continu, métriques, intervalles bootstrap, rapports A/B.
3. Contraintes : Python 3.13, bibliothèque standard (sauf adaptateurs réels en infrastructure), valeurs normatives lues dans `config/`, instants en ms UTC, prix en `Decimal`, aucune horloge ni réseau hors infrastructure.
4. Projet neuf (greenfield).

Point d'insertion dans le squelette : exécution papier minimale du squelette (pour le rejeu) (voir `mcl/robot-ema-v3/COUTURES.md`).

## 3. Étape 2 — Unités fonctionnelles

- 2.1 Entrées : ticks historiques et manifeste, profils, permissions et calendriers historiques, réponses IA archivées, scénarios nommés ; sorties : journaux C09, résultats par bloc et en continu, métriques, intervalles bootstrap, rapports A/B.
- 2.2 Workflow : import et manifeste → horloge rejouée → ticks au coordinateur → simulateur d'exécution → journal → métriques → bootstrap → rapport.

| Unité | Responsabilité | Entrée → sortie | Dépend de |
|---|---|---|---|
| `types_rejeu` | Représenter scénarios, blocs de dates C10 et manifestes de données. | paramètres de C10 et de l'export IA → objets immuables | amont-noyau |
| `journal` | Valider et sérialiser les enregistrements C09. | enregistrements du noyau → lignes JSON canoniques en ajout seul | types_rejeu, journal-persistant |
| `simulateur_execution` | Simuler les exécutions de référence et de stress à partir des ticks (port Courtier). | ordres protégés, ticks, scénario → accusés, fills, sorties SL/TP et marché causales | types_rejeu, amont-execution |
| `import_ticks` | Lire les ticks historiques et leur manifeste de couverture. | fichiers CSV/CSV.gz du cahier de données et manifeste → ticks ordonnés et couverture déclarée | types_rejeu, ticks-historiques |
| `metriques` | Calculer les métriques de C09, C10 et A13 depuis le journal. | journal d'un rejeu → effectifs, espérance, PF, drawdown, fréquence, rétention | journal |
| `rejeu` | Rejouer causalement des ticks à travers le coordinateur et le simulateur. | fabrique fournie par l'application, ticks, scénario, bloc → journal et état final | simulateur_execution, import_ticks, journal, amont-donnees-temps |
| `bootstrap` | Estimer l'incertitude par bootstrap de blocs de cinq jours de marché. | P&L nets et trades par jour de sortie → percentiles 2,5/97,5 et réplications invalides | metriques |
| `paper_ab` | Rejouer deux portefeuilles indépendants référence et veto IA. | mêmes ticks, coûts et permissions → deux journaux et métriques comparées | rejeu, metriques |
| `rapport_validation` | Assembler les rapports de validation C10 et A13. | résultats de rejeu → rapport sous .local/reports/ sans secret ni numéro de compte | bootstrap, paper_ab |

Question-test : « constructible et testable si rien d'autre n'existait ? »

| Unité | Réponse | A besoin de | Profondeur |
|---|---|---|---|
| `types_rejeu` | oui (feuille interne) | — | 0 |
| `journal` | non | types_rejeu | 1 |
| `simulateur_execution` | non | types_rejeu | 1 |
| `import_ticks` | non | types_rejeu | 1 |
| `metriques` | non | journal | 2 |
| `rejeu` | non | simulateur_execution, import_ticks, journal | 2 |
| `bootstrap` | non | metriques | 3 |
| `paper_ab` | non | rejeu, metriques | 3 |
| `rapport_validation` | non | bootstrap, paper_ab | 4 |

## 4. Étape 3 — Graphe de dépendances

- `types_rejeu` → amont-noyau
- `journal` → types_rejeu, journal-persistant
- `simulateur_execution` → types_rejeu, amont-execution
- `import_ticks` → types_rejeu, ticks-historiques
- `metriques` → journal
- `rejeu` → simulateur_execution, import_ticks, journal, amont-donnees-temps
- `bootstrap` → metriques
- `paper_ab` → rejeu, metriques
- `rapport_validation` → bootstrap, paper_ab

- **Contrôle de divergence** : `mcl.py analyser --ecrire` puis `analyser` (2026-11-05) : profondeurs proposées identiques aux profondeurs déclarées, zéro divergence.
- Regroupements retenus (unités indépendantes de même profondeur réunies dans une couche) : aucun.
- **Amont figé** (artefacts antérieurs, déclarés comme frontières autorisées partout) : amont-noyau, amont-donnees-temps, amont-execution.
- **Frontières externes** : journal-persistant, ticks-historiques.
- **Cycles** : aucun entre unités ; la machine à états éventuelle est condensée dans une seule unité.

## 5. Étape 4 — Carte des couches

| Couche | Unités | Dépend de | Module |
|---|---|---|---|
| 0 — types-rejeu | `types_rejeu` | amont-noyau | `src/xpbots/journal_rejeu/c0_types.py` |
| 1a — journal | `journal` | 0 | `src/xpbots/journal_rejeu/c1a_journal.py` |
| 1b — simulateur | `simulateur_execution` | 0, amont-execution | `src/xpbots/journal_rejeu/c1b_simulateur.py` |
| 1c — import-ticks | `import_ticks` | 0 | `src/xpbots/journal_rejeu/c1c_import_ticks.py` |
| 2a — metriques | `metriques` | 1a | `src/xpbots/journal_rejeu/c2a_metriques.py` |
| 2b — rejeu | `rejeu` | 1a, 1b, 1c, amont-donnees-temps | `src/xpbots/journal_rejeu/c2b_rejeu.py` |
| 3a — bootstrap | `bootstrap` | 2a | `src/xpbots/journal_rejeu/c3a_bootstrap.py` |
| 3b — paper-ab | `paper_ab` | 2a, 2b | `src/xpbots/journal_rejeu/c3b_paper_ab.py` |
| 4 — rapport | `rapport_validation` | 3a, 3b | `src/xpbots/journal_rejeu/c4_rapport.py` |

- **Groupes parallèles** : 1a, 1b, 1c; 2a, 2b; 3a, 3b (contrats finalisés ensemble, gates et gels séparés).

## 6. Encodage de la carte

- Outil : convention « une couche = un module nommé » + `mcl.py verifier --mode strict` en CI et revue de code (aucun outil d'architecture ajouté).
- Règle : dépendances autorisées vers toute couche plus interne, à profondeur quelconque.

## 7. Étape 5 — Contrats

- Esquisses : `mcl/journal-rejeu/contrats/couche-<id>.md` (2026-11-05) ; finalisation couche par couche.

## 8. Étape 6 — Frontières externes

| Frontière | Imports réels | Couches autorisées | Doublure |
|---|---|---|---|
| journal-persistant | — (port du noyau) | aucune (port du noyau) | `tests/robot/doublures/` |
| ticks-historiques | — (port du noyau) | aucune (port du noyau) | `tests/robot/doublures/` |

## 9. Étape 7 — Plan de construction

| Couche | Tests cat. 1 | Tests cat. 2 | Gate | Statut |
|---|---|---|---|---|
| 0 | scénarios référence, stress, perturbations nommées (R16), blocs C10, manifeste | — | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/journal-rejeu gate --couche 0 --unitaire "python tools/run_robot_tests.py --artefact journal_rejeu --couche 0 --categorie 1" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 0` | à construire |
| 1a | champs C09 complets, sérialisation stable, aucun secret | via 2 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/journal-rejeu gate --couche 1a --unitaire "python tools/run_robot_tests.py --artefact journal_rejeu --couche 1a --categorie 1" --integration "python tools/run_robot_tests.py --artefact journal_rejeu --couche 1a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1a` | à construire |
| 1b | délai 250 ms et un tick adverse (R9), stress 1,25 × spread, 1 000 ms, deux ticks ; TP au niveau ; gaps ; SL et TP à la même milliseconde (C11.12) | via 2b | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/journal-rejeu gate --couche 1b --unitaire "python tools/run_robot_tests.py --artefact journal_rejeu --couche 1b --categorie 1" --integration "python tools/run_robot_tests.py --artefact journal_rejeu --couche 1b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1b` | à construire |
| 1c | format du cahier de données, ordre stable, empreintes, refus sans manifeste (R5) | via 2b | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/journal-rejeu gate --couche 1c --unitaire "python tools/run_robot_tests.py --artefact journal_rejeu --couche 1c --categorie 1" --integration "python tools/run_robot_tests.py --artefact journal_rejeu --couche 1c --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1c` | à construire |
| 2a | espérance, PF, drawdown de fonds propres, fréquence avec jours à zéro, rétention N/A et < 50 | via 3 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/journal-rejeu gate --couche 2a --unitaire "python tools/run_robot_tests.py --artefact journal_rejeu --couche 2a --categorie 1" --integration "python tools/run_robot_tests.py --artefact journal_rejeu --couche 2a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 2a` | à construire |
| 2b | blocs C10 à 100 USD, arrêts non réinitialisés, rejeu continu | C11.14 : journal de décision identique entre rejeu et boucle paper alimentée par les mêmes ticks | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/journal-rejeu gate --couche 2b --unitaire "python tools/run_robot_tests.py --artefact journal_rejeu --couche 2b --categorie 1" --integration "python tools/run_robot_tests.py --artefact journal_rejeu --couche 2b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 2b` | à construire |
| 3a | blocs de 5 jours, 10 000 réplications, graine 20261104, percentiles 2,5/97,5 | via 4 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/journal-rejeu gate --couche 3a --unitaire "python tools/run_robot_tests.py --artefact journal_rejeu --couche 3a --categorie 1" --integration "python tools/run_robot_tests.py --artefact journal_rejeu --couche 3a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 3a` | à construire |
| 3b | deux portefeuilles indépendants à 100 USD, coût IA déduit une fois | A14 comptes A/B séparés | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/journal-rejeu gate --couche 3b --unitaire "python tools/run_robot_tests.py --artefact journal_rejeu --couche 3b --categorie 1" --integration "python tools/run_robot_tests.py --artefact journal_rejeu --couche 3b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 3b` | à construire |
| 4 | précision JSON jamais présentée comme taux de réussite | rapport complet d'un rejeu synthétique | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/journal-rejeu gate --couche 4 --unitaire "python tools/run_robot_tests.py --artefact journal_rejeu --couche 4 --categorie 1" --integration "python tools/run_robot_tests.py --artefact journal_rejeu --couche 4 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 4` | à construire |

## 10. Étape 8 — Checkpoints

- Tous les deux niveaux figés (`checkpoint_tous_les` = 2), signalés par `mcl.py statut`.

## 11. Gouvernance

- Profil : solo assisté par agent ; gardien de la carte et décideur des défigeages : l'utilisateur.
- Modification de contrat : défigeage tracé (`mcl.py defiger`) et ADR ; rayon via `mcl.py rayon`.

## 12. Bilan

- À compléter à la clôture de l'artefact (`mcl.py rapport`).

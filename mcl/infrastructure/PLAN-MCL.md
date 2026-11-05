# Plan MCL — infrastructure

> Artefact de chair du composite `robot-ema-v3`. Plan maître : `docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md`, section 7.I ; registre d'interprétation : `mcl/robot-ema-v3/INTERPRETATIONS.md`. Aucun code avant la section 9.

## 0. Périmètre de l'artefact

- **Artefact** : `infrastructure` (paquet `src/xpbots/infrastructure/`) — Adaptateurs réels des frontières externes : fichiers, horloge, SQLite, MT5, HTTP.
- **Échelle** : composant autonome ; **mode** : pur (chair du composite).
- **Règle de périmètre** : livré en phase(s) 9 et 10 du plan maître ; MCL ne gouverne que la construction du code de cet artefact.

## 1. Test d'applicabilité

| Question | Réponse | Justification |
|---|---|---|
| Structure connaissable ? | oui | Contrats normatifs C04, C08 (rapprochement, redémarrage), A04, A08, A10 |
| Contrats stabilisables tôt ? | oui | Seuils figés dans `config/`, fonctions de référence |
| Construire pour comprendre ? | non | Aucune recherche de variante |

- **Verdict** : applicable.
- **Bénéfice dégradé** : frontières externes metatrader5, sqlite, reseau, horloge-os, systeme-fichiers doublées.
- **Signaux de mauvais domaine** : divergences répétées, défigeages en chaîne → suspendre et re-cartographier.

## 2. Étape 1 — Comprendre la cible

1. Finalité : Implémenter les ports du noyau et des artefacts sur les vraies ressources : terminal MT5, fichiers, SQLite, horloge système et HTTPS.
2. Entrées : terminal MT5 connecté (Windows), système de fichiers, bases SQLite, réseau HTTPS. Sorties : implémentations réelles des ports et fiche de qualification C04.
3. Contraintes : Python 3.13, bibliothèque standard (sauf adaptateurs réels en infrastructure), valeurs normatives lues dans `config/`, instants en ms UTC, prix en `Decimal`, aucune horloge ni réseau hors infrastructure.
4. Projet neuf (greenfield).

Point d'insertion dans le squelette : lecteur de fixture et écrivain JSONL minimaux du squelette (voir `mcl/robot-ema-v3/COUTURES.md`).

## 3. Étape 2 — Unités fonctionnelles

- 2.1 Entrées : terminal MT5 connecté (Windows), système de fichiers, bases SQLite, réseau HTTPS ; sorties : implémentations réelles des ports et fiche de qualification C04.
- 2.2 Workflow : connexion → lecture des caractéristiques → flux de ticks → ordres et rapprochement ; fichiers et SQLite pour l'état, le journal, l'IPC et les sources externes.

| Unité | Responsabilité | Entrée → sortie | Dépend de |
|---|---|---|---|
| `horloge_systeme` | Fournir l'instant UTC en millisecondes du système. | — → instant UTC ms | amont-noyau, horloge-os |
| `journal_fichier` | Écrire le journal C09 en JSONL par ajout avec fsync. | lignes canoniques → fichier en ajout seul | amont-journal-rejeu, systeme-fichiers |
| `ipc_snapshot_fichier` | Lire le fichier de snapshot IA et le fermer immédiatement. | chemin commondata ou XPBOTS_COMMON_FILES_DIR → octets ≤ 32 Kio ou absence | amont-contexte-ia, systeme-fichiers |
| `ticks_historiques_fichiers` | Lire les fichiers de ticks historiques et leur manifeste. | CSV/CSV.gz du cahier de données → lignes brutes et empreintes | amont-journal-rejeu, systeme-fichiers |
| `sources_fondamentales_fichiers` | Lire les permissions et calendriers déposés par le module fondamental (R12, R13). | dossiers configurés → messages et versions avec heure de réception | amont-fondamental, systeme-fichiers |
| `stockage_sqlite` | Stocker l'état du robot de façon transactionnelle. | chemin sous runtime/ → état durable | amont-noyau, sqlite |
| `connexion_mt5` | Ouvrir et contrôler la connexion au terminal MT5. | terminal installé, compte démo → informations terminal et compte sans secret journalisé | metatrader5, amont-noyau |
| `transport_http` | Envoyer des requêtes HTTPS bornées. | requête HTTPS, délai, taille maximale → réponse ou erreur typée | reseau, amont-service-ia |
| `stockage_service_ia` | Stocker textes, travaux, résultats, budget et snapshots du service IA. | chemin sous runtime/ → persistance A10 avec FTS5 | sqlite, amont-service-ia |
| `flux_ticks_mt5` | Lire les ticks MT5 et la couverture du flux. | symbole courtier, instant ms → ticks UTC ordonnés (R14) | connexion_mt5, metatrader5 |
| `calcul_courtier_mt5` | Exposer les calculs et caractéristiques natifs du courtier. | ordre hypothétique, symbole → valeurs natives en Decimal | connexion_mt5, amont-execution, metatrader5 |
| `courtier_mt5` | Envoyer les ordres protégés et rapprocher positions et transactions. | ordre protégé avec magic et empreinte de clé → réponses natives normalisées | connexion_mt5, amont-execution, metatrader5 |
| `collecteur_rss` | Collecter les flux RSS officiels de façon conditionnelle. | flux Fed, BCE, BoE configurés → textes bruts datés | transport_http |
| `clients_llm` | Appeler les API Groq, Gemini et OpenAI facultative selon A08. | requête construite par le service → réponse brute et usage | transport_http |
| `qualification_c04` | Établir la fiche d'environnement C04 et la faisabilité du volume minimal. | terminal démo connecté → fiche horodatée sous .local/reports/ sans numéro de compte | calcul_courtier_mt5, flux_ticks_mt5, amont-execution |

Question-test : « constructible et testable si rien d'autre n'existait ? »

| Unité | Réponse | A besoin de | Profondeur |
|---|---|---|---|
| `horloge_systeme` | oui (feuille interne) | — | 0 |
| `journal_fichier` | oui (feuille interne) | — | 0 |
| `ipc_snapshot_fichier` | oui (feuille interne) | — | 0 |
| `ticks_historiques_fichiers` | oui (feuille interne) | — | 0 |
| `sources_fondamentales_fichiers` | oui (feuille interne) | — | 0 |
| `stockage_sqlite` | oui (feuille interne) | — | 0 |
| `connexion_mt5` | oui (feuille interne) | — | 0 |
| `transport_http` | oui (feuille interne) | — | 0 |
| `stockage_service_ia` | oui (feuille interne) | — | 0 |
| `flux_ticks_mt5` | non | connexion_mt5 | 1 |
| `calcul_courtier_mt5` | non | connexion_mt5 | 1 |
| `courtier_mt5` | non | connexion_mt5 | 1 |
| `collecteur_rss` | non | transport_http | 1 |
| `clients_llm` | non | transport_http | 1 |
| `qualification_c04` | non | calcul_courtier_mt5, flux_ticks_mt5 | 2 |

## 4. Étape 3 — Graphe de dépendances

- `horloge_systeme` → amont-noyau, horloge-os
- `journal_fichier` → amont-journal-rejeu, systeme-fichiers
- `ipc_snapshot_fichier` → amont-contexte-ia, systeme-fichiers
- `ticks_historiques_fichiers` → amont-journal-rejeu, systeme-fichiers
- `sources_fondamentales_fichiers` → amont-fondamental, systeme-fichiers
- `stockage_sqlite` → amont-noyau, sqlite
- `connexion_mt5` → metatrader5, amont-noyau
- `transport_http` → reseau, amont-service-ia
- `stockage_service_ia` → sqlite, amont-service-ia
- `flux_ticks_mt5` → connexion_mt5, metatrader5
- `calcul_courtier_mt5` → connexion_mt5, amont-execution, metatrader5
- `courtier_mt5` → connexion_mt5, amont-execution, metatrader5
- `collecteur_rss` → transport_http
- `clients_llm` → transport_http
- `qualification_c04` → calcul_courtier_mt5, flux_ticks_mt5, amont-execution

- **Contrôle de divergence** : `mcl.py analyser --ecrire` puis `analyser` (2026-11-05) : profondeurs proposées identiques aux profondeurs déclarées, zéro divergence.
- Regroupements retenus (unités indépendantes de même profondeur réunies dans une couche) : `journal_fichier` : proposé `0b`, retenu `0a`; `ipc_snapshot_fichier` : proposé `0c`, retenu `0a`; `ticks_historiques_fichiers` : proposé `0d`, retenu `0a`; `sources_fondamentales_fichiers` : proposé `0e`, retenu `0a`; `stockage_sqlite` : proposé `0f`, retenu `0b`; `connexion_mt5` : proposé `0g`, retenu `0c`; `transport_http` : proposé `0h`, retenu `0d`; `stockage_service_ia` : proposé `0i`, retenu `0e`; `calcul_courtier_mt5` : proposé `1b`, retenu `1a`; `courtier_mt5` : proposé `1c`, retenu `1a`; `collecteur_rss` : proposé `1d`, retenu `1b`; `clients_llm` : proposé `1e`, retenu `1b`.
- **Amont figé** (artefacts antérieurs, déclarés comme frontières autorisées partout) : amont-noyau, amont-donnees-temps, amont-execution, amont-fondamental, amont-contexte-ia, amont-journal-rejeu, amont-service-ia.
- **Frontières externes** : metatrader5, sqlite, reseau, horloge-os, systeme-fichiers.
- **Cycles** : aucun entre unités ; la machine à états éventuelle est condensée dans une seule unité.
- **Racines multiples** (alerte de `mcl.py analyser`, attendue) : l'infrastructure est un ensemble d'adaptateurs indépendants ; son enveloppe est la couche `app` du composite, qui les câble.

## 5. Étape 4 — Carte des couches

| Couche | Unités | Dépend de | Module |
|---|---|---|---|
| 0a — fichiers-et-horloge | `horloge_systeme`, `journal_fichier`, `ipc_snapshot_fichier`, `ticks_historiques_fichiers`, `sources_fondamentales_fichiers` | amont-contexte-ia, amont-fondamental, amont-journal-rejeu, amont-noyau | `src/xpbots/infrastructure/fichiers` |
| 0b — sqlite-robot | `stockage_sqlite` | amont-noyau | `src/xpbots/infrastructure/sqlite_robot` |
| 0c — mt5-connexion | `connexion_mt5` | amont-noyau | `src/xpbots/infrastructure/mt5/connexion.py` |
| 0d — http | `transport_http` | amont-service-ia | `src/xpbots/infrastructure/http` |
| 0e — sqlite-ia | `stockage_service_ia` | amont-service-ia | `src/xpbots/infrastructure/sqlite_ia` |
| 1a — mt5-adaptateurs | `flux_ticks_mt5`, `calcul_courtier_mt5`, `courtier_mt5` | 0c, amont-execution | `src/xpbots/infrastructure/mt5/adaptateurs.py` |
| 1b — ia-adaptateurs | `collecteur_rss`, `clients_llm` | 0d | `src/xpbots/infrastructure/ia_adaptateurs.py` |
| 2 — qualification-c04 | `qualification_c04` | 1a, amont-execution | `src/xpbots/infrastructure/mt5/qualification_c04.py` |

- **Groupes parallèles** : 0a, 0b, 0c, 0d, 0e; 1a, 1b (contrats finalisés ensemble, gates et gels séparés).

## 6. Encodage de la carte

- Outil : convention « une couche = un module nommé » + `mcl.py verifier --mode strict` en CI et revue de code (aucun outil d'architecture ajouté).
- Règle : dépendances autorisées vers toute couche plus interne, à profondeur quelconque.

## 7. Étape 5 — Contrats

- Esquisses : `mcl/infrastructure/contrats/couche-<id>.md` (2026-11-05) ; finalisation couche par couche.

## 8. Étape 6 — Frontières externes

| Frontière | Imports réels | Couches autorisées | Doublure |
|---|---|---|---|
| metatrader5 | MetaTrader5 | 0c, 1a | `tests/robot/doublures/` |
| sqlite | sqlite3 | 0b, 0e | `tests/robot/doublures/` |
| reseau | urllib, http, ssl, socket | 0d | `tests/robot/doublures/` |
| horloge-os | time | 0a | `tests/robot/doublures/` |
| systeme-fichiers | — (port du noyau) | aucune (port du noyau) | `tests/robot/doublures/` |

## 9. Étape 7 — Plan de construction

| Couche | Tests cat. 1 | Tests cat. 2 | Gate | Statut |
|---|---|---|---|---|
| 0a | remplacement atomique, fsync, fermeture immédiate, horloge UTC ms | contrats de port communs | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/infrastructure gate --couche 0a --unitaire "python tools/run_robot_tests.py --artefact infrastructure --couche 0a --categorie 1" --integration "python tools/run_robot_tests.py --artefact infrastructure --couche 0a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 0a` | à construire |
| 0b | BEGIN IMMEDIATE, atomicité, reprise | contrats de port | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/infrastructure gate --couche 0b --unitaire "python tools/run_robot_tests.py --artefact infrastructure --couche 0b --categorie 1" --integration "python tools/run_robot_tests.py --artefact infrastructure --couche 0b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 0b` | à construire |
| 0c | initialisation et terminal_info sur doublure | contrat MT5 démo manuel | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/infrastructure gate --couche 0c --unitaire "python tools/run_robot_tests.py --artefact infrastructure --couche 0c --categorie 1" --integration "python tools/run_robot_tests.py --artefact infrastructure --couche 0c --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 0c` | à construire |
| 0d | HTTPS seul, délais, taille maximale, redirections bornées | transport factice | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/infrastructure gate --couche 0d --unitaire "python tools/run_robot_tests.py --artefact infrastructure --couche 0d --categorie 1" --integration "python tools/run_robot_tests.py --artefact infrastructure --couche 0d --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 0d` | à construire |
| 0e | tables A10, FTS5, transaction du budget | concurrence | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/infrastructure gate --couche 0e --unitaire "python tools/run_robot_tests.py --artefact infrastructure --couche 0e --categorie 1" --integration "python tools/run_robot_tests.py --artefact infrastructure --couche 0e --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 0e` | à construire |
| 1a | même suite de contrats que les doublures (flux, calculs, courtier) | --contrat-mt5-demo sur le poste Windows | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/infrastructure gate --couche 1a --unitaire "python tools/run_robot_tests.py --artefact infrastructure --couche 1a --categorie 1" --integration "python tools/run_robot_tests.py --artefact infrastructure --couche 1a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1a` | à construire |
| 1b | RSS conditionnel, clients Groq/Gemini/OpenAI factices | conformité manuelle avec les clés de l'utilisateur | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/infrastructure gate --couche 1b --unitaire "python tools/run_robot_tests.py --artefact infrastructure --couche 1b --categorie 1" --integration "python tools/run_robot_tests.py --artefact infrastructure --couche 1b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1b` | à construire |
| 2 | fiche complète ou ENVIRONMENT_NOT_READY ; faisabilité à 0,5 % ; liaison d'un symbole ; heure des ticks (R14) | qualification réelle sur compte démo | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/infrastructure gate --couche 2 --unitaire "python tools/run_robot_tests.py --artefact infrastructure --couche 2 --categorie 1" --integration "python tools/run_robot_tests.py --artefact infrastructure --couche 2 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 2` | à construire |

## 10. Étape 8 — Checkpoints

- Tous les deux niveaux figés (`checkpoint_tous_les` = 2), signalés par `mcl.py statut`.

## 11. Gouvernance

- Profil : solo assisté par agent ; gardien de la carte et décideur des défigeages : l'utilisateur.
- Modification de contrat : défigeage tracé (`mcl.py defiger`) et ADR ; rayon via `mcl.py rayon`.

## 12. Bilan

- À compléter à la clôture de l'artefact (`mcl.py rapport`).

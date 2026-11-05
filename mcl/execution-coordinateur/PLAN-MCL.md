# Plan MCL — execution-coordinateur

> Artefact de chair du composite `robot-ema-v3`. Plan maître : `docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md`, section 7.D ; registre d'interprétation : `mcl/robot-ema-v3/INTERPRETATIONS.md`. Aucun code avant la section 9.

## 0. Périmètre de l'artefact

- **Artefact** : `execution-coordinateur` (paquet `src/xpbots/execution/`) — Contrats C06–C09 : cotation, prix exécutables, risque all-in, réservations, dimensionnement, arbitrage, cycle d'ordre, sorties obligatoires, coordinateur.
- **Échelle** : composant autonome ; **mode** : pur (chair du composite).
- **Règle de périmètre** : livré en phase(s) 4 et 5 du plan maître ; MCL ne gouverne que la construction du code de cet artefact.

## 1. Test d'applicabilité

| Question | Réponse | Justification |
|---|---|---|
| Structure connaissable ? | oui | Contrats normatifs C04, C06, C07, C08, C09, C11.2, C11.5–C11.7, C11.10–C11.13 |
| Contrats stabilisables tôt ? | oui | Seuils figés dans `config/`, fonctions de référence |
| Construire pour comprendre ? | non | Aucune recherche de variante |

- **Verdict** : applicable.
- **Bénéfice dégradé** : frontières externes stockage-etat, calcul-courtier, courtier-execution, journal-persistant, horloge-os doublées.
- **Signaux de mauvais domaine** : divergences répétées, défigeages en chaîne → suspendre et re-cartographier.

## 2. Étape 1 — Comprendre la cible

1. Finalité : Transformer les signaux des méthodes en ordres protégés dimensionnés à 0,5 % ou en refus motivés, gérer positions et sorties obligatoires et journaliser chaque décision (C09).
2. Entrées : ticks et cotations, bougies enrichies, signaux (port Strategie), autorisations fondamentales et contexte IA (ports du noyau), profils d'instrument, fonds propres, réponses du courtier. Sorties : ordres protégés, demandes de sortie, issues des signaux, enregistrements C09, alertes déterministes.
3. Contraintes : Python 3.13, bibliothèque standard (sauf adaptateurs réels en infrastructure), valeurs normatives lues dans `config/`, instants en ms UTC, prix en `Decimal`, aucune horloge ni réseau hors infrastructure.
4. Projet neuf (greenfield).

Point d'insertion dans le squelette : coordinateur de refus et exécution papier minimale du squelette (voir `mcl/robot-ema-v3/COUTURES.md`).

## 3. Étape 2 — Unités fonctionnelles

- 2.1 Entrées : ticks et cotations, bougies enrichies, signaux (port Strategie), autorisations fondamentales et contexte IA (ports du noyau), profils d'instrument, fonds propres, réponses du courtier ; sorties : ordres protégés, demandes de sortie, issues des signaux, enregistrements C09, alertes déterministes.
- 2.2 Workflow : rapprochement → sorties obligatoires → bougie et état technique → limites de méthode → fondamental et calendrier → contexte IA → cotation, stop, taille, marge, réservation → ordre protégé → confirmation → issue.

| Unité | Responsabilité | Entrée → sortie | Dépend de |
|---|---|---|---|
| `types_execution` | Représenter profil d'instrument C04, positions possédées, réservations, état du compte et paramètres d'exécution. | caractéristiques lues de l'environnement ; bloc common → objets immuables ; champs absents marqués inconnus, jamais zéro | amont-noyau, amont-donnees-temps |
| `garde_cotation` | Contrôler fraîcheur, croisement, plafond de spread, écart d'entrée et TTL d'un signal. | cotation Bid/Ask horodatée, instant courant, signal (clôture T, C, A_t) → verdict ; motifs SPREAD_CAP, ENTRY_GAP, SIGNAL_EXPIRED | types_execution |
| `prix_executables` | Convertir B_SL en SL exécutable, choisir E et calculer TP avec les arrondis au tick de C06. | sens, B_SL, Bid, Ask, k, tick_size et contraintes natives → E, SL, TP, D en Decimal sur la grille ; refus avant ordre si contrainte native (R7) | types_execution |
| `gardes_compte` | Suivre base quotidienne UTC et pic de fonds propres et imposer les arrêts quotidien et global persistants. | fonds propres courants (flottant et frais inclus), instant → état de garde et demandes de clôture | types_execution, stockage-etat |
| `registre_reservations` | Réserver et libérer le risque initial de façon atomique et persistante par clé d'intention. | clé d'intention C08, risque Decimal, symbole canonique → réservation unique par clé ; totaux et occupation par symbole | types_execution, stockage-etat |
| `risque_all_in` | Calculer la perte pessimiste au stop et les frais aller-retour pour un volume. | volume de la grille, niveaux, A_t, profil, port CalculCourtier → risque en USD Decimal, spread jamais recompté | prix_executables, calcul-courtier |
| `arbitrage` | Ordonner les signaux simultanés selon les priorités figées et l'occupation des sous-jacents. | signaux du même instant, registre → liste ordonnée ; aucune fusion ni couverture opposée | registre_reservations |
| `dimensionnement` | Retenir le plus grand volume de la grille native qui respecte simultanément les cinq contraintes C07. | instantané des fonds propres et des réserves, niveaux, profil → volume arrondi vers le bas ; refus MIN_VOLUME_OR_RISK_REJECT, ACCOUNT_RISK_CAP, MARGIN_REJECT, SYMBOL_BUSY ou ENVIRONMENT_NOT_READY | risque_all_in, registre_reservations, gardes_compte, calcul-courtier |
| `cycle_ordre` | Envoyer l'ordre protégé et gérer accusé ambigu, rapprochement, fill partiel et rétablissement des protections. | intention réservée, réponses du port Courtier, instants → actions (envoyer, rapprocher, corriger TP, clôturer d'urgence), issue et alertes | dimensionnement, prix_executables, courtier-execution, horloge-os |
| `sorties_obligatoires` | Déterminer la première échéance de sortie et produire les clôtures prioritaires. | positions possédées, instant, demandes FLATTEN/annonce/gardes, séances → demandes de sortie ordonnées ; blocage des entrées du symbole tant qu'une clôture est en attente | cycle_ordre, amont-donnees-temps |
| `coordinateur` | Ordonner les traitements C08 pour chaque événement et journaliser chaque décision C09. | événements de marché et d'horloge ; ports Strategie, ControleFondamental, ContexteIA, Courtier, CalculCourtier, Stockage, Journal → ordres, sorties, issues et enregistrements C09 | sorties_obligatoires, arbitrage, garde_cotation, amont-noyau, journal-persistant |

Question-test : « constructible et testable si rien d'autre n'existait ? »

| Unité | Réponse | A besoin de | Profondeur |
|---|---|---|---|
| `types_execution` | oui (feuille interne) | — | 0 |
| `garde_cotation` | non | types_execution | 1 |
| `prix_executables` | non | types_execution | 1 |
| `gardes_compte` | non | types_execution | 1 |
| `registre_reservations` | non | types_execution | 1 |
| `risque_all_in` | non | prix_executables | 2 |
| `arbitrage` | non | registre_reservations | 2 |
| `dimensionnement` | non | risque_all_in, registre_reservations, gardes_compte | 3 |
| `cycle_ordre` | non | dimensionnement, prix_executables | 4 |
| `sorties_obligatoires` | non | cycle_ordre | 5 |
| `coordinateur` | non | sorties_obligatoires, arbitrage, garde_cotation | 6 |

## 4. Étape 3 — Graphe de dépendances

- `types_execution` → amont-noyau, amont-donnees-temps
- `garde_cotation` → types_execution
- `prix_executables` → types_execution
- `gardes_compte` → types_execution, stockage-etat
- `registre_reservations` → types_execution, stockage-etat
- `risque_all_in` → prix_executables, calcul-courtier
- `arbitrage` → registre_reservations
- `dimensionnement` → risque_all_in, registre_reservations, gardes_compte, calcul-courtier
- `cycle_ordre` → dimensionnement, prix_executables, courtier-execution, horloge-os
- `sorties_obligatoires` → cycle_ordre, amont-donnees-temps
- `coordinateur` → sorties_obligatoires, arbitrage, garde_cotation, amont-noyau, journal-persistant

- **Contrôle de divergence** : `mcl.py analyser --ecrire` puis `analyser` (2026-11-05) : profondeurs proposées identiques aux profondeurs déclarées, zéro divergence.
- Regroupements retenus (unités indépendantes de même profondeur réunies dans une couche) : aucun.
- **Amont figé** (artefacts antérieurs, déclarés comme frontières autorisées partout) : amont-noyau, amont-donnees-temps.
- **Frontières externes** : stockage-etat, calcul-courtier, courtier-execution, journal-persistant, horloge-os.
- **Cycles** : aucun entre unités ; la machine à états éventuelle est condensée dans une seule unité.

## 5. Étape 4 — Carte des couches

| Couche | Unités | Dépend de | Module |
|---|---|---|---|
| 0 — types-execution | `types_execution` | amont-donnees-temps, amont-noyau | `src/xpbots/execution/c0_types.py` |
| 1a — garde-cotation | `garde_cotation` | 0 | `src/xpbots/execution/c1a_cotation.py` |
| 1b — prix-executables | `prix_executables` | 0 | `src/xpbots/execution/c1b_prix.py` |
| 1c — gardes-compte | `gardes_compte` | 0 | `src/xpbots/execution/c1c_gardes_compte.py` |
| 1d — registre-reservations | `registre_reservations` | 0 | `src/xpbots/execution/c1d_reservations.py` |
| 2a — risque-all-in | `risque_all_in` | 1b | `src/xpbots/execution/c2a_risque.py` |
| 2b — arbitrage | `arbitrage` | 1d | `src/xpbots/execution/c2b_arbitrage.py` |
| 3 — dimensionnement | `dimensionnement` | 1c, 1d, 2a | `src/xpbots/execution/c3_dimensionnement.py` |
| 4 — cycle-ordre | `cycle_ordre` | 1b, 3 | `src/xpbots/execution/c4_cycle_ordre.py` |
| 5 — sorties-obligatoires | `sorties_obligatoires` | 4, amont-donnees-temps | `src/xpbots/execution/c5_sorties.py` |
| 6 — coordinateur | `coordinateur` | 1a, 2b, 5, amont-noyau | `src/xpbots/execution/c6_coordinateur.py` |

- **Groupes parallèles** : 1a, 1b, 1c, 1d; 2a, 2b (contrats finalisés ensemble, gates et gels séparés).

## 6. Encodage de la carte

- Outil : convention « une couche = un module nommé » + `mcl.py verifier --mode strict` en CI et revue de code (aucun outil d'architecture ajouté).
- Règle : dépendances autorisées vers toute couche plus interne, à profondeur quelconque.

## 7. Étape 5 — Contrats

- Esquisses : `mcl/execution-coordinateur/contrats/couche-<id>.md` (2026-11-05) ; finalisation couche par couche.

## 8. Étape 6 — Frontières externes

| Frontière | Imports réels | Couches autorisées | Doublure |
|---|---|---|---|
| stockage-etat | sqlite3 | aucune (port du noyau) | `tests/robot/doublures/` |
| calcul-courtier | MetaTrader5 | aucune (port du noyau) | `tests/robot/doublures/` |
| courtier-execution | MetaTrader5 | aucune (port du noyau) | `tests/robot/doublures/` |
| journal-persistant | — (port du noyau) | aucune (port du noyau) | `tests/robot/doublures/` |
| horloge-os | time | aucune (port du noyau) | `tests/robot/doublures/` |

## 9. Étape 7 — Plan de construction

| Couche | Tests cat. 1 | Tests cat. 2 | Gate | Statut |
|---|---|---|---|---|
| 0 | profil complet ou ENVIRONMENT_NOT_READY ; clé d'intention ; paramètres du bloc common | — | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/execution-coordinateur gate --couche 0 --unitaire "python tools/run_robot_tests.py --artefact execution --couche 0 --categorie 1" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 0` | à construire |
| 1a | spread au plafond admis, TTL exactement 5 s expiré (C11.2), âge 2 s, écart 0,25A, R3, première cotation après clôture (C11.3) | via 6 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/execution-coordinateur gate --couche 1a --unitaire "python tools/run_robot_tests.py --artefact execution --couche 1a --categorie 1" --integration "python tools/run_robot_tests.py --artefact execution --couche 1a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1a` | à construire |
| 1b | S01.5 : E 1,10010, SL 1,09945, TP 1,10108 ; vente SL 1,10065, TP 1,09902 ; concordance rounded_levels ; C11.5 ; contraintes natives (R7) | via 2a et 4 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/execution-coordinateur gate --couche 1b --unitaire "python tools/run_robot_tests.py --artefact execution --couche 1b --categorie 1" --integration "python tools/run_robot_tests.py --artefact execution --couche 1b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1b` | à construire |
| 1c | base 00:00 UTC, 98 % et 90 % exacts, flottant et frais inclus, persistance sans remise à zéro (C11.13) | via 3 et 6 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/execution-coordinateur gate --couche 1c --unitaire "python tools/run_robot_tests.py --artefact execution --couche 1c --categorie 1" --integration "python tools/run_robot_tests.py --artefact execution --couche 1c --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1c` | à construire |
| 1d | réservation atomique avant envoi, idempotence par clé, libération à la clôture seulement | via 3 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/execution-coordinateur gate --couche 1d --unitaire "python tools/run_robot_tests.py --artefact execution --couche 1d --categorie 1" --integration "python tools/run_robot_tests.py --artefact execution --couche 1d --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 1d` | à construire |
| 2a | g = 0,000025 et distance 0,00070 (S01.5) ; frais minimaux et paliers (C11.7) ; spread non recompté | via 3 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/execution-coordinateur gate --couche 2a --unitaire "python tools/run_robot_tests.py --artefact execution --couche 2a --categorie 1" --integration "python tools/run_robot_tests.py --artefact execution --couche 2a --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 2a` | à construire |
| 2b | LONDON_V3 avant EMA_V3 puis EURUSD, GBPUSD, XAUUSD ; une position par sous-jacent (C11.10, R17) | via 6 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/execution-coordinateur gate --couche 2b --unitaire "python tools/run_robot_tests.py --artefact execution --couche 2b --categorie 1" --integration "python tools/run_robot_tests.py --artefact execution --couche 2b --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 2b` | à construire |
| 3 | 0,01 lot standard refusé à 0,70 USD (C11.6) ; micro admis à 0,07 USD ; 1 % réservé, deux positions, marge ≤ Eqt/3 ; positions externes (R8) | bloc 0→3 réel avec doublure de calculs courtier | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/execution-coordinateur gate --couche 3 --unitaire "python tools/run_robot_tests.py --artefact execution --couche 3 --categorie 1" --integration "python tools/run_robot_tests.py --artefact execution --couche 3 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 3` | à construire |
| 4 | accusé 5 s, rapprochement 1 s/30 s puis 5 s, fill partiel, corrections TP 0,25/1/3 s et 15 s, SL absent, TP dépassé (C11.11, C11.12) | courtier scripté sur le bloc 0→4 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/execution-coordinateur gate --couche 4 --unitaire "python tools/run_robot_tests.py --artefact execution --couche 4 --categorie 1" --integration "python tools/run_robot_tests.py --artefact execution --couche 4 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 4` | à construire |
| 5 | 7 200 s, 16:00 Londres, annonce, FLATTEN, gardes, 60 s avant fermeture, blackout ; égalités d'échéances | flux absent à l'heure de sortie, réessai chaque seconde | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/execution-coordinateur gate --couche 5 --unitaire "python tools/run_robot_tests.py --artefact execution --couche 5 --categorie 1" --integration "python tools/run_robot_tests.py --artefact execution --couche 5 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 5` | à construire |
| 6 | ordre C08, second contrôle avant envoi, journal C09, redémarrage, verrou de propriété en netting | bloc A+B+D réel, TECHNICAL_CONTROL_NEUTRAL nommé : cycle de trade complet, 7ᵉ entrée refusée, C11.10 à C11.13 | `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/execution-coordinateur gate --couche 6 --unitaire "python tools/run_robot_tests.py --artefact execution --couche 6 --categorie 1" --integration "python tools/run_robot_tests.py --artefact execution --couche 6 --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"` puis `figer --couche 6` | à construire |

## 10. Étape 8 — Checkpoints

- Tous les deux niveaux figés (`checkpoint_tous_les` = 2), signalés par `mcl.py statut`.

## 11. Gouvernance

- Profil : solo assisté par agent ; gardien de la carte et décideur des défigeages : l'utilisateur.
- Modification de contrat : défigeage tracé (`mcl.py defiger`) et ADR ; rayon via `mcl.py rayon`.

## 12. Bilan

- À compléter à la clôture de l'artefact (`mcl.py rapport`).

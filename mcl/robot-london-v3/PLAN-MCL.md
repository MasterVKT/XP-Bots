# Plan MCL — robot-london-v3 (composite)

> Document de travail MCL du **composite** : robot 2 London Breakout M15 (`LONDON_V3`) et composants partagés.
> La source de vérité est le [plan d'implémentation](../../docs/architecture/robot_london_v3/README.md)
> (version 1.4.7, validé par l'utilisateur le 05/11/2026). Ce fichier en reprend les sections 0 à 2 et renvoie
> au plan pour le reste ; en cas d'écart, le plan prévaut et l'écart est corrigé ici dans la même modification.
> Fichiers voisins : `carte.json` (carte au grain des paquets, servant à `analyser` et `verifier`, **jamais à
> `figer`**) et `journal.jsonl` (traces de l'outil). Chaque artefact de chair a son propre dossier
> `mcl/<artefact>/`, avec sa carte, ses contrats, son journal et son gate.

## 0. Périmètre de l'artefact

- **Artefact** : le système complet du robot London et de ses composants partagés : noyau, données et temps,
  moteur London, exécution et coordinateur, contrôles fondamentaux, lecteur du contexte IA, orchestration,
  journal et rejeu, infrastructure, points d'entrée, service IA ; puis, en phase 13, la préparation des données
  historiques et le moteur V1 de comparaison.
- **Échelle** : application entière. **Mode** : composite. Le squelette (phase 1) est construit hors protocole,
  en code de production minimal, déployable dès le départ ; chaque composant est ensuite un artefact MCL
  distinct, construit couche par couche et branché sur le squelette en remplaçant le segment minimal
  correspondant ([document 02](../../docs/architecture/robot_london_v3/02_cartographie_mcl.md), §3).
- **Règle de périmètre** : l'ordre de livraison vient de la section « Ordre de construction et de
  qualification » du [guide d'implémentation](../../docs/architecture/GUIDE_IMPLEMENTATION.md) ; sa
  correspondance, étape par étape, avec les phases du plan est donnée au document 02, §5. MCL ne gouverne que
  l'ordre de construction à l'intérieur de chaque artefact.
- **Hors périmètre** (plan, §6) : le robot EMA (S01), dont seules les interfaces partagées sont préparées ; le
  module fondamental externe, dont le robot consomme les permissions ; toute recherche de variante plus
  rentable ; tout ordre réel sans décision humaine tracée ; toute modification d'une valeur figée.

## 1. Test d'applicabilité (au niveau de l'artefact)

| Question | Réponse | Justification |
|---|---|---|
| 1. La structure est-elle connaissable avant construction ? | Oui | Spécification 3.1.0 déterministe et figée, exports `config/`, `schemas/` et `prompts/`, fonctions de référence, cartographie XP-Bots de la skill `xp-bots-mcl-robot-planning` |
| 2. Les contrats internes sont-ils stabilisables tôt ? | Oui | Règles et valeurs figées (C01, C02) ; types aux coutures fixés par C06 à C09 ; contrats des frontières externes finalisés tôt ([document 08](../../docs/architecture/robot_london_v3/08_contrats_frontieres.md)) |
| 3. Faut-il construire pour comprendre ? | Non pour le cœur ; partiellement pour l'adaptateur MT5 | Base horaire des ticks, SL attaché à l'entrée, modes de remplissage, appel d'ordre bloquant : l'infrastructure est construite contre les contrats du document 08, puis confrontée au réel par les sondes S-01 à S-08 en sous-étape 13.1 ; un écart ouvre un défigeage « correction » de la seule couche concernée ; le code des sondes n'est jamais promu en couche |

- **Verdict** : applicable.
- **Bénéfice dégradé assumé** : `infrastructure` et `service-ia` sont dominés par leurs frontières externes ;
  l'économie de doublures y est plus faible.
- **Signaux de mauvais domaine à surveiller** : divergences répétées entre carte et code réel ; défigeages en
  chaîne dès les premières couches. Réponse : suspendre, sonder, re-cartographier, informer l'utilisateur.

## 2. Étape 1 — Comprendre la cible, et décisions

### 2.1 Les quatre réponses de l'étape 1

1. **Finalité** : exécuter S02 sur les ticks Bid/Ask réels d'un compte standard USD de 100 USD, avec le risque de
   C07, la coordination de C08, la permission externe obligatoire de C05 et le veto IA facultatif de A07 ;
   produire un journal C09 rejouable ; reproduire en rejeu le protocole C10.
2. **Entrées de l'enveloppe** : ticks horodatés, états de connexion, caractéristiques C04 du compte et des
   symboles, réponses du courtier, permissions fondamentales, calendrier versionné, snapshot IA, horloge.
   **Sorties** : ordres d'entrée protégés, ajustements de TP, clôtures, alertes, journal C09 et journal
   d'entrées, rapports C10, A11 et A13.
3. **Contraintes** : Python 3.13 ; bibliothèque standard dans le cœur ; paquet `MetaTrader5` sous Windows, dans la
   seule infrastructure ; TTL de 5 s sans appel réseau entre signal et ordre ; développement et contrôles dans
   un conteneur Linux, sans intégration continue distante (D-10) ; exploitation sur le poste Windows de
   l'utilisateur à partir de la phase 13.
4. **Nature** : projet neuf ; `reference/` sert d'oracle de comparaison dans les tests, jamais de couche.

**Points d'insertion dans le squelette** : chaque artefact de chair remplace un ou plusieurs segments S1 à S7 ;
leurs contrats d'entrée et de sortie et la phase de remplacement sont au document 02, §3.1, et le registre des
coutures sera tenu dans `mcl/squelette/COUTURES.md` dès la phase 1.

### 2.2 Décisions consignées (plan, §3)

| Id | Décision | Statut |
|---|---|---|
| D-01 | Python 3.13 et MT5, piloté par le paquet officiel `MetaTrader5` 5.0.6231 | Arrêtée par l'utilisateur |
| D-02 | Sources dans `src/xpbots/` (paquet unique), tests dans `tests/robot/`, dossiers MCL dans `mcl/<artefact>/` | Arrêtée par l'utilisateur |
| D-03 | Noyau déterministe piloté par événements et coquille impérative | Arrêtée |
| D-04 | Tests en `unittest` et lanceur `tools/run_london_tests.py`, sans `pytest` | Arrêtée |
| D-05 | Cœur en bibliothèque standard ; `requirements-windows.txt` avec `MetaTrader5`, `numpy` et `tzdata` | Autorisée par l'utilisateur pour `MetaTrader5` |
| D-06 | État persistant en SQLite dans `runtime/`, transactions exclusives | Arrêtée |
| D-07 | Journal C09 en JSON Lines canonique et journal d'entrées rejouable, dans `logs/` | Arrêtée |
| D-08 | Numéro magique par couple (déploiement, stratégie) ; commentaire portant l'empreinte courte de la clé d'intention | Arrêtée |
| D-09 | Boucle en direct à 100 ms, constante d'ingénierie consignée | Arrêtée |
| D-10 | Intégration continue distante et porte `robot-suite` refusées : la suite tourne à chaque gate, à chaque fin de phase et avant chaque commit | Arrêtée : refus de l'utilisateur |
| D-11 | Permissions du module fondamental par dossier d'échange JSON à écriture atomique | Arrêtée par l'utilisateur |
| D-12 | Calendrier et horaires de séance par un service MQL5 d'export ; fermetures exceptionnelles dans un fichier tenu par l'humain | Arrêtée par l'utilisateur |
| D-13 | Compte de démonstration Deriv MT5 | Arrêtée par l'utilisateur |
| D-14 | Ticks du courtier s'ils couvrent la période, sinon source tierce déclarée contrefactuelle | Arrêtée par l'utilisateur |
| D-15 | Règles V1 fournies par l'utilisateur, portées dans `moteur-london-v1`, réservé au rejeu | Arrêtée par l'utilisateur |
| D-16 | Démonstration prospective après le gel du robot ; aucune date normative modifiée | Note |
| D-17 | Appels réels aux API LLM refusés ; autorisation redemandée en sous-étape 13.6 | Arrêtée : refus de l'utilisateur |
| D-18 | Stratégies injectées dans l'orchestration par la configuration de déploiement | Arrêtée |

Les douze arbitrages de spécification P-01 à P-12 (plan, §4) sont retenus selon leur recommandation et entrent
dans les contrats des couches indiquées par le plan.

## 3. Étapes 2 à 4 — Carte composite

Au grain composite, une unité est un artefact et une couche est son paquet. Les unités internes de chaque
artefact, leur question-test et leurs couches sont au document 02, §6 ; elles seront reprises dans la carte de
chaque artefact au début de sa phase.

| Couche | Artefact (unité) | Paquet | Dépend de | Phase |
|---|---|---|---|---|
| 0 | `noyau` | `xpbots.noyau` | — | 2 |
| 1 | `london-donnees-temps` | `xpbots.donnees` | noyau | 3 |
| 2a | `moteur-london` | `xpbots.london` | noyau, london-donnees-temps | 4 |
| 2b | `execution-coordinateur` | `xpbots.execution` | noyau, london-donnees-temps | 5 et 6 |
| 3a | `controles-fondamentaux` | `xpbots.fondamental` | noyau, execution-coordinateur | 7 |
| 3b | `contexte-ia` | `xpbots.contexte_ia` | noyau, execution-coordinateur | 8 |
| 3c | `infrastructure` | `xpbots.infra` | noyau, execution-coordinateur ; MT5, SQLite, fichiers, horloge, fils d'exécution | 11 |
| 4a | `orchestration` | `xpbots.orchestration` | noyau, london-donnees-temps, execution-coordinateur, controles-fondamentaux, contexte-ia | 9 |
| 4b | `service-ia` | `xpbots.service_ia` | noyau, contexte-ia ; SQLite, réseau, fichiers, horloge, fils d'exécution | 12 |
| 5 | `journal-rejeu` | `xpbots.rejeu` | noyau, execution-coordinateur, orchestration, moteur-london ; aléa | 10 |
| 6 | `points-entree` | `xpbots.app` | noyau, orchestration, journal-rejeu, infrastructure, moteur-london | 11 |

- **Groupes parallèles** : 2a ∥ 2b ; 3a ∥ 3b ∥ 3c ; 4a ∥ 4b. Aucune dépendance mutuelle n'y est permise ; en
  particulier, le moteur London et le coordinateur ne s'importent jamais. En phase 13 s'ajouteront
  `moteur-london-v1` (couche parallèle 2c, sous-étape 13.4) et `donnees-historiques` (couche parallèle 6b,
  sous-étape 13.3), selon le document 02, §5.
- **Résultat de `mcl.py analyser`** (05/11/2026) : profondeurs identiques au document 02, §5 ; aucun cycle ;
  aucune divergence ; une seule alerte, « plusieurs racines (`service-ia`, `points-entree`) », attendue parce que
  le robot et le service IA sont deux processus distincts.
- **Ordre de construction** : celui du plan (document 04), compatible avec cette carte : une phase ne commence
  que lorsque les artefacts dont elle dépend sont figés dans leur propre dossier MCL.

## 4. Encodage de la carte

- **Outil** : `mcl.py verifier`, qui analyse les imports Python par arbre syntaxique, y compris les imports placés
  dans une fonction. Aucun outil d'architecture natif n'est ajouté (aucune dépendance nouvelle, D-04 et D-05).
- **Règle** : dépendances autorisées vers n'importe quelle couche plus interne, à profondeur quelconque ; toutes
  les règles sont en mode strict, **y compris la divergence** (par défaut en avertissement) : toute dépendance
  réelle entre artefacts absente de la carte fait échouer la vérification.
- **Frontières externes déclarées** (une frontière importée hors de ses couches autorisées fait échouer la
  vérification ; la carte de chaque artefact restreint ensuite l'usage à ses seules couches internes) :

| Frontière | Modules | Couches autorisées |
|---|---|---|
| `MetaTrader5` | `MetaTrader5` | 3c (`infrastructure`) |
| `sqlite3` | `sqlite3` | 3c, 4b |
| `fichiers` | `os`, `pathlib`, `io`, `shutil`, `tempfile`, `gzip`, `glob` | 3c, 4b |
| `horloge` | `time` | 3c, 4b |
| `threading` | `threading`, `concurrent`, `queue` | 3c, 4b |
| `reseau` | `urllib`, `http`, `socket`, `ssl` | 4b |
| `aleatoire` | `random`, `secrets` | 5 (`journal-rejeu`, couche du bootstrap seulement dans sa propre carte) |
| `processus` | `subprocess`, `multiprocessing` | aucune |
| `reference` | `reference` | aucune : les fonctions de référence ne servent qu'aux tests |

- **Fichier hors carte** : seul `src/xpbots/__init__.py` (version du paquet, sans logique ni import) n'appartient
  à aucune couche ; `verifier` le compte comme « hors carte » sans échec.
- **Preuve de l'encodage** (05/11/2026, copie jetable hors du dépôt) : sur un arbre sain, vérification verte ; avec
  six violations volontaires (moteur London important le coordinateur, noyau important `time`, service IA
  important le coordinateur sans dépendance déclarée, points d'entrée important `sqlite3`, orchestration
  important `reference`, coordinateur important les points d'entrée), les six sont détectées et la vérification
  échoue.
- **Exécution** : `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier
  mcl/robot-london-v3 verifier` à la sortie de chaque phase (document 04, gabarit commun, étape 7), en plus du
  gate de chaque couche, qui vérifie la carte de son artefact.

## 5. Contrats, frontières et plan de construction

- **Contrats** : chaque artefact esquisse et finalise les siens dans `mcl/<artefact>/contrats/` ; la carte
  composite les désigne pour mémoire et n'est jamais figée.
- **Frontières externes et doublures** : document 02, §7 ; contrats finalisés tôt : document 08.
- **Plan de construction et de qualification** : document 04 (phases 0 à 13, gabarit commun, points d'arrêt) ;
  cas d'acceptation et commandes de gate : [document 03](../../docs/architecture/robot_london_v3/03_acceptation_et_tests.md).
- **Checkpoints** : propres à chaque artefact, aux niveaux indiqués par sa fiche de phase.

## 6. Gouvernance

- **Profil** : solo, un utilisateur et un agent de développement.
- **Gardien de la carte** : l'utilisateur. L'agent propose ; toute modification de la carte composite est
  justifiée dans ce fichier, dans la même modification, avec un nouveau passage de `analyser` sans divergence.
- **Défigeages** : dans le dossier de l'artefact concerné, par `mcl.py defiger` avec nature et motif, selon le
  plan (risques R-15 et R-18 du [document 05](../../docs/architecture/robot_london_v3/05_expert_risques_tracabilite.md)).
- **Baseline** : aucune ; le projet est neuf et toutes les règles sont strictes dès l'origine.

## 7. Suivi des phases

| Phase | Statut | Date | Preuves |
|---|---|---|---|
| 0 | Terminée | 05/11/2026 | Dossier composite initialisé ; carte sans divergence ; `verifier` vert ; encodage éprouvé par six violations détectées ; guide, règles du projet et skill de planification alignés sur D-01 et D-02 ; rapport d'arrêt de la phase |
| 1 | Terminée | 05/11/2026 | Squelette déployable : segments S1 à S7 dans leurs paquets définitifs ([registre des coutures](../squelette/COUTURES.md)) ; lanceur `tools/run_london_tests.py` ; fabrique de ticks ; test de bout en bout ; gardes de pureté et de carte composite ; 50 tests verts ; neuf mutations volontaires du squelette détectées sur copie jetable ; `verifier` vert sur le code réel |
| 2 | Terminée | 05/11/2026 | Artefact `noyau` : sept couches figées ([plan MCL du noyau](../noyau/PLAN-MCL.md)), gates verts avec régression intégrale, checkpoint après le niveau 1, deux défigeages « correction » de la couche 2 (dépendance vers 0a omise dans la carte ; ensemble exact des champs obligatoires non vérifié) ; treize mutations du noyau et neuf du squelette détectées ; couture S1 et S6 tracée ; squelette chargé par la configuration de production ; 127 tests verts ; `verifier` vert sur la carte du noyau et sur la carte composite |
| 3 | Terminée | 06/11/2026 | Artefact `london-donnees-temps` : huit couches figées ([plan MCL de london-donnees-temps](../london-donnees-temps/PLAN-MCL.md)), gates verts avec régression intégrale, checkpoints après les niveaux 1 et 3, un défigeage `extension` de 1a (export de l'état complet pour la reprise exacte) et un défigeage `correction` de 2b (empreinte chaînée vérifiée exactement) ; vingt-quatre mutations détectées ; couture S2 (remplacement) et extensions de S1, S3, S4, S6 et S7 tracées ; 197 tests verts ; `verifier` vert sur les cartes du noyau, de london-donnees-temps et composite |
| 4 | Terminée | 06/11/2026 | Artefact `moteur-london` : huit couches figées ([plan MCL](../moteur-london/PLAN-MCL.md)), contrats avant code et régression intégrale à chaque gate ; checkpoint après le niveau 1 ; S02, oracles `london_signal` et `london_setups`, causalité, quotas et propriété testés ; couture S3 remplacée et extensions S4/S7 tracées ; 532 tests verts des deux lignées, dont 79 propres à l’artefact ; 23 mutations distinctes détectées après une correction exacte de 1a, huit défigeages correctifs incluant la normalisation LF des fiches ; contrôles finaux consignés au bilan  |
| 5 | Terminée | 07/11/2026 | Onze couches 0a à 3 du coordinateur commun figées dans [london-execution-coordinateur](../london-execution-coordinateur/PLAN-MCL.md), checkpoints après les niveaux 1 et 3 ; un défigeage correctif 0a (risque nul confirmé et restauration mal formée), correction locale avant gel 1b (retrait pendant arrêt) ; 613 tests dont 80 propres au composant, cartes strictes, 29 mutations distinctes détectées et publication consignées au bilan ; arbitrage R4/R5 ; aucune couture, phase 6 non commencée |
| 6 | Terminée | 08/11/2026 | Cycle C08 (4), sorties (5a), reprise (5b) et coordinateur (6) figés dans le dossier commun ; checkpoint 6 ; couture S4 avec ordres, remplissages et sorties natives papier ; 707 tests dont 170 du coordinateur et 37 du squelette ; mutations, audit et publication au bilan ; phase 7 non commencée |

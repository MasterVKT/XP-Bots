# Coexistence des deux lignées de construction : robot 1 EMA_V3 et robot London LONDON_V3

Ce document décrit comment les deux robots sont construits côte à côte dans le même dépôt, ce que l'intégration du 6 novembre 2026 a changé, et les règles à respecter pour continuer sans collision. Il est normatif pour la construction du code ; il ne modifie aucune spécification métier.

## 1. Origine et décision

Deux sessions de construction ont travaillé en parallèle à partir du même point de départ, sans se connaître : l'une a construit le robot 1 (plan [PLAN_IMPLEMENTATION_ROBOT_EMA_V3](PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md)), l'autre le robot London (plan [robot_london_v3](robot_london_v3/README.md)). Chacune a créé son propre socle (noyau de types, composant données et temps) aux mêmes chemins, avec des contrats MCL figés différents.

Décision du 06/11/2026, prise sur délégation de l'utilisateur : **coexistence structurée** plutôt qu'unification immédiate. Motifs : aucune couche déjà validée et figée n'est réécrite ; chaque lignée garde ses contrats, ses tests et ses gates ; les deux robots restent indépendants, comme l'exigent les règles du dépôt. L'unification des socles reste possible plus tard, par un arbitrage explicite (règle R5).

## 2. Qui possède quoi

| Élément | Robot 1 | Robot London |
|---|---|---|
| Noyau (sources) | modules plats de `src/xpbots/noyau/` : `config`, `decisions`, `journal_schema`, `json_canonique`, `marche`, `ports`, `temps` | sous-paquets de `src/xpbots/noyau/` : `c0a_temps`, `c0b_nombres`, `c0c_configuration`, `c1a_marche`, `c1b_instrument`, `c1c_domaine`, `c2_journal` |
| Données et temps (sources) | `src/xpbots/donnees_temps/` | `src/xpbots/donnees/` |
| Moteur de la méthode | `src/xpbots/moteur_ema/` | `src/xpbots/london/` |
| Autres sources actuelles | `app/rejeu.py`, `app/segments_minimaux.py` | `app/rejeu_squelette.py`, `execution/squelette.py`, `infra/`, `orchestration/`, `rejeu/` |
| MCL, données et temps | `mcl/donnees-temps/` | `mcl/london-donnees-temps/` (ancien nom `mcl/donnees-temps/`, déplacé) |
| MCL, noyau | état dans les artefacts du plan composite | `mcl/noyau/` |
| MCL, plan composite | `mcl/robot-ema-v3/` | `mcl/robot-london-v3/` |
| Tests, données et temps | `tests/robot/donnees_temps/` | `tests/robot/london_donnees_temps/` |
| Autres tests | `tests/robot/moteur_ema/`, tests du squelette dans `tests/robot/app/` et `tests/robot/noyau/test_squelette_*.py` | `tests/robot/noyau/test_cat*`, `squelette/`, `transverses/`, `outils/` |
| Lanceur de tests | `tools/run_robot_tests.py` | `tools/run_london_tests.py` |
| Nom des fichiers de test par couche | `test_c<couche>_cat<k>_<thème>.py` | `test_cat<k>_c<couche>_<thème>.py` |
| Code de sortie si la sélection est vide | 5 | 1 |

Les `__init__.py` de `src/xpbots/`, `src/xpbots/app/` et `src/xpbots/noyau/` sont partagés : ils ne portent que des docstrings et la version du paquet, aucune logique.

Le registre exécutable de cette propriété est `tests/robot/outils/lignees.py`. Il est lu par les gardes des deux lignées. Les motifs propres à une lignée sont exclus de la carte de l’autre ; les motifs `COMMUN` restent contrôlés dans les deux cartes.

## 3. Ce que l'intégration a changé

- **Dossier MCL du London déplacé.** `mcl/donnees-temps/` du London est devenu `mcl/london-donnees-temps/`, et ses tests `tests/robot/london_donnees_temps/`. Les huit couches ont été défigées (nature « modification », motif tracé), puis refigées dans l'ordre des dépendances après un gate vert avec régression intégrale ; un checkpoint est journalisé. Le journal d'origine est conservé et complété, jamais réécrit. Le contenu des contrats est inchangé, hors chemins et mentions de documentation.
- **Deux lanceurs de tests.** Les deux versions du lanceur attendaient des comportements incompatibles pour une sélection vide (code 5 contre code 1) et des conventions de nommage différentes. Chaque lignée garde le sien ; les deux découvrent la suite intégrale sous `tests/robot/`.
- **Aides de test du robot 1.** Le module `tests/robot/outils.py` entrait en collision avec le paquet `tests/robot/outils/` du London. Il est devenu `tests/robot/outils/squelette_ema.py`, réexporté par `robot.outils` : aucun import existant n'a changé.
- **Gardes séparées.** La garde de pureté du London et les gardes de règles transversales du robot 1 ignorent les fichiers de l'autre lignée. Un nouveau test, `tests/robot/transverses/test_lignees.py`, interdit qu'un fichier soit déclaré aux deux lignées et interdit tout import d'une lignée vers l'autre.
- **Cartes composites.** Chaque carte composite exclut les fichiers de l'autre lignée, pour que ses règles d'architecture ne s'appliquent qu'à son propre code.
- **Gouvernance fusionnée.** `PROJECT_RULES`, le guide d'implémentation, le README et le registre des lacunes de skills décrivent désormais les deux robots.
- **Référence nominale restante.** Le contrat figé `mcl/noyau/contrats/couche-1a.md` cite encore le nom logique `donnees-temps` pour la future consommation par le composant données du London, aujourd'hui `london-donnees-temps`. C'est une référence de nom sans effet ; elle se corrigera lors du prochain défigeage de cette couche, pas avant.

## 4. Règles pour continuer

**R1. Noms.** Avant de créer un dossier `mcl/<nom>`, `tests/robot/<nom>` ou un paquet `src/xpbots/<nom>`, vérifier qu'il n'existe pas déjà dans l'autre lignée (liste des fichiers suivis par Git). Pour un nom déjà pris, le London utilise le préfixe `london-` (MCL) ou `london_` (tests et paquets), comme pour `london-donnees-temps`.

**R2. Registre.** Tout fichier ajouté dans un paquet partagé (`noyau`, `app`, `execution`) et tout nouveau paquet doivent être déclarés dans `tests/robot/outils/lignees.py`. Les fichiers propres à une lignée sont exclus de la carte de l’autre. Depuis l’arbitrage du 06/11/2026, `COMMUN` déclare les calculs du coordinateur : ils sont contrôlés par les deux cartes, sans exclusion croisée. Un fichier non déclaré est contrôlé par les deux gardes : l'échec qui en résulte est voulu, il force la déclaration.

**R3. Aucun import croisé.** Le code propre à une lignée n’importe jamais un module de l’autre. Le test `test_lignees.py` le vérifie. La frontière commune 0a adapte les types des deux noyaux, selon l’arbitrage §6 ; le reste du coordinateur consomme la forme canonique sans importer les moteurs.

**R4. Composants planifiés par les deux lignées.** Les deux plans prévoient chacun les composants suivants, sous les mêmes noms de paquet ou presque :

| Composant | Robot 1 | Robot London | Pourquoi il est commun |
|---|---|---|---|
| Coordinateur d'exécution | `execution` | `execution` | un seul coordinateur de compte partage risque et marge (C07, C08) |
| Permissions fondamentales | `fondamental` | `fondamental` | C05, valable pour les deux méthodes |
| Contexte IA et service IA | `contexte_ia`, `service_ia` | `contexte_ia`, `service_ia` | le service IA est partagé par les deux méthodes (A01 à A12) |
| Journal et rejeu | `journal_rejeu` | `rejeu` | C10 et C11 |
| Infrastructure courtier | `infrastructure` | `infra` | C04 |
| Points d'entrée | `app` | `app` | |

Ces composants ne se construisent qu'une fois. **Avant** la première construction de l'un d'eux par l'une ou l'autre lignée, consigner dans la section 6 un arbitrage daté : soit unification (un seul paquet consommé par les deux robots, défigeage tracé des couches concernées), soit séparation justifiée (noms préfixés). Deux versions sous le même nom de paquet sont interdites.

**R5. Dette de convergence des socles.** Le noyau et le composant données et temps existent en deux versions. Avant de construire un composant partagé qui consomme des signaux, des ticks, des bougies ou le journal des deux robots (coordinateur d'exécution, journal et rejeu, infrastructure, points d'entrée), arbitrer leur convergence. Option A : des adaptateurs entre les deux noyaux. Option B : un seul noyau, avec défigeage tracé puis refigeage des couches de l'autre lignée et rejeu des tests des deux robots. Comparer d'abord les deux contrats (types de signal, temps, marché, journal C09) : aucune option n'est présumée meilleure ici.

**R6. Gates MCL.** Pour une couche du robot 1, utiliser le lanceur du robot 1 avec ses filtres par artefact, couche et catégorie. Pour une couche du London, utiliser `tools/run_london_tests.py` avec les mêmes filtres, en régression `python tools/run_london_tests.py` puis `python tools/verify_project.py`. La suite intégrale se rejoue avec l'un ou l'autre lanceur.

**R7. Contrôle après toute modification d'un lanceur, d'un registre ou d'une carte.** Rejouer la suite intégrale, `python tools/verify_project.py`, la suite de gouvernance, et la vérification stricte de chaque dossier `mcl/` qui contient une `carte.json`.

## 5. Vérification de l'intégration

Au 06/11/2026 : suite intégrale verte avec les deux lanceurs, vérification stricte verte pour les douze cartes MCL, `verify_project.py` et suite de gouvernance vertes, huit couches de `london-donnees-temps` refigées après gate vert.

## 6. Registre des arbitrages

| Date | Décision | Décideur |
|---|---|---|
| 06/11/2026 | Coexistence structurée des deux lignées, sans unification immédiate des socles ; unification renvoyée aux règles R4 et R5 | session de construction, sur délégation de l'utilisateur |

### Arbitrage R4/R5 du 06/11/2026 — phase 5 London

Le coordinateur EMA est encore un plan sans code et sans contrat figé. La phase 5 construit une seule implémentation partagée sous `xpbots.execution.c*`, suivie dans `mcl/london-execution-coordinateur/`. Le préfixe du dossier de traçabilité distingue le plan exécuté de l'ancienne esquisse ; il ne désigne pas un second coordinateur de compte. Les deux plans consommeront ce même paquet. L'ancienne esquisse `mcl/execution-coordinateur` reste conservée comme historique de planification et ne doit pas être implémentée en parallèle.

Comparaison des socles : EMA exprime le sens par ±1, la clôture Bid en Decimal et le stop/ATR en flottant ; London utilise un sens nommé et des prix techniques flottants. Les deux représentent le temps en millisecondes UTC ; EMA conserve la séquence dans `Instant`, London distingue heure fournisseur et réception. EMA expose des ticks décimaux, London une cotation décimale dédiée. Leurs clés d'intention ont les mêmes composantes sémantiques mais des sérialisations différentes. Les journaux C09 ont des enveloppes, noms de types et schémas distincts : ils ne sont pas interchangeables.

L'option A de R5 est retenue : adaptateurs typés en 0a, des valeurs EMA existantes vers le domaine canonique London. La conversion vérifie les prix, le sens, la clé et la conservation du temps ; aucune heure de réception ne se devine. Les objets techniques restent flottants selon C03, les cotations et montants restent décimaux. Les anciens journaux ne sont ni convertis ni réécrits ; le futur producteur du coordinateur emploiera l'enveloppe canonique du noyau London, avec la provenance explicite des valeurs adaptées. Les détails de l'ancienne méthode restent conservés dans le contexte adapté. Aucun fichier des deux noyaux n'est défigé, car aucun contrat amont ne change.

Le registre `COMMUN` couvre les nouveaux sous-paquets du seul coordinateur. Les deux cartes composites le contrôlent, sans l'exclure comme code de l'autre lignée. La règle R3 reste stricte pour les fichiers propres aux méthodes ; seule la frontière d'adaptation commune 0a peut importer les types EMA et London. Les imports des moteurs de méthodes demeurent interdits au coordinateur. Les tests emploient de vrais objets des deux noyaux et un même registre de réservations, afin que la priorité et les plafonds ne puissent pas être appliqués séparément par robot.

Décision prise par la session de construction sur délégation de la demande explicite d'achever la phase 5. Aucune règle de risque, aucun coût et aucun seuil ne sont modifiés.

### Prolongement R4/R5 du 08/11/2026 — phase 6 London

Les quinze couches du coordinateur unique sont construites et gelées dans le même dossier actif.
Le cycle C08, les sorties, la reprise et l'enveloppe consomment les adaptateurs 0a existants ; aucun
moteur n'est importé par le coordinateur. London remplace S4 et utilise les commandes communes dans
son rejeu papier. Cette disponibilité n'intègre pas le robot EMA de plateforme et ne remplace pas
son squelette. L'extension additive du domaine London ajoute seulement deux causes de clôture ;
elle est tracée dans le journal MCL du noyau. Les noyaux EMA et journaux historiques restent intacts.

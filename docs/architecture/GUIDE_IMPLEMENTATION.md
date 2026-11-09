# Guide d'implémentation des deux robots

État du dépôt au 9 novembre 2026 : spécifications 3.1.0, paramètres figés, contrats et fonctions de référence disponibles ; plan d'implémentation du robot London arrêté, structure MCL composite dans `mcl/robot-london-v3/`, squelette composite déployable, noyau et données de marché de la lignée London figés dans `src/xpbots/` (types, configuration figée, journal C09, bougies M15 et H1 causales enrichies de TR, ATR et repères de Londres), moteur London S02 pur figé dans `mcl/moteur-london/` et branché en S3. Ses vrais signaux sont exécutés par le coordinateur commun en S4 et le transport papier S5, avec taille de tick et contrat explicitement déclarés. Le port C05 réel est disponible depuis la phase 7, avec permissions et calendrier scénarisés ; le contrôle technique neutre est un choix explicite. Les quinze couches du coordinateur commun sont figées dans `mcl/london-execution-coordinateur/` ; elles adaptent explicitement les types EMA. Le lecteur IA commun est figé depuis la phase 8 dans mcl/london-contexte-ia : snapshot strict, cache causal et reprise pure, port BLOCK/NEUTRAL injecté au bras IA du rejeu. La référence conserve le complément absent. Le robot de plateforme, le service HTTP LLM, le registre de budget transactionnel et l'adaptateur courtier restent à construire. Ce guide oriente la construction ; les deux spécifications autonomes fixent le comportement détaillé.

Mise à jour du 5 novembre 2026 : la construction du robot 1 (Python 3.13, MT5) suit le [plan d'implémentation du robot 1](PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md) ; son squelette composite existe dans `src/xpbots/`, sans adaptateur courtier réel. Le plan London et son suivi de phases figurent ci-dessous.

## Autorité des ressources

Les [deux spécifications](../../README.md) contiennent les règles complètes C01–C11, la méthode S01 ou S02 et le workflow IA A01–A15. Les exports de `config/`, `schemas/` et `prompts/` évitent une transcription manuelle. Les contrôles vérifient leur concordance. Le nom `parametres_figes_v3.json` et sa version technique 3.0.0 restent inchangés : la version documentaire 3.1.0 ajoute l'intégration IA sans modifier ce noyau.

Une contradiction entre texte, JSON et implémentation doit être signalée et résolue avant de poursuivre le composant concerné. Aucun paramètre ne doit être ajusté silencieusement au cours du portage.

La [référence utilisateur](../references/README.md), les anciennes simulations et les outils de travail d'autres projets ne sont pas des instructions normatives. Le registre de nettoyage permet de récupérer les anciens essais si une vérification historique les nécessite.

## Composants et travail restant

| Composant | Contrat à respecter | Point d'attention |
|---|---|---|
| Adaptateur de marché et d'exécution | C03, C06–C09 | Bid/Ask, taille minimale, pas, marge, frais, rejets et réconciliation réels |
| Moteur EMA indépendant | S01 | Moteur pur construit dans sa lignée ; intégration complète au compte restant à réaliser |
| Moteur London indépendant | S02 | Moteur pur figé et couture S3 réalisée ; sorties C08 construites et exécutées en papier |
| Coordonnateur de compte partagé | C06–C09 | Coordinateur unique construit en phases 5 et 6 ; cycle, sorties et rapprochement sur preuves ; persistance physique et adaptateur réel à construire |
| Contrôles fondamentaux obligatoires | C05 | Cinq couches communes figées dans mcl/london-controles-fondamentaux ; permissions et calendrier causaux, heartbeat et reprise ; sources physiques à construire |
| Service d'IA distant partagé | A01–A11 | Collecte officielle, preuve textuelle, qualification des API, budgets transactionnels et cache |
| Interface du complément IA | A08–A12 | Snapshot asynchrone, séquence, intégrité, cache persistant et expiration propre des vetos |
| Journal et moteur de rejeu | C10–C11, A13–A15 | Traces causales, coûts complets et comparaison de portefeuilles A/B |

L'analyse fondamentale externe et le complément LLM ont des rôles distincts. Une panne du complément facultatif donne `NEUTRAL` sans créer une permission fondamentale. Le complément ne choisit ni sens, ni lot, ni prix, ni sortie.

## Ordre de construction et de qualification

1. Exécuter les contrôles de référence. Porter et comparer les indicateurs, horaires Londres/UTC, états de signal, arrondis et stops sur les cas synthétiques existants.
2. Construire l'exécution et le coordonnateur du compte. Vérifier les caractéristiques réellement disponibles pour le compte standard, 100 USD, levier 1:100. Conserver le refus si le volume minimal dépasse le risque de 0,5 %.
3. Implémenter chaque méthode séparément, puis vérifier leurs interactions sur le même compte. Les règles de positions, de risque et de priorité restent communes ; les méthodes ne sont pas fusionnées.
4. Brancher le calendrier et les permissions fondamentales causales. Aucun avis rétrospectif ne doit être utilisé comme s'il était connu avant l'ordre.
5. Implémenter le service IA en arrière-plan et les adaptateurs des API autorisées. Les clés et les droits réels restent dans l'environnement. Aucun appel LLM ne doit attendre dans le chemin d'entrée de cinq secondes ; aucune inférence locale n'est admise.
6. Qualifier les sorties du modèle sur le corpus annoté, puis collecter les réponses prospectivement. Le mode initial `PAPER_AB` compare la référence et le complément, sans activer un veto IA réel non validé.
7. Appliquer les protocoles financiers de C11 et A13. Les critères IA de 60 journées de marché et 200 trades clos par méthode, avec assez d'événements affectés, complètent les contrôles techniques. Maintenir la rétention de 80 % des transactions comparables, déduire le coût IA partagé une seule fois et publier l'incertitude.

Les dates et champs de collecte sont décrits dans les [données historiques requises](../data/03_Donnees_Historiques_Requises_et_Validation.md). Un calendrier de collecte ne prouve pas à lui seul que l'effectif de validation sera atteint.

Le [plan d'implémentation intégrale du robot London](robot_london_v3/README.md) (`LONDON_V3`, version 1.4.9 du 9 novembre 2026, validé par l'utilisateur) décline cet ordre en phases MCL avec points d'arrêt ; ses décisions et arbitrages de spécification sont arrêtés. Ses phases 0 à 12 se construisent dans le conteneur de développement contre des contrats de frontière finalisés tôt ; les actions réservées à l'humain (poste, compte de démonstration, données, autorisation des API, annotation, mises en service) sont regroupées dans sa phase 13 de qualification.

## Emploi des fonctions de référence

`reference/technical.py` fournit les indicateurs et détecteurs de configurations, sans portefeuille, dimensionnement complet ou modèle de fills. `reference/llm_contracts.py` illustre validation textuelle, causalité, veto et bornes de coût, sans client HTTP, verrouillage concurrent du budget ou persistance de production. Leur [notice](../../reference/README.md) précise les limites.

Les dépendances de `requirements-dev.txt` concernent ces contrôles Python. Deux robots sont en construction, chacun selon son plan : le robot 1 (`EMA_V3`, [plan](PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md)) n'utilise que la bibliothèque standard, le paquet `MetaTrader5` étant réservé à son infrastructure (plan, section 1) ; pour le robot London (`LONDON_V3`, [plan](robot_london_v3/README.md)), le langage et la plateforme sont arrêtés depuis le 5 novembre 2026 : Python 3.13 et MT5, piloté par le paquet officiel `MetaTrader5`, avec les sources dans `src/xpbots/` (décisions D-01 et D-02) ; ses dépendances d'exécution suivent sa décision D-05. Aucun adaptateur factice n'a été ajouté : le code naît phase par phase, selon chaque plan, et l'état MCL de chaque artefact est tenu dans `mcl/`.

Pour les futurs historiques, traces et états privés, utiliser les emplacements exclus `data/raw/`, `data/cache/`, `data/private/`, `runtime/`, `logs/` et `.local/`. Les résultats synthétiques servant de fixtures peuvent être ajoutés explicitement dans `tests/` après revue.

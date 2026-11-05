# Guide d'implémentation des deux robots

État du dépôt au 4 novembre 2026 : spécifications 3.1.0, paramètres figés, contrats et fonctions de référence disponibles. Aucun robot de plateforme, service HTTP LLM, registre de budget transactionnel ou adaptateur courtier n'est encore fourni. Ce guide oriente la construction ; les deux spécifications autonomes fixent le comportement détaillé.

## Autorité des ressources

Les [deux spécifications](../../README.md) contiennent les règles complètes C01–C11, la méthode S01 ou S02 et le workflow IA A01–A15. Les exports de `config/`, `schemas/` et `prompts/` évitent une transcription manuelle. Les contrôles vérifient leur concordance. Le nom `parametres_figes_v3.json` et sa version technique 3.0.0 restent inchangés : la version documentaire 3.1.0 ajoute l'intégration IA sans modifier ce noyau.

Une contradiction entre texte, JSON et implémentation doit être signalée et résolue avant de poursuivre le composant concerné. Aucun paramètre ne doit être ajusté silencieusement au cours du portage.

La [référence utilisateur](../references/README.md), les anciennes simulations et les outils de travail d'autres projets ne sont pas des instructions normatives. Le registre de nettoyage permet de récupérer les anciens essais si une vérification historique les nécessite.

## Composants à construire

| Composant | Contrat à respecter | Point d'attention |
|---|---|---|
| Adaptateur de marché et d'exécution | C03, C06–C09 | Bid/Ask, taille minimale, pas, marge, frais, rejets et réconciliation réels |
| Moteur EMA indépendant | S01 | Tendance, armement, repli, reprise, consommation du signal et cooldown |
| Moteur London indépendant | S02 | Range 02:00–07:00 Londres, cassure, quotas par sens et fermeture horaire |
| Coordonnateur de compte partagé | C06–C09 | Un seul budget de risque et de marge pour les deux robots, sans double réservation |
| Contrôles fondamentaux obligatoires | C05 | Flux externe horodaté, permissions et calendrier ; absence ou péremption bloquante |
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

Le [plan d'implémentation intégrale du robot London](robot_london_v3/README.md) (`LONDON_V3`, version 1.3.0 du 5 novembre 2026, validé par l'utilisateur) décline cet ordre en phases MCL avec points d'arrêt ; ses décisions et arbitrages de spécification sont arrêtés.

## Emploi des fonctions de référence

`reference/technical.py` fournit les indicateurs et détecteurs de configurations, sans portefeuille, dimensionnement complet ou modèle de fills. `reference/llm_contracts.py` illustre validation textuelle, causalité, veto et bornes de coût, sans client HTTP, verrouillage concurrent du budget ou persistance de production. Leur [notice](../../reference/README.md) précise les limites.

Les dépendances de `requirements-dev.txt` concernent ces contrôles Python. Le langage, la plateforme et les dépendances du futur robot ne sont pas arrêtés par le rangement du dépôt. Aucun dossier d'application vide ni adaptateur factice n'a été ajouté.

Pour les futurs historiques, traces et états privés, utiliser les emplacements exclus `data/raw/`, `data/cache/`, `data/private/`, `runtime/`, `logs/` et `.local/`. Les résultats synthétiques servant de fixtures peuvent être ajoutés explicitement dans `tests/` après revue.

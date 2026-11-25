# Guide d'implémentation des deux robots

État du dépôt au 25 novembre 2026 : les spécifications 3.1.0 et leurs exports restent les contrats métier. Les phases 0 à 12 London ont construit le noyau, les données causales, le moteur S02, le coordinateur commun, C05, le lecteur IA, l’orchestration et le rejeu C10, puis l’infrastructure et les points d’entrée. Les quinze unités physiques sont figées dans `mcl/london-infrastructure/` et les neuf unités applicatives dans `mcl/points-entree/`. Le SDK est injecté ; les essais emploient FauxMT5, des fichiers et SQLite temporaires réels. La vraie boucle directe et le rejeu d’incident utilisent le même moteur ; deux COMMITs précèdent une entrée native et les défenses restent prioritaires pendant les pannes. C04 impose la convention qualifiée des ticks SDK, indépendamment des exports serveur D12. Le [guide d’exploitation](../exploitation/LONDON_M15.md) décrit les huit commandes et les incidents. Le bilan de phase 11 conserve ses quatorze contrats MT5 différés à 13.1 et ses 38 mutations détectées. Les sources MQL5 ne sont pas compilées ici. Le [service IA partagé](../../mcl/london-service-ia/PLAN-MCL.md) est construit : douze unités gelées, 222 tests propres, collecte causale, budget SQLite concurrent et trois workers. La couture avec le vrai lecteur et le London PAPER_AB passe ; quatorze mutations sont détectées. La suite actuelle compte 1 629 tests, dont vingt contrats physiques différés à 13.1/13.6. La [CLI du service](../exploitation/SERVICE_IA.md) et son HTTP inactif par défaut restent distincts du robot ; le producteur fondamental externe reste à fournir et l’intégration de plateforme EMA à réaliser selon son plan. Aucun résultat synthétique ne qualifie le terminal, le compte ou la rentabilité. Ce guide oriente la construction ; les deux spécifications autonomes fixent le comportement détaillé.

La construction du robot 1 (Python 3.13, MT5) suit le [plan d'implémentation du robot 1](PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md) ; son squelette composite existe dans `src/xpbots/` ; l’infrastructure commune construite en phase 11 London reste à intégrer et à qualifier pour cette lignée. Le plan London et son suivi de phases figurent ci-dessous.

## Autorité des ressources

Les [deux spécifications](../../README.md) contiennent les règles complètes C01–C11, la méthode S01 ou S02 et le workflow IA A01–A15. Les exports de `config/`, `schemas/` et `prompts/` évitent une transcription manuelle. Les contrôles vérifient leur concordance. Le nom `parametres_figes_v3.json` et sa version technique 3.0.0 restent inchangés : la version documentaire 3.1.0 ajoute l'intégration IA sans modifier ce noyau.

Une contradiction entre texte, JSON et implémentation doit être signalée et résolue avant de poursuivre le composant concerné. Aucun paramètre ne doit être ajusté silencieusement au cours du portage.

La [référence utilisateur](../references/README.md), les anciennes simulations et les outils de travail d'autres projets ne sont pas des instructions normatives. Le registre de nettoyage permet de récupérer les anciens essais si une vérification historique les nécessite.

## Composants et travail restant

| Composant | Contrat à respecter | Point d'attention |
|---|---|---|
| Adaptateur de marché et d'exécution | C03, C06–C09 | Construit contre le faux SDK ; Bid/Ask, minimum, pas, marge, frais, rejets et rapprochement à confronter au terminal en 13.1 |
| Moteur EMA indépendant | S01 | Moteur pur construit dans sa lignée ; intégration complète au compte restant à réaliser |
| Moteur London indépendant | S02 | Moteur pur figé et couture S3 réalisée ; sorties C08 construites et exécutées en papier |
| Coordonnateur de compte partagé | C06–C09 | Coordinateur unique construit en phases 5 et 6 ; cycle, sorties et rapprochement sur preuves ; persistance SQLite et adaptateur physique construits en phase 11, qualification du poste en 13.1 |
| Contrôles fondamentaux obligatoires | C05 | Cinq couches communes figées dans mcl/london-controles-fondamentaux ; permissions et calendrier causaux, heartbeat et reprise ; lecteurs physiques construits en phase 11 ; producteur externe et qualification restent nécessaires |
| Service d'IA distant partagé | A01–A11 | Collecte officielle, preuve textuelle, qualification des API, budgets transactionnels et cache |
| Interface du complément IA | A08–A12 | Lecteur, cache et producteur physique construits ; service partagé figé en phase 12, qualification API/RSS en 13.6 |
| Journal et moteur de rejeu | C10–C11, A13–A15 | Huit unités communes figées ; traces causales, coûts complets et comparaison A/B, validation financière réelle restant à effectuer |

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

Le [plan d'implémentation intégrale du robot London](robot_london_v3/README.md) (`LONDON_V3`, version 1.4.13 du 25 novembre 2026, validé par l'utilisateur) décline cet ordre en phases MCL avec points d'arrêt ; ses décisions et arbitrages de spécification sont arrêtés. Ses phases 0 à 12 se construisent dans le conteneur de développement contre des contrats de frontière finalisés tôt ; les actions réservées à l'humain (poste, compte de démonstration, données, autorisation des API, annotation, mises en service) sont regroupées dans sa phase 13 de qualification.

## Emploi des fonctions de référence

`reference/technical.py` fournit les indicateurs et détecteurs de configurations, sans portefeuille, dimensionnement complet ou modèle de fills. `reference/llm_contracts.py` illustre validation textuelle, causalité, veto et bornes de coût, sans client HTTP, verrouillage concurrent du budget ou persistance de production. Leur [notice](../../reference/README.md) précise les limites.

Les dépendances de `requirements-dev.txt` concernent ces contrôles Python. Deux robots sont en construction, chacun selon son plan : le robot 1 (`EMA_V3`, [plan](PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md)) n'utilise que la bibliothèque standard, le paquet `MetaTrader5` étant réservé à son infrastructure (plan, section 1) ; pour le robot London (`LONDON_V3`, [plan](robot_london_v3/README.md)), le langage et la plateforme sont arrêtés depuis le 5 novembre 2026 : Python 3.13 et MT5, piloté par le paquet officiel `MetaTrader5`, avec les sources dans `src/xpbots/` (décisions D-01 et D-02) ; ses dépendances d'exécution suivent sa décision D-05. Aucun adaptateur factice n'a été ajouté : le code naît phase par phase, selon chaque plan, et l'état MCL de chaque artefact est tenu dans `mcl/`.

Pour les futurs historiques, traces et états privés, utiliser les emplacements exclus `data/raw/`, `data/cache/`, `data/private/`, `runtime/`, `logs/` et `.local/`. Les résultats synthétiques servant de fixtures peuvent être ajoutés explicitement dans `tests/` après revue.

Depuis la phase 9 London, le moteur événementiel commun est figé dans `mcl/orchestration/`. S4 délègue à ce moteur unique ; S7 compose des fabriques London par méthode, symbole et bras et S5 route les réponses et preuves vers des comptes PAPER_AB indépendants. Le journal d’entrées inclut les calculs et résultats courtier normalisés ; son rejeu ne consulte aucun backend. La CLI accepte `--mode PAPER_AB`. Depuis la phase 10, les huit unités du [rejeu commun](../../mcl/london-journal-rejeu/PLAN-MCL.md) sont figées : lecteur intègre, simulateur C10, métriques, bootstrap et rapports. S1/S5 délèguent au bloc ; S7 expose --couts REFERENCE ou STRESS et le rapport NON_VALIDE_FIXTURE. La phase 11 a construit les sources physiques et les commandes `python -m xpbots.app` ; leur qualification externe reste en 13.1 et celle du service IA, construit en phase 12, en 13.6 après H-08. La prochaine sous-étape est 13.1, sur demande explicite.

# Plan MCL — london-execution-coordinateur

## 0. Périmètre

Phase 5 du [plan London](../../docs/architecture/robot_london_v3/README.md) : onze couches 0a à 3 de calculs purs C06 et C07. Les couches 4 à 6 sont cartographiées et esquissées seulement, pour la phase 6. Aucune couture : S4 continue de refuser les vraies cassures de S3.

## 1. Applicabilité

La structure et les règles sont connaissables et stabilisables dans C04, C06–C09, le document 02 §6.4 et les paramètres figés. Aucun prototype exploratoire n'est nécessaire. MCL s'applique à l'échelle composant en mode pur. Son coût est onze régressions intégrales avant les gels, avec sérialisation des niveaux et risque surveillé de contrats spéculatifs.

## 2. Étape 1 et arbitrage de coexistence

Le calculateur reçoit des signaux, cotations, profils C04 et instantanés du compte ; il rend niveaux, échéances, gardes, réservations et volume ou refus. Python 3.13, bibliothèque standard, instants UTC en millisecondes, calculs monétaires décimaux et aucun accès réel au courtier.

L'arbitrage R4/R5 du 06/11/2026 est dans [le registre de coexistence](../../docs/architecture/COEXISTENCE_ROBOT1_LONDON.md). Le paquet d'exécution est unique et commun aux deux méthodes. Il utilise les valeurs du noyau London comme forme canonique ; 0a adapte explicitement les signaux et ticks EMA existants. Les deux noyaux et leurs journaux historiques ne sont pas réécrits. Le dossier MCL préfixé évite de confondre ce composant avec le plan EMA encore vide `mcl/execution-coordinateur`. Cette esquisse EMA n'autorise plus une seconde implémentation.

Le contrôle de reprise sur `master` constate `85069c0`, 532 tests verts, 30 contrôles projet et 288 contrôles de référence verts, trois artefacts amont figés et carte composite verte. Les modifications préexistantes de `.gitattributes` et du CSV synthétique sont conservées hors du commit de cette phase.

## 3. Carte et frontières

Groupes parallèles : 0a types, 0b contrôles, 0c cotation, 0d prix, 0e échéances ; puis 1a port de calcul, 1b gardes, 1c réservations ; puis 2a risque et 2b arbitrage ; puis 3 dimensionnement. Les dépendances directes réelles sont encodées dans `carte.json`, toutes strictes, divergence comprise. Les feuilles consomment uniquement les socles amont ; les adaptateurs EMA sont limités à 0a. Les couches 4, 5a, 5b et 6 restent non construites.

La seule frontière synchrone est le calcul courtier, défini par le port 1a et doublé avec des formules synthétiques contrôlables à la main. La persistance physique du compte et des réservations appartient à l'infrastructure ultérieure ; les états purs sont exportables et restaurables. Les transitions de réservation sont sérialisées par un unique propriétaire de compte, avec numéro de version empêchant une admission sur un instantané périmé. Aucun faux courtier n'est injecté à la place d'une couche interne.

## 4. Contrats, tests et gates

Les quinze contrats sont d'abord esquissés ; les onze contrats de phase 5 sont finalisés juste avant leur code. Chaque couche passe catégorie 1, catégorie 2 si non feuille, `python tools/run_london_tests.py` et `python tools/verify_project.py`, puis est figée sans changement d'arbre entre gate et gel. Checkpoints après les niveaux 1 et 3 ; gate global en sortie. Les fichiers contractuels sont écrits en UTF-8 LF avant le gel.

Les sources de test sont C11.2, C11.5, C11.6, C11.7 et C11.10 au niveau des calculs, C11.13 pour les états de garde, S02.5 et `rounded_levels`. Les égalités sont exactes en décimal. P-04, P-05, P-06 et P-12 sont intégrés aux contrats correspondants. Les mutations sont exécutées sur copies temporaires hors dépôt avec régression intégrale et copie saine vérifiée.

## 5. Bilan

### 5.1 Construction et gels

Les onze couches de phase 5 sont figées, chacune après son gate propre et une régression intégrale des deux lignées. Les quatre couches de phase 6 restent des esquisses sans code. L'artefact complet n'est donc pas déclaré achevé. Les checkpoints après les profondeurs 1 et 3 sont dans `journal.jsonl` ; la carte active impose zéro avertissement et zéro divergence.

| Couche | Unité | Catégorie 1 | Catégorie 2 | Statut de phase 5 |
|---|---|---:|---:|---|
| 0a | Types, états et adaptateurs EMA | 9 | — | Figée après correction |
| 0b | Ports de contrôles | 2 | — | Figée |
| 0c | Garde de cotation | 6 | — | Figée |
| 0d | Prix exécutables | 6 | — | Figée |
| 0e | Échéances de sortie | 4 | — | Figée |
| 1a | Port de calcul courtier | 3 | 1 | Figée |
| 1b | Gardes du compte | 9 | 2 | Figée |
| 1c | Réservations | 8 | 1 | Figée |
| 2a | Risque all-in | 7 | 1 | Figée |
| 2b | Arbitrage partagé | 4 | 2 | Figée |
| 3 | Dimensionnement | 13 | 2 | Figée |
| Total | 80 tests propres | 71 | 9 | Onze couches |

Le total de régression passe de 532 à 613 : les 80 tests du composant et un test transverse de propriété des fichiers communs. Les 79 tests du moteur London et les 35 du squelette demeurent verts. Aucune couture n'est réalisée : S4 continue de refuser les vraies cassures S3, sans commande d'ordre.

### 5.2 Choix fixés dans les contrats

Les deux stratégies partagent le même registre, la même marge et les mêmes plafonds. L'ordre est celui des méthodes puis celui des symboles configurés ; le registre est relu après chaque admission. Le propriétaire de compte sérialise les opérations et le numéro de version interdit une proposition périmée. Cela ne prétend pas implémenter une transaction entre processus ni une persistance physique : celles-ci appartiennent à l'infrastructure future. Les positions externes bloquent l'admission, et les profits flottants ne libèrent pas le risque initial.

Les signaux et clés du noyau London sont la forme canonique. Les adaptateurs 0a acceptent les vrais types EMA ; l'adaptation d'une cotation exige explicitement son heure de réception, et celle du signal refuse une conversion de prix non exactement représentable selon le contrat. Les deux noyaux et leurs journaux ne changent pas. Les nouvelles couches communes sont contrôlées dans les deux cartes composites, sans exclusion croisée. Les moteurs ne sont jamais importés par le coordinateur.

P-04 conserve les deux âges de cotation, P-05 accepte le spread nul et les plafonds inclusifs ; le TTL exact est exclu. Les niveaux sont comparés à `rounded_levels`, le stop short ajoute le spread avant l'arrondi et le TP est recalculé depuis le prix réel sans déplacer le SL. Les échéances utilisent le premier remplissage effectif, les heures de Londres et les pauses natives, y compris une échéance déjà dépassée.

Le port externe fournit les profits et frais USD par volume, la marge isolée et un contrôle natif de marge totale. Le dimensionnement ajoute uniquement la marge des réservations non matérialisées, applique P-06 en décimal à partir de la fraction chargée, contrôle fonds libres et stop-out, et balaie la grille native en ordre décroissant. Il ne suppose ni frais linéaires ni monotonie ; le coût est proportionnel au nombre de volumes parcourus. Il rend une proposition, sans réserve automatique et sans envoi.

Après remplissage, budget et fonds propres de référence restent ceux de la tentative initiale. Le volume de position doit être confirmé ; le prix et les frais d'entrée réels sont fournis, seule la réserve de sortie demeure et le TP est recalculé. Le calcul propose la réduction admissible ou un refus que le futur cycle devra traduire en clôture. L'exemple L-01 donne exactement 0,80 USD à 0,08 lot dans les deux sens avec le port synthétique, sans double comptage du spread.

P-12 reconstitue la base UTC par le livre complet des mouvements, sous preuve d'absence de position à minuit. Les flux externes identifiés sont neutralisés une seule fois, y compris sur le pic antérieur à un arrêt ; un flux non identifié refuse l'environnement. Les arrêts sont restaurables et le global ne se lève que par une nouvelle décision tracée. Le contrôle fondamental neutre reste un scénario technique explicitement nommé ; le complément IA absent ne crée aucune permission.

### 5.3 Corrections et problèmes rencontrés

| Identifiant | Type et preuve | Source | Gravité | Correction et validation |
|---|---|---|---|---|
| P5-01 | Défaut de contrat : le maximum de zéro et de la perte, avec frais nuls qualifiés, peut donner un risque exactement nul | 0a `Reservation` | Admission incorrectement refusée | Défigeage `correction` tracé ; risque non négatif et volume strictement positif ; la place reste occupée ; test exact et nouveau gate intégral avant regel |
| P5-02 | Défaut de restauration : une entrée mal typée pouvait être hachée avant sa validation | 0a collections | Exception hors contrat | Même défigeage 0a ; validation des éléments avant unicité ; entrée non hachable capturée par test ; consommateurs revalidés |
| P5-03 | Défaut local capturé avant gel : retrait identifié pendant arrêt non répercuté sur l'ancien pic | 1b reprise P-12 | Faux arrêt global | Références et mouvements de flux mémorisés dans la base reconstituée ; translation du pic sur les seuls flux nouveaux ; test reproduisant le faux arrêt puis gate vert |
| P5-04 | Contradiction descriptive : anciens documents annonçant l'absence de tout calcul partagé | Guide, plans et skill risque | Passation trompeuse | Documentation alignée sur les sources observées ; copie de skill régénérée par l'outil canonique |
| P5-05 | Artefact généré parasite relevé par la porte de gouvernance | Cache local `agent_lifecycle.cpython-313.pyc` | Porte bloquante | Fichier généré inspecté puis retiré ; relance avec `-B`, porte de gouvernance verte sans toucher au moteur |
| P5-06 | Ressources du poste épuisées lors de vérifications concurrentes, puis interruption avant rapports finaux | `WinError 1450`, erreur d'allocation NumPy et rapports absents | Résultats non recevables | Exécutions invalidées ; relances isolées avec fils numériques limités ; journal progressif des mutations lié à l'empreinte des sources, sans modification du harnais de phase 4 |

P5-01 et P5-02 sont un seul défigeage formel de 0a. P5-03 relève de la construction locale avant son premier gel, et non d'un changement silencieux de contrat figé. Aucun artefact amont n'est défigé. Les ressources normatives, paramètres, preuves historiques et dépendances ne sont pas modifiés.

### 5.4 Vérification adversariale et sortie

La campagne reproductible `python tools/verifier_mutations_execution_phase5.py --ouvriers 2 --journal-progressif .local/reports/mutations_execution_phase5_progression.jsonl --rapport .local/reports/mutations_execution_phase5_passe2.json` injecte 29 défauts sur copies temporaires hors dépôt, avec une copie saine et la régression intégrale pour chacun. Limiter `OPENBLAS_NUM_THREADS` et `OMP_NUM_THREADS` à 1 sur le poste contraint en mémoire. Le journal conserve chaque résultat validé et refuse toute reprise si les sources, cartes ou paramètres ont changé. Les erreurs de ressources et les échecs sans test propre au composant ne comptent pas comme détection. La campagne achevée le 07/11/2026 détecte les 29 mutations distinctes, sans survivante et sans nouvelle correction du composant. Chaque mutation termine les 613 tests et échoue sur au moins un test propre au coordinateur ; les identifiants exacts sont conservés dans le rapport. La copie saine passe également les 613 tests. La première exécution interrompue sans rapport final n’est pas comptée comme une campagne validée.

| Couche | Mutations distinctes | Détectées |
|---|---:|---:|
| 0a | 2 | 2 |
| 0b | 1 | 1 |
| 0c | 4 | 4 |
| 0d | 2 | 2 |
| 0e | 1 | 1 |
| 1a | 1 | 1 |
| 1b | 4 | 4 |
| 1c | 4 | 4 |
| 2a | 3 | 3 |
| 2b | 2 | 2 |
| 3 | 5 | 5 |
| Total | 29 | 29 |

Les gates de construction vérifient 613 tests, puis 30 contrôles projet et 288 contrôles de référence. La sortie ajoute le gate global, la vérification des quatorze cartes, le validateur du plan London, les portes du cycle de vie et la gouvernance sur les seuls blobs préparés pour Git. Sous Windows, l'archive de vérification est créée avec `core.autocrlf=false`, puis ses octets CSV sont comparés au blob. Les deux modifications initiales de l'utilisateur restent hors index. Cette précaution reproduit les fichiers publiés sans inclure le cache local verrouillé ni lire `.env`.

### 5.5 Audit bidirectionnel et couverture

| Exigence autorisée | Résultat et fichiers concernés |
|---|---|
| Construire C06/C07, onze couches avec contrats avant code | `src/xpbots/execution/c*`, contrats, carte et journal du présent dossier ; tests propres et double externe `calculs_execution` |
| Partager un seul compte entre les deux méthodes | Arbitrage R4/R5, adaptateurs 0a, registre `lignees`, test transverse et deux cartes composites ; esquisse EMA conservée comme historique |
| Respecter MCL, checks et mutations | Gates de chaque couche, checkpoints 1 et 3, lanceur de mutations réutilisant le harnais existant, bilan et preuves de sortie |
| Préparer une reprise exacte, sans couture en phase 5 | Plan directeur 1.4.6, documents 02/03/04/08, guide, plans EMA et London, passation phase 6 et registre des coutures |
| Conserver les règles métier et publier uniquement le périmètre | Ressources protégées intactes, aucun ajout de dépendance ; attribution Git de session ; modifications initiales exclues |
| Achever le cycle de gouvernance | Orchestrateur, règles descriptives et skill risque actualisées, miroir généré, audit et portes machine |

L'inventaire des types de tâches est couvert : construction et gel par MCL et planification ; calculs par risque/exécution et qualification synthétique ; documentation par cohérence ; publication selon la passation ; maintenance des ressources descriptives par gouvernance ; contrôle final par audit et détecteur de lacunes. Aucune lacune de workflow nouvelle ne nécessite une skill ou une entrée de registre. L'actualisation de la skill risque corrige son état des ressources, sans ajouter de règle métier.

La phase ne qualifie aucun compte réel, aucune API, aucun instrument et aucune rentabilité. Elle ne construit ni cycle d'ordre, ni sorties effectives, ni rapprochement, ni infrastructure de stockage, ni couture S4. La prochaine demande explicite sera la phase 6 dans ce même dossier.

### 5.6 Publication et clôture

Le commit portant ce bilan publie la phase 5 sur `origin/master`, sans réécriture d’historique et sans pull request. Le contrôle machine relie les 83 fichiers préparés aux six groupes d’exigences du §5.5, vérifie les 39 fichiers contractuels par empreinte et par comparaison à leurs blobs, puis compare l’arbre testé à l’arbre publié. Les deux modifications préexistantes sont préservées hors commit.

Les contrôles de sortie comprennent le gate global, les quatorze cartes strictes, le plan London, les portes machine, les 30 contrôles projet, les 288 contrôles de référence et la gouvernance 8/8. La suite des deux robots est aussi relancée sur une archive des seuls blobs préparés. La gouvernance a été vérifiée sur une archive antérieure dont aucun fichier de gouvernance n’a changé ; les différences finales sont vérifiées explicitement. Les incidents de cache et de ressources ont été résolus dans la passe de remédiation décrite au §5.3, sans correction métier supplémentaire.

Les preuves machine courantes sont dans `.local/reports/` : rapports de mutations et progression, cartes, portes, gouvernance de publication, tests de publication et audit de complétion. Elles restent des résultats de travail ignorés par Git, distincts des preuves historiques protégées. La passation décrit la phase 6 ; aucune de ses quatre couches n’est implémentée ici.

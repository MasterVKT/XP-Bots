# Plan MCL — london-execution-coordinateur

## 0. Périmètre

Phases 5 et 6 du [plan London](../../docs/architecture/robot_london_v3/README.md) : onze couches 0a à 3 de calculs purs C06/C07, puis cycle d'ordre, sorties, reprise et enveloppe C08. Le §5 conserve le bilan historique de phase 5 ; le §6 suit la phase 6 et sa couture S4.

## 1. Applicabilité

La structure et les règles sont connaissables et stabilisables dans C04, C06–C09, le document 02 §6.4 et les paramètres figés. Aucun prototype exploratoire n'est nécessaire. MCL s'applique à l'échelle composant en mode pur. Son coût comprend quinze régressions intégrales avant les gels, plus les transitions et reprises correctives, avec sérialisation des niveaux et risque surveillé de contrats spéculatifs.

## 2. Étape 1 et arbitrage de coexistence

Le calculateur reçoit des signaux, cotations, profils C04 et instantanés du compte ; il rend niveaux, échéances, gardes, réservations et volume ou refus. Python 3.13, bibliothèque standard, instants UTC en millisecondes, calculs monétaires décimaux et aucun accès réel au courtier.

L'arbitrage R4/R5 du 06/11/2026 est dans [le registre de coexistence](../../docs/architecture/COEXISTENCE_ROBOT1_LONDON.md). Le paquet d'exécution est unique et commun aux deux méthodes. Il utilise les valeurs du noyau London comme forme canonique ; 0a adapte explicitement les signaux et ticks EMA existants. Les deux noyaux et leurs journaux historiques ne sont pas réécrits. Le dossier MCL préfixé évite de confondre ce composant avec le plan EMA encore vide `mcl/execution-coordinateur`. Cette esquisse EMA n'autorise plus une seconde implémentation.

Le contrôle de reprise sur `master` constate `85069c0`, 532 tests verts, 30 contrôles projet et 288 contrôles de référence verts, trois artefacts amont figés et carte composite verte. Les modifications préexistantes de `.gitattributes` et du CSV synthétique sont conservées hors du commit de cette phase.

## 3. Carte et frontières

Groupes parallèles : 0a types, 0b contrôles, 0c cotation, 0d prix, 0e échéances ; puis 1a port de calcul, 1b gardes, 1c réservations ; puis 2a risque et 2b arbitrage ; puis 3 dimensionnement, 4 cycle, 5a sorties et 5b reprise, 6 coordinateur. Les dépendances directes réelles sont encodées dans `carte.json`, toutes strictes, divergence comprise. Les feuilles consomment uniquement les socles amont ; les adaptateurs EMA sont limités à 0a.

La seule frontière synchrone est le calcul courtier, défini par le port 1a et doublé avec des formules synthétiques contrôlables à la main. La persistance physique du compte et des réservations appartient à l'infrastructure ultérieure ; les états purs sont exportables et restaurables. Les transitions de réservation sont sérialisées par un unique propriétaire de compte, avec numéro de version empêchant une admission sur un instantané périmé. Aucun faux courtier n'est injecté à la place d'une couche interne.

## 4. Contrats, tests et gates

Les quinze contrats sont d'abord esquissés ; les onze contrats de phase 5 sont finalisés juste avant leur code. Chaque couche passe catégorie 1, catégorie 2 si non feuille, `python tools/run_london_tests.py` et `python tools/verify_project.py`, puis est figée sans changement d'arbre entre gate et gel. Checkpoints après les niveaux 1 et 3 ; gate global en sortie. Les fichiers contractuels sont écrits en UTF-8 LF avant le gel.

Les sources de test sont C11.2, C11.5, C11.6, C11.7 et C11.10 au niveau des calculs, C11.13 pour les états de garde, S02.5 et `rounded_levels`. Les égalités sont exactes en décimal. P-04, P-05, P-06 et P-12 sont intégrés aux contrats correspondants. Les mutations sont exécutées sur copies temporaires hors dépôt avec régression intégrale et copie saine vérifiée.

## 5. Bilan de phase 5 — historique

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

## 6. Bilan de phase 6 — construction du 07 au 08/11/2026

### 6.1 Entrée et applicabilité

La demande explicite porte sur toute la phase 6, avec cycle d'ordre, sorties, reprise, enveloppe et couture S4, puis publication et arrêt avant la phase 7. Le contrôle initial constate `4213a07` sur `master` et `origin/master`, 613 tests verts, les ressources métier vertes, les trois artefacts amont figés et les onze couches de phase 5 figées. Les empreintes des deux modifications initiales sont conservées dans le rapport de travail et elles resteront hors commit.

C08 et les décisions du plan stabilisent la machine à états : MCL reste applicable sans prototype exploratoire. La couche 4 est une composante cyclique construite par transitions successives ; un contrôle catégorie 1 suit chaque ajout avant le gate intégral et le gel. Les couches 5a et 5b dépendent du cycle figé, puis 6 les compose ; checkpoint après le niveau 6. Les frontières externes sont les observations et actions du courtier, les calculs C04 et la transaction de stockage. Le cœur reçoit des valeurs, rend commandes et états, et ne lit aucune horloge ni fichier. Les doublures sont limitées à ces frontières.

### 6.2 Besoins amont identifiés avant construction

Le domaine ne nomme pas encore les clôtures obligatoires pour protection défaillante ou risque excessif après remplissage. Deux causes internes additives sont nécessaires, sans nouveau motif C09 ni changement d'une règle : `PROTECTION` et `RISQUE_APRES_REMPLISSAGE`. Elles seront ajoutées par défigeage `extension` de `mcl/noyau` 1c, avec contrat, test exact, gate intégral et regel avant le cycle.

Le registre expose le verrouillage mais pas la levée d'un verrou après preuve native de rapprochement. Une extension de `mcl/london-execution-coordinateur` 1c ajoutera `deverrouiller`, idempotent et limité au verrou nommé ; la décision de lever appartient à la couche 5b après rapprochement confirmé, jamais à une expiration. Le risque initial et les autres verrous sont conservés. Cette extension sera également testée, passée au gate et regelée avant les consommateurs.

### 6.3 Carte, frontière de stockage et couture

Les quatre paquets cartographiés sont `c4_cycle`, `c5a_sorties`, `c5b_reprise` et `c6_coordinateur`. Toute dépendance directe réellement nécessaire sera déclarée dans la carte. Le choix R4/R5 d'un seul coordinateur de compte demeure : aucune seconde implémentation EMA.

L'intention et sa réservation doivent être confirmées par la frontière de stockage avant l'envoi. Les états purs et les commandes distingueront cette confirmation d'un accusé du courtier ; un redémarrage rapprochera toute intention non terminale avant les admissions. La persistance physique reste une responsabilité de l'infrastructure de phase 11 ; le chemin papier emploiera une frontière mémoire explicite, jamais présentée comme stockage réel.

S4 minimal sera supprimé après gel de l'enveloppe. Le squelette recevra de vrais signaux, des profils synthétiques explicites, le contrôle technique neutre nommé et les réponses de S5 avant les nouvelles décisions. S5 restera un exécuteur papier minimal, sans prétendre réaliser le simulateur financier C10 de phase 10.

### 6.4 Interaction avec la garde de non-recopie

Le premier parcours du cycle a cinq tests verts ; sa régression à 620 tests révèle deux égalités numériques fortuites relevées par la garde EMA, qui contrôle aussi le code commun : 1 000 pour convertir s en ms et huit octets pour le hash d'identité. Il ne s'agit pas des paramètres de préchargement ou de repli. La correction de la garde limite explicitement chaque exception au fichier **et à la fonction** technique concernés. Un test négatif conserve l'interdiction des mêmes nombres dans le calcul de risque et dans tout autre module. Aucun paramètre métier ni son contrôle général n'est modifié.

### 6.5 Bloc 0 à 6 figé avant couture

Les quinze couches sont figées après leur construction. La couche 4 a été construite par transitions, chacune passée en catégorie 1 et en régression intégrale ; ses 32 tests de contrat et deux de jonction couvrent envoi protégé, accusés, premiers volumes positifs, reliquat annulé, retard de réponse, rapprochement rapide puis lent, alerte unique, protections, réduction et clôture confirmée. Une réduction en cours est rapprochée sans nouvelle quantité envoyée ; un refus natif confirmé permet un nouvel essai. Le budget et le risque initial restent engagés jusqu'à clôture et fin du reliquat.

5a sélectionne les sorties à partir des vraies échéances 0e, des gardes restaurées et du port C05. 5b exige propriété D-08, ticket et volume, ainsi que SL/TP natifs courants ; le netting demande une exclusivité explicite. Une disparition ou un historique vide ne prouve jamais une clôture. Les ordres de sortie sont distingués des reliquats d'entrée et ne remplacent pas leurs tickets.

6 compose les vraies couches sur un compte partagé. Les entrées préparées restent hors des commandes autorisées jusqu'à la preuve de persistance ; les contrôles sont relus juste avant transmission, avec le vrai calcul 3 appliqué au volume exact et au budget initial. Le timeout d'accusé démarre à cette transmission, et le TTL garde sa borne initiale. Une intention unique conserve les tentatives P-08. Les réponses natives et les clôtures précèdent les nouvelles admissions ; seul le premier volume réel consomme le quota. Un SL défaillant bloque les nouvelles entrées du compte pendant sa sécurisation.

| Périmètre actuel | Catégorie 1 | Catégorie 2 | Total |
|---|---:|---:|---:|
| Couches 0a à 3, extensions comprises | 74 | 9 | 83 |
| 4 cycle | 32 | 2 | 34 |
| 5a sorties | 7 | 2 | 9 |
| 5b reprise | 12 | 2 | 14 |
| 6 coordinateur | 25 | 4 | 29 |
| Composant commun | 150 | 19 | 169 |

La régression avant couture comporte 704 tests des deux robots, 30 contrôles projet et 288 contrôles de référence verts. Les données et fonctions de calcul externes restent synthétiques ; aucune API ni aucun courtier n'est appelé. À ce point, la couture S4/S5/S7, la démonstration de bout en bout, les mutations et les vérifications de publication restent à achever ; la bibliothèque seule n'est pas déclarée être la fin de phase.

### 6.6 Défigeages et corrections de construction

Le journal outillé trace les extensions du domaine 1c (`PROTECTION`, `RISQUE_APRES_REMPLISSAGE`), du registre 1c (`deverrouiller`) et de 3 (`revalider_avant_envoi`). Elles répondent à des besoins concrets de C08 sans toucher aux paramètres, motifs ou règles des méthodes. Le recontrôle financier ne compte pas deux fois sa réservation et conserve son risque gelé ; une version changée pendant un appel externe refuse l'envoi.

Les corrections formelles de 4 écartent une échéance TP déjà inactive lors d'une sortie, empêchent le renvoi d'une réduction en cours, et conservent l'ancrage d'incertitude dérivé du timeout lors d'une reprise tardive. L'extension de 5b distingue les ordres natifs d'entrée et de clôture. Sa modification de snapshot impose les protections courantes ; son [arbitrage](decisions/2026-11-07-protections-natives.md) et l'adaptation du consommateur 6 encore non gelé sont tracés. Chaque défigeage est suivi de son gate intégral et de son regel.

Les échecs locaux avant premier gel ont aussi capturé une transition intermédiaire invalide lors de l'annulation d'un reliquat, des indices numériques mal interprétés par la garde de non-recopie, deux noms de champs de tests erronés et une fixture faisant baisser l'équité de 1 000 à 100 USD, ce qui déclenchait correctement l'arrêt global. Ils ont été corrigés à la source avant les gels, sans désactiver de contrôle. Ces boucles de construction ne constituent pas les passes correctives de l'audit final de phase.

### 6.7 Couture et régression après intégration

S4 est remplacé par le vrai `CoordinateurCompte` ; l'ancien module d'exécution minimal est supprimé,
sans chemin de repli. Les interfaces de couture S1, S4, S5, S6 et S7 sont tracées dans le
[registre](../squelette/COUTURES.md). Le point d'entrée compose le coordinateur via l'orchestration
afin de conserver la carte composite et D-18 ; il n'importe pas directement la couche d'exécution.

Le pilote groupe les ticks au même instant de réception. Les faits natifs et issues sont appliqués
avant toute nouvelle bougie ; les intentions simultanées arrivent en un lot pour l'arbitrage commun.
Une échéance sans tick avance seulement le temps et le compte papier. Au même instant, le SL/TP
natif prime la sortie marché. L'autorisation d'entrée exige la preuve du stockage mémoire ; sa panne
ne bloque pas les commandes de sécurité. La transaction mémoire ne constitue pas un stockage durable.

Les profils, tailles de contrat et grilles de volume sont explicitement synthétiques : point=tick,
IOC, coûts nuls connus, marge à levier constant. Le scénario `TECHNICAL_CONTROL_NEUTRAL` est requis
par la commande. Ces conventions ne qualifient aucun compte C04 et ne réalisent pas le simulateur
C10. Le journal canonique conserve les mêmes clés d'intention, leurs tentatives et les seules issues
confirmées, le compte et les profils ; il sérialise les dates des gardes au format ISO.

La démonstration rejoue l'été et l'hiver avec préchargement complet, vrais signaux London, ordres
protégés, remplissage au tick suivant et clôture native. Un autre essai place GBPUSD avant EURUSD
au même instant et obtient l'ordre de demandes EURUSD puis GBPUSD. Les anciens tests minimaux sont
migrés dans la même couture : 37 tests du squelette. Après la correction tardive de 4 (33 catégorie 1
et 2 catégorie 2), le coordinateur compte 170 tests propres, dont 151 catégorie 1 et 19 catégorie 2.
La régression complète passe de 613 à 707 tests, les deux lignées réunies.

### 6.8 Inventaire des problèmes et remédiation

| Identifiant | Type et preuve | Source | Correction et validation |
|---|---|---|---|
| P6-01 | Besoins amont absents : causes de clôture et levée de verrou | Domaine 1c et registre 1c | Extensions additives formelles, tests, gates intégraux et gels ; risque initial conservé |
| P6-02 | Confirmation de stockage exigeant une revalidation financière sans recopier C07 | Dimensionnement 3 | Extension `revalider_avant_envoi`, volume et budget d'origine, réservation propre exclue du calcul seulement, version recontrôlée |
| P6-03 | Minuterie TP devenue inactive, réduction en cours et reprise tardive | Cycle 4 | Corrections formelles ; aucune retransmission de sortie ambiguë ; ancrage du timeout conservé ; tests et regels |
| P6-04 | Snapshot de reprise pouvant masquer un SL supprimé depuis le journal | Reprise 5b | Modification tracée du contrat : SL/TP natifs courants obligatoires ; propriété vérifiée avant protection ; consommateur 6 adapté avant son gel |
| P6-05 | Accusé de sortie inconnu après clôture native réactivant un rapprochement | Cycle 4 | Défaut reproduit en état CLOTUREE ; défigeage correction, test des accusés et annulations tardifs, aucun ordre ni minuterie après clôture ; gate à 707 puis regel |
| P6-06 | Date de garde non sérialisable et anciennes attentes S4 minimales | Couture et tests du squelette | Adaptation ISO dans le journal, attentes fondées sur le vrai contrôle et les faits natifs ; suite complète et bout en bout verts |
| P6-07 | Ancien état descriptif annonçant le cycle restant à construire | Plans, guide, règles, skill risque et passation | États factuels et version 1.4.7 alignés ; miroir régénéré ; contrôles documentaires et gouvernance |

Les corrections de construction précèdent l'audit final ; elles ne sont pas des tentatives de masquer
un contrôle. Aucun paramètre, coût, seuil, export normatif, dépendance ou preuve historique ne change.

### 6.9 Vérification adversariale

La commande `python tools/verifier_mutations_execution_phase6.py --ouvriers 1 --journal-progressif .local/reports/mutations_execution_phase6_progression.jsonl`
détecte les 19 mutations distinctes, sans survivante. La copie saine et chaque variante terminent les
707 tests des deux robots. Les motifs sont uniques et syntaxiquement valides ; chaque détection
implique un test fonctionnel du coordinateur ou de la couture concernée. Le rapport et le journal
progressif, liés aux empreintes des sources, restent sous `.local/reports/`. Les erreurs de mémoire
et les seuls échecs de carte ne comptent pas comme détection. Aucune mutation ne modifie le dépôt.

| Périmètre | Mutations détectées |
|---|---:|
| 4 : premier fill, reliquat, ACK inconnu et cadence | 4 |
| 5a : échéance exacte, priorité et FLATTEN | 3 |
| 5b : propriété, protections courantes et netting | 3 |
| 6 : TTL, C05, sécurité SL et revalidation | 4 |
| S4, S5, S7 : issue, prix, protections, doublons et scénario explicite | 5 |
| Total | 19 |

### 6.10 Sortie et limites

Le checkpoint CP6 est journalisé après le bloc 0 à 6 ; le gate global final revalide le bloc après
couture. La sortie contrôle les quatorze cartes strictes, le plan London, les portes machine, les
30 contrôles projet et les 288 contrôles de référence. La gouvernance et la suite des deux robots
sont vérifiées aussi sur une archive des seuls blobs préparés, obtenue avec `core.autocrlf=false`.
L'audit relie chaque fichier publié à une exigence, les contrats à leurs empreintes de gel, et l'arbre
testé à l'arbre du commit puis de `origin/master`. Les deux modifications initiales restent hors index.

Le commit portant ce bilan clôt la phase 6 sans réécriture d'historique ni pull request. La passation
prépare la phase 7 ; aucun producteur fondamental, lecteur IA, disque, terminal ou simulateur C10
n'est construit par anticipation. L'EMA conserve son squelette et consommera le coordinateur unique.
Les résultats synthétiques n'établissent ni qualification de courtier ni rentabilité.

Le premier collecteur de portes a refusé la sortie vide du moteur de cycle de vie sous la console
Windows. La relance avec la liste explicite des fichiers et `python -X utf8` pour cette seule commande
produit le rapport complet : cinq portes réussies, aucune troncature. Le code du hook reste intact ;
aucun encodage global n'est imposé aux tests historiques EMA.

### 6.11 Limite préexistante de la gouvernance Windows

La suite de gouvernance exécutée sur l'archive de publication termine sept étapes sur huit.
Seul `test_powershell_launcher_when_available` dépasse son délai de 120 secondes. Ce même test
échoue avec le même dépassement sur une archive exacte du commit initial `4213a07` : le défaut
est préexistant à la phase 6. Les sources des hooks et de leurs tests sont inchangées. Les essais
de démarrage PowerShell, avec et sans cache de modules isolé et sur les deux architectures
disponibles, dépassent aussi leur délai. Aucun test n'est ignoré ou désactivé, aucun délai augmenté.

Les cinq portes bloquantes applicables aux fichiers modifiés réussissent, dont le contrat de
gouvernance. Les 707 tests des robots, les contrôles projet et les références passent aussi sur
l'archive Git exacte. Cette limite du lanceur d'agent n'invalide pas les cas C08 hors ligne ; elle
reste explicitement à résoudre dans l'environnement Windows avant de déclarer ce lanceur qualifié.
Le rapport brut de gouvernance en échec et la comparaison au commit initial sont conservés sous
`.local/reports/`, sans transformer le résultat en réussite 8/8. La publication de phase 6 conserve
cette limite et ne déclare aucune mise en service réelle.

### Phase 10 — correction du prix Ask de stress

Le contrat 0d a été formellement défigé en modification : l’Ask exact imposé par
C10 (Bid + 1,25 × spread) peut tomber entre deux incréments natifs. C06 arrondit
les protections, sans prescrire cet arrondi de la cotation de stress. Le test
rouge a précédé le retrait de cette restriction locale. Les couches 0d, 2a, 3,
4, 5a, 5b et 6 ont toutes repassé leurs gates intégraux ; checkpoint enregistré.
Les deux fichiers contractuels révisés sont la fiche 0d et son test propre.
L’interface publique et les protections sur grille restent conservées. Preuves
et arbitrage : [DEFIGEAGE-0d-PHASE10.md](DEFIGEAGE-0d-PHASE10.md).

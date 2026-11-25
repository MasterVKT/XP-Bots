# Plan MCL — service IA commun, phase 12 London

## 0. Périmètre

L’artefact est un composant neuf partagé A04–A12 sous xpbots.service_ia. Le
dossier EMA service-ia reste une esquisse historique, selon l’arbitrage R4/R5
du 17/11/2026. Il fournit collecte, classification, notes, budget et snapshot,
jamais une permission C05 ni une décision d’ordre. La phase 13 reste exclue.

## 1. Applicabilité

La structure est connaissable, les contrats sont stabilisables et aucun
prototype n’est requis pour comprendre les règles déterministes. MCL est
applicable. Le grand nombre de frontières externes réduit le bénéfice des
doublures internes ; la régression intégrale croît à chaque gel. La couture
composite conserve le chemin démontrable du robot pendant la construction.

## 2. Cible et décomposition

Les entrées sont les ressources figées, textes RSS officiels, calendrier D12,
mapping issuer/type versionné, métriques calculées par le code, profils de
routes qualifiés et temps UTC explicite. Les sorties sont les archives SQLite,
notes séparées, alertes locales déterministes et snapshot A10. Python 3.13 et
la bibliothèque standard sont imposés. Aucun réseau ni secret n’est utilisé
dans les essais ; les fournisseurs sont NON_QUALIFIE avant 13.6.

Le flux collecte → nettoyage → job → enveloppe bornée → réservation → appel →
validation → veto → snapshot fait apparaître document, requête, tentative,
réserve, résultat, événement et séquence persistante. Les types constituent la
feuille. Chacune des six transformations de niveau 1 peut être construite sans
les cinq autres. Les trois unités de niveau 2 composent seulement leurs
dépendances déclarées ; le planificateur requiert ces trois blocs. La coquille
4 réalise les ports externes et compose le planificateur et le snapshot.
Cette question-test, et non l’ordre du flux, détermine le DAG ci-dessous.

## 3. Carte réelle

| Couche | Unité | Dépendances internes | Responsabilité |
|---|---|---|---|
| 0 | types | amonts canoniques | Définir les ressources IA immuables, documents, jobs, réponses et ports externes. |
| 1a | tokens | types | Borner le corps complet hors secret et réduire seulement des passages cohérents. |
| 1b | validation | types | Valider strictement extraction et notes selon les schémas exportés. |
| 1c | normalisation | types | Nettoyer les flux officiels et préserver identité, provenance et première connaissance. |
| 1d | budget | types | Admettre et rapprocher coûts, quotas et réservations dans une transaction injectée. |
| 1e | fournisseurs | types | Construire les requêtes A08 et décoder leurs réponses sans transport implicite. |
| 1f | snapshot | types | Former les snapshots A10 avec séquence persistée et validation du lecteur réel. |
| 2a | veto | types, validation | Construire le seul veto A06 après validation et appariement causal du calendrier. |
| 2b | routeur | types, tokens, validation, budget, fournisseurs | Router les jobs dans les délais, quotas et allowlists A08–A09. |
| 2c | collecteur | types, normalisation | Collecter par port HTTP conditionnel, avec redirections et reprises bornées. |
| 3 | planificateur | types, veto, routeur, collecteur, validation, budget | Planifier, dédupliquer et archiver extraction, notes et surveillance de dérive. |
| 4 | service | types, snapshot, planificateur, budget, routeur, collecteur, veto | Composer SQLite, HTTP, calendrier, publication et workers indépendants du robot. |

Les six unités 1a à 1f puis 2a à 2c sont constructibles en parallèle quand
leurs amonts sont gelés ; leurs gates et gels restent individuels. Le travail
de cette session les traite séquentiellement. L’analyse outillée initiale puis
la carte renseignée n’admettent aucune divergence. Les schémas et prompts
sont chargés depuis les exports, sans seuil métier recopié.

## 4. Contrats, frontières et validation

Les contrats sont esquissés dès la carte et finalisés juste avant chaque
couche. Les ports HTTP, transaction, publication et temps sont définis dans
[FRONTIERES.md](FRONTIERES.md). Les couches internes emploient ces ports ; seul
le module 4 ouvre des fichiers, SQLite, fils ou connexions HTTP. Il réutilise
l’infrastructure existante lorsque ses garanties correspondent au besoin.

Chaque couche passe catégories 1 et 2, puis la suite complète des deux robots
et verify_project. La feuille n’a pas de catégorie 2. Les checkpoints suivent
les profondeurs 1 et 3 ; le global final rejoue toute la régression. Les cas
A14 et les exigences sont affectés dans [EXIGENCES.md](EXIGENCES.md). Les
mutations sont exécutées sur une copie jetable hors du dépôt.

## 5. Bilan au 25/11/2026

Les douze unités sont figées après contrats finalisés avant code, tests propres,
intégration sur les vraies couches et régression intégrale des deux lignées.
Le composant compte 222 tests : 157 de catégorie 1, dont six contrats API/RSS
différés, et 65 de catégorie 2. La suite entière compte 1 629 tests, dont
1 609 réussis et vingt différés (quatorze contrats MT5 de 13.1 et six contrats
API/RSS de 13.6). Ces nombres incluent les quatre nouvelles gardes transverses.
Les 96 gels et 412 fichiers contractuels amont, vingt ressources protégées et
quinze modifications préexistantes sont conservés. Le dépôt possède désormais
21 cartes strictes et 108 couches gelées ; les composites restent hors gel.

| Couche | Catégorie 1 | Catégorie 2 | Gate intégral avant gel |
|---|---:|---:|---|
| 0 | 7 | — | Vert après précision des gardes de format |
| 1a | 6 | 3 | Vert |
| 1b | 9 | 4 | Vert |
| 1c | 10 | 6 | Vert |
| 1d | 18 | 5 | Vert |
| 1e | 15 | 2 | Vert |
| 1f | 9 | 2 | Vert |
| 2a | 10 | 6 | Vert |
| 2b | 16 | 8 | Vert après correction des délais avant gel |
| 2c | 10 | 6 | Vert |
| 3 | 13 | 16 | Vert après correction A12/A13 |
| 4 | 34, dont six différés | 7 | Vert après correction CLI et extension A11 |

### 5.1 Reprise, carte et checkpoints

La reprise initiale part du commit 37787c65a130c1daccc53552949e6ef300498f77,
avec 1 403 tests, dont quatorze différés. L'arbitrage R4/R5 du 17/11/2026
précède l'initialisation : l'esquisse EMA mcl/service-ia demeure historique.
Les deux composites et la lignée COMMUN désignent l'unique implémentation.
La carte réelle place les six transformations indépendantes au niveau 1 ;
seule l'enveloppe 4 réalise les ports physiques. L'architecture interdit les
imports du robot, de l'exécution, du rejeu, du SDK et de reference dans le service.

CP1 suit un global vert de 1 502 tests, avant le niveau 2. CP3 suit le global
vert de 1 586 tests en 990,455 s ; il est journalisé le 25/11/2026 avant la
construction de 4. Les revues ne demandent aucune révision d'un contrat amont.
Un seul normaliseur, validateur, routeur et registre sert les deux méthodes.
Les deux traitements Retry-After ont des sorties distinctes : durée de route
A08 et échéance de collecte A04, sans duplication d'un seuil exporté.

Après les nouveaux gels correctifs de 3 et 4, le statut outillé signale deux
niveaux figés depuis CP3. CP4 est donc consigné le 25/11/2026 sur le bloc
complet, après le global corrigé vert. La revue ne demande aucune révision
supplémentaire : la suspension appartient au planificateur, les sélecteurs SQL
restent des ports de stockage et les archives/cache A10 gardent leurs rôles
distincts. Aucun code ou contrat n'est changé par ce checkpoint. Le statut
confirme ensuite toutes les couches figées, sans checkpoint dû.

### 5.2 Défauts découverts et défigeages

Le premier gate 0 est rouge : les gardes historiques confondent formats HTTP,
cardinalité d'une paire et urllib.parse avec des seuils ou du réseau. Les
exceptions sont restreintes à leur affectation, fonction et paquet ; quatre
tests négatifs supplémentaires interdisent leur extension arbitraire. Aucun
contrat amont n'est modifié. Le nouveau gate est vert avant le premier gel.

Le premier gate 2b est interrompu avant gel pendant sa revue : Retry-After
immense revenait à zéro et une route ignorée répétait la pause du secours.
Deux tests capturent ces défauts, puis le gate delais passe (1 542 tests,
983,349 s). Le journal conserve le rouge et son code d'interruption ; il
n'existe aucun gel ni défigeage de 2b avant ces corrections. Avant le gel de 3,
le test des audits après quota épuisé corrige aussi la confusion entre une
non-admission, à reporter au jour suivant, et un résultat sémantique invalide.

Le gate initial 4 est vert (1 619 tests, 1 532,559 s). La couche 4 seule est
ensuite défigée en correction : le profil projet_dedie ne représente pas
l'autorisation du secours payant. Deux tests CLI imposent désormais tarif
exporté et choix explicite de paiement ; le nouveau gate audits est vert
(1 621 tests, 1 499,118 s), puis 4 est regelée.

Un second défigeage de 4, de nature extension, termine les raccordements A11 :
fichier optionnel d'agrégats anonymisés vers le vrai port recevoir_metriques,
et affichage déterministe local via l'infrastructure. Cinq tests ajoutent
idempotence durable, refus atomique, causalité, poursuite RSS et absence de
fuite de contenu. Le contrat optionnel est conservateur ; 0 à 3 restent
figées. Le gate a11 complet est vert (1 626 tests, 1 537,955 s) avant le nouveau
gel. Les traces exactes de
gates, empreintes et motifs sont dans le journal MCL versionné.

Une revue adversariale suivante découvre que la suspension empêchait les
nouvelles extractions mais republiait encore un veto déjà actif. Les couches
3 et 4 sont défigées en correction, la seconde pour la preuve du consommateur
physique. Deux tests de jonction et une couture SQLite/fichier reproduisent
le cas avant correction. La sélection des publications filtre désormais les
fournisseurs suspendus sans supprimer leurs archives, y compris après reprise.
Un changement de modèle et deux dérives retirent l'événement ; une seule
dérive reste admise. Le lecteur déjà informé conserve sa preuve jusqu'à sa
fin propre selon A10 : un snapshot vide n'est pas une révocation. Un nouveau
lecteur ne reçoit plus le veto suspendu. Aucune règle du lecteur n'est changée.
Le gate de 3 est vert en 1 383,664 s, celui de 4 en 1 528,485 s, avec nouveaux
gels immédiats. Le global corrigé est vert en 1 337,860 s : 1 629 tests, vingt
différés, puis les 30 contrôles projet et 288 de référence. Les empreintes
des contrats amont restent intactes.

La première campagne de mutations est interrompue pour ce correctif. Ses
preuves sont conservées : M12-01 à M12-03 détectées, M12-04 provoquant bien
deux échecs fonctionnels en catégorie 2. Son filtre attendait par erreur la
catégorie 1 ; il s'agissait d'un défaut de harnais, pas d'un mutant réel
survivant. Le filtre est corrigé et une campagne complète sur la cohorte finale
ajoute M12-14, qui réintroduit la publication des vetos suspendus.

### 5.3 Choix de conception fixés

Les types et ressources sont immuables ; schémas, prompts, fournisseurs,
seuils et tarifs maximaux viennent des exports. Les six oracles sont comparés
uniquement dans les tests : parse_model_output, parse_advisory_output,
build_policy_event, make_snapshot, reserve_cost_usd et budget_admits.
La borne UTF-8 porte sur l'enveloppe complète hors secret et les preuves
réellement transmises. Une extraction n'est jamais tronquée. Les notes ne
citent que les documents et métriques du dossier effectivement envoyé.

L'identité d'un texte préserve publication et première vue, y compris lors
des corrections et republications. L'archive conserve l'heure de connaissance
du contenu. L'appariement A06 emploie la vraie garde C05, D12, une importance
native et un mapping issuer/type versionné et complet ; aucune absence
d'annonce n'est inventée. Les preuves de refus et de veto sont archivées.
Le calendrier physique conserve versions, disponibilités et compteur durable,
y compris à timestamps égaux ; la mémoire n'avance qu'après COMMIT.

La réservation Decimal est atomique avant HTTP. SQLite emploie WAL/FULL et
BEGIN IMMEDIATE ; deux connexions concurrentes éprouvent le registre réel.
Les modifications imbriquées persistent sans alias. L'usage brut est conservé
même si la sortie est inutilisable ; un usage absent conserve sa réserve,
sur son mois original. La reprise ne réinfère pas et suspend les nouveaux
appels tant que les usages antérieurs inconnus restent à rapprocher.
Les profils incomplets, la gratuité non prouvée et le payant non autorisé
ne deviennent jamais admissibles par la simple présence d'une clé.

Les codecs A08 ne transportent rien. L'ouvreur physique est inactif par défaut,
limite endpoints, en-têtes, délais, octets et redirections, ferme les réponses
et rejette la réflexion d'une clé synthétique. Les trois boucles séparent
collecte, inférence unique et heartbeat. Le writer réserve la séquence avant
l'écriture atomique existante, préserve l'ancien fichier à échec et ne prolonge
jamais le veto. Verrous et manifeste empêchent deux producteurs ou le reset
silencieux de la base. Les alertes affichées restent locales et sans contenu
API. Les agrégats du code sont importés atomiquement ; aucune performance
n'est recalculée par l'IA. Les hypothèses sont des tickets versionnés bornés
par le plafond mensuel commun. Dérive et changements de modèle persistent
la suspension ; aucun redémarrage ne vaut requalification A13.

### 5.4 Couture réelle et vérification adversariale

La couture est additive : le service produit le fichier A10 consommé par
le lecteur réel existant et le moteur London PAPER_AB, sans nouveau moteur
ni appel synchrone signal→ordre. Six séances complètes été/hiver couvrent
snapshot valide, absent et corrompu. Avec veto valide, REFERENCE remplit à
08:15 et IA attend le nouveau signal de 08:30 ; l'expiration à 08:22 ne
rattrape aucun ancien signal. Sans fichier valide, les bras remplissent
le même premier signal. Une autre séance maintient l'appel en cours vingt
secondes pendant l'entrée : les deux bras décident avant la réponse ; les
archives ultérieures ne réécrivent pas ces décisions. Un seul appel produit
l'événement commun et un seul registre reçoit son coût.

Quatorze mutations sont exécutées sur copies jetables hors dépôt : une par
unité et une sur la couture IPC/PAPER_AB. Chaque copie part d'une baseline
entièrement verte, puis chaque mutant rejoue toute la suite. Les quatorze sont
détectées par des tests de comportement ; erreurs d'import, syntaxe ou garde
SDK ne valent pas détection. La restauration des octets et empreintes est
vérifiée après chaque mutant. Le catalogue détaillé figure ci-dessous.

| Mutation | Couche | Changement réellement injecté |
|---|---|---|
| M12-01 | 0 | Accepter les doublons d'en-têtes à casse différente |
| M12-02 | 1a | Omettre la réserve UTF-8 de l'enveloppe |
| M12-03 | 1b | Accepter une citation absente du texte envoyé |
| M12-04 | 1c | Renouveler la première vue à la republication |
| M12-05 | 1d | Refuser la borne budgétaire inclusive |
| M12-06 | 1e | Facturer les tokens de sortie comme ceux d'entrée |
| M12-07 | 1f | Publier sans les événements validés |
| M12-08 | 2a | Ouvrir la borne fermée d'appariement calendrier |
| M12-09 | 2b | Autoriser le secours payant par défaut |
| M12-10 | 2c | Ignorer le Retry-After supérieur au backoff |
| M12-11 | 3 | Suspendre à un seul changement matériel |
| M12-12 | 4 | Lire le registre concurrent sans BEGIN IMMEDIATE |
| M12-13 | Couture | Écrire dans un fichier différent de celui du lecteur |
| M12-14 | 3 | Republier un veto déjà actif après suspension du fournisseur |

### 5.5 Limites et exploitation

Le global final, les cartes strictes, le plan London, les ressources et la
gouvernance sont verts ; les contrôles et rapports de travail restent dans
.local/reports. Le journal MCL conserve les gates et les gels dans le dépôt.
Le [guide d'exploitation](../../docs/exploitation/SERVICE_IA.md) décrit la CLI,
le profil public non qualifié, les agrégats, le rapprochement et les incidents.
Aucune API LLM, source RSS ou SDK réel, aucun secret, compte, ordre,
installation ou CI distante n'a été utilisé pour ces essais. Les fournisseurs restent NON_QUALIFIE, le mode PAPER_AB,
le payant désactivé et le veto réel non autorisé. Les vingt contrats différés
et les qualifications sémantiques et financières appartiennent à la phase 13.
Le producteur C05 externe n'est pas fourni par ce service ; l'intégration de
plateforme EMA reste une étape distincte de sa propre lignée.

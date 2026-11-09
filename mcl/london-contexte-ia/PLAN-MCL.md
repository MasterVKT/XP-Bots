# Plan MCL — london-contexte-ia

## 0. Périmètre

Phase 8 London, composant pur commun sous `xpbots.contexte_ia`, après l'arbitrage R4/R5 du
09/11/2026. Le lecteur valide les snapshots reçus, conserve les vetos et implémente le port
canonique BLOCK/NEUTRAL. Aucun appel API, service IA, fichier physique, SQLite ou orchestration
A/B complète. L'esquisse EMA historique est préservée ; aucune phase EMA n'est déclarée réalisée.

## 1. Applicabilité

Structure connaissable : oui, A07/A10/A12. Contrats stabilisables : oui, export IA figé et schéma
xp-ai-context-v1. Exploration nécessaire : non. MCL s'applique. Coût annoncé : quatre gates
intégraux avant les gels, checkpoint après 2, gate global et mutations avec suite complète. Aucun
groupe parallèle : les quatre unités forment une chaîne. Le squelette donne le chemin de bout en bout.

## 2. Étape 1 — Cible

Entrées : octets UTF-8 exacts de l'IPC, réception UTC en ms, configuration chargée, politique du bras,
état de reprise pur. Sorties : réception acceptée/rejetée, cache et état immuables, décision mémoire
et identifiants C09. Python 3.13, bibliothèque standard ; aucune valeur figée recopiée. Le socle C05
reste obligatoire, le contexte optionnel n'accorde jamais ALLOW et ne commande aucune clôture.
La base initiale est 782 tests verts et 30 contrôles projet avec 288 de référence. Quinze fichiers
préexistants sont préservés par empreinte et exclus de la publication.

## 3. Étape 2 — Unités et question-test

| Unité | Responsabilité et objets intermédiaires | Constructible seule ? | Dépendances |
|---|---|---|---|
| types | Paramètres chargés, JSON canonique, snapshot et veto immuables, réception et politique | Oui, feuille interne | noyau canonique |
| snapshot | Taille avant JSON, hash et schéma complets, heures, séquence et allowlist | Non | types |
| cache | État, dernière séquence, preuve d'acceptation, identités scellées et cache actif | Non | types, snapshot |
| contexte | Politique du bras et du réel, port mémoire et contexte C09 | Non | types, cache, port commun |

Le flux reçu passe par validation puis cache, mais les profondeurs viennent de ces dépendances.
Les horodatages de réception et de génération restent distincts. Les seules données nouvelles
proviennent de snapshots alors reçus. Le cache actif s'arrête aux échéances propres des événements ;
une identité déjà connue ne peut être prolongée, même après expiration.

## 4. Étape 3 — Graphe

types → noyau ; snapshot → types ; cache → types, snapshot ; contexte → types, cache, port commun.
Aucun cycle. Les dépendances directes réelles sont encodées, y compris vers les types. La divergence
doit être nulle avant construction. Aucun import du C05 parallèle ou des moteurs de méthode.

## 5. Étape 4 — Couches

| Couche | Paquet | Contrat |
|---|---|---|
| 0 | c0_types | types, paramètres et primitives JSON |
| 1 | c1_snapshot | snapshot complètement validé |
| 2 | c2_cache | réception, séquence, cache et reprise |
| 3 | c3_contexte | décision et politique du bras |

## 6. Carte encodée

`carte.json` est stricte pour invariant, parallèles, externes, cycles, divergence et contrats figés.
Les deux composites désignent le même dossier actif. Les profondeurs des composants EMA encore
planifiés sont recalculées selon leurs dépendances au port commun ; leurs identifiants restent stables.

## 7. Contrats

Chaque fiche est finalisée avant sa couche, puis gelée avec l'interface publique et ses tests.
Les paramètres et empreintes viennent de ConfigurationFigee/ExportIA. Le noyau fournit UTC, les
décisions et les détails C09 ; aucun contrat amont ne doit être copié ni réinventé.

## 8. Frontières externes

IPC : octets ou absence, réception donnée par l'appelant, source scénarisée pour la couture.
Stockage : export/import des valeurs d'état, sans fichier ; physique en phase 11. Les couches
internes et le coordinateur restent réels. Le service IA et ses clients HTTP sont hors phase.

## 9. Construction et acceptation

Ordre 0 → 1 → 2 → 3. Catégorie 1 : contrat propre et bornes ; catégorie 2 : vraie jonction.
Commandes : `python tools/run_london_tests.py --artefact london_contexte_ia --couche <id> --categorie <1|2>`.
Chaque gate rejoue `python tools/run_london_tests.py` et `python tools/verify_project.py`, puis le
gel est immédiat sans changement d'arbre. Les nouveaux fichiers passent aussi le contrôle Git
de format avant le gel pour détecter les défauts invisibles au diff des seuls fichiers déjà suivis.

A14-2 : réception tardive et préfixes (1/2/3 et couture) ; A14-7 : expiration sans prolongation
(2/3) ; A14-8 : panne neutre et C05 bloquant (3/couture) ; A14-16 : fichier altéré, recul, reprise
(1/2). L-15 : vrai moteur London, veto de 08:15 puis nouvelle clôture de 08:30, et réception tardive.
La comparaison avec overlay_decision couvre les snapshots normatifs et leurs altérations.

Point de référence à tester explicitement : overlay_decision retourne au premier événement actif,
avant de vérifier les suivants. Le contrat A10/A12 impose de rejeter un snapshot mal formé entier.
Le lecteur valide donc toute la liste avant d'ajouter un veto ; cette limite d'oracle doit être
documentée et testée sans modifier la référence protégée ni une règle normative.

## 10. Checkpoint

Après 2 : revue des interfaces, duplications et reprise ; régression intégrale puis checkpoint
outillé. La couture ajoute le lecteur réel au bras IA ; la référence garde ComplementAbsent.
Pas de nouvel appel LLM ni d'inférence locale. Mutations par couche et par segment modifié sur copies
temporaires, copie saine d'abord ; seules les détections fonctionnelles comptent.

## 11. Gouvernance

La session tient les rôles de construction et traces, dans la délégation de phase 8. Les contrats
figés ne changent que par défigeage formel. R7 : registre/cartes vérifiés avec suite intégrale,
ressources, gouvernance et toutes les cartes. Rapports courants sous `.local/reports/` seulement.
Sortie : directeur 1.4.9, bilan, coutures et passation phase 9, audit, commit français et push.

## 12. Bilan

Les quatre couches sont figées après leurs gates intégraux, sans défigeage. CP2 suit le niveau 2. Les artefacts amont restent inchangés.

### 12.1 Construction et contrats réalisés

| Couche | Catégorie 1 | Catégorie 2 | Garanties principales |
|---|---:|---:|---|
| 0 | 10 | — | Types immuables, paramètres chargés, UTC canonique, JSON strict et empreinte exacte |
| 1 | 12 | 3 | Validation atomique de tout le snapshot, bornes de taille et d'âge, oracle partiel |
| 2 | 15 | 3 | Séquence et identités scellées, causalité, cache actif distinct, reprise sur preuves |
| 3 | 10 | 5 | Vrai port du coordinateur, politique du bras et du réel, description causale C09 |
| Total | 47 | 11 | 58 tests propres, sans doublure interne |

Les gels suivent immédiatement leurs gates verts, sans changement d'arbre intermédiaire.
Les suites intégrales passent successivement à 792, 807, 825 et 840 tests ; le checkpoint après
2 rejoue 825 tests et les ressources. Le gate global après couture passe à 851 tests des deux
lignées, avec 30 contrôles projet et 288 de référence. Le journal MCL donne commandes, dates,
durées et empreintes ; il est produit par l'outil, jamais édité à la main.

R4/R5 désigne le dossier actif `london-contexte-ia`, ses tests préfixés et un seul bloc source
`xpbots.contexte_ia`. Le noyau canonique fournit configuration, UTC et DecisionContexteIA ; le
coordinateur fournit LecteurContexteIA. L'adaptateur EMA existant reste la frontière entre
domaines. Les deux cartes composites pointent ces contrats ; les profondeurs EMA des futurs
consommateurs sont recalculées, sans déclarer de phase EMA supplémentaire terminée. L'esquisse
historique `mcl/contexte-ia` et les cinq artefacts amont figés restent intacts.

Le validateur refuse la taille avant l'analyse, les doublons JSON, les nombres non finis, les
clés supplémentaires, les types illégaux, hash/configuration incorrects, futur, péremption,
recul et tout événement mal formé. Il valide toute la liste avant de l'ajouter. Un événement
déjà expiré peut figurer dans un heartbeat valide mais n'est jamais activé. La publication et
la qualification sémantique A06 appartiennent au producteur : le lecteur ne les invente pas
à partir de generated_at, car ces données ne figurent pas dans le format de snapshot.

Le cache sépare réception, génération et première connaissance. La relecture conserve la
première réception ; un heartbeat vide ou mal formé n'efface aucun veto validé. Une même
séquence avec un autre hash et toute réécriture d'ID sont refusées sans ajout partiel. Les
identités scellées restent distinctes du petit cache actif afin d'empêcher une résurrection.
Leur rétention n'est pas arbitrairement tronquée ; la persistance physique future devra les
représenter durablement. Les requêtes historiques filtrent les connaissances futures.

La reprise revalide les octets originaux à leur réception d'origine, vérifie leurs métadonnées,
séquences, identités, connaissance et cohérence mutuelle, même si chaque preuve isolée est
valide. Une preuve perdue, altérée ou contradictoire est refusée. Le temps observé est monotone
et aucune échéance n'est renouvelée. Export/import sont purs, sans fichier ni réinférence.

### 12.2 Couture et acceptation

S4/S5/S7 injectent le lecteur réel au coordinateur du bras IA. REFERENCE conserve le véritable
ComplementAbsent. La politique est explicite ; un veto réel reste neutre tant que la validation
financière exigée manque. NEUTRAL n'accorde aucune permission. `SourceSnapshotScenario` double
les seules arrivées externes, avec octets et réception ; les couches internes restent réelles.
Réceptions et échéances rejoignent la minuterie C08 sans tick, bougie ni cotation fabriqués.
Le moteur démarre au temps du coordinateur : cache ancien accepté sans recul, état futur refusé.

Les onze tests ajoutés portent le squelette à 60 tests. A14-2 est prouvé par préfixes et réception
tardive ; A14-7 par la borne exclusive de fin et le heartbeat sans prolongation ; A14-8 par
l'absence ou la corruption de l'IA avec C05 toujours bloquant ; A14-16 par altérations, recul
et reprise sans renouvellement. Une arrivée pendant la persistance est vue à la revalidation
avant envoi. Un veto après fill ne ferme pas une position ; FLATTEN C05 reste obligatoire.
Le journal C09 conserve politique, décision, ID, item, fournisseur, hash, réception et bornes
réelles du veto, sans réponse de modèle ni secret.
Une sonde indépendante sérialise aussi les huit enregistrements d'un refus réel, vérifie leur
JSON canonique et retrouve sans perte les IDs, dates, fournisseur et hash de preuve ; son
rapport courant est `.local/reports/phase8_journal_reel.json`.

L-15 utilise les vrais flux, préchargement, moteur London et coordinateur, sur journées été et
hiver. La publication synthétique est à 08:07, classification reçue à 08:08, fin à 08:22 : la
cassure de 08:15 est refusée sans quota, aucun rattrapage à expiration, puis la nouvelle bougie
valide de 08:30 est remplie. Dans la variante reçue à 08:23, 08:15 n'est pas réécrit. Les autres
tests vérifient déterminisme, compte des ticks, validation de liaison et absence d'effet rétroactif.

### 12.3 Oracle, problèmes et remédiations

`overlay_decision` est comparé réellement dans les tests pour snapshots valides, altérés,
futurs, périmés, séquences en recul, cache, borne d'âge et garde financière. La référence retourne
toutefois au premier veto actif, avant de valider la suite de la liste : une fixture valide puis
malformée prouve son BLOCK prématuré. Le lecteur rejette ce snapshot entier selon A10/A12.
Il n'y a donc aucune revendication d'égalité universelle avec cet oracle partiel, et la référence
protégée reste inchangée. Les doublons JSON exigent aussi le contrôle des octets, absent d'un
oracle qui reçoit déjà un dictionnaire.

| Identifiant | Type et preuve | Traitement | Validation |
|---|---|---|---|
| P8-01 | Limite de l'oracle : veto actif avant événement malformé | Validation atomique normative conservée, limite explicitée | Tests catégorie 2 de 1 et 3, référence inchangée |
| P8-02 | Erreur d'attendu dans le nouveau test de reprise : attribut instant_ms absent de Enveloppe | Utilisation du champ réel instant_utc_ms, sans changement du noyau | Test de reprise puis suite intégrale de 851 tests |
| P8-03 | Risque de reprise avec preuves isolément valides mais contradictoires | Contrôle croisé des séquences, réceptions, IDs et contenu avant gel de 2 | Test propre dédié et toutes les régressions suivantes |

Les erreurs de construction sont corrigées avant l'audit de clôture. Aucun défaut introduit
ne reste ouvert. Le comportement de l'oracle partiel est une limite déclarée ; aucun contrat
métier, seuil, coût, dépendance, ressource protégée ou preuve historique n'est modifié.

### 12.4 Vérification adversariale

`python tools/verifier_mutations_contexte_phase8.py --ouvriers 1 --journal-progressif .local/reports/mutations_contexte_phase8_progression.jsonl`
détecte dix mutations sur dix, sans survivante. La copie saine et chacune des dix variantes
terminent les 851 tests des deux lignées. Chaque motif est unique et syntaxiquement valide ;
chaque détection implique un test fonctionnel du lecteur ou de la couture concernée. Une seule
garde de carte ou un échec de ressources ne constitue jamais une détection recevable.

Couverture : JSON canonique (0), âge exact et futur (1), connaissance future et réécriture d'ID
(2), garde financière et politique REFERENCE (3), preuve IA dans le journal (S4/S6), réception
effectivement appliquée (S5), injection au coordinateur (S7). Les empreintes relient les résultats
aux sources et cartes courantes. Aucune source du dépôt n'est mutée ; les rapports restent
sous `.local/reports/` et le harnais est versionné pour reproduire la campagne.

### 12.5 Contrôles de sortie et limites

Le gate global final, les seize cartes strictes, les six statuts d'artefacts figés, le plan
London, les portes machine et la gouvernance sont rejoués avant publication. Une archive des
seuls blobs préparés vérifie aussi les deux robots, les ressources et la gouvernance ; cet
arbre doit être celui du commit publié. Les contrats sont comparés octet pour octet à leurs
gels et blobs Git LF. Les quinze modifications préexistantes sont intactes et exclues du commit.
La recherche d'usages rg et le graphe d'impact sont recoupés avec les imports réels ; le graphe
borne sa liste à 500 des 519 nœuds impactés, ce qui ne remplace pas la suite intégrale.

Le directeur est en version 1.4.9 et la passation prépare la phase 9, non commencée. Aucun
service HTTP, appel LLM, inférence locale, source physique, ACL, persistance durable, budget
transactionnel, orchestration A/B complète, simulateur C10 ou adaptateur MT5 n'est construit.
Le hash détecte la corruption, sans authentifier un producteur malveillant. Le papier synthétique
au prochain tick et sans frais ne prouve ni qualification de compte, ni qualité sémantique,
ni rentabilité. L'intégration EMA de ce bloc reste future.

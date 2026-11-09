# Plan MCL — london-controles-fondamentaux

## 0. Périmètre

Phase 7 London : C05 commun aux deux méthodes, sous `xpbots.fondamental`, dossier actif préfixé
selon l'arbitrage R4/R5 du registre de coexistence. L'esquisse EMA reste historique. Les messages
fondamentaux et le calendrier sont fournis ; aucun calcul macro, terminal, fichier réel ou API.

## 1. Applicabilité et étape 1

Structure connaissable, contrats stabilisables dans C05 et D-11/D-12, aucun prototype exploratoire :
MCL s'applique au composant pur. Coût : cinq gates avec régression intégrale, puis checkpoint après 2,
gate global, couture et mutations. Les quinze modifications préexistantes de gouvernance et de fixtures
sont conservées par empreinte et exclues du commit ; elles ne sont pas des travaux de phase 7.

Entrées : octets exacts des permissions et exports MQL5, réception UTC, conversion serveur qualifiée
injectée et table d'importance versionnée. Sorties : états exportables, refus, traces de réception et
heartbeat, décisions du port C05 et symboles à clôturer. Python 3.13, bibliothèque standard, aucune
horloge ; les instants viennent de l'appelant. Le code métier ne lit ni fichiers ni réseau.

## 2. Carte et frontières

| Couche | Unité | Dépendances internes |
|---|---|---|
| 0 | Types et JSON strict, devises C05 | — |
| 1a | Validation des messages | 0 |
| 1b | Calendrier et fenêtres d'annonces causales | 0 |
| 2 | Dernière permission, séquences, interruption et heartbeat | 0, 1a |
| 3 | Port C05, décisions et clôtures | 0, 1b, 2 |

1a et 1b sont indépendantes. Les types, le validateur puis les états précèdent l'enveloppe.
Le port de conversion du temps serveur et les sources de messages/calendrier sont les seules
frontières doublées. Stockage physique et lectures appartiennent à la phase 11 ; ici export/import
d'états purs. Le domaine canonique et le port d'exécution sont ceux déjà gelés ; aucune couche interne
n'est doublée. La carte stricte déclare toutes les dépendances directes réelles.

## 3. Contrats, tests et gates

Chaque contrat est finalisé juste avant sa couche. Catégorie 1 : schéma, types, causalité et bornes
propres. Catégorie 2 : jonction sur le vrai bloc. Régression : `python tools/run_london_tests.py` puis
`python tools/verify_project.py`, avant chaque gel, sans changement d'arbre entre gate et gel.

C11.8 se répartit sur 1a, 2 et 3 ; C11.9 sur 1b et 3 ; A14-6 et A14-8 côté socle sur 3 ; L-14 sur
1b puis la couture avec le vrai coordinateur. Heartbeat manqué en 2 ; invalidité, expiration,
direction et FLATTEN en 2/3 ; calendrier tardif/périmé et préfixes causaux en 1b/3. La table devises
est comparée explicitement à C05 en 0. Les fixtures respectent les formats D-11 et D-12 exacts.

## 4. Couture prévue

Le coordinateur reçoit le vrai port C05. Le scénario technique neutre reste explicitement nommé ;
le rejeu de permissions scénarisées doit fermer à N−900 s, bloquer une permission invalide ou
expirée et donner priorité à FLATTEN. Aucune orchestration A/B ni lecture réelle anticipée.

## 5. Bilan

Les cinq couches sont figées après leurs gates intégraux ; CP2 suit le niveau 2. Aucun contrat métier amont ne change. Un défigeage correction de 1b retire une ligne blanche finale de son test après le contrôle Git de l’index ; l’AST et le comportement restent identiques, puis le gate et le gel sont rejoués.

### 5.1 Interaction avec la garde de non-recopie

Le premier gate de 0 passe ses huit tests propres, puis échoue parmi les 715 tests de régression :
la table de devises explicitement imposée par C05 est confondue avec des paramètres recopiés.
La correction borne l'exception au fichier, à l'affectation globale `_DEVISES` et aux six textes de
cette table. Un test négatif maintient leur interdiction dans toute autre affectation, fonction ou
fichier. Aucun seuil ni paramètre n'est autorisé par cette exception. Le gate complet est relancé
avant le premier gel ; cette garde transverse n'est pas un contrat figé d'une couche métier.

### 5.2 Clarification descriptive du format D-12

La description du document 01 citait une heure de dernière mise à jour qui n'est pas un champ du
format précis du document 08 §4.1. La description est alignée sur les dix champs définis, dont
la révision native ; known_at reste l'heure locale de lecture d'un événement nouveau ou changé.
Les fixtures n'ajoutent aucun champ inventé et aucun contrat C05 normatif n'est modifié.

### 5.3 Résultat et choix de contrat

| Couche | Catégorie 1 | Catégorie 2 | Garanties principales |
|---|---:|---:|---|
| 0 | 8 | — | JSON strict, types immuables, identités natives et table devises C05 |
| 1a | 7 | 2 | Format exact D-11, causalité des heures et borne exclusive de validité |
| 1b | 15 | 3 | Format exact D-12, conversion externe qualifiée, versions et connaissance causales |
| 2 | 12 | 3 | Séquences, dernière permission valide, interruption explicite, heartbeat et reprise |
| 3 | 8 | 4 | Port canonique, FLATTEN, HIGH, refus sans liquidation arbitraire et échéances |
| Total | 50 | 12 | 62 tests propres ; toutes les couches sont gelées |

Chaque gel suit immédiatement son gate vert sans modification intermédiaire de l'arbre. Les
gates successifs passent à 716, 725, 743, 758 et 770 tests des deux robots. Le checkpoint après 2
relance la suite intégrale : les interfaces suffisent au consommateur, aucune extraction ou
révision du contrat n'est nécessaire. L'absence de fournisseur réel ne crée aucune permission.

Les types et paramètres proviennent du noyau canonique ; le port de contrôle appartient au
coordinateur commun. La conversion serveur et la classification HIGH restent des frontières
externes explicites. Les messages gardent issued_at, known_at et réception séparés ; la relecture
ne renouvelle rien. La garde connaît uniquement les versions reçues à l'instant de consultation.
Les paramètres chargés pilotent toutes les durées, fenêtres et limites. Aucun seuil n'est recopié.

### 5.4 Couture et acceptation

La composition Python exige le vrai `PermissionsFondamentales` ou le scénario technique neutre
explicitement choisi, de façon exclusive. `SourceFondamentaleScenario` est la seule doublure des
arrivées externes : octets D-11/D-12 et réception déclarée, jamais une permission inventée par le
port. Le pilote ajoute les échéances C05 aux minuteries C08 sans créer de cotation ou de bougie.
Le journal canonique conserve messages, réceptions, versions, refus, heartbeat et expiration.
Un contrôle distinct sérialise aussi les enregistrements réels C05, vérifie leur JSON canonique
et leur relecture sans perte des champs représentables ; sa preuve reste sous `.local/reports/`.

Les douze tests de couture portent le squelette à 49 et la suite intégrale à 782. Ils vérifient
absence et invalidité, expiration, NO_NEW et direction incompatible, changement de direction sans
clôture, FLATTEN, annonce apprise tardivement, revalidation juste avant transmission, déterminisme,
interruption sans reprise rétroactive, reprise C05 antérieure au premier tick sans recul du temps, et L-14 sur les vrais flux et moteur London en été et hiver.
La demande L-14 est émise à N−900 s ; le fill au tick suivant ne réécrit pas son heure d'envoi.

L'examen des scénarios sans cotation fraîche confirme C08 : la demande est prioritaire dès la
réception et conserve SL/TP, tandis que l'envoi attend un marché négociable. Une seconde fixture
fournit une cotation fraîche juste avant la réception et vérifie l'envoi immédiat. Aucun changement
du coordinateur gelé ni abaissement d'exigence métier ne résulte de cet attendu corrigé.

C11.8 est couvert aux frontières de validation, à l'expiration, au signal et avant transmission ;
C11.9 aux bornes de fenêtre, aux devises et aux révisions tardives ; A14-6/8 côté socle vérifient
qu'une IA absente ou neutre ne remplace pas C05. Les détails et motifs restent ceux de C09.

### 5.5 Inventaire des problèmes et remédiation

| Identifiant | Type et preuve | Correction | Validation |
|---|---|---|---|
| P7-01 | Faux positif de non-recopie pour la table de devises imposée | Exception AST limitée à l'affectation globale et à ses six textes, test négatif | Gate 0 et toutes les régressions suivantes |
| P7-02 | Description D-12 annonçant un champ absent du format précis | Description alignée sur révision native et connaissance locale | Fixtures exactes, tests calendrier et contrôles documentaires |
| P7-03 | Attendu d'envoi immédiat sans cotation fraîche dans deux fixtures | Séparer demande prioritaire, marché négociable et remplissage | Cas avec et sans cotation fraîche, C08 inchangé |
| P7-04 | S4 utilisait toujours le neutre dans la composition Python | Choix explicite et exclusif, port C05 réel, arrivées et minuteries causales | Douze scénarios de couture et mutations S4/S5/S7 |
| P7-05 | États descriptifs des documents et skill C05 antérieurs au bloc | Directeur 1.4.8, bilan, passation phase 8, cartes composites et miroir | Plan, liens, gouvernance et portes machine |
| P7-07 | Contrôle Git de l’index : ligne blanche finale dans un nouveau test déjà gelé | Défigeage correction de 1b, retrait de cette seule ligne, égalité AST ; nouveau gate et gel | Contrôle de l’index, campagne de mutations et archive intégralement rejoués sur le nouvel arbre |
| P7-08 | Reprise C05 antérieure au premier tick : recul d’horloge papier reproduit | Initialisation S4 sur le temps public du coordinateur ; rejet d’un état C05 futur ; alertes échues observées au démarrage | Test de reprise réel, mutation dédiée, régression de 782 tests et douze mutations |
| P7-06 | Un mutant de borne heartbeat rendait le pilote incapable de progresser | Exécution arrêtée, mutant remplacé par une alerte mal classée qui termine ; campagne intégrale neuve | Les cinq résultats de l'essai interrompu sont conservés séparément et exclus du décompte final |

Les erreurs de construction sont corrigées avant l'audit final. Aucun export normatif, seuil,
coût, dépendance, référence ou preuve conservée n'est modifié. Les quinze fichiers préexistants
de gouvernance et de fixtures sont préservés par empreinte et exclus de la publication.

### 5.6 Vérification adversariale

`python tools/verifier_mutations_fondamental_phase7.py --ouvriers 1 --journal-progressif .local/reports/mutations_fondamental_phase7_progression.jsonl`
détecte douze mutations sur douze, sans survivante. La copie saine et chaque variante terminent
les 782 tests des deux robots. Chaque motif est unique, syntaxiquement valide et change un
comportement ; chaque détection implique un test fonctionnel C05 ou de la couture concernée.
Une erreur de mémoire ou un seul défaut de carte ne compte jamais comme preuve de détection.

Couverture : table de devises (0), fin de validité (1a), début de fenêtre et connaissance future
(1b), réécriture de séquence et classification du heartbeat (2), FLATTEN et HIGH sans permission (3), contexte
C09 et horloge de reprise (S4), séquence reçue journalisée (S5), scénario CLI obligatoire (S7). Les empreintes lient
les résultats aux sources ; les rapports courants restent dans `.local/reports/`. Aucune source
du dépôt n'est mutée par la campagne.

Chaque changement de source ouvre une nouvelle campagne complète. Les résultats antérieurs sont
archivés sous leurs anciennes empreintes et ne sont jamais réattribués à la révision courante.

### 5.7 Sortie et limites

Le gate global final, les quinze cartes strictes, les statuts gelés, le plan London, les portes
machine et les contrôles de ressources sont rejoués avant publication. Une archive des seuls blobs
préparés vérifie aussi les deux robots et les ressources ; les contrats sont rapprochés de leurs
empreintes de gel et de ces mêmes blobs Git. L'arbre testé doit être celui du commit publié.

La phase 8 reste non commencée. Aucun calcul macro, fournisseur de permissions, lecture physique,
adaptateur MT5, persistance durable, orchestration A/B ni simulateur C10 n'est construit. Le
convertisseur serveur et la table HIGH réels attendent qualification ; les tests utilisent des
frontières synthétiques déclarées. L'intégration EMA au compte reste future. Le papier S5 à coûts
nuls et prochain tick ne prouve aucune qualification de compte ni rentabilité.

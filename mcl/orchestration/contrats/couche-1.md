# Couche 1 — Bras et reprise

Finalisé avant code le 09/11/2026, après gel de 0. Consommateur : moteur 2.

| Élément | Contrat |
|---|---|
| Unité | bras |
| Responsabilité | Composer un compte, ses stratégies isolées, son coordinateur réel et son journal |
| Signature | construire_bras(configuration, deploiement, nom, profils, port, fondamental, instant_ms, ...), Bras(...), etat, sur_bougie, appliquer_issue, consommer, alerte |
| Entrée | ConfigurationFigee, Deploiement 0, fabriques, ports C08/C05, observation/base UTC, EtatBras éventuel |
| Sortie | Bras réel, résultats techniques canoniques, SortieMoteur C09/C08 et EtatBras pur |
| Effets de bord | Mémoire du bras seulement ; aucune entrée envoyée ni persistance externe |
| Erreurs | ErreurOrchestration pour fabrique, état, symbole ou résultat incohérents ; erreurs amont conservées |

Les fabriques reçoivent la configuration et une table de tick d'un seul symbole. Les instances
sont distinctes par méthode et symbole ; le moteur 2 vérifie aussi leur séparation entre bras.
Une fabrique doit rendre une stratégie structurelle portant son identifiant déclaré. Une
fabrique réutilisant un objet est refusée. Les résultats M15 doivent porter méthode, symbole
et clôture attendus ; H1 ne produit rien. Aucun import d'un moteur de méthode.

construire_bras compose le vrai CoordinateurCompte avec le port du compte. En mode d'évaluation
A/B chargé, l'identifiant effectif ajoute le nom du bras au déploiement de base : les clés et
preuves des deux comptes ne peuvent être confondues. En mode simple, l'identifiant est conservé.
REFERENCE utilise ComplementAbsent ; IA utilise le LecteurContexte réel ou l'absence facultative.
En DEMO/REEL, un lecteur fourni doit porter sa politique d'exécution réelle. La qualification
financière reste celle du lecteur et ne peut être fabriquée par le bras. C05 n'est jamais neutre
implicitement : le port fourni est celui choisi explicitement par la composition.

Le constructeur Bras accepte aussi un coordinateur déjà composé, pour la couture simple
existante ; il ne le remplace pas et ne lit aucun de ses champs privés. Les profils, le nom,
la configuration et les ports sont exposés pour le contrôle de composition du moteur. Le port
de transport est facultatif uniquement dans cette couture simple ; A/B exige des ports distincts.

TraceStrategie(identifiant, symbole, nature, instant_ms, valeur, resultat=None) conserve chaque
bougie et issue reçue par les méthodes publiques, avec sa réception. EtatBras contient nom,
signature de configuration/déploiement, EtatCoordinateur, historique, numéro de journal et
intentions déjà journalisées et empreinte canonique SHA-256 de l'ensemble. Cette empreinte est
vérifiée avant utilisation de l'état ; elle détecte l'altération d'une histoire ou de son lien
au coordinateur, sans prétendre authentifier un processus malveillant. Les collections sont immuables. La signature inclut empreintes,
fabriques, tailles et mode ; état étranger, futur, historique incohérent ou résultat divergent
au rejeu sont refusés. La reprise reconstruit les stratégies par leurs API publiques sans
réinférence et utilise l'état du coordinateur avec son rapprochement natif C08. Aucun quota
ou état privé n'est recopié. Une fabrique de reprise doit fournir des instances fraîches.

consommer(lot, instant_ms, contexte=None) livre les issues au destinataire méthode/symbole,
conserve les traces C08 et les mises à jour d'intention sans doublon, puis rend SortieMoteur.
Le contexte est une fonction pure donnant permission, version calendrier et description IA ;
elle est fournie par le moteur 2, sans dépendance parallèle directe à C05. Les commandes
restent celles du coordinateur ; aucun redimensionnement ou filtre financier n'est ajouté.
Les numéros C09 sont propres au bras et reprennent sans remise à zéro. Les historiques de
reprise ne sont pas tronqués arbitrairement ; la persistance durable reste future.

Tests propres et jonctions : test_cat1_c1_bras.py, test_cat2_c1_bras.py ; vraies fabriques London,
vrai coordinateur et transport papier externe explicite. Cas d'isolation, reprise, revalidation,
quota et journal ; A14-9/17 complétés par le moteur 2.

Extension tracée du 09/11/2026, consommateur 2 : PortCalculJournalise délègue les sept méthodes
au vrai appeler_calcul, conserve leurs AppelCalcul normalisés et expose drainer() et ses appels
d'initialisation. debut_rejeu(appels), puis terminer_rejeu(), reproduisent strictement noms,
arguments, options et résultats sans appeler le backend. Une divergence est mémorisée et levée
hors du coordinateur, dont appeler_calcul absorbe normalement les erreurs externes ; un nombre
d'appels différent est aussi refusé. Après divergence, le rejeu est arrêté, sans réutiliser ce bras.

CoordinateurTrace hérite du vrai C6 sans remplacer aucune méthode métier ; son seul ajout est
le port enveloppé et sa propriété publique calculs. L'option appels_initialisation=None permet
de rejouer aussi le démarrage. construire_bras conserve sa signature et ajoute cette option.
Bras.calculs expose ce port lorsqu'il est présent ; un ancien C6 brut reste accepté par Bras,
mais un moteur journalisable exigera la trace. Bras.profil_compte expose la métadonnée initiale.

journaliser_cloture(bougie, resultat, compte, permission=None, version_calendrier=None,
snapshot_ia=None) produit le vrai C09 de clôture M15, après passage dans sur_bougie. Sa vue de
détecteur contient le nombre de bougies, la dernière clôture et la dernière issue publics,
reconstruits depuis l'historique, avec le résultat technique et son contexte. La représentation
canonique des contextes appartient au bras, sans import de helpers privés par le moteur 2.
consommer applique aussi cette représentation aux objets de contexte reçus. Aucun type existant
ni règle métier n'est modifié ; les paramètres nouveaux sont facultatifs par défaut.

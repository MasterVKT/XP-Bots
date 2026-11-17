# Couche 1b — session durable et projection C09

`SessionDurable(depot, journal, initialisation)` reçoit le vrai DepotSQLite,
le vrai JournalFichiers déjà réparé par l'assemblage au démarrage et les octets
canoniques d'initialisation de la composition. Elle ne touche jamais directement
aux fichiers, à SQLite ou à l'horloge. Les données métier restent dans le moteur.

`persister(moteur, sortie=None, *, courtier=None, livres=None)` archive dans un
COMMIT unique le checkpoint réel du moteur, ses seules nouvelles entrées, l'état
natif fourni, les checkpoints des livres et leurs opérations nouvelles, les
décisions C09, intentions, réservations et arrêts. `livres` associe chaque bras
à `{'checkpoint': bytes, 'operations': tuple[bytes, ...]}` ; les valeurs du livre
restent opaques, sans dépendance parallèle sur 1a. L'initialisation complète est
écrite une seule fois. Le checkpoint persistant ne contient aucun journal complet.
Les enveloppes externes ont leur numérotation propre, consécutive et commune.

Le résultat `PersistanceSession` contient le numéro COMMIT, les preuves C08
associées aux préparations de la sortie et le succès de la projection JSONL.
Aucune preuve n'est produite avant le retour réussi du vrai COMMIT. Une panne
de projection après ce COMMIT conserve la preuve durable et signale séparément
le besoin de réparation, sans rejouer l'entrée ou le COMMIT. Une seconde
persistance sans nouvelle entrée peut enregistrer la préparation native avant
son autorisation par la boucle ; elle ne duplique pas les décisions précédentes.

`charger()` restitue l'initialisation, le checkpoint, le journal moteur complet,
les checkpoints/opérations des livres et l'état natif. Signature, numéros,
schémas, compteurs et concordance des arrêts durables sont contrôlés. Un arrêt
global ne se lève pas par une reprise. La garde quotidienne possède une clé
par date UTC ; le changement normal de journée ne supprime pas l'arrêt historique.
Une identité ou un état incohérent est refusé, sans créer un compte neuf.

Catégorie 1 : deltas et compteurs, initialisation unique, erreurs de COMMIT et
de projection distinctes, répétition sans duplication, reprise altérée refusée,
arrêts conservés. Catégorie 2 : vrai moteur, SQLite et fichiers temporaires,
reprise des entrées et égalité du journal C09, livre natif préparé au second
COMMIT, comptes A/B et récupération d'une projection indisponible. Les
commandes défensives et l'ordonnancement restent dans la couche 2.

## Correction P11-14 — sorties après échec de COMMIT

La session conserve en mémoire chaque sortie fournie dont le COMMIT a échoué.
Une tentative suivante archive aussi ces décisions C09, dans l'ordre, avec les
nouvelles entrées. Une sortie répétée de même numéro doit être identique. Le
tampon est vidé seulement après COMMIT réussi, même si la projection échoue.
Les preuves proviennent exclusivement de la sortie du checkpoint courant ;
un ancien lot retenu n'autorise pas une transmission avec une révision périmée.

L'API reste inchangée : le consommateur fournit chaque sortie avant d'avancer
à l'événement suivant. La session ne reconstruit pas des sorties qui ne lui
ont jamais été fournies. Un rejeu incident complet exige ainsi un journal C09
complet depuis la composition initiale. Le tampon transitoire ne remplace pas
SQLite ; un arrêt pendant l'indisponibilité repart du dernier COMMIT acquis.


## Correction P11-13 — checkpoint de journal

Le schéma persistant est `xp-session-direct-v2`. Son champ checkpoint est un
`CheckpointJournalMoteur`, obtenu par `exporter_checkpoint_journal()` ; il
contient les états courants des coordinateurs et du flux, les engagements
courants C05 et IA,
ainsi que le compteur et la chaîne du journal. Aucun historique de stratégie
n'est recopié dans les persistances régulières. Les intentions, réservations
et arrêts proviennent de ces coordinateurs courants. Le schéma v1 est refusé
explicitement ; aucune migration implicite d'un déploiement n'est effectuée.

`charger()` renvoie ce checkpoint de journal et les entrées archivées. Le
consommateur reconstruit le moteur initial avec ses calculs d'initialisation
archivés, rejoue les entrées par le chemin public et compare le checkpoint de
journal obtenu avant de construire la reprise C08 existante à partir d'un
checkpoint complet exporté une seule fois. Il ne continue pas directement
le moteur de rejeu comme une session native. Cette correction borne le coût
régulier ; elle ne promet pas une durée constante de reconstruction au démarrage.

Catégorie 2 : après le vrai préchargement et une cassure London, la taille du
snapshot n'inclut plus les milliers de traces de stratégie ; journal complet,
preuves de COMMIT, positions et arrêts durables restent conservés.

## Extension P11-17 — marqueurs de reprise C08

Finalisée avant code le 14/11/2026. Le constructeur accepte le paramètre
optionnel `reprise=None`, ou un CheckpointJournalMoteur réel obtenu juste après
la construction C08 du moteur repris. Une session préalable doit exister ;
signature, instant et compteur correspondent au dernier checkpoint durable.
Ce marqueur est conservé en attente jusqu'au prochain COMMIT réussi, avant
les nouvelles entrées, sous la nature externe REPRISE_MOTEUR. Il ne contient
aucune commande et ne donne aucune preuve de transmission.

`charger()` ajoute la clé `reprises` seulement si de tels marqueurs existent :
tuple de checkpoints courts dans l'ordre du journal, chacun au compteur du
préfixe qui le précède. Les anciennes sessions sans marqueur conservent leur
forme de retour. Le schéma physique v2 reste identique : les marqueurs sont
dans le journal externe incrémental, pas dans chaque snapshot. La session
vérifie les types, sceaux, signatures, compteurs et dates ; le consommateur
doit refaire C08 à chaque préfixe et comparer le marqueur, jamais restaurer
directement ces états courts.

Catégories 1 et 2 : marqueur unique malgré un COMMIT refusé puis retenté,
absence avant le COMMIT, erreur de préfixe ou de déploiement, restitution des
octets et préservation des entrées et C09 déjà archivés.

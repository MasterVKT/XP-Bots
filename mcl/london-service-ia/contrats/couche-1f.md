# Couche 1f — snapshot

Statut : contrat finalisé le 17/11/2026 après gel de 0 et avant code.
Consommateurs cartographiés : service.
Dépend de : types.

Unité : snapshot.
Responsabilité : Former les snapshots A10 avec séquence persistée et validation du lecteur réel.
Signature : fabriquer_snapshot(ressources,sequence,genere_ms,evenements) -> bytes ;
EcrivainSnapshot(ressources,depot,publier).publier(genere_ms,evenements)
-> PublicationSnapshot(sequence,octets,publie,erreur=None).
Entrée : ressources réelles, séquence positive, génération UTC et événements
déjà validés A06 ; dépôt transactionnel et port publier(octets) externe.
Sortie : enveloppe A10 canonique égale à make_snapshot, validée par le lecteur
réel existant ; publication confirmée ou code d’erreur statique.
Effets de bord : réservation durable de séquence et archive préparée dans une
transaction injectée, puis appel au port hors transaction. Aucun I/O physique.
Erreurs, exceptions : ErreurService pour paramètres, compteur, configuration,
temps ou snapshot invalide. Erreur de port : résultat publie=false ; aucune
exception brute, réponse LLM ou donnée confidentielle n’est exposée.

## Spécification exécutable

test_cat1_c1f_snapshot.py couvre format, refus, séquences, reprise, archive,
échecs et taille. test_cat2_c1f_snapshot.py compare make_snapshot et traverse
le vrai lecteur IA et son cache, sans doubler ces couches.

## Comportements documentés

Le schéma et les primitives sont repris du lecteur IA figé. Le payload contient
l’empreinte d’intégration de la configuration chargée ; son hash porte sur le
JSON canonique UTF-8. Tous les événements sont validés avant publication ; aucun
événement partiel n’est extrait d’un snapshot malformé. Le plafond est exporté.
Les fenêtres des événements et leur ordre sont conservés, sans prorogation.

Le port publier retourne None au succès et lève OSError ou ValueError à l’échec,
comme l’écriture atomique réutilisée en 4. Un retour différent est une violation
de port signalée. La coquille garantit les retries A10 et le maintien de l’ancien
fichier si le remplacement échoue. Cette unité n’attend jamais physiquement.

Le compteur est dans schedule_state/snapshot_sequence avec génération et digest.
L’archive context_snapshots conserve séquence, génération, hash et payload avant
l’appel physique, avec statut PREPARED : elle ne prétend pas prouver la lecture
effective du fichier. Une publication échouée peut laisser un trou de séquence,
jamais un recul. Le redémarrage réutilise ce compteur ; un compteur perdu avec
une archive existante, une génération en recul ou un autre digest est refusé.
Un heartbeat ne modifie jamais valid_from/valid_until. Il ne lance aucune API.

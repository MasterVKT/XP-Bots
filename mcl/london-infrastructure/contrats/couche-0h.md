# Couche 0h — verrou de processus physique

Contrat finalisé le 14/11/2026 avant code. Nouvelle feuille identifiée par la
question MCL d'indépendance : ce verrou n'a besoin d'aucun autre composant.
Parents externes : fichiers et verrou système standard Windows/POSIX. Aucun
SDK, horloge, compte, algorithme de risque ou identifiant de déploiement.

VerrouProcessus(chemin).acquerir() ouvre un fichier persistant et acquiert un
verrou exclusif système non bloquant, puis rend self. La répétition sur le
même objet propriétaire est inerte. Un autre objet ou processus sur le même
fichier échoue avec ValueError et un code statique, sans chemin sensible.
Les parents du chemin sont créés si nécessaire. Le fichier contient au moins
un octet pour le verrou Windows ; il ne porte aucune donnée de compte.

liberer() est idempotente et ferme le descripteur, y compris si le déverrouillage
échoue. Le contexte with acquiert puis libère. Le fichier n'est jamais supprimé,
ce qui évite qu'un concurrent verrouille une nouvelle identité de fichier.
La mort du processus libère le verrou système ; aucune suppression manuelle
d'un fichier O_EXCL ni supposition à partir d'un PID n'est utilisée.

Windows utilise msvcrt.locking sur le premier octet ; POSIX utilise fcntl.flock.
Les imports sont tardifs dans la branche de plateforme. Une plateforme non
prise en charge refuse. Les erreurs d'ouverture et d'acquisition ferment leur
descripteur et rendent un code statique. Aucun attente ni nouvelle tentative
silencieuse ; l'appelant décide du traitement opérationnel.

L'assemblage 4 placera ce verrou dans le dossier FILE_COMMON partagé,
XPBots/execution/v1/coordinateur.lock, avant toute ouverture de base/journal.
Ce périmètre interdit deux coordinateurs XP-Bots simultanés dans le même
dossier commun, y compris depuis deux déploiements. Il est volontairement
commun à leurs comptes ; la phase 11 ne fournit pas un superviseur de
plusieurs terminaux indépendants. Les bras PAPER_AB restent dans le même
processus, avec leurs vrais livres séparés.

Catégorie 1 : deux propriétaires, répétition, contexte, erreurs sans fuite,
fichier non supprimé, exclusion entre vrais processus et libération après
leur terminaison forcée. Pas de doublure du verrou ou du système de fichiers.
Comme feuille, pas de catégorie 2 artificielle ; la jonction réelle appartient
à l'assemblage 4 et à la boucle directe.

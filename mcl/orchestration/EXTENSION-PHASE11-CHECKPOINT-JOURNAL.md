# Checkpoint de journal pour la boucle D-09

P11-13 est établi sur la vraie journée London préchargée : le checkpoint complet
atteint 2 928 819 octets après 5 509 entrées ; son export prend 428 ms et son codec
248 ms. La persistance suivante, avec quatre nouvelles entrées, prend 807 ms.
La sonde est hors concurrence de gate et exécute les vrais moteur et SQLite.
L'ancien benchmark sur des entrées sans historique de stratégie n'était pas
représentatif du direct. Les résultats sont conservés dans le rapport local
phase11_d09_persistance_complete.json.

Le journal complet d'entrées est déjà durable et contient tous les calculs
nécessaires au rejeu sans backend. Le checkpoint régulier n'a donc pas besoin de
recopier l'historique de chaque stratégie. Une nouvelle API additive expose un
checkpoint de journal avec la signature, l'instant, le compteur et la chaîne
des entrées, les flux, les états des coordinateurs, C05 et IA. Le scellement
porte sur ces valeurs ; ce n'est ni une authentification ni une autorisation.

Au redémarrage, l'enveloppe reconstruit le moteur initial réel et rejoue les
entrées archivées. Elle compare le checkpoint de journal obtenu au checkpoint
durable, puis exporte le checkpoint complet une seule fois pour utiliser la
reprise C08 existante et imposer le rapprochement natif avant nouvelles entrées.
Il n'y a ni second moteur de décision ni accès aux états privés d'une stratégie.
La reprise est linéaire dans le journal ; aucun objectif de temps constant au
redémarrage n'est ajouté. En marche, le coût de sérialisation ne dépend plus
du nombre de bougies déjà vues par la stratégie.

Le checkpoint complet, EtatMoteur et leurs constructeurs restent disponibles
avec leurs contrats antérieurs. La source et les tests de 2/3 passent par
défigeage additive ; la session durable 1b change de format et de contrat par
défigeage de modification. Une nouvelle sonde complète est requise après
correction, ainsi que les gates et gels avant la boucle et la répétition générale.

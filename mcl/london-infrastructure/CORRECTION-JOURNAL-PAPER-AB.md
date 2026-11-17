# Projection C09 des comptes PAPER_AB

P11-12 est révélé par la jonction de session durable : les sorties du vrai moteur
PAPER_AB portent les déploiements `racine:REFERENCE` et `racine:IA`, nécessaires
à l'indépendance des clés et des comptes. JournalFichiers n'acceptait que l'égalité
avec le nom racine de son dossier. Le COMMIT conservait les données, mais la
projection des deux bras était refusée et la réparation de démarrage échouait.

La correction est limitée au mode PAPER_AB et au suffixe exact du bras canonique.
Elle ne change aucune enveloppe et ne crée aucun chemin à partir du suffixe.
Les déploiements étrangers et suffixes croisés restent interdits. Le contrat
0d est défigé avant modification ; le consommateur 4 est revalidé, avec une
jonction physique de fermeture et réparation sur les deux bras. Les nouvelles
unités d'application ne seront gelées qu'après cette remontée.

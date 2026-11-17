# P11-15 — engager les contrôles courants sans recopier leurs historiques

La répétition physique courte a produit une entrée et une clôture, avec C05
réel, fichiers temporaires et journal C09/rejeu exactement identiques. Après
658 itérations et 1 317 entrées, son checkpoint atteignait 782 181 octets et la
dernière persistance 165,7 ms. Les historiques C05 et les preuves IA scellées
étaient recopiés par le checkpoint régulier, comme l'avait été l'historique
de stratégie avant P11-13. Les durées concernent cette machine et cette fixture.

Décision technique dans le périmètre autorisé de phase 11 : modifier seulement
la représentation opaque fondamental/ia de CheckpointJournalMoteur. Les faits
courants sont engagés par leurs empreintes et métadonnées ; une mémoïsation
conserve seulement les objets courants. Aucun décodage, permission, critère
de veto ou algorithme d'exécution n'est remplacé. Le journal reste complet,
y compris les anciens calendriers et identités de veto expirées.

Le checkpoint complet et EtatMoteur conservent tous les historiques. La reprise
reconstruit toujours ces états complets par le vrai rejeu, compare la projection
puis passe par les constructeurs C08 existants. Les projections ne servent
jamais directement à restaurer C05 ou l'IA. Un ancien format de checkpoint
de journal n'est pas converti silencieusement.

Rayon constaté : 2 → codec 3 ; hors artefact, session 1b, composition 1f,
rapports 1e et boucle 2. Ces consommateurs n'exploitent pas le contenu de ces
deux champs et gardent leurs contrats ; revalidation de leurs jonctions et
régression intégrale. La couche 3 reçoit un cas d'aller-retour supplémentaire
après le nouveau gel 2. Nouveau gate/gel 2, puis 3, avant de reprendre la boucle.

# P11-14 — conserver les décisions dont le COMMIT a échoué

Le test réel de boucle ferme l'écriture SQLite par query_only, laisse le moteur
traiter ses événements défensifs, rétablit l'écriture puis rejoue le journal.
Avant correction, les entrées du moteur étaient conservées, mais les décisions
C09 du premier événement étaient perdues : JOURNAL_C09_INCIDENT_DIVERGENT.

Le défigeage correction de 1b envisageait aussi un lot explicite de sorties.
La lecture du consommateur réel établit qu'il fournit chaque sortie au moment
de sa production ; un changement d'interface n'est donc pas nécessaire. La
correction reste à contrat d'appel constant : la session retient les sorties
non COMMITées et les archive à la tentative réussie suivante. Le tampon est
vidé après le COMMIT, avant la projection. Les preuves sont celles du seul
checkpoint courant. Une répétition contradictoire est refusée avant écriture.

Le tampon transitoire n'est ni un nouveau journal durable ni un second moteur.
Les sorties jamais fournies ne sont pas inventées. La boucle assure la couture
complète ; la commande incident refuse toute différence du journal C09 réel.
Rayon : 1b → 2 → 3 ; 2 et 3 ne sont pas encore figées. Tests nouveaux à la
source 1b, nouveau gate/gel 1b avant reprise de la construction de 2.

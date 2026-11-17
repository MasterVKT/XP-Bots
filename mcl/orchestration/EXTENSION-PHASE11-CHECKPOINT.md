# Extension de l’orchestration pour la persistance de phase 11

Le consommateur physique doit persister un état à chaque événement et conserver
le journal d’entrée en ajout seul, sans dupliquer toute son histoire à chaque
scrutation D-09. La photographie publique initiale contient le journal complet.
La mesure locale sur fixture synthétique donne 10,238 ms à 200 entrées,
58,480 ms à 1 000, 172,990 ms à 3 000 et 267,443 ms à 6 000. Ces mesures décrivent
cette machine et cette fixture, sans garantie de capacité sur le poste réel.
Preuve de travail : `.local/reports/phase11_cout_etat_moteur.json`.

L’extension additive de la couche 2 fournit un checkpoint lié au journal par
compteur et chaîne, et une lecture de son suffixe. La photographie et la reprise
antérieures restent disponibles. Le défigeage est tracé avant modification du
contrat ; tests propres, jonctions, régression intégrale et nouveau gel précèdent
la construction du codec consommateur. Aucune règle, priorité, durée ou coût
de trading n’est changé.

Une nouvelle couche pure 3 assurera ensuite l’encodage et le décodage durables des
types publics de l’orchestration et de ses amonts. Elle est placée ici parce que
seule l’orchestration peut importer les types C03 au-dessus de la couche des
données. L’application et l’infrastructure ne doivent ni importer ces données
directement, ni lire des clés privées, ni charger une classe désignée par un
document non fiable. Le codec utilisera un registre fermé de types publics,
sans import dynamique, avec refus des doublons, nombres non finis et versions
inconnues. Les octets seront transportés par les lecteurs et SQLite de phase 11.

Cette évolution appartient au bloc commun existant et respecte l’arbitrage R4/R5.
Elle ne crée ni second moteur, ni second coordinateur, ni source de marché et ne
réalise aucune qualification de courtier. La confrontation des frontières réelles
reste en phase 13. Les 246 fichiers contractuels de départ sont inventoriés ;
seuls les contrats explicitement défigés peuvent changer.

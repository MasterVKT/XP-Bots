# Défigeage du 10/11/2026 — couche 0d — modification

Quoi : retirer la restriction qui imposait la grille native aux deux côtés d'une
cotation de recherche. Le contrat de prix continue de construire E=Ask/Bid et
d'arrondir SL/TP sur le tick_size exact, avec les contraintes natives de C06.

Pourquoi : la jonction de phase 10 sur le vrai London en stress échouait avec
ENVIRONMENT_NOT_READY/cotation. Un spread historique de dix ticks multiplié
exactement par 1,25 donne 12,5 ticks. Arrondir ce spread modifierait C10 ; le
refuser systématiquement ajouterait une exclusion absente du protocole. Le test
propre ajouté à 0d montre le refus avant la correction, avec E=1.100125 attendu,
SL=1.09920 et TP=1.10198. Le calcul reste indépendant de toute connaissance future.

Nature : modification d'un choix d'ingénierie de phase 5, pas d'une règle des
spécifications. L'autorité est C06 et C10 ; les exports et preuves protégés restent
intacts. La demande humaine d'achever la phase 10 autorise cette correction
nécessaire. L'agent assure la revue du propriétaire et des consommateurs à partir
de leurs contrats et de leurs tests ; aucune approbation humaine distincte n'est
présumée ni rapportée.

Rayon outillé : directs 2a, 3, 4, 6 ; transitifs 5a, 5b. Cascade dans l'ordre
0d, 2a, 3, 4, 5a, 5b, 6, avec gate intégral à chaque unité. Les contrats des six
consommateurs restent inchangés s'ils passent. Aucun contournement dans le
simulateur ou dans l'exécuteur ; l'Ask exact du stress atteint les mêmes gardes
de spread, de TTL et de risque que la référence.

Clôture : 0d refigée le 10/11/2026 après sept tests propres et gate intégral vert
de 1 007 tests ; les six consommateurs ont chacun passé leur gate propre et de
jonction avec la même régression intégrale, sans adaptation. Le checkpoint est
journalisé. Une assertion de comparaison de clés A/B, étrangère au calcul des
prix, a été corrigée dans la couche 2 non encore gelée avant ces gates. Les deux fichiers de contrat modifiés sont la fiche 0d et sa suite de
tests ; l'interface publique conserve sa signature.

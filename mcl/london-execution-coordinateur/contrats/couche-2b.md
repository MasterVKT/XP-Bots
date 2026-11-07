# Contrat de la couche 2b — arbitrage

- **Statut** : finalisé le 06/11/2026 avant son implémentation.
- **Consommateurs cartographiés** : 6.
- **Dépend de** : 0a, 1c.

Unité : arbitrage
Responsabilité : Séquence stable selon stratégie puis univers ; chaque candidat porte le nouvel instantané réel des réservations.
Signature : `CandidatArbitrage`, `ordonner_signaux(signaux, commun)`, `candidats_admission(signaux, commun, registre)`
Entrée : Signaux canoniques réels d’une même clôture, y compris signaux EMA adaptés ; paramètres et registre de compte unique.
Sortie : Séquence stable selon stratégie puis univers ; chaque candidat porte le nouvel instantané réel des réservations.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

L’ordre vient exclusivement de simultaneous_strategy_priority puis universe_priority. Les signaux d’instants différents ne sont pas mélangés. Les doublons sémantiques sont refusés plutôt que fusionnés ; deux sens restent des candidats distincts mais le registre interdit leur couverture sur le même actif. Aucun score, vote, compensation ou partage par méthode n’est ajouté.

La séquence d’admission est un générateur : après le traitement et l’éventuelle réservation atomique du candidat précédent, la prochaine itération relit le registre réel. Elle ne préfabrique pas des admissions sur un état initial commun. Le consommateur applique les vrais calculs de dimensionnement puis la comparaison de version de 1c, et réévalue tout candidat suivant ; la couche n’invente ni volume ni droit d’ordre. Un risque nul continue d’occuper une place. Le coordinateur complet et l’envoi restent en phase 6.

## Spécification exécutable

`test_cat1_c2b_arbitrage.py` : priorité exacte, instants, doublons et instantanés frais ; `test_cat2_c2b_arbitrage.py` : vrais objets EMA adaptés et London sur un seul registre, sans fusion ni couverture.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.

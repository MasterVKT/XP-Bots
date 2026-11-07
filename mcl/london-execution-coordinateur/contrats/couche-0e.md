# Contrat de la couche 0e — echeances_sortie

- **Statut** : finalisé le 06/11/2026 avant son implémentation.
- **Consommateurs cartographiés** : 5a, 6.
- **Dépend de** : noyau amont ; aucune autre couche de cet artefact.

Unité : echeances_sortie
Responsabilité : Première échéance horaire et toutes les causes à égalité, dans l’ordre durée, sortie locale, fermeture native, blackout.
Signature : `EcheanceSortie`, `premiere_echeance(premier_remplissage_ms, strategie, technique, horaires)`
Entrée : Instant du premier remplissage, identifiant de méthode configuré, export technique et horaires natifs vérifiés couvrant ce remplissage.
Sortie : Première échéance horaire et toutes les causes à égalité, dans l’ordre durée, sortie locale, fermeture native, blackout.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

Les quatre échéances sont : première exécution + durée maximale, sortie locale du jour Londres propre à la méthode, prochaine fermeture ou pause native moins la garde, et prochain début de blackout UTC. Le remplissage n’est pas décalé à une frontière M15. Une sortie déjà échue à l’entrée reste échue : ne pas la reporter au lendemain. Si le remplissage survient dans le blackout, sa borne de début déjà atteinte s’applique. Les horaires doivent être connus ; une fermeture indéterminée est un refus ENVIRONMENT_NOT_READY, jamais une hypothèse d’ouverture continue. Les événements SL/TP, annonces, FLATTEN et pertes sont des sorties événementielles du futur coordinateur, pas des échéances inventées ici. Les deux méthodes configurées sont prises en charge sans décalage UTC constant.

## Spécification exécutable

`tests/robot/london_execution_coordinateur/test_cat1_c0e_echeances_sortie.py` : durée réelle, local Londres été/hiver, pause native, blackout et insuffisance des horaires.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.

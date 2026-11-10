# Contrat de la couche 0d — prix_executables

- **Statut** : finalisé le 06/11/2026 avant son implémentation.
- **Consommateurs cartographiés** : 2a, 3, 4, 6.
- **Dépend de** : noyau amont ; aucune autre couche de cet artefact.

Unité : prix_executables
Responsabilité : Niveaux décimaux E/SL/TP/D, ou refus natif motivé ; TP recalculé depuis le prix réel et indicateur de dépassement courant.
Signature : `NiveauxExecutables`, `RefusPrix`, `construire_niveaux(signal, cotation, profil, commun)`, `recalculer_objectif(niveaux, prix_reel, cotation=None)`
Entrée : Signal, cotation décimale non croisée, profil C04 complet et paramètres communs ; prix moyen réellement rempli pour recalcul. Le modèle de stress C10 peut produire un Ask entre deux incréments de prix ; E reste exactement ce prix exécutable du modèle.
Sortie : Niveaux décimaux E/SL/TP/D, ou refus natif motivé ; TP recalculé depuis le prix réel et indicateur de dépassement courant.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

Achat : E=Ask, SL arrondi vers le bas de B_SL ; vente : E=Bid, SL arrondi vers le haut de B_SL+spread. D=sens×(E−SL)>0. TP=E+sens×k×D, arrondi vers le haut en achat et vers le bas en vente. L’epsilon de grille est celui du noyau, jamais appliqué au volume. Le stop technique est recontrôlé dans (0, maximum_chart_stop_atr×A], avant arrondi. Les distances natives sont contrôlées depuis le côté de déclenchement Bid/Ask : distance minimale incluse, niveau de gel strictement dépassé s’il est non nul. Pas de déplacement de stop pour obtenir l’acceptation. Profil, protections attachables et convention de déclenchement vérifiée sont nécessaires. Après fill le SL accepté reste fixe ; seul le TP change depuis le prix moyen. Un SL déjà franchi rend le recalcul impossible ; le TP est considéré dépassé sur Bid en achat, Ask en vente, égalité incluse.

## Spécification exécutable

Révision du 10/11/2026, phase 10 : défigeage de nature modification. La restriction
antérieure imposait la grille du tick aux deux côtés de la cotation. Elle
refusait le spread exact du stress C10 lorsque le nombre de ticks du spread
historique n'est pas divisible par quatre. C06 impose l'arrondi des protections,
conservé ici, et l'entrée au prix Ask/Bid ; C10 fixe le spread de recherche. La
cotation n'est ni arrondie ni corrigée pour faciliter une entrée. Les contrôles
de spread, de TTL, de stop, de marge et de risque restent actifs. Les prix natifs
réels restent qualifiés à la frontière de données. Les consommateurs 2a, 3, 4,
5a, 5b et 6 sont revérifiés dans cet ordre après le nouveau gel.

`tests/robot/london_execution_coordinateur/test_cat1_c0d_prix_executables.py` : C11.5, S02.5, oracle rounded_levels, trois arrondis, limites natives, recalcul et TP dépassé.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.

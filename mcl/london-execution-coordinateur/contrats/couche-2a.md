# Contrat de la couche 2a — risque_all_in

- **Statut** : finalisé le 06/11/2026 avant son implémentation.
- **Consommateurs cartographiés** : 3, 6.
- **Dépend de** : 0a, 0d, 1a.

Unité : risque_all_in
Responsabilité : Perte prix, frais, glissement par jambe, prix pessimistes et risque all-in en Decimal ; ou ENVIRONMENT_NOT_READY.
Signature : `MesureRisque` ; `calculer_risque(signal, niveaux, volume, profil, commun, port, *, apres_remplissage=False, frais_entree_reels=None)` ; `verifier_profil(profil, commun)`
Entrée : Vrais niveaux exécutables, volume natif, profil complet, port de calcul réel ou doublure externe ; coûts d’entrée réellement connus après remplissage.
Sortie : Perte prix, frais, glissement par jambe, prix pessimistes et risque all-in en Decimal ; ou ENVIRONMENT_NOT_READY.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

Avant envoi : g=max(tick_size, slippage_budget_atr_per_leg×A), entrée pessimiste E+sens×g et sortie SL−sens×g. Perte=max(0,−profit natif USD). Le spread est déjà présent dans E/SL et ne s’ajoute jamais. Les frais aller-retour sont calculés pour chaque volume par le port vérifié, minima et non-linéarités compris. Le volume doit être sur la grille native exacte, sans epsilon ni arrondi à la hausse.

Après remplissage : les niveaux contiennent le vrai prix moyen, l’entrée pessimiste est ce prix sans nouvelle réserve d’entrée ; seule la sortie conserve g. Les frais d’entrée réellement connus sont conservés, même lors d’une réduction du volume restant ; seuls les frais de sortie sont estimés pour le volume restant. Une valeur inconnue ne vaut pas zéro. Le profil est revalidé via le constructeur C04 réel ; commission nulle non confirmée, nombre invalide ou échec du port donnent ENVIRONMENT_NOT_READY. Aucun budget, marge ou réservation ne sont modifiés par ce calcul.

## Spécification exécutable

`test_cat1_c2a_risque_all_in.py` : C11.5–C11.7, L-01 exact, coûts non linéaires, après fill et pannes ; `test_cat2_c2a_risque_all_in.py` : vrai moteur London, vrais niveaux et calculateur synthétique externe.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.

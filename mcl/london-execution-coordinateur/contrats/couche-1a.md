# Contrat de la couche 1a — port_calcul

- **Statut** : finalisé le 06/11/2026 avant son implémentation.
- **Consommateurs cartographiés** : 2a, 3, 4, 6.
- **Dépend de** : 0a.

Unité : port_calcul
Responsabilité : Protocole synchrone sans envoi d’ordre ; résultat natif ou refus ENVIRONMENT_NOT_READY.
Signature : `CalculCourtier` ; `appeler_calcul(port, fonction, *args, **kwargs)`
Entrée : Port externe injecté et arguments typés ; profit, frais USD, marge isolée, contrôle natif total, spécifications et compte.
Sortie : Protocole synchrone sans envoi d’ordre ; résultat natif ou refus ENVIRONMENT_NOT_READY.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

Le port expose profit(profil,sens,volume,entree,sortie), frais_aller_retour(profil,sens,volume), frais_sortie(profil,sens,volume), marge(profil,sens,volume,entree), controler(ordre,compte,remplacement=False), specifications(symbole), etat_compte(). Profit et tous les frais sont en USD et Decimal ; une commission nulle exige la preuve du profil. Les frais incluent les minima par ordre, paliers, autres frais et conversion vérifiée ; le cœur n’invente aucun frais nul. Après remplissage, le coût d’entrée déjà réel est fourni séparément et seule la sortie encore à venir est estimée par frais_sortie. La marge isolée n’est pas la marge totale. Le contrôle natif renvoie ControleNatif, avec marge totale après ordre, marge libre et stop-out. En remplacement, le contrôle calcule le compte après réduction de la position possédée désignée par la clé, sans ajouter une deuxième position.

Tout appel lève une exception de frontière ou rend None/valeur invalide : le calcul consommateur refuse ENVIRONMENT_NOT_READY, avec le nom de la fonction. La fonction d’appel attrape les erreurs de cette frontière seulement et vérifie les types et bornes de résultat. Elle ne connaît aucune API MT5, ne journalise ni n’envoie ; le futur coordinateur enregistrera les arguments/résultats dans son journal d’entrées. Les types de profil, compte et contrôle sont ceux des couches réelles.

## Spécification exécutable

`test_cat1_c1a_port_calcul.py` : protocole, résultats et échecs ; `test_cat2_c1a_port_calcul.py` : vraie commande/compte et doublure de calcul externe.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.

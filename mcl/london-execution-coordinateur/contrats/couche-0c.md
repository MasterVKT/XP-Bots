# Contrat de la couche 0c — garde_cotation

- **Statut** : finalisé le 06/11/2026 avant son implémentation.
- **Consommateurs cartographiés** : 6.
- **Dépend de** : noyau amont ; aucune autre couche de cet artefact.

Unité : garde_cotation
Responsabilité : ADMISSIBLE, ATTENDRE ou EXPIREE ; motifs et dernière cause de C09.
Signature : `EtatCotation`, `VerdictCotation`, `evaluer_cotation(signal, cotation, instant_ms, commun, derniere_cause=None)`
Entrée : Signal technique, cotation optionnelle, instant courant entier, paramètres communs chargés et dernière cause d’attente éventuelle.
Sortie : ADMISSIBLE, ATTENDRE ou EXPIREE ; motifs et dernière cause de C09.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

Le TTL se mesure depuis la clôture théorique ; l’instant égal à sa borne est expiré. Avant cette borne, la cotation doit être du même symbole, connue après la clôture (heures fournisseur et réception au moins égales à celle-ci), sans heure future, non croisée et avec deux âges au plus égaux au maximum P-04. Bid=Ask est admis selon P-05. Une cotation absente ou invalide donne l’attente COTATION_INVALIDE, ou AUCUNE_COTATION en l’absence de toute cotation. Spread et écart Bid–clôture sont comparés en Decimal à leurs bornes chargées, égalité admise. La première cause est la validité, puis le spread, puis l’écart. À expiration, conserver la dernière cause explicite P-08 ; aucune entrée rétroactive ni libération de veto d’un autre contrôle.

## Spécification exécutable

`tests/robot/london_execution_coordinateur/test_cat1_c0c_garde_cotation.py` : C11.2, TTL exact, deux âges, heures futures et antérieures à la clôture, spread nul/croisé et bornes exactes.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.

# Contrat de la couche 1c — registre_reservations

- **Statut** : finalisé le 06/11/2026 avant son implémentation.
- **Consommateurs cartographiés** : 2b, 3, 5b, 6.
- **Dépend de** : 0a.

Unité : registre_reservations
Responsabilité : Transition atomique sérialisée, idempotente et restaurable, ou refus C09 sans mutation.
Signature : `RegistreReservations(commun, etat=None)` : `verifier_admission`, `reserver(reservation, compte, version_attendue)`, `sur_issue`, `verrouiller`, `marge_en_attente`, `risque_total`, `etat`
Entrée : État pur du registre, compte actuel, clé complète et proposition de réserve, version de l’instantané.
Sortie : Transition atomique sérialisée, idempotente et restaurable, ou refus C09 sans mutation.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

Le propriétaire unique du compte sérialise les appels ; une comparaison de version refuse toute nouvelle admission calculée sur un état périmé. Ce mécanisme pur n’est pas une transaction physique multi-processus : la sauvegarde atomique avant envoi appartient à l’infrastructure C08, sans nouvel ordre ici. Rejouer une proposition identique par clé ne réserve rien de plus, même après premier remplissage. Modifier les montants d’une clé existante est une erreur.

Les réserves et positions réelles sont dédupliquées par clé, en retenant le plus grand risque initial si un rapprochement diffère. Toute position externe bloque les nouvelles admissions. Le risque total inclut la nouvelle réserve et toutes les positions/intentions possédées ; la borne est inclusive. Positions et intentions non encore matérialisées partagent le plafond de compte. Le symbole canonique ET le sous-jacent empêchent deux contrats ou méthodes sur le même actif. Les verrous bloquent l’admission. Les marges des réservations non encore matérialisées s’ajoutent au contrôle natif cumulé ; une position présente au compte n’est pas recomptée comme intention.

REMPLIE marque la réserve sans la libérer. Une REFUSEE/EXPIREE ne termine qu’une intention non remplie. CLOTUREE libère la réserve et conserve une clé terminée empêchant sa résurrection. Ni profit flottant ni changement de jour ne libère de risque. En remplacement après fill, seule la clé possédée existante et remplie peut être exclue du calcul avant d’ajouter son volume restant ; les autres positions et réserves restent intégralement comptées.

## Spécification exécutable

`test_cat1_c1c_registre_reservations.py` : plafonds exacts, CAS, idempotence, alias, externes, libération ; `test_cat2_c1c_registre_reservations.py` : deux méthodes, vrai compte et reprise.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.

# Contrat de la couche 1c — registre_reservations

- **Statut** : finalisé le 06/11/2026 ; étendu le 07/11/2026 par défigeage `extension` pour la levée explicite d'un verrou après rapprochement C08.
- **Consommateurs cartographiés** : 2b, 3, 5b, 6.
- **Dépend de** : 0a.

Unité : registre_reservations
Responsabilité : Transition atomique sérialisée, idempotente et restaurable, ou refus C09 sans mutation.
Signature : `RegistreReservations(commun, etat=None)` : `verifier_admission`, `reserver(reservation, compte, version_attendue)`, `sur_issue`, `verrouiller`, `deverrouiller(sous_jacent)`, `marge_en_attente`, `risque_total`, `etat`
Entrée : État pur du registre, compte actuel, clé complète et proposition de réserve, version de l’instantané.
Sortie : Transition atomique sérialisée, idempotente et restaurable, ou refus C09 sans mutation.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

Le propriétaire unique du compte sérialise les appels ; une comparaison de version refuse toute nouvelle admission calculée sur un état périmé. Ce mécanisme pur n’est pas une transaction physique multi-processus : la sauvegarde atomique avant envoi appartient à l’infrastructure C08, sans nouvel ordre ici. Rejouer une proposition identique par clé ne réserve rien de plus, même après premier remplissage. Modifier les montants d’une clé existante est une erreur.

Les réserves et positions réelles sont dédupliquées par clé, en retenant le plus grand risque initial si un rapprochement diffère. Toute position externe bloque les nouvelles admissions. Le risque total inclut la nouvelle réserve et toutes les positions/intentions possédées ; la borne est inclusive. Positions et intentions non encore matérialisées partagent le plafond de compte. Le symbole canonique ET le sous-jacent empêchent deux contrats ou méthodes sur le même actif. Les verrous bloquent l’admission. Les marges des réservations non encore matérialisées s’ajoutent au contrôle natif cumulé ; une position présente au compte n’est pas recomptée comme intention.

`deverrouiller` retire uniquement le verrou textuel demandé et incrémente la version une fois s'il existait ; s'il est absent, l'état est renvoyé inchangé. Les autres verrous, réserves, risques et clés terminées sont conservés, y compris après restauration. La couche 5b ne demande cette levée qu'après rapprochement natif confirmé ; une temporisation ou une simple absence de réponse ne constitue jamais une preuve. Le registre ne prend lui-même aucune décision de rapprochement.

REMPLIE marque la réserve sans la libérer. Une REFUSEE/EXPIREE ne termine qu’une intention non remplie. CLOTUREE libère la réserve et conserve une clé terminée empêchant sa résurrection. Ni profit flottant ni changement de jour ne libère de risque. En remplacement après fill, seule la clé possédée existante et remplie peut être exclue du calcul avant d’ajouter son volume restant ; les autres positions et réserves restent intégralement comptées.

## Spécification exécutable

`test_cat1_c1c_registre_reservations.py` : plafonds exacts, CAS, idempotence, alias, externes, libération ; `test_cat2_c1c_registre_reservations.py` : deux méthodes, vrai compte et reprise.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.


## Extension additive du 10/11/2026 — tentative refusée avant tout fill

Défigeage extension tracé, consommateur 6 :
annuler_tentative(cle,version_attendue) -> EtatReservations | RefusExecution.
La coquille de décision 6 doit d’abord constater un refus natif explicite non
permanent sans aucun fill ; un timeout/None ou statut inconnu n’est jamais cette preuve.
L’opération est pure et atomique : version exacte, clé non terminale, réserve non
remplie et aucun verrou de son symbole/sous-jacent. Elle retire la réserve et
incrémente la version, sans inscrire la clé aux terminees. Répétition au numéro
de version courant d’une clé déjà retirée non terminale : état inchangé.
Version périmée, clé terminale ou verrou : RefusExecution ; réserve remplie :
ErreurExecution, jamais de libération. Aucun changement du comportement des
méthodes existantes. Les nouvelles tentatives doivent être complètement
dimensionnées, réservées et persistées par le coordinateur, avant toute entrée.
Décision et cas : [CORRECTION-REFUS-PRIX-PHASE11.md](../CORRECTION-REFUS-PRIX-PHASE11.md).

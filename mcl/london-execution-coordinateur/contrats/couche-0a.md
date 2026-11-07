# Contrat de la couche 0a — types_execution

- **Statut** : finalisé le 06/11/2026 avant son implémentation ; corrigé par défigeage `correction` avant construction de 2a : risque nul C07 et collections restaurées mal formées.
- **Consommateurs cartographiés** : 1a, 1b, 1c, 2a, 2b, 3, 4, 5a, 5b, 6.
- **Dépend de** : noyau amont ; aucune autre couche de cet artefact.

Unité : types_execution
Responsabilité : Valeurs d’exécution et états restaurables ; adaptateurs conservant la sémantique des deux noyaux.
Signature : `RefusExecution`, `EtatIntention`, `PositionCompte`, `EtatCompte`, `Reservation`, `EtatReservations`, `EtatGardes`, `ControleNatif`, `OrdreCalcule` ; `adapter_signal_ema`, `adapter_cotation_ema`, `adapter_cle_ema`
Entrée : Objets immuables du noyau canonique ; objets Signal, Tick et CleIntention réels du noyau EMA aux seules fonctions d’adaptation. Montants Decimal finis ; instants entiers UTC.
Sortie : Valeurs d’exécution et états restaurables ; adaptateurs conservant la sémantique des deux noyaux.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

Les positions portent une clé possédée ou None pour une position externe, le symbole canonique et le sous-jacent. Une position externe n’est jamais attribuée au robot. Une réserve garde son risque initial et sa marge ; elle est identifiée par la clé complète, non par son empreinte abrégée. Les collections sont copiées en tuples ; les clés sont uniques. L’état du compte comprend fonds propres, solde, marge utilisée, positions et indicateur de flux externe non neutralisé. Une réserve ne peut pas avoir un volume nul ni un risque négatif.

Les états de gardes comprennent le jour UTC, la base, le pic, les deux verrous, l’instant observé et les références de décisions. Le contrôle natif exprime la marge TOTALE après ordre, la marge libre après ordre et le contrôle de stop-out, jamais la seule marge isolée. Les commandes de calcul ne sont pas des envois.

L’adaptateur de signal accepte uniquement le vrai type Signal EMA, convertit ±1 vers le sens nommé, conserve instant, ATR, stop, objectif et provenance dans le contexte. La clôture décimale doit faire un aller-retour exact par la représentation flottante courte ; sinon la conversion est refusée. Le contexte EMA est recopié en valeurs JSON (Decimal en texte exact). L’adaptateur de tick conserve exactement Bid et Ask décimaux et l’heure fournisseur, et exige une heure de réception explicite. L’adaptateur de clé conserve les cinq composantes ; il ne convertit jamais une clé sérialisée ou un ancien journal.

Correction normative C07 : un volume doit être strictement positif ; un risque initial peut être nul et ne peut jamais être négatif. Une réserve à risque nul occupe toujours une place. Les collections d'état acceptent des tuples ou listes et sont validées avant leur hachage ; un mauvais type, y compris une valeur non hachable, lève l'erreur ValueError de la couche.

## Spécification exécutable

`tests/robot/london_execution_coordinateur/test_cat1_c0a_types_execution.py` : types stricts, booléens, mutabilité, clés, positions externes, adaptations de vrais objets EMA et pertes de représentation refusées.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.

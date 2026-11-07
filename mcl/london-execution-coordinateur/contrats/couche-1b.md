# Contrat de la couche 1b — gardes_compte

- **Statut** : finalisé le 06/11/2026 avant son implémentation.
- **Consommateurs cartographiés** : 3, 5a, 5b, 6.
- **Dépend de** : 0a.

Unité : gardes_compte
Responsabilité : Base UTC vérifiée, pic et verrous persistants en mémoire exportable, ou refus lorsque la base/les flux sont inconnus.
Signature : `MouvementCompte`, `BaseReconstituee`, `reconstituer_base_utc(compte, mouvements, couverture, *, aucune_position_minuit)` ; `GardesCompte(commun, etat=None)` avec `observer`, `neutraliser_flux`, `reactiver`, `refus`, `etat`
Entrée : Instantané réel du compte ; mouvements de solde USD identifiés et couverture complète de l’historique ; état restauré optionnel.
Sortie : Base UTC vérifiée, pic et verrous persistants en mémoire exportable, ou refus lorsque la base/les flux sont inconnus.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

P-12 : à 00:00 UTC exactement, la base est l’équité observée ; en dehors de cet instant, elle est reconstituée par solde courant moins tous les mouvements depuis minuit, sur historique couvrant toute cette période et sans position à minuit. La base reconstituée est rapportée au jour UTC et à l’instantané exact ; les premières équités du jour ne la remplacent jamais. Le pic hors fonctionnement est borné par le solde reconstitué et ses variations chronologiques, pas par un flottant inventé. Les mouvements sont uniques, ordonnés causalement et sans heure future. Dépôts/retraits identifiés sont neutralisés en translatant les bases et le pic, avec référence idempotente ; flux inconnu bloque l’entrée.

Aux seuils inclusifs, équité ≤ base×(1−limite quotidienne) déclenche le verrou jusqu’au jour UTC suivant ; équité ≤ pic×(1−baisse globale) déclenche l’arrêt persistant. Le jour Londres n’intervient pas. Les pertes flottantes et frais sont déjà dans l’équité. Un état restauré garde les verrous ; un redémarrage ne réactive rien. Seule `reactiver` avec une nouvelle référence de décision de déploiement peut lever l’arrêt global, et ne lève pas le verrou quotidien du même jour. Tout compte observé doit avancer ou conserver son instant, jamais revenir dans le passé. Les demandes effectives de clôture appartiennent à la phase 6.

La reconstitution conserve également chaque flux identifié avec sa référence et son montant. À une reprise sur un nouveau jour UTC, les flux nouveaux translatent le pic antérieur ; une référence déjà neutralisée ne le translate pas une seconde fois. Un retrait ne doit donc jamais créer artificiellement une baisse globale. Ce cas a été ajouté et corrigé avant le premier gel de la couche.

## Spécification exécutable

`test_cat1_c1b_gardes_compte.py` : C11.13, seuils exacts, P-12, flux et erreurs ; `test_cat2_c1b_gardes_compte.py` : reprise réelle des états et jours UTC/Londres.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.

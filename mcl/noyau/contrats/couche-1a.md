# Contrat de la couche 1a — marche

- **Statut** : finalisé le 05/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : couche 2 (`journal`) ; plus tard `donnees-temps` (ticks → bougies),
  `execution-coordinateur` (cotations), `infrastructure` et `journal-rejeu` (construction des ticks)
- **Dépend de** : couches 0a (`instant`) et 0b (`nombres`), réelles et figées ; aucune frontière externe

---

Unité : marche
Responsabilité : Représenter ticks, cotations et bougies Bid validés.
Signature : `Tick(symbole, symbole_courtier, instant_fournisseur_ms, instant_reception_ms, numero, bid, ask, drapeaux=0)`
avec la propriété `cle -> CleEvenement(instant_reception_ms, numero)` ;
`Cotation(symbole, bid: Decimal, ask: Decimal, instant_fournisseur_ms, instant_reception_ms)` avec la propriété
`spread -> Decimal` ; `cotation_depuis_tick(tick: Tick, pas: Decimal) -> Cotation` ;
`Bougie(symbole, debut_ms, duree_ms, ouverture, haut, bas, cloture, nombre_evenements, valide, motif_invalidite, instant_disponibilite_ms)`
avec la propriété `fin_ms` ; `ErreurMarche(ValueError)`.
Entrée : symboles non vides ; instants entiers en millisecondes UTC (couche 0a) ; numéro entier ≥ 0 ; Bid et Ask
du tick : nombres finis strictement positifs (flottants du courtier, `drapeaux` entier ≥ 0, 0 quand la source
n'en fournit pas) ; Bid et Ask de la cotation : décimaux finis strictement positifs ; pas de grille > 0 ; bougie
alignée (`debut_ms` multiple de `duree_ms`), OHLC flottants, motif d'invalidité identifiant majuscule.
Sortie : objets immuables. Le tick garde Bid et Ask en flottants ; `cotation_depuis_tick` les convertit par la
représentation décimale la plus courte (0b) et exige qu'ils soient sur la grille du pas ; `spread = ask − bid`.
Une cotation croisée (Bid > Ask) reste représentable : son admissibilité relève de `execution-coordinateur`
(C06, P-05). Bougie valide : quatre prix finis, `bas ≤ min(ouverture, clôture) ≤ max(ouverture, clôture) ≤ haut`,
au moins un événement, aucun motif d'invalidité. Bougie invalide : motif obligatoire (`AUCUN_BID` par P-02,
ou autre), prix tous absents ou tous cohérents. `instant_disponibilite_ms ≥ fin_ms` (C03.2, C03.4).
Effets de bord : aucun.
Erreurs, exceptions : `ErreurMarche` pour tout champ manquant, de mauvais type, hors bornes, non aligné, un prix
de cotation hors de la grille, ou une bougie incohérente.

---

## Spécification exécutable

`tests/robot/noyau/test_cat1_c1a_marche.py` et `tests/robot/noyau/test_cat2_c1a_marche.py`.

## Comportements documentés (loi de Hyrum)

Les flottants du tick sont conservés tels quels (`int` converti en `float`) ; aucun arrondi n'est appliqué au
tick. Le texte des messages d'erreur n'est pas garanti.

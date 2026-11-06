# Contrat de la couche 1a — range_londres

- **Statut** : finalisé le 06/11/2026, avant implémentation ; gel après gate vert. Corrigé le 06/11/2026 par défigeage `correction` : fins LF pour la conservation des empreintes après normalisation Git. Test des extrêmes hétérogènes ajouté après mutation survivante max/min.
- **Consommateurs cartographiés** : couche 2, moteur London.
- **Dépend de** : couches 0a et 0b réelles et figées ; noyau et données réels ; aucune frontière externe.

Unité : range_londres
Responsabilité : celle du document 02, §6.3, sans ajout de règle métier.
Signature : `construire_range(jour: date, bougies: Iterable[BougieEnrichie], parametres: ParametresLondon) -> RangeLondon | RefusLondon`.
Entrée : paramètres London typés, valeurs du noyau et bougies enrichies réelles, selon la signature.
Sortie : valeur validée ou refus fermé conforme au document 01, §9.3.
Effets de bord : aucun accès externe ; seule la classe de quotas conserve son état interne.
Erreurs, exceptions : `ErreurLondon` pour les violations décrites ci-dessous.

Le calendrier fournit exactement les ouvertures attendues de [début, fin). Seules ces ouvertures sont
lues ; les suivantes ne déplacent jamais les extrêmes. Toutes les bougies du range doivent être M15, du même
symbole et valides. Un intervalle absent donne NO_SETUP/RANGE_INCOMPLET ; un intervalle invalide donne
NO_SETUP/RANGE_BOUGIE_INVALIDE, ou DATA_GAP avec le même détail si la cause est TROU_DONNEES ou HORAIRES_INCONNUS.
La largeur nulle donne NO_SETUP/RANGE_HORS_BORNES. La disponibilité est le maximum des disponibilités des
vingt bougies : aucune réception tardive antérieure dans le range n'est anticipée. Une ouverture attendue en
double, un mauvais type, une durée ou un symbole discordants lève ErreurLondon. Une journée inactive ne
construit pas de range et donne OUTSIDE_SESSION/JOUR_INACTIF.

## Spécification exécutable

`tests/robot/moteur_london/test_cat1_c1a_range_londres.py` et
`tests/robot/moteur_london/test_cat2_c1a_range_londres.py`.

## Comportements documentés (loi de Hyrum)

Les comparaisons n'ajoutent aucune tolérance ; les tests aux bornes utilisent des valeurs dyadiques.
Le texte exact des erreurs n'est pas garanti. Les refus rendent les codes et détails du noyau, sans nouveau code.

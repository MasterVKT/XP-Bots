# Contrat de la couche 1b — indicateurs

- **Statut** : finalisé le 06/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : couche 2b (`etat_indicateurs`)
- **Dépend de** : couche 0a (réelle et figée) ; aucune frontière externe

---

Unité : indicateurs
Responsabilité : Calculer TR, ATR14 Wilder et A_t par récurrence incrémentale.
Signature : `EtatIndicateurs(periode, cloture_precedente, tr_initiaux, atr)` ; `etat_initial(periode: int) -> EtatIndicateurs` ;
`avancer(etat: EtatIndicateurs, haut: float, bas: float, cloture: float) -> ResultatIndicateurs` ;
`ResultatIndicateurs(tr, atr, a, etat)`.
Entrée : état précédent ; haut, bas, clôture Bid finis d'une bougie **valide**, `bas ≤ clôture ≤ haut` ; période
entière > 0 (`atr_period`, lue par l'appelant).
Sortie : `tr = haut − bas` pour la première bougie de la chaîne, sinon
`max(haut − bas, |haut − C_préc|, |bas − C_préc|)` (C03.10) ; `atr` absent tant que moins de `periode` TR ; à la
`periode`-ième bougie, moyenne des `periode` premiers TR par somme séquentielle dans l'ordre des bougies ; ensuite
`((periode − 1) × ATR_préc + TR) / periode` (Wilder, ordre d'opérations de `wilder` de la référence) ;
`a` = ATR de la bougie précédente de la chaîne (A_t = ATR de t − 1, C03.11), absent tant qu'il n'existe pas ;
nouvel état immuable. Flottants 64 bits.
Effets de bord : aucun.
Erreurs, exceptions : `ErreurDonneesTemps` pour une période invalide, un prix non fini, `bas > haut` ou une
clôture hors de `[bas, haut]`.

---

## Spécification exécutable

`tests/robot/donnees_temps/test_cat1_c1b_indicateurs.py` et `tests/robot/donnees_temps/test_cat2_c1b_indicateurs.py`.

## Comportements documentés (loi de Hyrum)

La moyenne initiale séquentielle peut différer d'un ulp de `numpy.mean` (référence) ; les comparaisons à l'oracle
utilisent une tolérance relative de 1e−12. Le texte des messages d'erreur n'est pas garanti.

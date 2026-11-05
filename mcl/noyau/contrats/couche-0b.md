# Contrat de la couche 0b — nombres

- **Statut** : finalisé le 05/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : couches 1a (`marche` : cotations sur la grille), 1b (`instrument` : champs
  décimaux du profil) ; plus tard `execution-coordinateur` (niveaux exécutables, volumes, montants)
- **Dépend de** : aucune couche ; aucune frontière externe (bibliothèque standard `decimal`)

---

Unité : nombres
Responsabilité : Convertir les flottants du courtier en décimaux sûrs et ramener une valeur sur une grille avec contrôle d'erreur.
Signature : `decimal_depuis(valeur: int | float | Decimal | str) -> Decimal` ;
`arrondir_sur_grille(valeur, pas, sens: Arrondi) -> Decimal` ; `est_sur_grille(valeur, pas) -> bool` ;
`Arrondi.BAS`, `Arrondi.HAUT` ; `EPSILON_GRILLE = Decimal('1e-8')` ; `ErreurNombre(ValueError)`.
Entrée : flottant converti par sa représentation décimale la plus courte (`repr`), jamais par son développement
binaire (`0.1` → `Decimal('0.1')`) ; entier exact ; décimal fini ; texte décimal (`'15.00'`) ; pas : nombre fini
strictement positif de mêmes types.
Sortie : décimal fini ; `arrondir_sur_grille` rend `n × pas` avec `n = floor(valeur/pas + ε)` vers le bas et
`n = ceil(valeur/pas − ε)` vers le haut, ε = 1e−8 unité de grille (sémantique de `rounded_levels` de
`reference/technical.py`), à l'exposant du pas ; `est_sur_grille` teste l'appartenance exacte.
Effets de bord : aucun ; calculs dans un contexte décimal local de 50 chiffres, jamais dans le contexte global.
Erreurs, exceptions : `ErreurNombre` pour un booléen, un NaN, un infini, un texte illisible, un type non pris en
charge, un pas nul ou négatif.

---

## Spécification exécutable

`tests/robot/noyau/test_cat1_c0b_nombres.py` (profondeur 0 : pas de catégorie 2).

## Comportements documentés (loi de Hyrum)

L'exposant du résultat d'un arrondi est celui du pas (`Decimal('0.00001')` → cinq décimales). Le texte des
messages d'erreur n'est pas garanti.

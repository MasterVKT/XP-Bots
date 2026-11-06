# Contrat de la couche 0b — types_london

- **Statut** : finalisé le 06/11/2026, avant implémentation ; gel après gate vert. Corrigé le 06/11/2026 par défigeage `correction` : fins LF pour la conservation des empreintes après normalisation Git.
- **Consommateurs cartographiés** : couches 1a, 1b, 1c, 1d, 1e et 2.
- **Dépend de** : aucune couche de cet artefact.

Unité : types_london
Responsabilité : Définir les valeurs immuables intermédiaires.
Signature : `ErreurLondon(ValueError)` ; `RangeLondon(jour, haut, bas, disponible_ms)` avec `largeur` ;
`GelATRH1(jour, atr, fin_h1_ms, disponible_ms)` ; `Cassure(sens, fraction_corps, fraction_cloture, buffer)` ;
`StopLocal(niveau, multiple_objectif, distance, composantes, contraignantes)` ;
`EtatQuotas(jour=None, remplissages=())` ; `RefusLondon(motif, detail)` ;
`nombre_fini(valeur, nom, minimum=None, strict=False)` ; `tick_flottant(tick_size: Decimal)` ;
`verifier_bougie(enrichie, unite, duree_ms, symbole=None)`.
Entrée : jours `date` sans datetime ; instants UTC du noyau ; prix finis, `haut > bas` ; ATR strictement
positif ; disponibilité du gel ≥ fin H1 ; fractions dans [0, 1], buffer positif ; tuple de trois composantes
finies et tuple non vide de noms parmi `BOUGIE`, `FRONTIERE`, `PLANCHER_ATR` ; clés d'intention distinctes.
Sortie : objets immuables ; refus contrôlé par `verifier_motif` du noyau ; état de quotas avec jour obligatoire
si des remplissages existent. Le helper de bougie exige type, unité, durée et symbole éventuel cohérents.
La taille de tick est obligatoirement un `Decimal` fini positif, représentable en flottant fini positif.
Effets de bord : aucun.
Erreurs, exceptions : `ErreurLondon` pour une violation de ces contraintes (booléens refusés comme nombres).

## Spécification exécutable

`tests/robot/moteur_london/test_cat1_c0b_types_london.py` ; pas de catégorie 2 à cette profondeur.

## Comportements documentés (loi de Hyrum)

Les composantes du stop sont ordonnées bougie, frontière, plancher ATR. Les clés conservées par `EtatQuotas`
permettent de restaurer les quotas sans recompter un premier remplissage. Le texte des erreurs n'est pas garanti.

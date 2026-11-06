# Contrat de la couche 0a — types_donnees

- **Statut** : finalisé le 06/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : couches 1a, 1b, 1c, 2a, 2b, 3 ; plus tard `moteur-london`, `orchestration`
- **Dépend de** : noyau figé (`c1a_marche.Bougie`) ; aucune couche de l'artefact ; aucune frontière externe

---

Unité : types_donnees
Responsabilité : Définir les objets intermédiaires du flux de données.
Signature : `ErreurDonneesTemps(ValueError)` ; `UniteTemps` (`M15`, `H1`) avec `duree_ms(commun) -> int` ;
`StatutCouverture` (`COUVERT`, `FERMETURE_OFFICIELLE`, `TROU`, `INCONNU`) ; `NatureTrou` (`DEBUT`, `FIN`) ;
`ChangementTrou(symbole, nature, intervalle_ms, instant_ms)` ; `AnomalieDonnees(symbole, raison, instant_ms)` ;
`IndicateursBougie(tr, atr, a, rang)` ; `IdentitePrechargement(premiere_ms, nombre, empreinte)` ;
`BougieEnrichie(bougie, unite, indicateurs, jour_londres, ouverture_locale, cloture_locale, jour_utc)`.
Entrée : `duree_ms` lit `timeframe_seconds` (M15) ou `h1_seconds` (H1) des `ParametresCommuns` ; textes non
vides ; instants entiers ≥ 0 ; flottants finis ; `rang` entier ≥ 0 ; empreinte : 64 caractères hexadécimaux.
Sortie : objets immuables. `IndicateursBougie` : `tr ≥ 0`, `atr` et `a` absents (`None`) ou ≥ 0.
`BougieEnrichie` : `indicateurs` présents si et seulement si la bougie est valide ; repères locaux conscients du
fuseau ; dates `date`.
Effets de bord : aucun.
Erreurs, exceptions : `ErreurDonneesTemps` pour tout champ de mauvais type ou hors bornes, ou une incohérence
entre validité de la bougie et présence des indicateurs.

---

## Spécification exécutable

`tests/robot/donnees_temps/test_cat1_c0a_types.py` (profondeur 0 : pas de catégorie 2).

## Comportements documentés (loi de Hyrum)

Les énumérations sont des `StrEnum`. Le texte des messages d'erreur n'est pas garanti.

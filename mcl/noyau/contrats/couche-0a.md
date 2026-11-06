# Contrat de la couche 0a — instant

- **Statut** : finalisé le 05/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : couches 1a (`marche`), 1b (`instrument`), 1c (`domaine`)
- **Dépend de** : aucune couche ; aucune frontière externe (bibliothèque standard `datetime`)

---

Unité : instant
Responsabilité : Représenter un instant UTC en millisecondes entières et ordonner les événements de façon stable.
Signature : `instant_depuis_iso(texte: str) -> int` ; `instant_depuis_datetime(moment: datetime) -> int` ;
`verifier_instant(valeur: object) -> int` ; `instant_vers_iso(instant_ms: int) -> str` ;
`instant_vers_datetime(instant_ms: int) -> datetime` ; `aligner(instant_ms: int, duree_ms: int) -> int` ;
`CleEvenement(instant_ms: int, numero: int)` (ordonnable, immuable) ; `ErreurInstant(ValueError)`.
Entrée : texte ISO-8601 avec suffixe `Z` ou décalage `+00:00` (ex. `2026-07-15T07:00:00.250Z`) ; datetime
conscient de son fuseau, quel qu'il soit ; entier de millisecondes ≥ 0 (booléens refusés) ; durée entière > 0.
Sortie : entier de millisecondes depuis l'origine UTC ; texte `AAAA-MM-JJTHH:MM:SS.mmmZ` ; datetime UTC
conscient ; `aligner` rend `floor(instant / durée) × durée` ; `CleEvenement` s'ordonne par instant puis numéro.
Effets de bord : aucun.
Erreurs, exceptions : `ErreurInstant` pour un texte illisible, sans fuseau, avec un décalage non nul (comme
`utc()` de `reference/llm_contracts.py`), un datetime naïf, une précision inférieure à la milliseconde non
nulle, un entier négatif ou non entier, une durée non entière ou ≤ 0, un numéro négatif.

---

## Spécification exécutable

`tests/robot/noyau/test_cat1_c0a_temps.py` (profondeur 0 : pas de catégorie 2).

## Comportements documentés (loi de Hyrum)

Les instants sont des `int` Python ordinaires ; aucune autre représentation n'est promise. Le texte des messages
d'erreur n'est pas garanti.

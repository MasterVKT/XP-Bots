# Contrat de la couche 2b — etat_indicateurs

- **Statut** : finalisé le 06/11/2026 (figé par `mcl.py figer` après gate vert) ; corrigé le 06/11/2026
  (défigeage `correction` : la spécification exécutable calcule l'empreinte chaînée exactement ; interface inchangée)
- **Consommateurs cartographiés** : couche 3 (`flux_bougies`)
- **Dépend de** : couches 0a et 1b (réelles et figées) ; noyau figé (`c1a_marche.Bougie`) ; aucune frontière externe

---

Unité : etat_indicateurs
Responsabilité : Tenir la chaîne d'indicateurs, le préchargement, les rangs et la reprise par export et import.
Signature : `SCHEMA_ETAT = 'xp-etat-indicateurs-v1'` ; `ChaineIndicateurs(periode: int)` avec
`ajouter(bougie: Bougie) -> IndicateursBougie | None`, `identite -> IdentitePrechargement`,
`nombre_valides -> int`, `exporter(empreinte_configuration: str) -> dict` et
`ChaineIndicateurs.importer(donnees: Mapping, empreinte_configuration: str) -> ChaineIndicateurs`.
Entrée : bougies du noyau d'une même durée, en ordre strictement croissant de début ; période entière > 0 ;
empreinte de configuration : 64 caractères hexadécimaux (empreinte canonique de l'export technique).
Sortie : une bougie invalide ne rend rien et n'entre dans aucune récurrence (P-03) : la bougie valide suivante
calcule son TR avec la dernière clôture valide ; une bougie valide rend `IndicateursBougie(tr, atr, a, rang)`
calculés par 1b, `rang` = nombre de bougies valides avant elle depuis le début de la chaîne (P-10 : décision
possible sur la bougie de rang ≥ minimum − 1) ; `identite` : début de la première bougie valide, nombre de
bougies valides, empreinte chaînée `h_n = SHA-256(h_{n−1} | début | durée | O | H | L | C)` (prix par leur `repr`,
`h_0` = 64 zéros), donc deux préchargements différents ont des identités différentes (C03.7) ; `exporter` rend un
dictionnaire JSON de l'état complet ; `importer` le restitue à l'identique.
Effets de bord : état interne de la chaîne.
Erreurs, exceptions : `ErreurDonneesTemps` pour une bougie hors ordre ou d'une autre durée, un objet qui n'est pas
une bougie du noyau, un export d'un autre schéma, d'une autre empreinte de configuration, incomplet, de mauvais
type ou incohérent.

---

## Spécification exécutable

`tests/robot/london_donnees_temps/test_cat1_c2b_etat_indicateurs.py` et `tests/robot/london_donnees_temps/test_cat2_c2b_etat_indicateurs.py`.

## Comportements documentés (loi de Hyrum)

Le dictionnaire exporté est sérialisable en JSON strict (nombres finis) ; ses clés ne sont pas une interface
pour d'autres consommateurs que `importer`. Le texte des messages d'erreur n'est pas garanti.

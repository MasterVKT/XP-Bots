# Contrat de la couche 2a — validation_bougies

- **Statut** : finalisé le 06/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : couche 3 (`flux_bougies`)
- **Dépend de** : couches 0a, 1a et 1c (réelles et figées) ; noyau figé (`c1a_marche.Bougie`,
  `c1b_instrument.HorairesCotation`) ; aucune frontière externe

---

Unité : validation_bougies
Responsabilité : Combiner bougie brute et couverture en bougie valide ou invalide motivée, et signaler les trous.
Signature : `ValidateurBougies(symbole, en_trou=False)` avec `en_trou -> bool` et
`valider(brute: BougieBrute, horaires: HorairesCotation, couverture: SourceCouverture) -> ResultatValidation` ;
`ResultatValidation(bougie, statut, changement)` ; motifs `AUCUN_BID`, `MARCHE_FERME`, `TROU_DONNEES`,
`HORAIRES_INCONNUS`.
Entrée : bougie brute du symbole (1a) ; horaires du noyau ; source de couverture (1c).
Sortie : statut de l'intervalle par `classer_intervalle` (1c), puis bougie du noyau : `COUVERT` avec au moins un
Bid → valide ; `COUVERT` sans événement → invalide `AUCUN_BID`, sans état de trou (P-02) ; `FERMETURE_OFFICIELLE`
→ invalide `MARCHE_FERME`, prix éventuels conservés, état de trou inchangé ; `TROU` → invalide `TROU_DONNEES` ;
`INCONNU` → invalide `HORAIRES_INCONNUS`. Aucune bougie synthétique ; disponibilité de la bougie brute
conservée. Changement d'état (C03.6) : `DEBUT` au premier intervalle `TROU` ou `INCONNU` hors trou, `FIN` au
premier intervalle `COUVERT` qui le suit (flux rétabli) ; `intervalle_ms` = début de cet intervalle,
`instant_ms` = disponibilité de sa bougie.
Effets de bord : état de trou du validateur.
Erreurs, exceptions : `ErreurDonneesTemps` pour une bougie brute d'un autre symbole ou de mauvais type, ou pour une
erreur de classement levée par 1c.

---

## Spécification exécutable

`tests/robot/london_donnees_temps/test_cat1_c2a_validation.py` et `tests/robot/london_donnees_temps/test_cat2_c2a_validation.py`.

## Comportements documentés (loi de Hyrum)

Le flux (couche 3) utilise l'état de trou du validateur M15 comme état de trou du symbole. Le texte des messages
d'erreur n'est pas garanti.

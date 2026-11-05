# Contrat de la couche 1c — indicateurs (artefact `donnees-temps`)

- **Statut** : finalisé (phase 2, 2026-11-05) ; gel tracé dans `mcl/donnees-temps/journal.jsonl`.
- **Consommateurs cartographiés** : couche 2 (`etat_indicateurs`) ; hors artefact : `moteur-ema` (noms des
  indicateurs).
- **Dépend de** : aucune couche interne ; amont figé : aucun ; frontières externes : aucune.
- **Module** : `src/xpbots/donnees_temps/c1c_indicateurs.py`
- **Sources normatives** : C03 points 8 à 12 ; plan maître 7.A.

---

Unité : indicateurs
Responsabilité : Calculer de façon incrémentale l'EMA à graine SMA, le RSI et l'ATR de Wilder et le TR, en
flottants 64 bits et dans l'ordre exact des récurrences.
Signature : `EtatEMA(n).maj(cloture) -> float | None` ; `EtatWilder(n).maj(x) -> float | None` ;
`EtatRSI(n).maj(cloture) -> float | None` ; `EtatATR(n).maj(h, l, c) -> MesureATR(tr, atr, a_t)` ; pour chacun
`valeur`, `exporter() -> dict`, `importer(dict)` ; noms : `cle_ema(n)`, `cle_ema_decalee(n, k)`, `cle_rsi(n)`,
`cle_atr(n)`, `CLE_TR`.
Entrée : clôtures et OHLC Bid (flottants finis) de bougies valides, dans l'ordre.
Sortie :
- EMA(n) : indisponible avant la n-ième clôture ; graine = moyenne exacte (`math.fsum`) des n premières clôtures ;
  ensuite `EMA_t = EMA_(t−1) + 2/(n+1) × (C_t − EMA_(t−1))` ;
- Wilder(n) : graine = moyenne exacte des n premières valeurs ; ensuite `(13 M_(t−1) + x_t)/14` pour n = 14, soit
  `((n−1) M_(t−1) + x_t)/n` ;
- RSI(n) : variations entre clôtures ; Wilder des hausses et des baisses ; 50 si les deux moyennes sont nulles,
  100 si seule la baisse est nulle, 0 si seule la hausse est nulle, sinon `100 − 100/(1 + hausse/baisse)` ;
  disponible à partir de la (n+1)-ième clôture ;
- TR : `max(H−L, |H−C_(t−1)|, |L−C_(t−1)|)`, `H−L` pour la première bougie ; ATR = Wilder(n) du TR ; `a_t` =
  ATR de la bougie précédente (C03 point 11), `None` s'il n'existe pas encore.
Effets de bord : états récursifs internes.
Erreurs, exceptions : `ValeurInvalide` si une entrée n'est pas un flottant fini ou si une période n'est pas un
entier strictement positif ; `ValeurInvalide` si un état importé est incohérent.

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/donnees_temps/test_c1c_cat1_*.py`) : concordance avec `reference.technical`
  (`ema`, `wilder`, `rsi`, `add_indicators`) à 1e-12 près et mêmes comparaisons de seuil, indisponibilité avant
  la graine, cas RSI nuls (50, 100, 0), TR de la première bougie, `a_t` = ATR de t−1, export puis import à
  l'identique, entrées non finies refusées.
- Catégorie 2 : par les couches 2 et 3.

## Comportements documentés (loi de Hyrum)

La graine utilise une somme exactement arrondie : l'écart avec la moyenne de la référence (somme par paires de
numpy) est au plus de quelques ulp et ne change aucune comparaison de seuil sur les séries de contrôle.

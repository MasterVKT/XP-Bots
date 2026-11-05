# Contrat de la couche 1c — indicateurs (artefact `donnees-temps`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 2), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/donnees_temps/c1c_indicateurs.py`
- **Sources normatives** : C03 (points 1 à 12), C11.1, C11.3, C11.4 ; plan maître, section 7.A

---

Unité : indicateurs
Responsabilité : Calculer de façon incrémentale EMA graine SMA, RSI et ATR Wilder, TR et A_t = ATR de t−1.
Signature : EtatEMA(n).maj(cloture) -> float | None ; EtatRSI(n).maj(cloture) ; EtatATR(n).maj(h, l, c) ; a_t() -> float | None
Entrée : clôtures et OHLC Bid de bougies valides, dans l'ordre
Sortie : valeurs float64, None avant la graine ; historique EMA50 sur 4 bougies
Effets de bord : états récursifs internes
Erreurs, exceptions : ValeurInvalide si une entrée n'est pas finie

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/donnees_temps/test_c1c_cat1_*.py`) : égalité à reference.technical (ema, wilder, rsi, add_indicators) à 1e-12 près et mêmes comparaisons de seuil ; graines ; RSI 50/100/0 ; TR de la première bougie = H−L.
- Catégorie 2 (`tests/robot/donnees_temps/test_c1c_cat2_*.py`) : via les couches 2 et 3.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

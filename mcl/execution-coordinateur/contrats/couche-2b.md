# Contrat de la couche 2b — arbitrage (artefact `execution-coordinateur`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 4 et 5), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 6
- **Dépend de** : couches 1d (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/execution/c2b_arbitrage.py`
- **Sources normatives** : C04, C06, C07, C08, C09, C11.2, C11.5–C11.7, C11.10–C11.13 ; plan maître, section 7.D

---

Unité : arbitrage
Responsabilité : Ordonner les signaux simultanés selon les priorités figées et l'occupation des sous-jacents.
Signature : ordonner(signaux, priorites_strategies, priorites_symboles) -> list[Signal] ; symbole_libre(registre, symbole) -> bool
Entrée : signaux du même instant, registre
Sortie : liste ordonnée ; aucune fusion ni couverture opposée
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/execution/test_c2b_cat1_*.py`) : LONDON_V3 avant EMA_V3 puis EURUSD, GBPUSD, XAUUSD ; une position par sous-jacent (C11.10, R17).
- Catégorie 2 (`tests/robot/execution/test_c2b_cat2_*.py`) : via 6.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

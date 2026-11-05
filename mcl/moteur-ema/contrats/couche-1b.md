# Contrat de la couche 1b — conditions-repli (artefact `moteur-ema`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 3), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/moteur_ema/c1b_repli.py`
- **Sources normatives** : S01.1 à S01.6, C03.8–C03.11, C06 (conversion), A07 ; plan maître, section 7.B

---

Unité : conditions_repli
Responsabilité : Tester le contexte d'armement, la validité du repli et le contact avec la zone EMA15–EMA50.
Signature : contexte_armement(sens, c, e15, rsi) -> bool ; repli_valide(sens, c, e50, rsi, a) -> bool ; contact(bas, haut, e15, e50) -> bool
Entrée : valeurs de la bougie et indicateurs, A_t > 0
Sortie : booléens selon S01.2 points 4 à 6
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c1b_cat1_*.py`) : RSI de repli 40 admis ; clôture à EMA50−0,25A exactement admise ; mèche sous EMA50 sans clôture au-delà n'annule pas ; contact aux bornes.
- Catégorie 2 (`tests/robot/moteur_ema/test_c1b_cat2_*.py`) : via 2.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

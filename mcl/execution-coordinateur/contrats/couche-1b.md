# Contrat de la couche 1b — prix-executables (artefact `execution-coordinateur`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 4 et 5), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2a, 4
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/execution/c1b_prix.py`
- **Sources normatives** : C04, C06, C07, C08, C09, C11.2, C11.5–C11.7, C11.10–C11.13 ; plan maître, section 7.D

---

Unité : prix_executables
Responsabilité : Convertir B_SL en SL exécutable, choisir E et calculer TP avec les arrondis au tick de C06.
Signature : niveaux_executables(sens, b_sl, bid, ask, k, profil) -> NiveauxOrdre | Refus ; tp_apres_fill(prix_moyen, sl, sens, k, tick) -> Decimal
Entrée : sens, B_SL, Bid, Ask, k, tick_size et contraintes natives
Sortie : E, SL, TP, D en Decimal sur la grille ; refus avant ordre si contrainte native (R7)
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/execution/test_c1b_cat1_*.py`) : S01.5 : E 1,10010, SL 1,09945, TP 1,10108 ; vente SL 1,10065, TP 1,09902 ; concordance rounded_levels ; C11.5 ; contraintes natives (R7).
- Catégorie 2 (`tests/robot/execution/test_c1b_cat2_*.py`) : via 2a et 4.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

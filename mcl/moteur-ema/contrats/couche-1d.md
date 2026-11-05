# Contrat de la couche 1d — stop-objectif (artefact `moteur-ema`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 3), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/moteur_ema/c1d_stop.py`
- **Sources normatives** : S01.1 à S01.6, C03.8–C03.11, C06 (conversion), A07 ; plan maître, section 7.B

---

Unité : stop_objectif_ema
Responsabilité : Calculer buffer, B_SL non arrondi, refus au-delà de 2,50 A et multiple d'objectif.
Signature : stop_technique(sens, c, extreme_repli, a, tick_size) -> StopTechnique(b_sl, distance, trop_large) ; multiple_objectif() -> k
Entrée : sens, clôture, extrême du repli signal compris, A_t, tick_size Decimal
Sortie : B_SL sur l'échelle Bid, distance sens·(C−B_SL), drapeau trop large ; k = 1,5
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c1d_cat1_*.py`) : S01.5 : B_SL 1,09945 et 1,10055 ; extrême de la bougie de signal inclus ; plancher 0,80A ; STOP_TOO_WIDE au-delà de 2,5A.
- Catégorie 2 (`tests/robot/moteur_ema/test_c1d_cat2_*.py`) : via 3.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

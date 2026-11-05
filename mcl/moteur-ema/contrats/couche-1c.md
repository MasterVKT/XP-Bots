# Contrat de la couche 1c — bougie-reprise (artefact `moteur-ema`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 3), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/moteur_ema/c1c_reprise.py`
- **Sources normatives** : S01.1 à S01.6, C03.8–C03.11, C06 (conversion), A07 ; plan maître, section 7.B

---

Unité : bougie_reprise
Responsabilité : Tester la bougie de reprise de S01.3.
Signature : est_reprise(sens, o, h, l, c, tr, e15, rsi, a) -> bool
Entrée : OHLC Bid, TR, E15, RSI, A_t > 0
Sortie : vrai seulement si toutes les conditions S01.3 du sens sont vraies
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c1c_cat1_*.py`) : RSI 49,999 refusé, 50 admis ; O=C refusé ; TR > 2,5A refusé ; 0,65 exactement admis ; R = 0 refusé.
- Catégorie 2 (`tests/robot/moteur_ema/test_c1c_cat2_*.py`) : via 2.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

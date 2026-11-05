# Contrat de la couche 1d — stop-objectif (artefact `moteur-ema`)

- **Statut** : finalisé (phase 3, 2026-11-05) ; gel tracé dans `mcl/moteur-ema/journal.jsonl`.
- **Consommateurs cartographiés** : couche 3
- **Dépend de** : couche 0 (`ParametresEMA`) ; amont figé : `amont-noyau` (`Sens`) ; frontières externes : aucune
- **Module** : `src/xpbots/moteur_ema/c1d_stop.py`
- **Sources normatives** : S01.4, S01.5, C06 (B_SL non arrondi sur l'échelle Bid).

---

Unité : stop_objectif_ema
Responsabilité : Calculer le tampon, le stop technique B_SL non arrondi, la distance technique et le refus au-delà
du plafond ; le multiple d'objectif k est lu dans `ParametresEMA.multiple_objectif`.
Signature : `stop_technique(sens, cloture, extreme_repli, a_t, tick_size, p) -> StopTechnique` ;
`StopTechnique(b_sl, tampon, distance, trop_large)` (immuable).
Entrée : `Sens`, clôture Bid de signal, extrême du repli signal compris (plus bas en achat, plus haut en vente),
`A_t` > 0, `tick_size` décimal > 0 du profil, `ParametresEMA`.
Sortie : tampon = max(tick, `tampon_structurel_atr`·A) ; achat B_SL = min(extrême − tampon, C − `stop_min_atr`·A) ;
vente B_SL = max(extrême + tampon, C + `stop_min_atr`·A) ; distance = sens·(C − B_SL) > 0 ; `trop_large` si
distance > `stop_max_atr`·A. Calcul en flottants 64 bits dans l'ordre de la référence ; arrondi au tick et SL
exécutable hors de cette couche (C06).
Effets de bord : aucun.
Erreurs, exceptions : `ValueError` (sens non `Sens`, valeur non finie, A_t ≤ 0, tick non décimal ou ≤ 0).

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c1d_cat1_*.py`) : exemple S01.5 (B_SL 1,09945 et 1,10055, tampon 0,00005), plancher 0,80 A, extrême utilisé tel quel, tick supérieur au tampon ATR, trop large au-delà de 2,5 A, entrées invalides.
- Catégorie 2 : via la couche 3 (bloc réel, équivalence avec la référence).

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Le texte des messages d'erreur n'est pas garanti.
Toute valeur normative est lue dans `config/` par la couche 0, jamais recopiée.

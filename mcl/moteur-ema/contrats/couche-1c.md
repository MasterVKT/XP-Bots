# Contrat de la couche 1c — bougie-reprise (artefact `moteur-ema`)

- **Statut** : finalisé (phase 3, 2026-11-05) ; gel tracé dans `mcl/moteur-ema/journal.jsonl`.
- **Consommateurs cartographiés** : couche 2
- **Dépend de** : couche 0 (`ParametresEMA`) ; amont figé : `amont-noyau` (`Sens`) ; frontières externes : aucune
- **Module** : `src/xpbots/moteur_ema/c1c_reprise.py`
- **Sources normatives** : S01.3, S01.6.

---

Unité : bougie_reprise
Responsabilité : Tester la bougie de reprise de S01.3 (l'état de repli valide est vérifié par la couche 2).
Signature : `est_reprise(sens, o, h, l, c, tr, e_rapide, rsi, a_t, p) -> bool`.
Entrée : `Sens`, OHLC Bid en flottants, TR de la bougie, EMA rapide, RSI, `A_t` > 0, `ParametresEMA`.
Sortie : faux si R = H − L ≤ 0 ou TR > `tr_max_atr`·A ; achat : C > EMA rapide, C > O, RSI ≥ `rsi_signal_long_min`,
(C − L)/R ≥ `position_cloture_min` ; vente : C < EMA rapide, C < O, RSI ≤ `rsi_signal_court_max`,
(H − C)/R ≥ `position_cloture_min`. O = C ne donne jamais de signal.
Effets de bord : aucun.
Erreurs, exceptions : `ValueError` (sens non `Sens`, valeur non finie, A_t ≤ 0).

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c1c_cat1_*.py`) : RSI 49,999 refusé et 50 admis, O = C refusé, position de clôture exactement au seuil admise (achat et vente), TR au plafond admis et au-delà refusé, range nul refusé, entrées invalides.
- Catégorie 2 : via la couche 2 (bloc réel {0 → 2}).

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Le texte des messages d'erreur n'est pas garanti.
Toute valeur normative est lue dans `config/` par la couche 0, jamais recopiée.

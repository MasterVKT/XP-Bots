# Contrat de la couche 1b — conditions-repli (artefact `moteur-ema`)

- **Statut** : finalisé (phase 3, 2026-11-05) ; gel tracé dans `mcl/moteur-ema/journal.jsonl`.
- **Consommateurs cartographiés** : couche 2
- **Dépend de** : couche 0 (`ParametresEMA`) ; amont figé : `amont-noyau` (`Sens`) ; frontières externes : aucune
- **Module** : `src/xpbots/moteur_ema/c1b_repli.py`
- **Sources normatives** : S01.2 points 4 à 6, S01.6 ; R18.

---

Unité : conditions_repli
Responsabilité : Tester le contexte d'armement, la validité du repli et le contact avec la zone EMA rapide–lente.
Signature : `contexte_armement(sens, cloture, e_rapide, rsi, p) -> bool` ;
`repli_valide(sens, cloture, e_lente, rsi, a_t, p) -> bool` ; `contact(haut, bas, e_rapide, e_lente) -> bool`.
Entrée : `Sens`, nombres finis (clôture Bid, EMA, RSI), `A_t` > 0, `ParametresEMA`.
Sortie :
- armement : achat si C > EMA rapide et RSI ≥ `rsi_signal_long_min` ; vente si C < EMA rapide et
  RSI ≤ `rsi_signal_court_max` (R18 : seuils du signal, aucune clé dédiée) ;
- repli : achat si C ≥ EMA lente − `depassement_ema_lente_atr`·A et RSI ≥ `rsi_repli_long_min` ; vente si
  C ≤ EMA lente + `depassement_ema_lente_atr`·A et RSI ≤ `rsi_repli_court_max` ; seule la clôture est jugée (une
  mèche au-delà n'annule pas) ;
- contact : L ≤ max(EMA rapide, EMA lente) et H ≥ min(EMA rapide, EMA lente), bornes incluses.
Effets de bord : aucun.
Erreurs, exceptions : `ValueError` (sens non `Sens`, valeur non finie, A_t ≤ 0, bas > haut).

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c1b_cat1_*.py`) : seuil d'armement R18, clôture strictement au-delà de l'EMA rapide, RSI de repli au seuil admis (40), clôture exactement à EMA lente ∓ 0,25 A admise, mèche seule sans effet, bornes du contact, zone dans les deux ordres.
- Catégorie 2 : via la couche 2 (bloc réel {0 → 2}).

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Le texte des messages d'erreur n'est pas garanti.
Toute valeur normative est lue dans `config/` par la couche 0, jamais recopiée.

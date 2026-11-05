# Contrat de la couche 1a — tendance (artefact `moteur-ema`)

- **Statut** : finalisé (phase 3, 2026-11-05) ; gel tracé dans `mcl/moteur-ema/journal.jsonl`.
- **Consommateurs cartographiés** : couche 2
- **Dépend de** : couche 0 (dépendance cartographiée, sans import : comparaison pure) ; amont figé : `amont-noyau` (`Sens`) ; frontières externes : aucune
- **Module** : `src/xpbots/moteur_ema/c1a_tendance.py`
- **Sources normatives** : S01.1 (tendances longue et courte), S01.6 (égalités, pente nulle), C11.2.

---

Unité : tendance_ema
Responsabilité : Évaluer l'ordre EMA rapide/moyenne/lente et la pente de l'EMA lente sur le décalage configuré.
Signature : `sens_tendance(e_rapide, e_moyenne, e_lente, e_lente_decalee) -> Sens | None`.
Entrée : quatre nombres finis (EMA15_t, EMA25_t, EMA50_t, EMA50_(t−k) avec k = `slow_ema_slope_lookback_bars`,
fourni par l'appelant).
Sortie : `Sens.ACHAT` si e_rapide > e_moyenne > e_lente et e_lente > e_lente_decalee ; `Sens.VENTE` si
e_rapide < e_moyenne < e_lente et e_lente < e_lente_decalee ; sinon `None` (toute égalité, pente nulle ou ordre non
aligné).
Effets de bord : aucun.
Erreurs, exceptions : `ValueError` si une valeur n'est pas un nombre fini (booléen, None, NaN, infini).

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c1a_cat1_*.py`) : tendances strictes, EMA égales et pente nulle sans tendance, ordre non aligné, valeurs indisponibles refusées.
- Catégorie 2 : via les couches 2 et 3 (bloc réel).

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Le texte des messages d'erreur n'est pas garanti.
Toute valeur normative est lue dans `config/` par la couche 0, jamais recopiée.

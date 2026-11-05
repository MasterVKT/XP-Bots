# Contrat de la couche 0 — parametres-ema (artefact `moteur-ema`)

- **Statut** : finalisé (phase 3, 2026-11-05) ; gel tracé dans `mcl/moteur-ema/journal.jsonl`.
- **Consommateurs cartographiés** : couches 1b, 1c, 1d, 2, 3 (1a n'en a pas besoin : comparaison pure).
- **Dépend de** : aucune couche interne ; amont figé : `amont-noyau` (`BundleTechnique`, `ConfigurationInvalide`,
  `figer`), `amont-donnees-temps` couche 0 (`GENRES`, `FonctionNonImplementee`, `analyser_heure`) ; frontières
  externes : aucune.
- **Module** : `src/xpbots/moteur_ema/c0_parametres.py`
- **Sources normatives** : C02 (bloc `ema`, bloc `common`), S01.1 à S01.4, C03 points 8 et 9 ; R18.

---

Unité : parametres_ema
Responsabilité : Charger et valider le bloc `ema` de la configuration figée et les quatre seuils `common` de S01.
Signature : `charger_parametres_ema(bundle) -> ParametresEMA` ; `ParametresEMA(bloc, common, empreinte)` ;
`valider_bloc_ema(bloc) -> list[str]` ; constantes `SCHEMA_EMA` (23 clés → genre), `VARIANTES_IMPLEMENTEES`,
`CLES_COMMON`.
Entrée : bundle technique strict (`config/parametres_figes_v3.json`).
Sortie : objet en lecture seule exposant, sans aucune valeur recopiée : `strategie_id`, `periodes_ema` (rapide,
moyenne, lente), `periode_rsi`, `decalage_pente`, `rsi_repli_long_min`, `rsi_repli_court_max`,
`rsi_signal_long_min`, `rsi_signal_court_max` (aussi seuils d'armement, R18), `depassement_ema_lente_atr`,
`age_max_repli`, `position_cloture_min`, `clotures_cooldown`, `entrees_max_jour`, `debut_session`,
`fin_entrees_exclue`, `sortie_forcee` (textes `HH:MM:SS`), `heures` (trois `time`), `multiple_objectif` (flottant),
`tampon_structurel_atr`, `stop_min_atr`, `stop_max_atr`, `tr_max_atr` (bloc `common`), `empreinte`, `valeur(cle)`.
Effets de bord : aucun.
Erreurs, exceptions : `ConfigurationInvalide` (clé manquante ou en trop, type faux — un entier n'est pas un
booléen, un flottant n'est pas un entier —, trois périodes EMA strictement croissantes non respectées, fraction de
clôture hors ]0, 1], fenêtre vide, seuil `common` absent ou non positif, clé absente à la lecture) ;
`FonctionNonImplementee` si une variante diffère de `SMA_N`, `WILDER`, `EMA15_TO_EMA50`, corps directionnel
exigé, contact du signal non exigé, filtre H1 désactivé (le robot refuse de démarrer).

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c0_cat1_*.py`) : 23 clés exactes, valeurs lues dans `config/`,
  clés manquantes/en trop/mal typées, lecture seule, variantes non implémentées refusées, périodes, fenêtre,
  fraction, seuils `common` obligatoires.
- Catégorie 2 : aucune (feuille interne ; intégration couverte par les couches 2 et 3).

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Le texte des messages d'erreur n'est pas garanti.

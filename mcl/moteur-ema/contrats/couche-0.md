# Contrat de la couche 0 — parametres-ema (artefact `moteur-ema`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 3), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 1a, 1b, 1c, 1d
- **Dépend de** : couches aucune (réelles et figées) ; amont figé : amont-noyau ; frontières externes doublées : aucune
- **Module** : `src/xpbots/moteur_ema/c0_parametres.py`
- **Sources normatives** : S01.1 à S01.6, C03.8–C03.11, C06 (conversion), A07 ; plan maître, section 7.B

---

Unité : parametres_ema
Responsabilité : Charger et valider le bloc ema de la configuration figée.
Signature : charger_parametres_ema(bundle) -> ParametresEMA
Entrée : bundle JSON strict
Sortie : objet immuable du bloc ema
Effets de bord : aucun
Erreurs, exceptions : ConfigurationInvalide ; FonctionNonImplementee si un drapeau prend une valeur non prise en charge (h1_directional_filter_enabled, require_signal_touch, require_directional_body)

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c0_cat1_*.py`) : clés du bloc ema, drapeaux non implémentés refusés.
- Catégorie 2 (`tests/robot/moteur_ema/test_c0_cat2_*.py`) : —.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

# Contrat de la couche 1a — tendance (artefact `moteur-ema`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 3), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/moteur_ema/c1a_tendance.py`
- **Sources normatives** : S01.1 à S01.6, C03.8–C03.11, C06 (conversion), A07 ; plan maître, section 7.B

---

Unité : tendance_ema
Responsabilité : Évaluer l'ordre EMA15/25/50 et la pente de l'EMA50 sur quatre bougies.
Signature : sens_tendance(e15, e25, e50, e50_t_moins_4) -> -1 | 0 | 1
Entrée : quatre flottants disponibles
Sortie : 1 long, −1 court, 0 aucune tendance (égalités comprises)
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c1a_cat1_*.py`) : EMA égales ou pente EMA50 nulle : aucun armement (C11.2, S01.6) ; inégalités strictes.
- Catégorie 2 (`tests/robot/moteur_ema/test_c1a_cat2_*.py`) : via 2.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

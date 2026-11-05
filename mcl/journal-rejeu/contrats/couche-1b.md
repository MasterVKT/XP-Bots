# Contrat de la couche 1b — simulateur (artefact `journal-rejeu`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 8), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2b
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : amont-execution ; frontières externes doublées : aucune
- **Module** : `src/xpbots/journal_rejeu/c1b_simulateur.py`
- **Sources normatives** : C09, C10, C11.12, C11.14, A13, A14 ; plan maître, section 7.H

---

Unité : simulateur_execution
Responsabilité : Simuler les exécutions de référence et de stress à partir des ticks (port Courtier).
Signature : SimulateurCourtier(scenario, profils).envoyer(ordre) ; sur_tick(tick) -> list[Execution]
Entrée : ordres protégés, ticks, scénario
Sortie : accusés, fills, sorties SL/TP et marché causales
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/journal_rejeu/test_c1b_cat1_*.py`) : délai 250 ms et un tick adverse (R9), stress 1,25 × spread, 1 000 ms, deux ticks ; TP au niveau ; gaps ; SL et TP à la même milliseconde (C11.12).
- Catégorie 2 (`tests/robot/journal_rejeu/test_c1b_cat2_*.py`) : via 2b.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

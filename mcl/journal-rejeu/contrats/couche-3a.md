# Contrat de la couche 3a — bootstrap (artefact `journal-rejeu`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 8), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 4
- **Dépend de** : couches 2a (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/journal_rejeu/c3a_bootstrap.py`
- **Sources normatives** : C09, C10, C11.12, C11.14, A13, A14 ; plan maître, section 7.H

---

Unité : bootstrap
Responsabilité : Estimer l'incertitude par bootstrap de blocs de cinq jours de marché.
Signature : bootstrap(panel_journalier, parametres) -> Intervalles
Entrée : P&L nets et trades par jour de sortie
Sortie : percentiles 2,5/97,5 et réplications invalides
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/journal_rejeu/test_c3a_cat1_*.py`) : blocs de 5 jours, 10 000 réplications, graine 20261104, percentiles 2,5/97,5.
- Catégorie 2 (`tests/robot/journal_rejeu/test_c3a_cat2_*.py`) : via 4.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

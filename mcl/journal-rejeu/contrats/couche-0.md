# Contrat de la couche 0 — types-rejeu (artefact `journal-rejeu`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 8), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 1a, 1b, 1c
- **Dépend de** : couches aucune (réelles et figées) ; amont figé : amont-noyau ; frontières externes doublées : aucune
- **Module** : `src/xpbots/journal_rejeu/c0_types.py`
- **Sources normatives** : C09, C10, C11.12, C11.14, A13, A14 ; plan maître, section 7.H

---

Unité : types_rejeu
Responsabilité : Représenter scénarios, blocs de dates C10 et manifestes de données.
Signature : Scenario ; BlocC10 ; Manifeste
Entrée : paramètres de C10 et de l'export IA
Sortie : objets immuables
Effets de bord : aucun
Erreurs, exceptions : ScenarioInterdit si une perturbation est demandée hors rejeu

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/journal_rejeu/test_c0_cat1_*.py`) : scénarios référence, stress, perturbations nommées (R16), blocs C10, manifeste.
- Catégorie 2 (`tests/robot/journal_rejeu/test_c0_cat2_*.py`) : —.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

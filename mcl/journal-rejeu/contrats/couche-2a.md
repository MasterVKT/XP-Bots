# Contrat de la couche 2a — metriques (artefact `journal-rejeu`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 8), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3a, 3b
- **Dépend de** : couches 1a (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/journal_rejeu/c2a_metriques.py`
- **Sources normatives** : C09, C10, C11.12, C11.14, A13, A14 ; plan maître, section 7.H

---

Unité : metriques
Responsabilité : Calculer les métriques de C09, C10 et A13 depuis le journal.
Signature : metriques(journal, jours_de_marche) -> Metriques
Entrée : journal d'un rejeu
Sortie : effectifs, espérance, PF, drawdown, fréquence, rétention
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/journal_rejeu/test_c2a_cat1_*.py`) : espérance, PF, drawdown de fonds propres, fréquence avec jours à zéro, rétention N/A et < 50.
- Catégorie 2 (`tests/robot/journal_rejeu/test_c2a_cat2_*.py`) : via 3.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

# Contrat de la couche 3b — planificateur (artefact `service-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 4
- **Dépend de** : couches 1a, 2b (réelles et figées) ; amont figé : aucun ; frontières externes doublées : collecte-rss
- **Module** : `src/xpbots/service_ia/c3b_planificateur.py`
- **Sources normatives** : A02, A04 à A11, A14 ; plan maître, section 7.G

---

Unité : planificateur
Responsabilité : Planifier collectes, classifications, briefings, journaux et revues.
Signature : Planificateur.tick(i) -> list[Job]
Entrée : horloge Londres, file, budget
Sortie : travaux ordonnés par priorité A09
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/service_ia/test_c3b_cat1_*.py`) : 07:45, 16:15, vendredi 16:45 Londres ; priorités A09.
- Catégorie 2 (`tests/robot/service_ia/test_c3b_cat2_*.py`) : via 4.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

# Contrat de la couche 3 — permissions (artefact `controles-fondamentaux`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 6), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : aucune couche interne ; hors artefact : execution-coordinateur (port ControleFondamental)
- **Dépend de** : couches 1b, 2 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/fondamental/c3_permissions.py`
- **Sources normatives** : C05, C08 point 2, C11.8, C11.9 ; plan maître, section 7.E

---

Unité : permissions
Responsabilité : Combiner direction, état de risque et annonces en autorisation ou motif de refus.
Signature : ControleFondamental.autoriser(symbole, sens, i) -> Autorisation | Refus ; demandes_sortie(i)
Entrée : symbole, sens, instant
Sortie : autorisation ou FUNDAMENTAL_INVALID, FUNDAMENTAL_DIRECTION, NEWS_WINDOW ; demandes FLATTEN et annonce
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/fondamental/test_c3_cat1_*.py`) : direction incompatible, NO_NEW, FLATTEN, TECHNICAL_CONTROL_NEUTRAL seulement nommé.
- Catégorie 2 (`tests/robot/fondamental/test_c3_cat2_*.py`) : avec execution-coordinateur : FLATTEN prioritaire, contrôle au signal puis avant l'ordre.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

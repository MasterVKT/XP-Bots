# Contrat de la couche 4 — rapport (artefact `journal-rejeu`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 8), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : aucune couche interne ; hors artefact : app
- **Dépend de** : couches 3a, 3b (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/journal_rejeu/c4_rapport.py`
- **Sources normatives** : C09, C10, C11.12, C11.14, A13, A14 ; plan maître, section 7.H

---

Unité : rapport_validation
Responsabilité : Assembler les rapports de validation C10 et A13.
Signature : rapport(resultats) -> Rapport
Entrée : résultats de rejeu
Sortie : rapport sous .local/reports/ sans secret ni numéro de compte
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/journal_rejeu/test_c4_cat1_*.py`) : précision JSON jamais présentée comme taux de réussite.
- Catégorie 2 (`tests/robot/journal_rejeu/test_c4_cat2_*.py`) : rapport complet d'un rejeu synthétique.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

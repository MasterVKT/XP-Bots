# Contrat de la couche 3b — paper-ab (artefact `journal-rejeu`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 8), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 4
- **Dépend de** : couches 2a, 2b (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/journal_rejeu/c3b_paper_ab.py`
- **Sources normatives** : C09, C10, C11.12, C11.14, A13, A14 ; plan maître, section 7.H

---

Unité : paper_ab
Responsabilité : Rejouer deux portefeuilles indépendants référence et veto IA.
Signature : rejouer_ab(fabrique, ticks, archives_ia) -> ResultatAB
Entrée : mêmes ticks, coûts et permissions
Sortie : deux journaux et métriques comparées
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/journal_rejeu/test_c3b_cat1_*.py`) : deux portefeuilles indépendants à 100 USD, coût IA déduit une fois.
- Catégorie 2 (`tests/robot/journal_rejeu/test_c3b_cat2_*.py`) : A14 comptes A/B séparés.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

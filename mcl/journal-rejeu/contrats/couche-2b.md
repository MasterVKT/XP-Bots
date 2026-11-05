# Contrat de la couche 2b — rejeu (artefact `journal-rejeu`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 8), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3b
- **Dépend de** : couches 1a, 1b, 1c (réelles et figées) ; amont figé : amont-donnees-temps ; frontières externes doublées : aucune
- **Module** : `src/xpbots/journal_rejeu/c2b_rejeu.py`
- **Sources normatives** : C09, C10, C11.12, C11.14, A13, A14 ; plan maître, section 7.H

---

Unité : rejeu
Responsabilité : Rejouer causalement des ticks à travers le coordinateur et le simulateur.
Signature : rejouer(fabrique_coordinateur, ticks, scenario, bloc) -> ResultatRejeu
Entrée : fabrique fournie par l'application, ticks, scénario, bloc
Sortie : journal et état final
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/journal_rejeu/test_c2b_cat1_*.py`) : blocs C10 à 100 USD, arrêts non réinitialisés, rejeu continu.
- Catégorie 2 (`tests/robot/journal_rejeu/test_c2b_cat2_*.py`) : C11.14 : journal de décision identique entre rejeu et boucle paper alimentée par les mêmes ticks.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

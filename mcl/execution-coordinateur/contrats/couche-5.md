# Contrat de la couche 5 — sorties-obligatoires (artefact `execution-coordinateur`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 4 et 5), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 6
- **Dépend de** : couches 4 (réelles et figées) ; amont figé : amont-donnees-temps ; frontières externes doublées : aucune
- **Module** : `src/xpbots/execution/c5_sorties.py`
- **Sources normatives** : C04, C06, C07, C08, C09, C11.2, C11.5–C11.7, C11.10–C11.13 ; plan maître, section 7.D

---

Unité : sorties_obligatoires
Responsabilité : Déterminer la première échéance de sortie et produire les clôtures prioritaires.
Signature : echeance(position, maintenant, contexte) -> MotifSortie | None ; demandes(...) -> list[DemandeSortie]
Entrée : positions possédées, instant, demandes FLATTEN/annonce/gardes, séances
Sortie : demandes de sortie ordonnées ; blocage des entrées du symbole tant qu'une clôture est en attente
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/execution/test_c5_cat1_*.py`) : 7 200 s, 16:00 Londres, annonce, FLATTEN, gardes, 60 s avant fermeture, blackout ; égalités d'échéances.
- Catégorie 2 (`tests/robot/execution/test_c5_cat2_*.py`) : flux absent à l'heure de sortie, réessai chaque seconde.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

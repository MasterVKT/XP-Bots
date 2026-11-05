# Contrat de la couche 4 — cycle-ordre (artefact `execution-coordinateur`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 4 et 5), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 5
- **Dépend de** : couches 1b, 3 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : courtier-execution, horloge-os
- **Module** : `src/xpbots/execution/c4_cycle_ordre.py`
- **Sources normatives** : C04, C06, C07, C08, C09, C11.2, C11.5–C11.7, C11.10–C11.13 ; plan maître, section 7.D

---

Unité : cycle_ordre
Responsabilité : Envoyer l'ordre protégé et gérer accusé ambigu, rapprochement, fill partiel et rétablissement des protections.
Signature : CycleOrdre.envoyer(intention) -> Action ; sur_evenement(reponse | delai | tick) -> list[Action]
Entrée : intention réservée, réponses du port Courtier, instants
Sortie : actions (envoyer, rapprocher, corriger TP, clôturer d'urgence), issue et alertes
Effets de bord : journal des requêtes et réponses
Erreurs, exceptions : aucune retransmission aveugle ; UNKNOWN_ORDER_STATE

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/execution/test_c4_cat1_*.py`) : accusé 5 s, rapprochement 1 s/30 s puis 5 s, fill partiel, corrections TP 0,25/1/3 s et 15 s, SL absent, TP dépassé (C11.11, C11.12).
- Catégorie 2 (`tests/robot/execution/test_c4_cat2_*.py`) : courtier scripté sur le bloc 0→4.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

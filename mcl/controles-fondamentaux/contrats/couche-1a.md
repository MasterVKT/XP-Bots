# Contrat de la couche 1a — message-permission (artefact `controles-fondamentaux`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 6), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/fondamental/c1a_message.py`
- **Sources normatives** : C05, C08 point 2, C11.8, C11.9 ; plan maître, section 7.E

---

Unité : message_permission
Responsabilité : Valider un message fundamental-permission-v1 et ses heures.
Signature : valider_message(json, recu_a) -> MessagePermission | Refus
Entrée : texte JSON reçu et instant de réception locale
Sortie : message valide ou motif d'invalidité
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/fondamental/test_c1a_cat1_*.py`) : ordre des heures, durée ≤ 900 s, futur refusé, réception ≥ known_at (C11.8).
- Catégorie 2 (`tests/robot/fondamental/test_c1a_cat2_*.py`) : via 2.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

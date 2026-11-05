# Contrat de la couche 1c — validateurs (artefact `service-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2a, 2b
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/service_ia/c1c_validateurs.py`
- **Sources normatives** : A02, A04 à A11, A14 ; plan maître, section 7.G

---

Unité : validateurs_sorties
Responsabilité : Valider strictement les sorties d'extraction et informatives.
Signature : valider_extraction(texte, item) ; valider_note(texte, kind, preuves)
Entrée : réponse brute, texte transmis
Sortie : objet validé ou refus (aucun veto)
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/service_ia/test_c1c_cat1_*.py`) : clés en trop, doublons, enums, citation inventée, item_id étranger, tronqué (A14).
- Catégorie 2 (`tests/robot/service_ia/test_c1c_cat2_*.py`) : via 2a.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

# Contrat de la couche 1a — normalisation (artefact `service-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2a, 3b
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/service_ia/c1a_normalisation.py`
- **Sources normatives** : A02, A04 à A11, A14 ; plan maître, section 7.G

---

Unité : normalisation_textes
Responsabilité : Normaliser et dédoublonner les textes officiels collectés.
Signature : normaliser(brut, issuer, vu_a) -> TexteSource
Entrée : texte brut et métadonnées de collecte
Sortie : TexteSource daté ou marqué non daté
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/service_ia/test_c1a_cat1_*.py`) : item_id, URL canonique, SHA-256, dates absentes ou futures, dédoublonnage.
- Catégorie 2 (`tests/robot/service_ia/test_c1a_cat2_*.py`) : via 2a.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

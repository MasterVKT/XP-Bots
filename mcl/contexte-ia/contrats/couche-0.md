# Contrat de la couche 0 — format-snapshot (artefact `contexte-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 7), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 1
- **Dépend de** : couches aucune (réelles et figées) ; amont figé : amont-noyau ; frontières externes doublées : aucune
- **Module** : `src/xpbots/contexte_ia/c0_format.py`
- **Sources normatives** : A03, A07, A10, A12, A14 ; plan maître, section 7.F

---

Unité : format_snapshot
Responsabilité : Définir le format canonique xp-ai-context-v1 et les paramètres de lecture du snapshot.
Signature : canonique(payload) -> bytes ; empreinte(payload) -> str ; ParametresSnapshot
Entrée : payload JSON
Sortie : octets canoniques et SHA-256 identiques à reference.llm_contracts.digest
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/contexte_ia/test_c0_cat1_*.py`) : JSON canonique, paramètres IA, empreinte d'intégration.
- Catégorie 2 (`tests/robot/contexte_ia/test_c0_cat2_*.py`) : —.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

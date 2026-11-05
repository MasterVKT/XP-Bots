# Contrat de la couche 0e — sqlite-ia (artefact `infrastructure`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 9 et 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : aucune couche interne
- **Dépend de** : couches aucune (réelles et figées) ; amont figé : amont-service-ia ; frontières externes doublées : sqlite
- **Module** : `src/xpbots/infrastructure/sqlite_ia`
- **Sources normatives** : C04, C08 (rapprochement, redémarrage), A04, A08, A10 ; plan maître, section 7.I

---

Unité : stockage_service_ia
Responsabilité : Stocker textes, travaux, résultats, budget et snapshots du service IA.
Signature : StockageServiceIA.transaction_exclusive() ; tables A10
Entrée : chemin sous runtime/
Sortie : persistance A10 avec FTS5
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/infrastructure/test_c0e_cat1_*.py`) : tables A10, FTS5, transaction du budget.
- Catégorie 2 (`tests/robot/infrastructure/test_c0e_cat2_*.py`) : concurrence.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

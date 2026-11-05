# Contrat de la couche 0b — sqlite-robot (artefact `infrastructure`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 9 et 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : aucune couche interne
- **Dépend de** : couches aucune (réelles et figées) ; amont figé : amont-noyau ; frontières externes doublées : sqlite
- **Module** : `src/xpbots/infrastructure/sqlite_robot`
- **Sources normatives** : C04, C08 (rapprochement, redémarrage), A04, A08, A10 ; plan maître, section 7.I

---

Unité : stockage_sqlite
Responsabilité : Stocker l'état du robot de façon transactionnelle.
Signature : StockageSQLite (port Stockage).transaction() ; lire(cle) ; ecrire(cle, valeur)
Entrée : chemin sous runtime/
Sortie : état durable
Effets de bord : base SQLite
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/infrastructure/test_c0b_cat1_*.py`) : BEGIN IMMEDIATE, atomicité, reprise.
- Catégorie 2 (`tests/robot/infrastructure/test_c0b_cat2_*.py`) : contrats de port.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

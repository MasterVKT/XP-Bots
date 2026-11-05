# Contrat de la couche 2 — cache-vetos (artefact `contexte-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 7), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3
- **Dépend de** : couches 1 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : stockage-etat
- **Module** : `src/xpbots/contexte_ia/c2_cache_vetos.py`
- **Sources normatives** : A03, A07, A10, A12, A14 ; plan maître, section 7.F

---

Unité : cache_vetos
Responsabilité : Conserver les vetos validés jusqu'à leur échéance propre, redémarrage compris.
Signature : CacheVetos.integrer(snapshot) ; actifs(symbole, i) -> list[Veto] ; sauvegarder() ; restaurer()
Entrée : snapshots acceptés
Sortie : vetos actifs
Effets de bord : persistance via le port Stockage
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/contexte_ia/test_c2_cat1_*.py`) : échéance propre, snapshot périmé sans révocation, reprise après redémarrage sans réinférence.
- Catégorie 2 (`tests/robot/contexte_ia/test_c2_cat2_*.py`) : via 3.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

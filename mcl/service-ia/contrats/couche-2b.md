# Contrat de la couche 2b — routeur (artefact `service-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3b
- **Dépend de** : couches 1b, 1c, 1d (réelles et figées) ; amont figé : aucun ; frontières externes doublées : transport-llm
- **Module** : `src/xpbots/service_ia/c2b_routeur.py`
- **Sources normatives** : A02, A04 à A11, A14 ; plan maître, section 7.G

---

Unité : routeur_fournisseurs
Responsabilité : Choisir et appeler les fournisseurs dans l'ordre et les délais A08.
Signature : Routeur.executer(job) -> ResultatJob
Entrée : job de classification ou informatif
Sortie : résultat validé ou NEUTRAL
Effets de bord : appels HTTPS comptés
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/service_ia/test_c2b_cat1_*.py`) : ordre des fournisseurs, délais, pauses, échéance 75 s, 401/429/5xx.
- Catégorie 2 (`tests/robot/service_ia/test_c2b_cat2_*.py`) : transport factice.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

# Contrat de la couche 4 — service (artefact `service-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : aucune couche interne ; hors artefact : app
- **Dépend de** : couches 3a, 3b (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/service_ia/c4_service.py`
- **Sources normatives** : A02, A04 à A11, A14 ; plan maître, section 7.G

---

Unité : service
Responsabilité : Exécuter le service : collecteur, worker unique, heartbeat.
Signature : ServiceIA.executer()
Entrée : environnement configuré
Sortie : snapshot et journaux informatifs
Effets de bord : processus de longue durée
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/service_ia/test_c4_cat1_*.py`) : worker unique, file bornée, heartbeat indépendant.
- Catégorie 2 (`tests/robot/service_ia/test_c4_cat2_*.py`) : A14 côté service de bout en bout sans API réelle.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

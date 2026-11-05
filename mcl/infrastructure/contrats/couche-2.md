# Contrat de la couche 2 — qualification-c04 (artefact `infrastructure`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 9 et 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : aucune couche interne ; hors artefact : app
- **Dépend de** : couches 1a (réelles et figées) ; amont figé : amont-execution ; frontières externes doublées : aucune
- **Module** : `src/xpbots/infrastructure/mt5/qualification_c04.py`
- **Sources normatives** : C04, C08 (rapprochement, redémarrage), A04, A08, A10 ; plan maître, section 7.I

---

Unité : qualification_c04
Responsabilité : Établir la fiche d'environnement C04 et la faisabilité du volume minimal.
Signature : qualifier(symboles) -> FicheEnvironnement | ENVIRONMENT_NOT_READY
Entrée : terminal démo connecté
Sortie : fiche horodatée sous .local/reports/ sans numéro de compte
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/infrastructure/test_c2_cat1_*.py`) : fiche complète ou ENVIRONMENT_NOT_READY ; faisabilité à 0,5 % ; liaison d'un symbole ; heure des ticks (R14).
- Catégorie 2 (`tests/robot/infrastructure/test_c2_cat2_*.py`) : qualification réelle sur compte démo.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

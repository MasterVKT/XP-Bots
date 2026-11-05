# Contrat de la couche 0 — types-execution (artefact `execution-coordinateur`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 4 et 5), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 1a, 1b, 1c, 1d
- **Dépend de** : couches aucune (réelles et figées) ; amont figé : amont-donnees-temps, amont-noyau ; frontières externes doublées : aucune
- **Module** : `src/xpbots/execution/c0_types.py`
- **Sources normatives** : C04, C06, C07, C08, C09, C11.2, C11.5–C11.7, C11.10–C11.13 ; plan maître, section 7.D

---

Unité : types_execution
Responsabilité : Représenter profil d'instrument C04, positions possédées, réservations, état du compte et paramètres d'exécution.
Signature : ProfilInstrument ; PositionPossedee ; Reservation ; EtatCompte ; charger_parametres_execution(bundle)
Entrée : caractéristiques lues de l'environnement ; bloc common
Sortie : objets immuables ; champs absents marqués inconnus, jamais zéro
Effets de bord : aucun
Erreurs, exceptions : ProfilIncomplet (traduit en ENVIRONMENT_NOT_READY)

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/execution/test_c0_cat1_*.py`) : profil complet ou ENVIRONMENT_NOT_READY ; clé d'intention ; paramètres du bloc common.
- Catégorie 2 (`tests/robot/execution/test_c0_cat2_*.py`) : —.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

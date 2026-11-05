# Contrat de la couche 1c — gardes-compte (artefact `execution-coordinateur`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 4 et 5), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : stockage-etat
- **Module** : `src/xpbots/execution/c1c_gardes_compte.py`
- **Sources normatives** : C04, C06, C07, C08, C09, C11.2, C11.5–C11.7, C11.10–C11.13 ; plan maître, section 7.D

---

Unité : gardes_compte
Responsabilité : Suivre base quotidienne UTC et pic de fonds propres et imposer les arrêts quotidien et global persistants.
Signature : GardesCompte.sur_fonds_propres(instant, equity) -> OK | DAILY_LOSS_LOCK | GLOBAL_DRAWDOWN_HALT
Entrée : fonds propres courants (flottant et frais inclus), instant
Sortie : état de garde et demandes de clôture
Effets de bord : base, pic et arrêt persistés
Erreurs, exceptions : ArretGlobalActif tant qu'aucune décision de déploiement tracée ne le lève

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/execution/test_c1c_cat1_*.py`) : base 00:00 UTC, 98 % et 90 % exacts, flottant et frais inclus, persistance sans remise à zéro (C11.13).
- Catégorie 2 (`tests/robot/execution/test_c1c_cat2_*.py`) : via 3 et 6.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

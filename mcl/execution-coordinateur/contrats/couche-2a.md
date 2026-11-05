# Contrat de la couche 2a — risque-all-in (artefact `execution-coordinateur`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 4 et 5), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3
- **Dépend de** : couches 1b (réelles et figées) ; amont figé : aucun ; frontières externes doublées : calcul-courtier
- **Module** : `src/xpbots/execution/c2a_risque.py`
- **Sources normatives** : C04, C06, C07, C08, C09, C11.2, C11.5–C11.7, C11.10–C11.13 ; plan maître, section 7.D

---

Unité : risque_all_in
Responsabilité : Calculer la perte pessimiste au stop et les frais aller-retour pour un volume.
Signature : risque_all_in(volume, niveaux, a, profil, calcul) -> Decimal ; reserve_glissement(a, tick) -> Decimal
Entrée : volume de la grille, niveaux, A_t, profil, port CalculCourtier
Sortie : risque en USD Decimal, spread jamais recompté
Effets de bord : aucun
Erreurs, exceptions : CalculIndisponible (traduit en ENVIRONMENT_NOT_READY)

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/execution/test_c2a_cat1_*.py`) : g = 0,000025 et distance 0,00070 (S01.5) ; frais minimaux et paliers (C11.7) ; spread non recompté.
- Catégorie 2 (`tests/robot/execution/test_c2a_cat2_*.py`) : via 3.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

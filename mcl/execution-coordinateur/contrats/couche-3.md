# Contrat de la couche 3 — dimensionnement (artefact `execution-coordinateur`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 4 et 5), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 4
- **Dépend de** : couches 1c, 1d, 2a (réelles et figées) ; amont figé : aucun ; frontières externes doublées : calcul-courtier
- **Module** : `src/xpbots/execution/c3_dimensionnement.py`
- **Sources normatives** : C04, C06, C07, C08, C09, C11.2, C11.5–C11.7, C11.10–C11.13 ; plan maître, section 7.D

---

Unité : dimensionnement
Responsabilité : Retenir le plus grand volume de la grille native qui respecte simultanément les cinq contraintes C07.
Signature : dimensionner(equity, niveaux, a, profil, registre, calcul) -> Volume | Refus
Entrée : instantané des fonds propres et des réserves, niveaux, profil
Sortie : volume arrondi vers le bas ; refus MIN_VOLUME_OR_RISK_REJECT, ACCOUNT_RISK_CAP, MARGIN_REJECT, SYMBOL_BUSY ou ENVIRONMENT_NOT_READY
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/execution/test_c3_cat1_*.py`) : 0,01 lot standard refusé à 0,70 USD (C11.6) ; micro admis à 0,07 USD ; 1 % réservé, deux positions, marge ≤ Eqt/3 ; positions externes (R8).
- Catégorie 2 (`tests/robot/execution/test_c3_cat2_*.py`) : bloc 0→3 réel avec doublure de calculs courtier.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

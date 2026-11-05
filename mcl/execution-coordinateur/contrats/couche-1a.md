# Contrat de la couche 1a — garde-cotation (artefact `execution-coordinateur`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 4 et 5), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 6
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/execution/c1a_cotation.py`
- **Sources normatives** : C04, C06, C07, C08, C09, C11.2, C11.5–C11.7, C11.10–C11.13 ; plan maître, section 7.D

---

Unité : garde_cotation
Responsabilité : Contrôler fraîcheur, croisement, plafond de spread, écart d'entrée et TTL d'un signal.
Signature : controler_cotation(cotation, maintenant, signal, profil) -> Conforme | Attendre(motif) | Expire
Entrée : cotation Bid/Ask horodatée, instant courant, signal (clôture T, C, A_t)
Sortie : verdict ; motifs SPREAD_CAP, ENTRY_GAP, SIGNAL_EXPIRED
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/execution/test_c1a_cat1_*.py`) : spread au plafond admis, TTL exactement 5 s expiré (C11.2), âge 2 s, écart 0,25A, R3, première cotation après clôture (C11.3).
- Catégorie 2 (`tests/robot/execution/test_c1a_cat2_*.py`) : via 6.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

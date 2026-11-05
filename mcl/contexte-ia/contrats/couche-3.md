# Contrat de la couche 3 — contexte (artefact `contexte-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 7), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : aucune couche interne ; hors artefact : execution-coordinateur (port ContexteIA), service-ia (format)
- **Dépend de** : couches 2 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/contexte_ia/c3_contexte.py`
- **Sources normatives** : A03, A07, A10, A12, A14 ; plan maître, section 7.F

---

Unité : contexte
Responsabilité : Rendre BLOCK ou NEUTRAL pour un symbole et un instant, jamais ALLOW.
Signature : ContexteIA.decision(symbole, instant_ms) -> DecisionContexteIA (BLOCK | NEUTRAL ; le bras A/B est porté par l'instance) ; recharger()
Entrée : symbole, instant, bras PAPER_AB, mode
Sortie : décision et identifiants de preuve
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/contexte_ia/test_c3_cat1_*.py`) : BLOCK/NEUTRAL jamais ALLOW, bras A/B, réel sans validation financière = NEUTRAL, publication+900 s.
- Catégorie 2 (`tests/robot/contexte_ia/test_c3_cat2_*.py`) : avec moteur-ema et execution-coordinateur : insertion A07 (AI_CONTEXT_VETO, cooldown, aucun fill).

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

# Contrat de la couche 3 — pipeline-marche (artefact `donnees-temps`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 2), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : aucune couche interne ; hors artefact : moteur-ema, execution-coordinateur, journal-rejeu, app
- **Dépend de** : couches 1a, 1b, 2 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/donnees_temps/c3_pipeline.py`
- **Sources normatives** : C03 (points 1 à 12), C11.1, C11.3, C11.4 ; plan maître, section 7.A

---

Unité : pipeline_marche
Responsabilité : Produire par symbole les bougies enrichies et les événements de trou à partir des ticks, de la couverture et de l'horloge.
Signature : PipelineMarche(symbole).sur_tick(t) ; sur_couverture(evt) ; sur_horloge(i) -> list[BougieEnrichie | EvenementTrou]
Entrée : ticks, événements de couverture, instants d'horloge
Sortie : BougieEnrichie (bougie, indicateurs, A_t, jour Londres, statut) ou EvenementTrou
Effets de bord : états des couches inférieures
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/donnees_temps/test_c3_cat1_*.py`) : statuts OK/WARMUP/DATA_GAP, ordre des émissions, effacement après trou (R5, R6).
- Catégorie 2 (`tests/robot/donnees_temps/test_c3_cat2_*.py`) : C11.1 préfixe causal sur ticks synthétiques ; trou puis récupération ; changement d'heure de bout en bout.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

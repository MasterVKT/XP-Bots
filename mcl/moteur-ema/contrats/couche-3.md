# Contrat de la couche 3 — moteur (artefact `moteur-ema`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 3), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : aucune couche interne ; hors artefact : execution-coordinateur (port Strategie), app
- **Dépend de** : couches 1d, 2 (réelles et figées) ; amont figé : amont-donnees-temps ; frontières externes doublées : stockage-etat
- **Module** : `src/xpbots/moteur_ema/c3_moteur.py`
- **Sources normatives** : S01.1 à S01.6, C03.8–C03.11, C06 (conversion), A07 ; plan maître, section 7.B

---

Unité : moteur_ema
Responsabilité : Produire à chaque clôture admissible un signal ou un motif technique et appliquer l'issue reçue.
Signature : MoteurEMA (port Strategie).sur_cloture(bougie_enrichie, tick_size) -> ResultatTechnique ; appliquer_issue(cle, issue) ; notifier_sortie(symbole, instant)
Entrée : BougieEnrichie, tick_size, issues
Sortie : Signal ou motif, état du détecteur et niveaux structurels
Effets de bord : état persisté via le port Stockage
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c3_cat1_*.py`) : motifs et ordre des traitements ; compteur de six fills (T11) ; persistance.
- Catégorie 2 (`tests/robot/moteur_ema/test_c3_cat2_*.py`) : bloc A+B réel : S01.6 complet, C11.4, causalité.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

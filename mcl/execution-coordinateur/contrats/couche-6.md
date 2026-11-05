# Contrat de la couche 6 — coordinateur (artefact `execution-coordinateur`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 4 et 5), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : aucune couche interne ; hors artefact : journal-rejeu, app
- **Dépend de** : couches 1a, 2b, 5 (réelles et figées) ; amont figé : amont-noyau ; frontières externes doublées : journal-persistant
- **Module** : `src/xpbots/execution/c6_coordinateur.py`
- **Sources normatives** : C04, C06, C07, C08, C09, C11.2, C11.5–C11.7, C11.10–C11.13 ; plan maître, section 7.D

---

Unité : coordinateur
Responsabilité : Ordonner les traitements C08 pour chaque événement et journaliser chaque décision C09.
Signature : Coordinateur.sur_tick(tick) ; sur_horloge(i) ; sur_bougie(symbole, bougie_enrichie) ; demarrer() ; redemarrer()
Entrée : événements de marché et d'horloge ; ports Strategie, ControleFondamental, ContexteIA, Courtier, CalculCourtier, Stockage, Journal
Sortie : ordres, sorties, issues et enregistrements C09
Effets de bord : état persisté, journal
Erreurs, exceptions : toute exception sur le chemin d'entrée = refus ; sur le chemin de sortie = réessai

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/execution/test_c6_cat1_*.py`) : ordre C08, second contrôle avant envoi, journal C09, redémarrage, verrou de propriété en netting.
- Catégorie 2 (`tests/robot/execution/test_c6_cat2_*.py`) : bloc A+B+D réel, TECHNICAL_CONTROL_NEUTRAL nommé : cycle de trade complet, 7ᵉ entrée refusée, C11.10 à C11.13.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

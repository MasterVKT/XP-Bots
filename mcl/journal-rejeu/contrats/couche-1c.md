# Contrat de la couche 1c — import-ticks (artefact `journal-rejeu`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 8), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2b
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : ticks-historiques
- **Module** : `src/xpbots/journal_rejeu/c1c_import_ticks.py`
- **Sources normatives** : C09, C10, C11.12, C11.14, A13, A14 ; plan maître, section 7.H

---

Unité : import_ticks
Responsabilité : Lire les ticks historiques et leur manifeste de couverture.
Signature : importer(source, manifeste) -> Iterable[Tick]
Entrée : fichiers CSV/CSV.gz du cahier de données et manifeste
Sortie : ticks ordonnés et couverture déclarée
Effets de bord : aucun
Erreurs, exceptions : ManifesteAbsent ; EmpreinteInvalide

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/journal_rejeu/test_c1c_cat1_*.py`) : format du cahier de données, ordre stable, empreintes, refus sans manifeste (R5).
- Catégorie 2 (`tests/robot/journal_rejeu/test_c1c_cat2_*.py`) : via 2b.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

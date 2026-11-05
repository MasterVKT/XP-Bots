# Contrat de la couche 1a — journal (artefact `journal-rejeu`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 8), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2a, 2b
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : journal-persistant
- **Module** : `src/xpbots/journal_rejeu/c1a_journal.py`
- **Sources normatives** : C09, C10, C11.12, C11.14, A13, A14 ; plan maître, section 7.H

---

Unité : journal
Responsabilité : Valider et sérialiser les enregistrements C09.
Signature : Journal.ecrire(enregistrement) ; valider(enregistrement) -> list[Erreur]
Entrée : enregistrements du noyau
Sortie : lignes JSON canoniques en ajout seul
Effets de bord : écriture via le port Journal
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/journal_rejeu/test_c1a_cat1_*.py`) : champs C09 complets, sérialisation stable, aucun secret.
- Catégorie 2 (`tests/robot/journal_rejeu/test_c1a_cat2_*.py`) : via 2.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

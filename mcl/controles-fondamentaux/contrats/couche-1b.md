# Contrat de la couche 1b — garde-annonces (artefact `controles-fondamentaux`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 6), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : source-calendrier
- **Module** : `src/xpbots/fondamental/c1b_annonces.py`
- **Sources normatives** : C05, C08 point 2, C11.8, C11.9 ; plan maître, section 7.E

---

Unité : garde_annonces
Responsabilité : Contrôler fraîcheur et couverture du calendrier et les fenêtres HIGH par devise.
Signature : GardeAnnonces.entree_autorisee(symbole, i) -> bool | NEWS_WINDOW ; sorties_dues(i) -> list
Entrée : versions de calendrier connues à l'instant
Sortie : verdict et demandes de clôture à N−900 s
Effets de bord : historique des versions conservé
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/fondamental/test_c1b_cat1_*.py`) : [N−900, N+900) début inclus fin exclue, fraîcheur 86 400 s, couverture 172 800 s, annonce tardive, calendrier révisé sans réécriture (C11.9).
- Catégorie 2 (`tests/robot/fondamental/test_c1b_cat2_*.py`) : via 3.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

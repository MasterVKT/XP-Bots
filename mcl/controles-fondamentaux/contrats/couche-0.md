# Contrat de la couche 0 — types-fondamentaux (artefact `controles-fondamentaux`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 6), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 1a, 1b
- **Dépend de** : couches aucune (réelles et figées) ; amont figé : amont-donnees-temps, amont-noyau ; frontières externes doublées : aucune
- **Module** : `src/xpbots/fondamental/c0_types.py`
- **Sources normatives** : C05, C08 point 2, C11.8, C11.9 ; plan maître, section 7.E

---

Unité : types_fondamentaux
Responsabilité : Représenter messages de permission, événements et versions de calendrier et la table devises par symbole.
Signature : MessagePermission ; EvenementCalendrier ; VersionCalendrier ; devises_du_symbole(symbole)
Entrée : JSON strict ; paramètres news_* et fundamental_*
Sortie : objets immuables
Effets de bord : aucun
Erreurs, exceptions : SymboleInconnu

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/fondamental/test_c0_cat1_*.py`) : schéma, énumérations, table devises par symbole (R10).
- Catégorie 2 (`tests/robot/fondamental/test_c0_cat2_*.py`) : —.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

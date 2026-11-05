# Contrat de la couche 1a — sessions-londres (artefact `donnees-temps`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 2), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3 ; hors artefact : execution-coordinateur (sorties horaires)
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/donnees_temps/c1a_sessions.py`
- **Sources normatives** : C03 (points 1 à 12), C11.1, C11.3, C11.4 ; plan maître, section 7.A

---

Unité : sessions_londres
Responsabilité : Calculer jours Londres et UTC, appartenance aux fenêtres de méthode, heures locales de sortie et blackout de rollover via Europe/London.
Signature : jour_londres(i) ; jour_utc(i) ; dans_fenetre(ouverture, cloture, debut, fin_exclue) -> bool ; instant_local(jour, 'HH:MM:SS') -> Instant ; dans_blackout(i) -> bool
Entrée : Instant ms UTC ; heures locales lues dans la configuration de la méthode
Sortie : dates et booléens exacts selon zoneinfo Europe/London, jours 0–4 seulement
Effets de bord : aucun
Erreurs, exceptions : HeureLocaleInvalide si l'heure demandée n'existe pas ou est ambiguë ce jour-là

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/donnees_temps/test_c1a_cat1_*.py`) : changements d'heure 2025/2026, 08:15 première clôture, 15:45 dernière, 16:00 exclue, week-end exclu, jour UTC ≠ jour Londres, blackout [21:00,23:00) UTC, concordance local_decision_in_window.
- Catégorie 2 (`tests/robot/donnees_temps/test_c1a_cat2_*.py`) : avec 1b et 1c via la couche 3.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.

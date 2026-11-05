# Contrat de la couche 1a — sessions-londres (artefact `donnees-temps`)

- **Statut** : finalisé (phase 2, 2026-11-05) ; gel tracé dans `mcl/donnees-temps/journal.jsonl`.
- **Consommateurs cartographiés** : couche 3 (`pipeline_marche`) ; hors artefact : `moteur-ema` (fenêtres
  08:00–16:00), `execution-coordinateur` (sortie 16:00 Londres, blackout, jour UTC), `controles-fondamentaux`.
- **Dépend de** : couche 0 (`ParametresTechniques`, `analyser_heure`) ; amont figé : aucun ; frontières externes :
  aucune (base IANA via `zoneinfo`, `tzdata` déclaré).
- **Module** : `src/xpbots/donnees_temps/c1a_sessions.py`
- **Sources normatives** : C03 point 3 (Europe/London, jours locaux, jour UTC du risque), S01.1 (fenêtre),
  C08 (blackout `[21:00, 23:00)` UTC) ; plan maître 7.A ; cas C11.2 (fin de fenêtre) et C11.4.

---

Unité : sessions_londres
Responsabilité : Calculer jours Londres et UTC, appartenance aux fenêtres de méthode, heures locales de sortie et
blackout de rollover via le fuseau `session_timezone`.
Signature : `SessionsLondres(parametres)` ; `local(instant_ms) -> datetime` ; `jour_londres(instant_ms) -> date` ;
`jour_utc(instant_ms) -> date` ; `jour_actif(jour) -> bool` ;
`dans_fenetre(ouverture_ms, cloture_ms, debut, fin_exclue) -> bool` ; `instant_local(jour, heure) -> int` ;
`dans_blackout(instant_ms) -> bool`.
Entrée : instants en ms UTC ; heures `HH:MM:SS` lues dans la configuration de la méthode.
Sortie :
- `dans_fenetre` est vrai si et seulement si l'ouverture et la clôture tombent le même jour Londres, que ce jour
  est actif (`active_weekdays_local`), que l'heure locale d'ouverture est ≥ `debut` et que l'heure locale de
  clôture est < `fin_exclue` (identique à `reference.technical.local_decision_in_window`) ;
- `instant_local` rend l'instant UTC d'une heure locale d'un jour donné, changements d'heure compris ;
- `dans_blackout` est vrai si l'heure UTC appartient à `[rollover_blackout_utc_start, rollover_blackout_utc_end)`.
Effets de bord : aucun.
Erreurs, exceptions : `HeureLocaleInvalide` si l'heure locale demandée n'existe pas ou est ambiguë ce jour-là ;
`ValueError` si l'ouverture n'est pas strictement antérieure à la clôture ; `ConfigurationInvalide` pour une heure
mal formée.

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/donnees_temps/test_c1a_cat1_*.py`) : changements d'heure 2025 et 2026 (08:00 Londres
  = 07:00 UTC en été, 08:00 UTC en hiver), première clôture admissible 08:15, dernière 15:45, clôture à 16:00
  exclue, week-end exclu, jour UTC différent du jour Londres, bougie à cheval sur minuit exclue, blackout début
  inclus et fin exclue, heures inexistantes et ambiguës refusées, concordance avec
  `reference.technical.local_decision_in_window` sur des semaines complètes encadrant les changements d'heure.
- Catégorie 2 : par la couche 3.

## Comportements documentés (loi de Hyrum)

Le jour d'une bougie pour les méthodes est le jour Londres de son instant de clôture (comme dans la référence).
Aucun décalage fixe n'est employé : seul le fuseau IANA de la configuration fait foi.

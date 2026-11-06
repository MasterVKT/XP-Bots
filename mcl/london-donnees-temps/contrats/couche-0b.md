# Contrat de la couche 0b — sessions_londres

- **Statut** : finalisé le 06/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : couche 3 (`flux_bougies` : repères locaux) ; plus tard `moteur-london`
  (range, fenêtre, sortie) et `execution-coordinateur` (jour UTC, blackout)
- **Dépend de** : noyau figé (`c0a_temps`, `c0c_configuration`) ; aucune couche de l'artefact ; aucune frontière
  externe (`zoneinfo`, base IANA ; `tzdata` sous Windows)

---

Unité : sessions_londres
Responsabilité : Calculer jours et heures de Londres, fenêtres, jour UTC et blackout.
Signature : `CalendrierLondres(fuseau: str, jours_actifs: tuple[int, ...], blackout_debut: time, blackout_fin: time)` ;
`CalendrierLondres.depuis_parametres(commun: ParametresCommuns)` (lit `session_timezone`,
`active_weekdays_local`, `rollover_blackout_utc_start`, `rollover_blackout_utc_end`) ; méthodes
`datetime_local(instant_ms) -> datetime`, `jour_local(instant_ms) -> date`, `jour_actif(jour: date) -> bool`,
`instant_local(jour: date, heure: time) -> int`,
`ouvertures(jour: date, debut: time, fin_exclue: time, duree_ms: int) -> tuple[int, ...]`,
`decision_dans_fenetre(ouverture_ms, cloture_ms, debut: time, fin_exclue: time) -> bool`,
`jour_utc(instant_ms) -> date`, `dans_blackout(instant_ms) -> bool`, `prochain_debut_blackout(instant_ms) -> int` ;
`ErreurSessions(ValueError)`.
Entrée : instants entiers UTC (noyau 0a) ; jours `date` ; heures `time` ; durée entière > 0.
Sortie : `datetime_local` conscient du fuseau ; `instant_local` rend l'instant UTC d'une heure locale d'un jour
de Londres ; `ouvertures` rend les ouvertures `[début, fin)` du jour à pas de durée (20 pour 02:00–07:00 en M15,
été comme hiver) ; `decision_dans_fenetre` reproduit `local_decision_in_window` de `reference/technical.py` :
même date locale à l'ouverture et à la clôture, jour de clôture actif, heure locale d'ouverture ≥ début, heure
locale de clôture < fin exclue, heures tronquées à la seconde ; `dans_blackout` teste `[début, fin)` en heure UTC
(fenêtre qui passe minuit admise) ; `prochain_debut_blackout` rend le plus petit début ≥ l'instant.
Effets de bord : aucun.
Erreurs, exceptions : `ErreurSessions` pour un fuseau inconnu, des jours hors de 0 à 6, un blackout de durée nulle,
une heure locale inexistante ou ambiguë (changement d'heure), des bornes d'ouvertures non multiples de la durée
ou non alignées, une durée invalide, un instant refusé par le noyau.

---

## Spécification exécutable

`tests/robot/london_donnees_temps/test_cat1_c0b_sessions.py` (profondeur 0 : pas de catégorie 2).

## Comportements documentés (loi de Hyrum)

Les changements d'heure britanniques tombent le dimanche à 01:00 UTC de 2019 à 2027 (vérifié par la suite), donc
jamais un jour actif. Le texte des messages d'erreur n'est pas garanti.

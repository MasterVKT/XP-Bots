# Contrat de la couche 1b — constructeur-bougies (artefact `donnees-temps`)

- **Statut** : finalisé (phase 2, 2026-11-05) ; gel tracé dans `mcl/donnees-temps/journal.jsonl`.
- **Consommateurs cartographiés** : couche 3 (`pipeline_marche`).
- **Dépend de** : couche 0 (`CalendrierSeances`) ; amont figé : `amont-noyau` (`Tick`, `Bougie`, `Instant`,
  `MS_PAR_SECONDE`) ; frontières externes : aucune (les événements de couverture viennent du flux réel ou du
  manifeste, transmis par l'appelant).
- **Module** : `src/xpbots/donnees_temps/c1b_bougies.py`
- **Sources normatives** : C03 points 2, 4, 5 et 6 ; R4 et R5 du registre d'interprétation ; plan maître 7.A ;
  cas C11.1 (H1 partielle invisible) et C11.3.

---

Unité : constructeur_bougies
Responsabilité : Agréger les ticks d'un symbole en bougies Bid clôturées sur `[T, T+période)` aligné sur l'époque
UTC et qualifier chaque intervalle clôturé.
Signature : `ConstructeurBougies(symbole, periode_s, seances, debut_observation_ms)` ;
`ajouter_tick(tick) -> list[ClotureIntervalle]` ; `couverture(instant_ms, etablie) -> list[ClotureIntervalle]` ;
`avancer(instant_ms) -> list[ClotureIntervalle]` ; `terminer(fin_ms) -> list[ClotureIntervalle]` ;
propriétés `couverture_etablie`, `ticks_ignores`, `intervalle_final_abandonne`.
Entrée : ticks du symbole dans l'ordre strict (ms, séquence) ; transitions de couverture du flux (établie ou
interrompue) à un instant ; avances d'horloge ; calendrier des séances natives.
Sortie : pour chaque intervalle clôturé (dans l'ordre), une `ClotureIntervalle(ouverture_ms, cloture_ms, bougie,
attendu, complet, motif_incomplet, couverture_etablie)` :
- l'intervalle se clôt quand l'horloge atteint `T+période` (tick de frontière, transition ou avance) ; le tick à
  `T+période` appartient à l'intervalle suivant ;
- `attendu` : le marché est ouvert sur une partie de l'intervalle ; un intervalle non attendu et sans tick ne
  produit rien (fermeture officielle ≠ trou) ;
- `complet` : couverture établie sur toute la portion ouverte et au moins un Bid ; sinon `motif_incomplet` =
  `COUVERTURE` (interruption du flux) ou `SANS_BID` (R4 : aucun Bid alors que le flux était établi) ; une minute
  sans changement n'est pas un trou ;
- `bougie` : OHLC Bid des ticks de l'intervalle, `valide = complet`, ou `None` si aucun tick ;
- `couverture_etablie` : état de la couverture à la fin de l'intervalle (limite à gauche).
Les intervalles qui commencent avant le début d'observation sont ignorés (ni bougie ni trou) ; à `terminer`,
l'intervalle non terminé est abandonné (jamais clos, causalité).
Effets de bord : état de la bougie en formation et historique élagué de la couverture.
Erreurs, exceptions : `TickHorsOrdre` si un tick ne suit pas strictement le précédent ou concerne un autre symbole ;
`HorlogeEnRecul` si l'horloge recule ; `CalendrierInconnu` (couche 0) si les séances ne couvrent pas l'intervalle.

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/donnees_temps/test_c1b_cat1_*.py`) : tick de frontière, égalités de milliseconde
  départagées par la séquence, clôture par avance d'horloge sans tick, minute inchangée ≠ trou, fermeture officielle
  sans tick ≠ trou, interruption inexpliquée = incomplet `COUVERTURE`, intervalle attendu sans Bid = incomplet
  `SANS_BID` (R4), début d'observation non aligné, abandon de l'intervalle final, H1 invisible avant sa clôture
  (C11.1), tick hors ordre et horloge en recul refusés.
- Catégorie 2 : par la couche 3.

## Comportements documentés (loi de Hyrum)

Une transition de couverture survenant exactement à l'instant de clôture n'est pas encore prise en compte dans
`couverture_etablie` de cet intervalle (elle s'applique à l'intervalle suivant).

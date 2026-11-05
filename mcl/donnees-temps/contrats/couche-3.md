# Contrat de la couche 3 — pipeline-marche (artefact `donnees-temps`, enveloppe)

- **Statut** : finalisé (phase 2, 2026-11-05) ; modifié par le défigeage R6′ du 2026-11-05
  (`mcl/donnees-temps/defigeages/2026-11-05-couche-3-r6.md`) ; gels tracés dans `mcl/donnees-temps/journal.jsonl`.
- **Consommateurs cartographiés** : aucune couche interne (enveloppe) ; hors artefact : `app` (rejeu, boucle
  paper), `moteur-ema` (bougies enrichies), `execution-coordinateur` (journal des événements de données),
  `journal-rejeu`.
- **Dépend de** : couches 0 (`CalendrierSeances`), 1a (`SessionsLondres`), 1b (`ConstructeurBougies`, `ClotureIntervalle`), 2
  (`EtatIndicateursSymbole`, `SpecIndicateurs`) ; amont figé : `amont-noyau` (`BougieEnrichie`, `StatutBougie`,
  `EvenementDonnees`) ; frontières externes : aucune (la récupération d'historique est une fonction fournie par
  l'appelant : flux réel en phase 9, absente en rejeu).
- **Module** : `src/xpbots/donnees_temps/c3_pipeline.py`
- **Sources normatives** : C03 points 1 à 7 ; R4, R5 et R6′ du registre d'interprétation (décidés) ; plan maître
  7.A ; cas C11.1, C11.3, C11.4.

---

Unité : pipeline_marche
Responsabilité : Produire, pour un symbole, les bougies enrichies et les événements de données à partir des ticks,
des transitions de couverture et de l'horloge.
Signature : `PipelineMarche(symbole, periode_s, seances, sessions, spec, debut_observation_ms, recuperation=None,
etat=None)` ; `sur_tick(tick)`, `sur_couverture(instant_ms, etablie)`, `sur_horloge(instant_ms)`,
`terminer(fin_ms)`, chacune `-> list[BougieEnrichie | EvenementDonnees]` ; propriétés `etat`, `en_trou`.
`recuperation(symbole, debut_ms, fin_ms) -> Sequence[Tick] | None` rend l'historique complet des ticks de
`[début, fin)` (couverture établie par construction) ou `None` s'il est indisponible.
Entrée : ticks du symbole dans l'ordre strict, transitions de couverture, avances d'horloge, calendrier des séances,
spécification des indicateurs ; éventuellement un état d'indicateurs restauré (redémarrage).
Sortie, dans l'ordre des clôtures :
- intervalle complet hors trou : indicateurs mis à jour, `BougieEnrichie` au statut `WARMUP` tant que le
  préchauffage n'est pas atteint, puis `OK` ; l'événement `PRECHARGEMENT` (empreinte) précède la bougie qui
  l'atteint ;
- intervalle attendu incomplet (`COUVERTURE` ou `SANS_BID`, R4) : événement `TROU`, puis la bougie au statut
  `DATA_GAP` si elle existe ; les indicateurs ne sont pas mis à jour ; l'état d'avant le trou est conservé ;
- en trou, à chaque clôture où la couverture est établie : sortie du trou. L'état d'avant le trou est conservé ;
  la récupération de `[début du trou, clôture)` est demandée et seules les bougies reconstruites complètes sont
  appliquées, dans l'ordre ; la clôture courante complète est appliquée dans sa version reconstruite si elle est
  complète, sinon dans sa version en direct (aucune décision rétroactive : les bougies passées ne sont pas réémises).
  Historique complet et cohérent jusqu'à la clôture courante : événement `RECUPERATION` (`bougies` = nombre de
  bougies reconstruites appliquées). Sinon (R6′) : événement `RECALCUL` (`motif` parmi `RECUPERATION_INDISPONIBLE`,
  `HISTORIQUE_INVALIDE`, `HISTORIQUE_INCOMPLET` ; `bougies` = reconstructions complètes appliquées) : les
  indicateurs sont recalculés sur les seules bougies valides, aucun préchauffage n'est relancé, aucune bougie n'est
  inventée ; le préchargement en cours continue sur les bougies valides ;
- en trou sans couverture établie : bougie complète au statut `DATA_GAP` (entrées bloquées) ;
- redémarrage avec un état restauré : si des intervalles attendus ont été manqués depuis la dernière clôture
  appliquée, le pipeline démarre en trou (récupération ou recalcul à la première clôture couverte).
Le jour Londres d'une bougie est celui de son instant de clôture.
Effets de bord : états des couches 1b et 2 ; appel de la fonction de récupération.
Erreurs, exceptions : celles des couches 1b et 2 ; `ValueError` si l'état restauré ne correspond pas à la
spécification ; `CalendrierInconnu` si les séances ne couvrent pas la période utile.

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/donnees_temps/test_c3_cat1_*.py`) : statuts `WARMUP` puis `OK` à la bougie du
  préchauffage avec l'événement `PRECHARGEMENT`, trou de couverture puis recalcul sans récupération (aucun
  préchauffage relancé), recalcul identique au calcul sur les seules bougies valides, trou `SANS_BID`,
  récupération réussie identique au flux sans trou, historique incomplet ou incohérent conduisant au recalcul,
  récupération partielle appliquée (R6′), trou pendant le préchauffage (préchargement continu), bougie complète en trou sans couverture,
  redémarrage après des intervalles manqués (trou) ou pendant une fermeture officielle (continuité).
- Catégorie 2 (`tests/robot/donnees_temps/test_c3_cat2_*.py`) : bloc réel {0 → 3} : C11.1 préfixe causal (retirer
  ou modifier des ticks futurs ne change aucune sortie passée), changement d'heure de bout en bout (jour Londres),
  trou puis récupération de bout en bout identique au flux continu, concordance des indicateurs avec
  `reference.technical.add_indicators` sur les bougies produites.

## Comportements documentés (loi de Hyrum)

Un événement `TROU` est émis pour chaque intervalle attendu incomplet. La tentative de récupération a lieu à la
première clôture dont la couverture est établie (limite à gauche, couche 1b).

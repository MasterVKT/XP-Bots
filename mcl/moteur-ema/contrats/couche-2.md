# Contrat de la couche 2 — machine-etats (artefact `moteur-ema`)

- **Statut** : finalisé (phase 3, 2026-11-05) ; gel tracé dans `mcl/moteur-ema/journal.jsonl`.
- **Consommateurs cartographiés** : couche 3.
- **Dépend de** : couches 0 (`ParametresEMA`), 1a (`sens_tendance`), 1b (`contexte_armement`, `repli_valide`,
  `contact`), 1c (`est_reprise`) ; amont figé : `amont-noyau` (`Sens`, `Rempli`, `Refuse`) ; frontières externes :
  aucune.
- **Module** : `src/xpbots/moteur_ema/c2_machine_etats.py`
- **Sources normatives** : S01.1, S01.2, S01.4 (compteur), S01.6, C08 (position possédée, sortie), A07 (refus
  définitif) ; R1, R2 ; plan maître 7.B (T1 à T12).

---

Unité : machine_etats_ema
Responsabilité : Gérer, pour un symbole, armement, contact, repli de 1 à `age_max_repli` bougies, reprise,
cooldown, position possédée, issue en attente et compteur journalier des entrées remplies.
Signature : `MachineEtatsEMA(p)` ; `etape(obs: ObservationEMA) -> Transition` ; `appliquer_issue(issue)` ;
`notifier_sortie(instant_ms)` ; `effacer()` ; `entrees_remplies(jour) -> int` ; `etat_detecteur() -> dict` ;
`exporter() -> dict` ; `MachineEtatsEMA.importer(p, donnees)` ; propriétés `etat`, `sens`, `signal_cloture_ms`.
Types : `EtatTechnique` (`IDLE`, `ARMED_LONG`, `ARMED_SHORT`, `PULLBACK_LONG`, `PULLBACK_SHORT`, `COOLDOWN`,
`OWNED_POSITION`, `ATTENTE_ISSUE`) ; `NatureTransition` (`POSITION`, `ATTENTE`, `HORS_FENETRE`, `DONNEES`,
`IGNOREE`, `AUCUNE`, `ARMEMENT`, `ANNULATION`, `EXPIRATION`, `CONTACT`, `REPLI`, `REPRISE`) ;
`ObservationEMA(cloture_ms, jour, dans_fenetre, exploitable, o, h, l, c, tr, e_rapide, e_moyenne, e_lente,
e_lente_decalee, rsi, a_t)` (valeurs exigées finies, A_t > 0 et L ≤ H si exploitable) ;
`Reprise(sens, plus_bas, plus_haut, age, debut_ms)` avec `extreme` ; `Transition(nature, avant, apres, tendance,
reprise)`.
Entrée : une observation par clôture M15, dans l'ordre ; issues et sorties dans l'ordre C08 (avant la clôture
suivante quand elles sont connues).
Sortie, ordre d'évaluation à chaque clôture :
1. changement de jour Londres : armement, repli et cooldown effacés (T10) ;
2. `OWNED_POSITION` → `POSITION` (aucune préparation, même hors fenêtre) ; `ATTENTE_ISSUE` → `ATTENTE` (R2) ;
3. hors fenêtre → `HORS_FENETRE`, tout est effacé, cooldown compris ;
4. inexploitable → `DONNEES`, armement et repli effacés, cooldown conservé et non décompté ;
5. `COOLDOWN` → `IGNOREE` ; une clôture ≤ instant de départ du cooldown n'est pas décomptée (R1), chaque clôture
   strictement postérieure décompte une des `clotures_cooldown` clôtures ; à zéro, `IDLE` (T7, T9) ;
6. `IDLE` → `ARMEMENT` si tendance et contexte d'armement, sinon `AUCUNE` ; la bougie d'armement n'est jamais
   repli ni signal (T1) ;
7. armé ou en repli : tendance différente ou repli invalide → `ANNULATION` puis réarmement possible sans entrée
   (T4) ; armé sans contact → `AUCUNE` ; premier contact → `CONTACT`, âge 1 (T2) ; en repli → âge + 1, au-delà de
   `age_max_repli` → `EXPIRATION` puis réarmement possible sans entrée (T5), sinon `REPLI` avec extrêmes de toutes
   les bougies (T3) ;
8. reprise S01.3 → `REPRISE` (extrêmes signal compris, âge), repli consommé, état `ATTENTE_ISSUE` (T6).
`appliquer_issue` (seulement en `ATTENTE_ISSUE`, instant ≥ clôture du signal) : `Rempli` → `OWNED_POSITION`,
une entrée comptée sur le jour Londres du signal (T8, T11, remplissage partiel compris) ; `Refuse` → `COOLDOWN`
à partir de l'instant de l'issue (T7, R2). `notifier_sortie` (seulement en `OWNED_POSITION`, instant ≥ fill) →
`COOLDOWN` à partir de l'instant de sortie (T9, R1). `effacer` (trou, C03.6) : armement et repli effacés.
`entrees_remplies(jour)` : compteur du jour Londres demandé (0 pour un autre jour), restauré par `importer`
(jamais remis à zéro par un redémarrage, T11). `etat_detecteur` : `etat`, `sens`, `age_repli`, `plus_bas_repli`,
`plus_haut_repli`, `debut_repli_ms`, `cooldown_restantes`, `entrees_jour`.
Effets de bord : état interne exportable (format `xp-moteur-ema-etat-v1`, types JSON).
Erreurs, exceptions : `IssueInattendue` (issue sans signal en attente, sortie sans position) ; `ValueError`
(observation invalide, issue antérieure au signal, sortie antérieure au fill) ; `EtatIncompatible` (état exporté
illisible ou incohérent).

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c2_cat1_*.py`) : T1 à T12 une transition par test, R1 (sortie pile
  sur une clôture), R2 (issue différée, refus ou fill tardif), S01.6 (pente nulle, RSI 40, reprise sans nouveau
  contact, mèche, baisse de l'EMA rapide, âge 8 admis et 9 annulé), effacements, compteur, persistance.
- Catégorie 2 (`tests/robot/moteur_ema/test_c2_cat2_*.py`) : bloc réel {0 → 2} nourri des indicateurs de la
  référence : configurations identiques à `reference.technical.ema_setups` sur trois séries synthétiques à
  tendances (instant, sens, clôture, A, B_SL, âge).

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Le texte des messages d'erreur et l'ordre des clés de
`etat_detecteur` ne sont pas garantis.

# Contrat de la couche 3 — moteur (artefact `moteur-ema`, enveloppe)

- **Statut** : finalisé (phase 3, 2026-11-05) ; gel tracé dans `mcl/moteur-ema/journal.jsonl`.
- **Consommateurs cartographiés** : aucune couche interne (enveloppe) ; hors artefact : `app` (rejeu, via le port
  `Strategie`), `execution-coordinateur` (phases 4–5), `journal-rejeu` (phase 8).
- **Dépend de** : couches 0 (`ParametresEMA`), 1d (`stop_technique`), 2 (`MachineEtatsEMA`, `ObservationEMA`,
  `NatureTransition`, `IssueInattendue`) ; amont figé : `amont-noyau` (`BougieEnrichie`, `StatutBougie`,
  `EvenementDonnees`, `Signal`, `ResultatTechnique`, `CleIntention`, `Refuse`, `MotifRefus`, JSON canonique, port
  `Stockage`), `amont-donnees-temps` (`SessionsLondres`, clés d'indicateurs de la couche 1c) ; frontière externe
  doublée : `stockage-etat` (port `Stockage` ; doublure `tests/robot/doublures/stockage_memoire.py`).
- **Module** : `src/xpbots/moteur_ema/c3_moteur.py`
- **Sources normatives** : S01.1 à S01.6, C03 points 6, 7 et 11, C06 (B_SL), C08 (étape 4, position possédée),
  C09 (motifs, état du détecteur), A07 ; R1, R2, R18.

---

Unité : moteur_ema
Responsabilité : Produire à chaque clôture M15 un signal `EMA_V3` ou un motif technique, appliquer les issues, les
sorties et les trous, et persister l'état de chaque symbole.
Signature : `MoteurEMA(parametres, sessions, ticks: Mapping[str, Decimal], stockage)` (port `Strategie`) ;
`strategie_id` ; `symboles` ; `machine(symbole)` ; `sur_cloture(bougie_enrichie) -> ResultatTechnique` ;
`appliquer_issue(cle, issue)` ; `notifier_sortie(symbole, instant_ms)` ; `sur_evenement_donnees(evenement)` ;
constante `PREFIXE_STOCKAGE`.
Entrée : bougies enrichies des symboles configurés, dans l'ordre ; tick_size décimal > 0 par symbole (profil) ;
issues des signaux (clé C08 exacte) ; sorties de position ; événements de données.
Sortie de `sur_cloture` : observation construite avec la fenêtre S01.1 (`SessionsLondres.dans_fenetre` sur
`session_start_local` et `entry_end_local_exclusive` : ouverture ≥ 08:00, clôture < 16:00, même jour Londres actif)
et les indicateurs EMA rapide/moyenne/lente, EMA lente décalée, RSI, TR et `A_t` ; bougie exploitable seulement au
statut `OK` avec tous les indicateurs. Motif, par priorité : position possédée → `SYMBOL_BUSY` ; issue en attente
(R2) → `UNKNOWN_ORDER_STATE` ; statut `WARMUP` → `WARMUP` ; `DATA_GAP` → `DATA_GAP` ; hors fenêtre →
`OUTSIDE_SESSION` ; indicateurs manquants malgré `OK` → `WARMUP` ; reprise : stop de la couche 1d, trop large →
`STOP_TOO_WIDE` (repli consommé, cooldown) ; puis entrées remplies du jour Londres ≥ `entrees_max_jour` →
`DAILY_ENTRY_CAP` (repli consommé, cooldown ; S01.4, C08 étape 4) ; sinon `Signal(strategie_id, symbole,
clôture, sens, clôture Bid décimale, A_t, B_SL non arrondi, multiple_objectif, état)` en attente d'issue ; toute
autre clôture → `NO_SETUP`. L'état du détecteur (`etat_detecteur` de la couche 2, plus `transition`,
`tendance` et, sur une reprise, `b_sl`, `tampon`, `distance_stop`, `extreme_repli`, `plus_bas_repli`,
`plus_haut_repli`, `age_repli`, `debut_repli_ms`) accompagne chaque résultat et chaque signal.
`appliquer_issue` : la clé doit désigner la méthode, le symbole, la clôture et le sens du signal en attente.
`sur_evenement_donnees` : `TROU` d'un symbole configuré → armement et repli effacés (C03.6) ; autres natures et
autres symboles sans effet.
Effets de bord : écriture, après chaque changement, de l'état exporté du symbole en JSON canonique sous la clé
`moteur_ema/<strategie_id>/<symbole>` ; lecture de ces clés à la construction (redémarrage : même état, compteur
de fills jamais remis à zéro, C03.7, S01.2 point 2).
Erreurs, exceptions : `ValueError` (paramètres, sessions ou ticks invalides, symbole non configuré, bougie non
enrichie) ; `IssueInattendue` (issue sans signal en attente correspondant, sortie sans position) ; `EtatIncompatible`
(état persisté illisible).

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c3_cat1_*.py`) : conformité au port, configuration invalide, signal
  complet (B_SL, k, état), motifs `NO_SETUP`, `WARMUP`, `DATA_GAP`, `OUTSIDE_SESSION` (08:00, 15:45, 16:00,
  dimanche), `STOP_TOO_WIDE` puis cooldown, `UNKNOWN_ORDER_STATE`, `SYMBOL_BUSY`, sortie puis clôture ignorée,
  issues inattendues, septième entrée refusée puis nouveau jour après redémarrage (T11), refus non comptés, trou,
  événements sans effet, redémarrage au même état, symboles indépendants.
- Catégorie 2 (`tests/robot/moteur_ema/test_c3_cat2_*.py`) : bloc réel {donnees-temps → moteur-ema} : bougies
  identiques aux sources, signaux identiques à `reference.technical.ema_setups` (instant, sens, clôture, âge
  exacts ; A et B_SL à 1e-12 relatif), fenêtre et jours sur le changement d'heure d'octobre (C11.4), motifs et
  cooldown, causalité C11.1, trou effaçant le repli.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Le format interne de l'état persisté relève de la
couche 2 ; seule sa clé de stockage est garantie ici.

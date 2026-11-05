# 06 — Vérification exhaustive du plan

Retour au [plan directeur](README.md). Ce document prouve, élément par élément, que le plan couvre toute la
[spécification 02](../../../livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md), tous les
paramètres des [exports techniques](../../../config/parametres_figes_v3.json) et
[IA](../../../config/parametres_IA_integration_v1.json), et que les consignes de la skill
`anthropic-skills:expert-scalper-m15` ont été confrontées, une à une, aux choix de conception.

## 1. Méthode et résultat

1. **Contrôle mécanique reproductible** : `python tools/verifier_plan_london.py` vérifie que chaque clé des blocs
   `common` (73) et `london` (20) et chacune des 70 clés de la configuration IA est rattachée à une unité dans ce
   document ; que les 20 motifs minimaux de C09 figurent dans la table du [document 01](01_architecture.md),
   §9.3 ; que les 14 cas C11, les 8 cas S02.6 et les 18 cas A14 sont affectés dans le
   [document 03](03_acceptation_et_tests.md) ; que chaque section de la spécification (C01 à C11, C03.1 à C03.12,
   S02.1 à S02.6, A01 à A15) figure dans la matrice du §4 ; que chaque ligne de cette matrice et de la table des
   consignes d'expert (§5) désigne un emplacement du plan ; que les décisions D-xx du plan directeur sont toutes
   arrêtées, autorisées ou de simple note ; que chaque action humaine H-xx du plan directeur a sa procédure au
   [document 07](07_procedures_humaines.md) ; que chaque étape et chaque garde-fou de la skill de planification a
   sa ligne au §8 ; qu'aucune phase de 0 à 12 n'exige d'action humaine (plan directeur, §2.3, et fiches du
   [document 04](04_phases.md)) ; que les actions H-02 à H-12 se situent toutes en phase 13 (plan directeur, §5,
   et rubriques « Quand » du document 07) ; que chaque frontière du [document 02](02_cartographie_mcl.md), §7, a
   son contrat au [document 08](08_contrats_frontieres.md), §1, et réciproquement. Code de sortie non nul au
   moindre manque.
2. **Relecture exigence par exigence** : chaque phrase normative de la spécification a été relue et rattachée à
   une unité, une phase et un test (§4).
3. **Confrontation à la skill d'expert** : chaque consigne de la skill (fichier principal et ses quatre
   références) est classée et rattachée au plan (§5), puis chaque règle est soumise au contrôle de codifiabilité
   que la skill exige pour un robot (§6).
4. **Application de la skill de planification** : chaque étape et chaque garde-fou de
   `xp-bots-mcl-robot-planning` est rattaché à sa preuve dans le plan (§8).
5. **Résultat** : quinze manques ont été trouvés et corrigés dans le plan (§7) ; aucun écart avec une règle
   figée n'a été introduit.

## 2. Paramètres techniques figés

### 2.1 Bloc `common` (73 clés)

| Clés | Rôle dans le robot | Unité consommatrice | Vérification |
|---|---|---|---|
| `version`, `frozen_date` | Identité de la version figée, journalisée au démarrage et dans l'empreinte des règles | `noyau` 0c, `noyau` 2 | Enregistrement de démarrage |
| `default_mode` | Mode par défaut `PAPER` | `points-entree` 0 | Démarrage sans mode explicite |
| `account_currency`, `account_leverage`, `initial_equity_usd` | Contrôle du profil de compte (C04) ; capital initial de chaque compte simulé (C10) | `noyau` 1b ; `journal-rejeu` 1b, 2 | Compte non USD ou levier différent refusés ; compte simulé à 100 USD |
| `universe_priority` | Univers admis et ordre des symboles en arbitrage | `execution-coordinateur` 2b ; `points-entree` 0 (symboles liés) | C11.10, L-17 |
| `timeframe_seconds`, `h1_seconds` | Durées des bougies M15 et H1 | `donnees-temps` 1a | C11.3 |
| `bar_price`, `bar_alignment` | Valeurs exigées `BID` et `UTC` ; toute autre valeur refusée | `noyau` 0c ; `donnees-temps` 1a | Configuration altérée refusée |
| `session_timezone`, `active_weekdays_local` | Fuseau des sessions et jours actifs | `donnees-temps` 0b | L-02 à L-05 |
| `warmup_closed_m15_bars`, `warmup_closed_h1_bars` | Préchargement minimal (P-10) | `donnees-temps` 2b ; `moteur-london` 1b | L-07 |
| `atr_period`, `atr_method`, `atr_signal_reference` | ATR14 de Wilder ; A_t = ATR de t − 1 | `donnees-temps` 1b ; `noyau` 0c | Oracle `wilder` |
| `structural_buffer_atr` | Guard = max(`tick_size`, valeur × A) | `moteur-london` 1d | L-11 |
| `minimum_chart_stop_atr`, `maximum_chart_stop_atr` | Plancher et maximum de la distance technique | `moteur-london` 1d ; `execution-coordinateur` 0d | L-11 |
| `maximum_signal_true_range_atr` | TR maximal de la bougie de signal | `moteur-london` 1c | L-10 |
| `slippage_budget_atr_per_leg` | Réserve g par jambe, déviation demandée | `execution-coordinateur` 2a ; `infrastructure` 2d | L-01 |
| `max_entry_bid_gap_atr` | Écart d'entrée maximal | `execution-coordinateur` 0c | L-19 |
| `max_spread_price` | Plafonds de spread par symbole | `execution-coordinateur` 0c | L-18 |
| `risk_fraction_per_entry` | Budget B de la tentative | `execution-coordinateur` 3 | C11.6 |
| `account_max_initial_reserved_risk_fraction`, `account_max_positions`, `max_positions_per_canonical_symbol` | Réserves et places du compte | `execution-coordinateur` 1c | C11.10, L-17 |
| `max_margin_fraction_of_equity` | Plafond de marge (P-06) | `execution-coordinateur` 3 | C11.7 |
| `daily_equity_loss_limit_fraction`, `peak_equity_drawdown_halt_fraction`, `risk_day_timezone` | Gardes quotidienne (jour UTC) et globale | `execution-coordinateur` 1b | C11.13 |
| `simultaneous_strategy_priority` | Priorité des méthodes | `execution-coordinateur` 2b | C11.10 |
| `entry_signal_ttl_seconds`, `quote_max_age_seconds` | TTL et âge de cotation (P-04) | `execution-coordinateur` 0c | C11.2, L-18 |
| `request_ack_timeout_seconds`, `reconcile_fast_poll_seconds`, `reconcile_fast_window_seconds`, `reconcile_slow_poll_seconds` | Accusé d'ordre et rapprochement | `execution-coordinateur` 4 | C11.11 |
| `protective_update_max_attempts`, `protective_update_retry_delays_seconds`, `protective_update_deadline_seconds` | Correction du TP après remplissage | `execution-coordinateur` 4 | C11.11 |
| `exit_retry_interval_seconds` | Réessai de sortie sans cotation | `execution-coordinateur` 5a | C11.12 |
| `native_market_close_guard_seconds`, `max_position_wallclock_seconds`, `rollover_blackout_utc_start`, `rollover_blackout_utc_end` | Échéances de sortie et blackout | `execution-coordinateur` 0e ; `donnees-temps` 0b | L-14 |
| `news_before_seconds`, `news_after_seconds`, `news_calendar_max_age_seconds`, `news_forward_coverage_seconds` | Garde d'annonces | `controles-fondamentaux` 1b | C11.9 |
| `fundamental_mode` | Valeur exigée `EXTERNAL_REQUIRED` ; scénario neutre refusé hors contrôle technique | `noyau` 0c ; `points-entree` 2 | C11.8 |
| `fundamental_max_validity_seconds`, `fundamental_expected_heartbeat_seconds`, `fundamental_timestamp_future_tolerance_seconds` | Validité des permissions | `controles-fondamentaux` 1a, 2 | C11.8 |
| `allow_pyramiding`, `allow_averaging_down`, `allow_martingale`, `allow_trailing_stop`, `allow_break_even_move`, `allow_partial_take_profit`, `mandatory_retest`, `new_indicator_vote_score`, `dxy_enabled`, `mfi_enabled`, `bollinger_enabled`, `fibonacci_enabled`, `daily_pivots_enabled`, `extra_roc_momentum_enabled`, `fresh_ma_cross_enabled` | Options exclues : aucune n'est implémentée ; une valeur vraie est refusée au démarrage | `noyau` 0c | Test « option désactivée activée » |
| `trade_count_retention_target`, `combined_mean_fills_per_trading_day_target` | Cibles de rétention et de fréquence rapportées, jamais des quotas | `journal-rejeu` 1c, 3 | Rapport C10 |

### 2.2 Bloc `london` (20 clés)

| Clés | Rôle dans le robot | Unité consommatrice | Vérification |
|---|---|---|---|
| `strategy_id` | Identifiant de la méthode (clé d'intention, priorité, journal) | `moteur-london` 0a ; `execution-coordinateur` 2b | C11.10 |
| `range_start_local`, `range_end_local_exclusive`, `expected_range_m15_bars` | Ouvertures du range et contrôle de cohérence | `donnees-temps` 0b ; `moteur-london` 0a, 1a | S02.6-1 |
| `range_h1_atr_frozen_local` | Instant de gel de A_H1 | `moteur-london` 1b | L-07 |
| `range_min_h1_atr`, `range_max_h1_atr` | Admissibilité de la largeur | `moteur-london` 2 | L-06 |
| `session_start_local`, `entry_end_local_exclusive` | Fenêtre des bougies de signal | `donnees-temps` 0b ; `moteur-london` 2 | S02.6-3 |
| `force_exit_local` | Sortie forcée | `execution-coordinateur` 0e | L-14 |
| `breakout_buffer_atr`, `signal_body_fraction_min`, `signal_close_location_min` | Bougie de cassure | `moteur-london` 1c | L-10 |
| `boundary_stop_inside_atr` | Composante du stop à l'intérieur du range | `moteur-london` 1d | L-11 |
| `fresh_close_cross_required`, `h1_directional_filter_enabled`, `exit_on_close_back_inside_range_enabled` | Options exclues : faux exigé | `moteur-london` 0a | Configuration altérée refusée |
| `max_filled_entries_per_symbol_local_day`, `max_filled_entries_per_direction_local_day` | Quotas journaliers | `moteur-london` 1e | L-12 |
| `take_profit_gross_price_r` | Multiple d'objectif k | `moteur-london` 1d ; `execution-coordinateur` 0d | L-01 |

## 3. Paramètres de l'intégration IA (70 clés)

| Clés | Rôle | Unité consommatrice | Vérification |
|---|---|---|---|
| `integration_version`, `document_version` | Identité de l'intégration ; empreinte de configuration comparée par le lecteur de snapshot | `noyau` 0c ; `contexte-ia` 1 | Snapshot d'une autre configuration refusé |
| `default_evaluation_mode` | `PAPER_AB` par défaut quand le service est actif | `points-entree` 0 | Démarrage en mode IA |
| `live_veto_requires_financial_validation` | Veto réel neutralisé sans A13 | `contexte-ia` 3 | A14-8 |
| `local_inference_allowed`, `synchronous_llm_on_entry_allowed` | Faux exigé ; imports réseau interdits dans le cœur | `noyau` 0c ; cartes MCL | A14-1, A14-15 |
| `shared_service_across_strategies` | Service unique pour les deux méthodes, coûts alloués une fois | `service-ia` 3 ; `journal-rejeu` 3 | A14-11 |
| `snapshot_heartbeat_seconds`, `snapshot_write_retry_seconds` | Écriture du snapshot par le service | `service-ia` 2c | A14-16 |
| `ea_snapshot_poll_seconds` | Lecture par le robot | `points-entree` 1a ; `infrastructure` 0e | A14-1 |
| `snapshot_max_age_seconds`, `snapshot_max_bytes`, `snapshot_minimum_accepted_sequence` | Acceptation du snapshot | `contexte-ia` 1 | A14-16 |
| `providers` | Liste autorisée : identifiants vérifiés par le lecteur, routes du service | `contexte-ia` 1 ; `service-ia` 1d, 2b | A14-15 |
| `feeds` | Flux officiels et devises | `service-ia` 2a | Contrat RSS |
| `monthly_total_budget_usd`, `monthly_paid_api_subcap_usd`, `paid_fallback_enabled_by_default`, `paid_price_review_max_age_days` | Budget et route payante | `service-ia` 1c, 2b | A14-13, A14-14 |
| `max_api_attempts_per_utc_day`, `max_event_classification_attempts_per_day`, `max_reserved_tokens_per_utc_day`, `max_input_tokens_upper_bound`, `max_output_tokens_including_reasoning`, `input_count_fallback_utf8_overhead_tokens` | Plafonds et bornes de tokens | `service-ia` 0b, 1c, 2b | A14-14 |
| `provider_min_request_spacing_seconds`, `provider_quota_safety_fraction`, `http_inference_timeout_seconds`, `job_deadline_seconds`, `max_provider_attempts_per_job`, `provider_fallback_delays_seconds`, `max_llm_concurrent_jobs` | Routeur et travailleur unique | `service-ia` 2b, 4 | A14-12 |
| `max_response_bytes`, `evidence_quote_max_characters`, `evidence_quote_min_characters_for_veto` | Validation des sorties | `service-ia` 0c, 1b | A14-4 |
| `rss_poll_seconds`, `rss_http_timeout_seconds`, `rss_failure_backoff_seconds`, `rss_max_download_bytes`, `max_document_plaintext_bytes` | Collecte RSS | `service-ia` 2a, 1a | Contrat RSS |
| `unscheduled_policy_veto_seconds_from_publication`, `calendar_same_issuer_match_seconds`, `calendar_matching_event_kind` | Construction du veto et appariement au calendrier | `service-ia` 1b | A14-5 à A14-7 |
| `pre_session_brief_local`, `daily_journal_local`, `weekly_review_local`, `brief_news_lookback_seconds` | Planification | `service-ia` 3 | Planificateur |
| `weekly_golden_cases`, `golden_drift_suspend_if_changed_cases_greater_than` | Dérive : suspension des vetos du fournisseur | `service-ia` 3 | Scénario de dérive |
| `advisory_max_observations`, `advisory_max_uncertainties`, `advisory_max_hypotheses`, `advisory_max_text_characters`, `advisory_max_evidence_ids_per_observation` | Sorties informatives | `service-ia` 0c | Oracle `parse_advisory_output` |
| `new_research_hypotheses_max_per_month` | Plafond des hypothèses de recherche | `service-ia` 3 ; processus du document 05, §1 | Revue mensuelle |
| `model_classification_test_items`, `model_min_material_event_precision`, `model_min_material_event_recall`, `free_vs_paid_max_precision_gap`, `free_vs_paid_max_recall_gap` | Qualification sémantique | Sous-étape 13.6 ; `journal-rejeu` 3 | Rapport A13 |
| `financial_min_market_days`, `financial_min_closed_trades_per_strategy`, `financial_min_affected_baseline_trades`, `financial_min_affected_market_days`, `financial_min_retention` | Critères financiers A13 | `journal-rejeu` 0b, 3 ; sous-étape 13.7 | Rapport A13 |
| `bootstrap_replications`, `bootstrap_block_market_days`, `bootstrap_seed`, `bootstrap_lower_percentile`, `bootstrap_upper_percentile` | Bootstrap de C10 et A13 | `journal-rejeu` 1d | Cas calculé à la main |

## 4. Exigences de la spécification, une par ligne

| Id | Exigence (résumé fidèle) | Où dans le plan | Vérification |
|---|---|---|---|
| C01-1 | Lire la spécification n'autorise ni compte, ni identifiants, ni ordre réel | Plan directeur §6 ; `points-entree` 2 (mode réel verrouillé) | Refus du mode réel sans décision |
| C01-2 | Conception figée, rentabilité non validée, aucune valeur à optimiser | Plan directeur §0 et §6 ; perturbations C10 non sélectives (`journal-rejeu` 2) | Rapport C10 |
| C01-3 | Aucun élément exclu réactivé ; toute modification crée une version | `noyau` 0c ; `moteur-london` 0a | Options exclues refusées |
| C01-4 | Compte standard USD de 100 USD, levier 100 ; risque de 0,5 % ; jamais de volume fixe | `noyau` 1b ; `execution-coordinateur` 3 ; sous-étape 13.1 | C11.6 |
| C02-1 | JSON normatif ; contradiction = défaut signalé | Plan directeur §0 et §4 | Arbitrages P-01 à P-12 |
| C02-2 | Caractéristiques du courtier = données d'environnement ; aucun champ manquant ne vaut zéro | `noyau` 1b ; `infrastructure` 2a | Profil incomplet refusé |
| C03.1 | UTC à la milliseconde, ordre stable ; heures fournisseur et réception ; aucune donnée avant sa disponibilité | `noyau` 0a, 1a ; document 01, principe 3 et §9.2 | C11.1 |
| C03.2 | Intervalles M15 et H1 alignés sur l'époque UTC, OHLC Bid, tick de frontière dans la bougie suivante | `donnees-temps` 1a | C11.3 |
| C03.3 | `Europe/London` IANA, jamais un décalage unique ; jours Londres pour la stratégie, jour UTC pour la perte (Douala UTC+1 : affichage seulement) | `donnees-temps` 0b ; `execution-coordinateur` 1b | C11.4 |
| C03.4 | Seules les bougies closes ; H1 accessible à sa clôture ; aucune H1 partielle dans une M15 antérieure ; H1 de 07:00 admissible si reçue | `donnees-temps` 3 ; `moteur-london` 1b | C11.1, L-07 |
| C03.5 | Validité : couverture et au moins un Bid ; aucun remplissage synthétique ; fermetures et interruptions distinctes | `donnees-temps` 1c, 2a ; P-01, P-02 | L-08 |
| C03.6 | Trou inexpliqué : entrées bloquées, ranges effacés jusqu'à récupération et recalcul ; protections actives ; aucune suppression opportuniste | `donnees-temps` 2a, 3 ; `moteur-london` 2 ; P-03 | L-16 |
| C03.7 | Préchargement d'au moins 1 000 M15 et 300 H1, empreinte, persistance, reprise ; préchargement différent journalisé | `donnees-temps` 2b ; P-10 | Reprise après export et import |
| C03.8 | Formule EMA | Non utilisée par London ; relève du robot EMA (aucune EMA construite maintenant) | — |
| C03.9 | Formule RSI | Non utilisée par London ; relève du robot EMA | — |
| C03.10 | TR et ATR14 Wilder ; premier TR = H − L ; sauts après fermeture comptés | `donnees-temps` 1b | Oracle `wilder`, `add_indicators` |
| C03.11 | A_t = ATR M15 de t − 1, strictement positif ; ATR H1 figé à l'heure de la méthode | `donnees-temps` 1b ; `moteur-london` 1b, 1c | L-07, L-10 |
| C03.12 | Flottants 64 bits, ordre des récurrences, inégalités exactes, arrondis décimaux sur la grille avec contrôle d'erreur | Document 01, §6 ; `noyau` 0b ; `execution-coordinateur` 0d | Comparaison à `rounded_levels` |
| C03-13 | Indicateurs natifs non utilisés sans comparaison ; formules codées explicitement | `donnees-temps` 1b (récurrences propres) | Oracles |
| C03-14 | Aucun flux Mid, Last, CFD ou autre symbole à la place du Bid ; volume inutile | `donnees-temps` 1a ; D-14 | Données validées en 13.3 |
| C04-1 | Univers EURUSD, GBPUSD, XAUUSD ; priorité EURUSD puis GBPUSD ; or évalué à part | `universe_priority` ; registre de déploiement | Sous-étape 13.1 |
| C04-2 | Lire et enregistrer avant démarrage, recontrôler avant ordre toutes les caractéristiques listées (compte, symbole, contrat, tick, volumes, distances, gel, modes, frais, marge, stop-out, calendrier de cotation, pauses, fermetures) | `noyau` 1b ; `infrastructure` 2a, 3 ; D-12 (séances, fermetures exceptionnelles) | Contrat MT5, 13.1 |
| C04-3 | Fonctions de calcul du courtier ; marge isolée de `OrderCalcMargin` complétée ; règle inconnue → `ENVIRONMENT_NOT_READY` ; levier publicitaire ignoré | `infrastructure` 2c ; `execution-coordinateur` 3 ; sonde S-07 | C11.7 |
| C04-4 | Compte standard ≠ contrat standard ; disponibilité des micro non établie | Sous-étape 13.1 | Qualification |
| C04-5 | Un seul symbole par sous-jacent : plus petite exposition minimale vérifiée, puis coût aller-retour, puis ordre lexical ; choix conservé ; aucune bascule | `points-entree` 1c ; registre de déploiement | Sous-étape 13.1 |
| C04-6 | Jamais d'indice synthétique ; jamais d'arrondi du volume à la hausse | `execution-coordinateur` 3 ; registre | C11.6 |
| C05-1 | Fondamental produit ailleurs ; aucun substitut DXY ou macro | `controles-fondamentaux` (consommation seule) | — |
| C05-2 | Schéma `fundamental-permission-v1`, directions et états de risque | `controles-fondamentaux` 1a ; D-11 | C11.8 |
| C05-3 | Validité ≤ 900 s ; heartbeat 60 s, minute manquée journalisée ; blocage à l'expiration ; dernier message utilisable jusqu'à expiration | `controles-fondamentaux` 2 | C11.8 |
| C05-4 | Ordre des heures, durée positive, séquence strictement croissante, aucun horodatage futur ; réception ≥ `known_at`, les deux conservées | `controles-fondamentaux` 1a, 2 ; D-11 | C11.8 |
| C05-5 | Direction incompatible, `NO_NEW`, message absent, périmé, invalide ou interruption → blocage ; changement de direction sans clôture ; `FLATTEN` → clôture puis blocage | `controles-fondamentaux` 3 ; `execution-coordinateur` 5a | C11.8 |
| C05-6 | Contrôle au signal et juste avant l'ordre ; aucun renvoi d'un signal refusé | `execution-coordinateur` 6 ; `moteur-london` 2 | C11.8 |
| C05-7 | `TECHNICAL_CONTROL_NEUTRAL` seulement pour un contrôle technique isolé, nommé | `execution-coordinateur` 0b ; `points-entree` 2 | Refus en démo et en réel |
| C05-8 | Annonces HIGH d'un fournisseur et d'une table d'importance versionnés ; devises par symbole ; blocage propre à l'or par `risk_state` | `controles-fondamentaux` 1b ; D-12 | C11.9 |
| C05-9 | Aucune entrée dans `[N − 900 s, N + 900 s)` ; clôture des positions concernées à N − 900 s | `controles-fondamentaux` 1b ; `execution-coordinateur` 5a | C11.9, L-14 |
| C05-10 | Calendrier actualisé depuis ≤ 86 400 s et couvrant 172 800 s, sinon aucune entrée, sans liquidation | `controles-fondamentaux` 1b | C11.9 |
| C05-11 | Annonce apprise tardivement dans sa fenêtre : blocage et clôture immédiats | `controles-fondamentaux` 1b ; D-12 (cadence) | C11.9 |
| C05-12 | Versions de calendrier et heures de connaissance conservées, historique jamais réécrit | `controles-fondamentaux` 1b ; document 01, §2.2 | C11.9 |
| C05-13 | Un modèle fondamental entraîné sur le futur invalide le test combiné | Sous-étape 13.3 (validation des permissions historiques) | Rapport de données |
| C06-1 | Décision à la clôture d'une M15 admissible ; aucun LLM synchrone ; seul le snapshot en mémoire | Document 01, principe 2 ; `contexte-ia` | A14-1 |
| C06-2 | Expiration du signal à T + 5 s, borne exclue | `execution-coordinateur` 0c | C11.2 |
| C06-3 | Cotation valide, non croisée, âgée d'au plus 2 s ; attente d'une amélioration pendant le seul TTL | `execution-coordinateur` 0c ; P-04, P-05 | L-18 |
| C06-4 | Plafonds de spread absolus, S = Ask − Bid, aucun ratio spread/ATR | `execution-coordinateur` 0c | L-18 |
| C06-5 | Écart d'entrée ≤ 0,25 A, sinon attente ; recontrôle à chaque tentative ; refus permanents consommant le signal | `execution-coordinateur` 0c, 6 ; P-08 | L-19 |
| C06-6 | B_SL sur l'échelle Bid ; 0 < distance ≤ 2,50 A ; plancher 0,80 A distance minimale | `moteur-london` 1d | L-11 |
| C06-7 | Conversion achat et vente, D > 0, TP à k × D avec arrondis ; stop fixe ; TP recalculé sur le prix réel | `execution-coordinateur` 0d, 4 | L-01 |
| C06-8 | SL/TP déclenchés sur Bid pour un achat et Ask pour une vente, ou équivalence prouvée | Sonde S-03 ; `journal-rejeu` 1b | Contrat MT5 |
| C06-9 | Ni break-even, ni trailing, ni sortie partielle, ni sortie RSI, ni inversion ; k sur distance brute | Options exclues (`noyau` 0c) ; aucune unité de gestion | Configuration altérée refusée |
| C06-10 | Contrainte native de SL/TP invalidante → refus avant ordre, stop jamais déplacé ; protections attachables à l'entrée | `execution-coordinateur` 0d ; sonde S-02 | Contrat MT5 |
| C07-1 | Instantané des fonds propres et des réserves ; B gelé par tentative | `execution-coordinateur` 3 | C11.6 |
| C07-2 | g = max(`tick_size`, 0,05 A) par jambe ; réserve et tolérance, pas une garantie | `execution-coordinateur` 2a ; `infrastructure` 2d | L-01 |
| C07-3 | Risque all-in : entrée et sortie pessimistes, profit du courtier, frais | `execution-coordinateur` 2a | C11.5 |
| C07-4 | Spread jamais ajouté deux fois ; commission nulle seulement confirmée ; frais minimaux non linéaires | `execution-coordinateur` 2a ; `noyau` 1b | C11.7 |
| C07-5 | Plus grand volume de la grille sous les cinq contraintes simultanées | `execution-coordinateur` 3 | C11.6, C11.7 |
| C07-6 | Arrondi vers le bas ; `MIN_VOLUME_OR_RISK_REJECT` ; ni lot forcé, ni stop rapproché, ni martingale | `execution-coordinateur` 3 | C11.6 |
| C07-7 | Réserve attachée jusqu'à la clôture ; profits flottants sans libération ; recalcul avant toute autre entrée | `execution-coordinateur` 1c | C11.10 |
| C07-8 | Positions externes dans fonds propres et marge ; blocage des entrées faute de coordination ; jamais de clôture d'un autre propriétaire | `execution-coordinateur` 3, 5b ; document 01, §8 | C11.7, C11.11 |
| C07-9 | Après remplissage : risque recalculé avec le prix réel et la seule réserve de sortie ; réduction ou clôture | `execution-coordinateur` 4 | C11.11 |
| C07-10 | Garde quotidienne à 00:00 UTC, seuil de 98 %, clôture, annulation et blocage jusqu'au jour UTC suivant | `execution-coordinateur` 1b, 5a ; P-12 | C11.13 |
| C07-11 | Garde globale à 90 % du pic, arrêt persistant, levée par décision tracée seulement | `execution-coordinateur` 1b ; `points-entree` 1a | C11.13 |
| C07-12 | Aucun apport ni retrait en simulation ; flux réels identifiés et neutralisés | `journal-rejeu` 1b ; `execution-coordinateur` 1b | Rapport |
| C08-1 | Méthodes indépendantes ; priorités ; réévaluation après chaque réservation ; ni score ni couverture opposée | `execution-coordinateur` 2b ; D-18 | C11.10 |
| C08-2 | Clé d'intention persistante ; intention et réservation enregistrées avant envoi ; jamais de seconde entrée | `execution-coordinateur` 1c, 4 ; document 01, §7 | C11.11 |
| C08-3 | Ordre des traitements en cinq étapes | `orchestration` 2 ; `execution-coordinateur` 6 ; document 01, §4.3 | Test d'ordre combiné |
| C08-4 | Pas de détection pendant une position de la méthode ; état réinitialisé à la sortie ; refus d'une autre méthode journalisés | `moteur-london` 2 ; `noyau` 2 | L-13 |
| C08-5 | Accusé de 5 s ; réponse inconnue = verrou et rapprochement 1 s puis 5 s ; aucune retransmission aveugle ; alerte après 30 s | `execution-coordinateur` 4 | C11.11 |
| C08-6 | Partiel : reliquat annulé, entrée comptée au premier volume, jamais complétée | `execution-coordinateur` 4 ; `moteur-london` 1e | S02.6-7 |
| C08-7 | Ajustement du TP sans retirer le SL ; trois tentatives et échéance ; SL absent → clôture d'urgence ; TP non rétabli ou dépassé → clôture | `execution-coordinateur` 4 | C11.11 |
| C08-8 | Première échéance de sortie parmi les six listées | `execution-coordinateur` 0e, 5a | L-14 |
| C08-9 | Heures de sortie = instants d'envoi ; sans cotation, demande prioritaire et réessai chaque seconde ; aucune entrée rétroactive | `execution-coordinateur` 5a | C11.12 |
| C08-10 | Redémarrage : journal, rapprochement, compteurs et risques restaurés avant toute décision ; verrou de propriété en netting | `execution-coordinateur` 5b ; `points-entree` 1a ; document 01, §7.3 | C11.11, C11.13 |
| C09-1 | Enregistrer à chaque clôture et pour chaque intention les champs listés | `noyau` 2 ; `execution-coordinateur` 6 ; `orchestration` 2 | Enregistrements complets |
| C09-2 | Motifs minimaux (20 codes) | Document 01, §9.3 | Contrôle mécanique |
| C09-3 | Mesurer séparément configurations, signaux négociables, refus, entrées remplies, positions closes, résultats nets, drawdown de fonds propres | `journal-rejeu` 1c, 3 | Rapport C10 |
| C09-4 | Fréquence d'au moins une entrée par jour de marché pour EURUSD et GBPUSD des deux robots, rétention de 80 % ; jamais un quota ; jours à zéro inclus | `journal-rejeu` 1c ; `combined_mean_fills_per_trading_day_target`, `trade_count_retention_target` | Rapport C10 |
| C10-1 | Ticks Bid/Ask exacts EURUSD, GBPUSD, XAUUSD du 02/12/2019 au 03/11/2026 | Sous-étape 13.3 ; D-14 ; procédure H-09 ; artefact `donnees-historiques` (sondes S-09, S-10) | Données validées |
| C10-2 | Blocs de dates fixés, test réservé non consulté, période explorée en diagnostic, démonstration prospective | `journal-rejeu` 0b, 2 (verrou) ; D-16 | Verrou du test réservé |
| C10-3 | Exiger ticks ordonnés, contrats et coûts datés, calendriers avec heures de connaissance, permissions horodatées, sinon contrôle technique neutre seulement | Sous-étape 13.3 ; `journal-rejeu` 2 | Rapport de données |
| C10-4 | M1 pour un premier diagnostic seulement ; aucun tick généré en silence ; ordre intrabougie, spread variable et TTL reproduits | `journal-rejeu` 1a, 1b | C11.12 |
| C10-5 | Chaque robot sur son compte de 100 USD, puis les deux sur un compte unique ; jamais de courbes additionnées | `journal-rejeu` 2 (London seul maintenant, combiné avec le robot EMA) | Rapport C10 |
| C10-6 | Expériences par bloc à 100 USD avec préchargement sur leur passé ; rejeu continu 2020–2026 avec arrêts persistants ; rapports séparés | `journal-rejeu` 2, 3 | Rapport C10 |
| C10-7 | Scénario de référence : spreads historiques, commissions réelles, 250 ms, un tick adverse, limites au niveau ou mieux, protections natives d'abord, gaps subis | `journal-rejeu` 1b ; P-11 | Tests du simulateur |
| C10-8 | Stress : spread × 1,25, 1 000 ms, deux ticks adverses ; plafonds et TTL actifs ; TP limite non pénalisé ; comparaison aux journaux de démonstration | `journal-rejeu` 1b, 3 ; sous-étape 13.7 | Tests du simulateur |
| C10-9 | Ne jamais soustraire encore g du P&L | `journal-rejeu` 1b, 1c | Test de métrique |
| C10-10 | Comparer V3 à V1 sur le même moteur, compte, coûts et permissions ; référence technique neutre ; effet propre du fondamental et fréquences brutes | `moteur-london-v1` ; `journal-rejeu` 2, 3 | Sous-étape 13.5 |
| C10-11 | Rétention N_V3/N_V1 ; référence nulle N/A ; moins de 50 trades : trop faible ; ratio de configurations à part | `journal-rejeu` 1c | Test de métrique |
| C10-12 | Critères a priori : effectifs, espérance, profit factor, drawdown, rétention et fréquence, bootstrap exact, six perturbations sans sélection, pertes et arrêts rapportés | `journal-rejeu` 1c, 1d, 2, 3 | Rapport C10 |
| C10-13 | Résultat insuffisant = « non validé », sans retouche ; compte incompatible déclaré | `journal-rejeu` 3 ; sous-étapes 13.1 et 13.5 | Rapport C10 |
| C11 | Quatorze cas d'acceptation sur le robot réel | Document 03, §5.1 | Contrôle mécanique |
| S02-0 | Clôture hors du range pré-Londres ; indépendance des EMA et du RSI ; stop local plutôt qu'extrémité opposée ; aucun retest ni croisement récent | `moteur-london` 1c, 1d | S02.6 |
| S02.1 | Jours lundi à vendredi ; 20 M15 de `[02:00, 07:00)` toutes valides ; H, L, W > 0 ; A_H1 de la dernière H1 close au plus tard à 07:00, positive, 300 H1, ≤ 1 h ; disponibilité réelle et refus des signaux antérieurs ; aucune mise à jour après le gel ; largeur admissible bornes incluses ; aucun vote directionnel H1 ; range invalide → aucune entrée du jour | `donnees-temps` 0b ; `moteur-london` 1a, 1b, 2 ; P-09 | S02.6-1, S02.6-2 |
| S02.2 | Bougie ouverte ≥ 08:00 et close < 11:00 ; sortie 12:00 ou 7 200 s ; 07:00–08:00 sans effet ; prix déjà hors du range admis ; refus sans remplissage sans consommation ; jamais d'ordre rétroactif | `donnees-temps` 0b ; `moteur-london` 2 ; `execution-coordinateur` 0e | S02.6-3, S02.6-4 |
| S02.3 | A, b, R > 0, TR ≤ 2,50 A, corps ≥ 0,40 ; conditions achat et vente ; égalité au niveau plus buffer non admise ; ni ordre stop en attente, ni retest, ni score | `moteur-london` 1c | S02.6-5 |
| S02.4 | Guard ; B_SL à trois composantes ; refus au-delà de 2,50 A ; objectif 2 D ; quotas ; seconde direction après clôture et nouveau signal ; quotas au premier remplissage, persistés, remis à zéro au jour Londres ; pas de sortie sur retour dans le range | `moteur-london` 1d, 1e, 2 ; `execution-coordinateur` 0d | S02.6-6 à S02.6-8 |
| S02.5 | Exemple chiffré | Scénario L-01 | Test L-01 |
| S02.6 | Acceptation spécifique | Document 03, §5.2 | Contrôle mécanique |
| A01-1 | API distantes seulement, aucune inférence locale | `service-ia` ; cartes (imports interdits) | A14-15 |
| A01-2 | Document de référence examiné, pas une autorité | Plan directeur §0 | — |
| A01-3 | Trois usages et un veto étroit évalué en A/B, sans promesse de rentabilité | `service-ia` ; `orchestration` 1 ; sous-étape 13.7 | A14-17 |
| A01-4 | Le LLM ne choisit ni entrée, ni sens, ni stop, ni objectif, ni volume, ni durée, et ne produit aucune permission | `contexte-ia` 3 (`BLOCK` ou `NEUTRAL`) | A14-9 |
| A01-5 | Mode initial `PAPER_AB` : bras de référence et bras IA à 100 USD chacun, coordinateur partagé par les méthodes de chaque bras | `orchestration` 1, 2 ; document 01, §3 | A14-17 |
| A01-6 | Briefing et journal possibles dès la mise en place ; veto réel après A13 | `service-ia` 3 ; `contexte-ia` 3 | A14-8 |
| A02-1 | Bloc IA identique au fichier exporté | `noyau` 0c (empreinte de la configuration IA) | Contrôle de conservation |
| A02-2 | Ordre des fournisseurs, route payante désactivée, aucune facturation automatique | `service-ia` 1c, 2b | A14-13 |
| A02-3 | Variables d'environnement des clés, `XPBOTS_PAID_FALLBACK_ENABLED`, `XPBOTS_COMMON_FILES_DIR` ; secrets jamais affichés | `service-ia` 4 ; document 01, §2 et §11 | Garde des secrets |
| A02-4 | Pas de vote de modèles ; secours qualifié à part ; identifiants, versions et empreintes conservés | `service-ia` 2b ; journal du service | Rapport A13 |
| A03-1 | Chaîne RSS et calendrier → service → API → validateur et cache → snapshot → lecture en mémoire | Document 01, §2 ; `contexte-ia` ; `orchestration` | A14-2 |
| A03-2 | Aucun appel ni attente entre signal et entrée ; snapshot rechargé chaque seconde ; copie mémoire consultée à la décision **et juste avant l'ordre** ; réponse tardive sans effet | Document 01, principe 2 et §4.3 ; `execution-coordinateur` 6 ; `points-entree` 1a | A14-1, A14-2 |
| A03-3 | Heartbeat indépendant, travailleur d'inférence unique, file bornée, collecteur séparé | `service-ia` 4 | Test du service |
| A04-1 | Prix et statistiques calculés par le moteur ; dossier du classificateur sans prix, portefeuille ni signal | `service-ia` 1d (contenu du dossier) | A14-15 |
| A04-2 | Calendrier natif MT5 converti depuis l'heure du serveur ; exports versionnés rejoués ; flux Fed, BCE, BoE | D-12 ; document 01, §2.2 ; `service-ia` 2a | Contrat de l'export |
| A04-3 | BoE à tester, jamais contourné | `service-ia` 2a | Contrat RSS |
| A04-4 | Scrutation 60 s, requêtes conditionnelles, délais, plafond, reprises, redirections officielles bornées, aucun fichier joint | `service-ia` 2a | Tests du collecteur |
| A04-5 | Champs de chaque texte ; date absente ou future interdit le veto | `service-ia` 1a | Tests de normalisation |
| A04-6 | Dédoublonnage ; première heure de connaissance conservée ; republication sans renouvellement | `service-ia` 1a | Tests de normalisation |
| A04-7 | Briefing sur les douze dernières heures par SQLite FTS5 ; aucune base vectorielle | `service-ia` 3, 1c | Test du planificateur |
| A04-8 | Couverture partielle déclarée, jamais un « marché sûr » | `service-ia` ; `journal-rejeu` 3 | Rapport |
| A05-1 | Schéma, prompt exact, un texte par appel | `service-ia` 0c, 1d ; prompts exportés | A14-4 |
| A05-2 | Règles du validateur (objet strict, enums, `item_id`, citation exacte, longueurs) | `service-ia` 0c | Oracle `parse_model_output` |
| A05-3 | Réponse inutilisable sans veto ; aucune réparation par un second modèle | `service-ia` 0c, 2b | A14-4 |
| A05-4 | Textes non fiables, aucun outil, instructions séparées du dossier | `service-ia` 1d | A14-15 |
| A06 | Six conditions du veto, période `[réception, publication + 900 s)`, correspondance des devises, effet limité au refus d'entrées, ton informatif seulement | `service-ia` 1b ; `contexte-ia` 3 | A14-5 à A14-7 |
| A07 | Insertion London après cassure et stop, avant réservation ; refus de la seule bougie ; aucun rattrapage ; 11:00 exclu | `execution-coordinateur` 6 ; `moteur-london` 2 | A14-10, L-15 |
| A08-1 | HTTPS, aucune donnée de compte, clés dans l'environnement du service | `service-ia` 1d | Garde des secrets |
| A08-2 | Gabarits de requêtes des trois fournisseurs | `service-ia` 1d | Tests de requêtes |
| A08-3 | Lecture des réponses propre à chaque fournisseur | `service-ia` 1d | Tests de réponses |
| A08-4 | Usage brut conservé ; métrique absente = coût inconnu | `service-ia` 1c, 1d | A14-13 |
| A08-5 | Une inférence à la fois ; délais, échéance, espacement ; jamais d'appel en boucle | `service-ia` 2b, 4 | A14-12 |
| A08-6 | Traitement des codes 401, 403, 429, 5xx ; réservation conservée pour un résultat inconnu ; réponse tardive archivée | `service-ia` 2b | Tests du routeur |
| A08-7 | Panne générale : aucune inférence locale, extension neutre, veto validé conservé, C05 bloquant | `service-ia` 2b ; `contexte-ia` 3 | A14-8 |
| A09-1 | Budget de 15 USD par mois, sous-plafond payant de 3 USD, partagé | `service-ia` 1c | A14-14 |
| A09-2 | 24 tentatives par jour UTC dont 18 de classification, 150 000 tokens, 4 096 en entrée, 2 048 en sortie | `service-ia` 0b, 1c, 2b | A14-14 |
| A09-3 | Comptage complet ; borne de secours UTF-8 + 512 ; raccourcir sans perdre une négation | `service-ia` 0b | Tests de borne |
| A09-4 | Débit réservé ≤ 80 % du quota effectif | `service-ia` 2b | Tests du routeur |
| A09-5 | Plan de travail Londres (07:45, 16:15, vendredi 16:45), priorités, travaux périmés annulés, pas de rafale au redémarrage | `service-ia` 3 | Tests du planificateur |
| A09-6 | Transaction exclusive avant appel payant, réservation du coût maximal, refus au-delà des plafonds, décimal, rapprochement | `service-ia` 1c | A14-12 |
| A09-7 | Profil de prix ≤ 7 jours ; nouveau tarif = nouvelle borne ; dépassement → route désactivée ; liste autorisée stricte | `service-ia` 1c, 2b | A14-15 |
| A09-8 | Recharge automatique désactivée, projet dédié, frais de trading séparés | `service-ia` (procédure) ; `journal-rejeu` 3 | Checklist 13.7 |
| A10-1 | Service unique, tables SQLite minimales | `service-ia` 1c | Tests du stockage |
| A10-2 | Chemin MT5 du snapshot par le dossier commun réel | `infrastructure` 0e ; `service-ia` 2c | Contrat IPC |
| A10-3 | Écriture atomique avec nouvelles tentatives ; ancien snapshot conservé ; lecteur bref ; jamais de réponse brute | `service-ia` 2c ; `infrastructure` 0e | A14-16 |
| A10-4 | Format du snapshot : enveloppe, empreinte canonique, champs du payload, événements | `contexte-ia` 1 ; `service-ia` 2c | Oracle `make_snapshot` |
| A10-5 | Règles d'acceptation du lecteur, cache persistant, état conservé au redémarrage, ACL | `contexte-ia` 1, 2 ; document 01, §2 | A14-16 |
| A10-6 | Le modèle n'a accès ni au disque ni au budget ; identifiants ajoutés par le code | `service-ia` 1b, 1d | A14-15 |
| A10-7 | Pas de réinférence historique ; événements non expirés rechargés ; réserves restaurées | `service-ia` 4 ; `contexte-ia` 2 | A14-16 |
| A11-1 | Métriques A/B, refus, coûts et trous calculés par le code ; agrégat anonymisé pour l'IA | `journal-rejeu` 3 ; `service-ia` 3 | A14-18 |
| A11-2 | Prompts exacts, schéma informatif, bornes du validateur, journal séparé | `service-ia` 0c, 3 | Oracle `parse_advisory_output` |
| A11-3 | Rapport London par W/ATR_H1, heure de première cassure, sens, stop local, coût, nouveau signal après veto | `journal-rejeu` 3 ; document 05, §1.3 | Rapport A11 |
| A11-4 | Trois hypothèses par mois au plus, tickets versionnés, aucune modification automatique, jamais le test réservé | Document 05, §1 ; `journal-rejeu` 2 (verrou) | Revue mensuelle |
| A11-5 | Alertes opérationnelles déterministes affichées localement ; aucune messagerie par défaut | `points-entree` 1a ; `infrastructure` | Procédure d'exploitation |
| A12 | Effets exacts de chaque panne ; `NEUTRAL` n'est jamais `ALLOW` | `contexte-ia` 3 ; `execution-coordinateur` 0b, 6 | A14-8 |
| A13 | Contrats, sémantique, gratuit contre payant, PAPER_AB, collecte, critères financiers, incertitude, coût équitable, mémoire des modèles, dérive | Sous-étapes 13.6 et 13.7 ; `journal-rejeu` 1d, 2, 3 ; `service-ia` 3 (dérive) | Rapports A13 |
| A14 | Dix-huit cas d'acceptation IA | Document 03, §5.3 | Contrôle mécanique |
| A15 | Sources primaires de l'intégration | Contexte, non normatif pour le code | — |
| R | Références et limites de leur portée : aucune ne valide les seuils V3 ni leur rentabilité | Contexte, non normatif pour le code ; limite rappelée au plan directeur, §0 | — |

## 5. Consignes de la skill `expert-scalper-m15`, une par ligne

Verdicts : **aligné** (la règle V3 applique la consigne) ; **écart figé** (la règle V3 diffère et prévaut ; aucune
modification) ; **instrumenté** (la règle V3 ne l'applique pas, mais le robot mesure son effet dans le rapport
A11) ; **hors robot** (la consigne vise un trader humain).

| Id | Source de la skill | Consigne | Verdict | Traitement dans le plan |
|---|---|---|---|---|
| E-01 | Persona | Sélectivité ; « rester à plat » est une position | Aligné | Quotas S02.4 ; refus journalisés (`moteur-london` 1e, 2) |
| E-02 | Persona, workflow | Contexte de plus haute unité avant le déclencheur | Écart figé, instrumenté | Aucun filtre directionnel (`h1_directional_filter_enabled`) ; direction déléguée à C05 ; effet du fondamental mesuré (C10-10) |
| E-03 | Persona | Raisonner en scénarios et invalidations | Aligné | Le stop est l'invalidation, défini avant l'entrée (`moteur-london` 1d) |
| E-04 | Persona | Stop, taille et rapport gain/risque définis avant l'entrée | Aligné | `execution-coordinateur` 0d, 3 avant tout envoi |
| E-05 | Persona | Ne jamais inventer de cotation | Aligné | Aucun tick synthétique (C03.5, C10-4) ; sorties sans prix reconstruit (C11.12) |
| E-06 | Cadre par défaut | M15 d'exécution, H4 et H1 de contexte, D1 pour les niveaux | Écart figé | M15 et ATR H1 seulement ; aucun niveau D1 |
| E-07 | Cadre par défaut | Paires majeures, dont USDJPY | Écart figé | Univers figé `universe_priority` |
| E-08 | Cadre par défaut | Fenêtre Londres 08:00–11:00 heure de Paris | Écart figé, instrumenté | Fenêtre 08:00–11:00 Londres ; performance par heure de première cassure (A11-3) |
| E-09 | Cadre par défaut | Risque de 0,5 à 1 % par trade | Aligné | `risk_fraction_per_entry` |
| E-10 | Cadre par défaut | Gain/risque minimal 1:1,5, viser 1:2 | Aligné | Objectif 2 D brut ; R net réalisé rapporté (§7, correction 2) |
| E-11 | Cadre par défaut | Stop structurel validé par l'ATR M15, jamais un nombre fixe de pips | Aligné | Stop local à trois composantes en unités d'ATR (`moteur-london` 1d) |
| E-12 | Cadre par défaut | Cible au prochain niveau logique | Écart figé | Objectif 2 D fixe |
| E-13 | Cadre par défaut | Durée de 15 min à 2–3 h, sortie temporelle | Aligné | `max_position_wallclock_seconds` |
| E-14 | Cadre par défaut | À plat 15 à 30 min autour des annonces majeures | Aligné | Fenêtre HIGH ± `news_before_seconds` (`controles-fondamentaux` 1b) |
| E-15 | Workflow | Analyse descendante en six étapes et notation du setup | Écart figé | Étapes codifiées : conditions (spread, ATR, annonces), déclencheur, plan ; pas de biais HTF ni de note (score interdit par S02.3) |
| E-16 | Formats, conception de stratégie | Hypothèse d'avantage, conditions, règles non ambiguës, filtres, gestion de l'argent, indicateurs attendus, protocole de validation, règles codifiables, discrétion résiduelle signalée | Aligné | §6 (codifiabilité) ; indicateurs rapportés (§7, correction 2) ; protocole C10 en phase 13 |
| E-17 | Garde-fous | Rappel du risque, aucune promesse, pas de sur-trading, de revanche ni de martingale | Aligné | Plan directeur §0 ; document 05, §1.4 ; options exclues |
| E-18 | Setup 1 London Open Breakout | Range asiatique de largeur raisonnable en pips | Écart figé, instrumenté | Largeur normalisée par A_H1 ; rapport par tranche de W/A_H1 |
| E-19 | Setup 1 | Biais H4 aligné avec la cassure | Écart figé | Voir E-02 |
| E-20 | Setup 1 | Clôture M15 franche hors du range, par le corps et non la mèche ; volume tick | Aligné ; volume en écart figé | Corps ≥ `signal_body_fraction_min`, clôture ≥ `signal_close_location_min` ; volume inutile (C03) |
| E-21 | Setup 1 | Entrée au close ou sur retest | Aligné (close) | Entrée au marché après la clôture ; retest exclu (`mandatory_retest`) |
| E-22 | Setup 1 | Stop de l'autre côté de la borne cassée, avec marge | Aligné | Composante H_range − `boundary_stop_inside_atr` × A, marge en unités d'ATR |
| E-23 | Setup 1 | Objectif égal à la hauteur du range | Écart figé | 2 D |
| E-24 | Setup 1, setup 6, astuce 2 | La première cassure ment souvent ; préférer le piège puis la cassure opposée | Écart figé, instrumenté | Taux de retournement après première cassure (document 05, §1.3) ; éventuelle hypothèse de recherche versionnée |
| E-25 | Risque §1 | Diviser le risque par deux après deux pertes | Écart figé | Risque constant de 0,5 % |
| E-26 | Risque §1 | Perte journalière maximale de 2 à 3 %, hebdomadaire de 5 à 6 % | Aligné (jour) ; écart figé (semaine) | Garde quotidienne ; arrêt global à 10 % du pic |
| E-27 | Risque §1 | Taille de position par le risque et la valeur du pip | Aligné | Risque all-in par la fonction de profit du courtier, frais compris |
| E-28 | Risque §1 | Intégrer les coûts au calcul du gain | Aligné | Résultats nets ; spread compté une fois ; commissions réelles |
| E-29 | Risque §1 | Espérance positive sur au moins 100 trades | Aligné | Au moins 200 trades par méthode (C10-12) |
| E-30 | Risque §1 | Ni martingale, ni moyenne à la baisse, ni revanche | Aligné | `allow_martingale`, `allow_averaging_down` faux |
| E-31 | Risque §2 | Stop entre 1 et environ 2 ATR | Écart figé | Bornes `minimum_chart_stop_atr` et `maximum_chart_stop_atr` |
| E-32 | Risque §2 | Éloigner le stop des évidences et des chiffres ronds | Écart figé | Guard au-delà de la bougie ; aucun traitement des chiffres ronds |
| E-33 | Risque §2 | TP partiel à 1R, break-even, trailing | Écart figé | Options exclues |
| E-34 | Risque §2 | Sortie temporelle après 4 à 8 bougies | Aligné | 7 200 s, soit huit M15 |
| E-35 | Risque §2 | Ne jamais élargir un stop | Aligné | Stop fixe, jamais déplacé (C06-7, C06-10) |
| E-36 | Risque §3 | Grille de notation des setups | Écart figé | Score interdit |
| E-37 | Risque §4 | Liste de contrôle avant trade (fenêtre, annonces, clôture, stop, taille, spread) | Aligné | Pipeline d'admission du document 01, §4.3 |
| E-38 | Risque §5 | Indicateurs : taux de réussite, R moyen, profit factor, drawdown, espérance, par setup, session et paire | Aligné | `journal-rejeu` 1c, 3 (§7, correction 2) ; seuils de décision de C10 seulement |
| E-39 | Risque §6 | Compte à spread brut, exécution rapide, SL et TP attachés | Aligné (protections) ; instrumenté (latence) | SL et TP attachés (C06-10) ; latences d'accusé journalisées |
| E-40 | Risque §7 | Psychologie du trader | Hors robot | Robot automatique ; arrêts persistants sans intervention |
| E-41 | Risque §8 | Astuces : clôture M15 seule juge, spread comme indicateur, corrélations, lundi et vendredi, un marché d'abord, rejeu puis démo puis réel réduit | Aligné ou instrumenté ; écart figé pour le réel réduit | Décisions sur bougies closes ; plafonds de spread ; réserve totale bornée ; ventilation par jour ; EURUSD prioritaire ; protocole C10 ; risque réel inchangé |
| E-42 | Risque §9 | Drapeaux rouges (risque > 2 %, absence de stop, levier extrême) | Aligné | Aucun présent dans V3 |
| E-43 | Sessions §1–2 | Cascade multi-unités de temps, pas de « timeframe shopping » | Aligné | Unités de temps figées |
| E-44 | Sessions §3 | Zone de chasse Londres ; range asiatique de référence | Aligné (range) ; écart figé (horaire) | Range 02:00–07:00 Londres |
| E-45 | Sessions §3 | Jamais de position à cheval sur le rollover | Aligné | Blackout `rollover_blackout_utc_start` à `rollover_blackout_utc_end` |
| E-46 | Sessions §3 | Prudence le vendredi après-midi et les veilles de fériés | Instrumenté | Aucun filtre ; ventilation par jour |
| E-47 | Sessions §4 | Zone sans trade autour des publications majeures | Aligné | Table d'importance HIGH relue par l'humain (D-12) |
| E-48 | Sessions §4 | Un discours imprévu peut invalider le plan | Écart figé | A06 n'admet que les décisions monétaires imprévues, pas les discours |
| E-49 | Sessions §5 | Routine avant la séance | Aligné (information seule) | Briefing de 07:45 (A09), sans effet sur les décisions |
| E-50 | Analyse §1 | Structure de marché, BOS, CHoCH | Écart figé | Aucun filtre de structure |
| E-51 | Analyse §2 | Zones, chiffres ronds, extrêmes de session comme réservoirs de liquidité | Aligné (extrêmes du range) ; écart figé (chiffres ronds) | Range comme niveau de cassure |
| E-52 | Analyse §3 | Le close fait foi ; taille relative à l'ATR ; bougie de momentum pour les cassures | Aligné | Corps, position de clôture et TR en unités d'ATR (`moteur-london` 1c) |
| E-53 | Analyse §5 | ATR M15 non négociable ; filtre des marchés morts | Aligné ; filtre en écart figé | ATR pour buffers, stops et TR ; borne basse de W/A_H1 comme seul filtre de faible amplitude |
| E-54 | Analyse §5 | Pas d'empilement d'indicateurs ni d'optimisation des périodes | Aligné | Aucun indicateur ajouté ; aucune optimisation |
| E-55 | Analyse §6 | Fibonacci, pivots, VWAP | Écart figé | `fibonacci_enabled`, `daily_pivots_enabled` faux ; VWAP absent |
| E-56 | Analyse §7 | Volume tick pour valider une cassure | Écart figé | Volume inutile (C03) |
| E-57 | Analyse §8 | Concepts SMC subjectifs, difficiles à coder pour un robot | Aligné | Aucun concept SMC dans V3 |
| E-58 | Analyse §9 | Grille de confluence | Écart figé | Score interdit (S02.3) |
| E-59 | Setups, préambule | Tout setup suppose séance active, spread normal, aucune annonce majeure à moins de 30 min et ATR M15 sain | Aligné ; écart figé pour la durée | Fenêtre de séance, plafonds de spread, garde d'annonces ± `news_before_seconds`, A_t strictement positif |
| E-60 | Setups, préambule | Un stop structurel inférieur à 1 ATR est élargi, ou le trade est abandonné | Écart figé | Plancher `minimum_chart_stop_atr` intégré à B_SL |
| E-61 | Setup 2, pullback EMA | Repli sur la zone EMA20–EMA50 en tendance H1 | Hors robot | Relève de la méthode S01 (robot EMA), non construite dans ce plan |
| E-62 | Setup 3, cassure et retest | Cassure en clôture puis retour sur le niveau avec rejet | Écart figé | Retest exclu (`mandatory_retest` faux) ; entrée après la clôture de cassure |
| E-63 | Setup 4, balayage et retournement | Perçage d'un extrême puis réintégration en clôture | Écart figé, instrumenté | Jamais tradé ; retournements après cassure mesurés (E-24) |
| E-64 | Setup 5, continuation New York | Reprise du sens londonien pendant la séance de New York | Hors robot | Aucune entrée après `entry_end_local_exclusive`, sortie forcée à `force_exit_local` |
| E-65 | Setup 6, fausse cassure | Réintégration en clôture dans les 1 à 3 bougies, puis position opposée | Écart figé, instrumenté | Ni sortie sur retour dans le range (`exit_on_close_back_inside_range_enabled` faux) ni inversion ; une vente reste possible sur un nouveau signal valide (S02.4) ; taux de réintégration mesuré |
| E-66 | Setup 7, VWAP | Rebond sur le VWAP ou retour à la valeur | Écart figé | Aucun VWAP |
| E-67 | Setup 8, compression et expansion | Compression des bandes de Bollinger avant Londres | Écart figé | `bollinger_enabled` faux ; la borne basse de W/A_H1 est le seul filtre de compression |
| E-68 | Setup 9, momentum sur retracement | EMA8, EMA20, MACD, sortie partielle et trailing | Écart figé | `extra_roc_momentum_enabled` et `allow_trailing_stop` faux |
| E-69 | Setup 10, double sommet à balayage | Figure M ou W sur zone H1 ou H4 | Écart figé | Aucune figure chartiste |
| E-70 | Sélection selon le régime | Compression pré-séance : setups 1 et 8 ; après une annonce, attendre 15 à 30 min et ne pas jouer le setup 1 pendant le pic | Aligné | S02 vise ce régime ; fenêtre d'annonce `[N − 900 s, N + 900 s)` |
| E-71 | Conception et automatisation | Remplacer tout jugement visuel par une définition mesurable ; « range asiatique » défini de 00:00 à 07:00 heure de Paris ; setup 1 très codifiable ; concepts SMC fragiles à automatiser | Aligné ; écart figé pour l'horaire du range | Toutes les règles mesurables (§6) ; range `[02:00, 07:00)` Londres figé ; aucun concept SMC |

## 6. Contrôle de codifiabilité (consigne « conception de stratégie » de la skill)

La skill exige, pour un robot, que chaque règle soit codifiable de façon déterministe et que toute règle
discrétionnaire résiduelle soit signalée.

| Famille de règles | Déterministe | Unité |
|---|---|---|
| Horaires, jours, range, gel de A_H1, fenêtre (S02.1, S02.2, C03.3) | Oui | `donnees-temps` 0b ; `moteur-london` 1a, 1b, 2 |
| Bougie de cassure, stop local, objectif, quotas (S02.3, S02.4) | Oui | `moteur-london` 1c, 1d, 1e |
| Données, validité, trous, indicateurs (C03) | Oui, après les arbitrages P-01 à P-03 et P-10 | `donnees-temps` |
| Cotation, niveaux, risque, dimensionnement, ordres, sorties (C06 à C08) | Oui, après P-04 à P-06, P-08 et P-12 | `execution-coordinateur` |
| Permissions et annonces (C05) | Oui pour leur application | `controles-fondamentaux` |
| Veto IA (A06, A07) | Oui pour sa construction et son application ; la classification par le LLM est une entrée externe validée | `service-ia` 1b ; `contexte-ia` |

**Éléments non déterministes signalés** (des entrées humaines ou externes, versionnées, jamais des règles du
robot) : contenu des permissions du module fondamental externe ; table d'importance HIGH et table des types de
décision par issuer (D-12) ; fichier des fermetures exceptionnelles (D-12) ; classification du LLM ; annotation
humaine A13 ; décisions de déploiement. **Constantes d'ingénierie** (jamais réglées sur un résultat, consignées
au registre de déploiement) : période de boucle de D-09, plafond du dossier d'échange de D-11, cadences d'export
de D-12, tolérance d'arrondi ε du document 01, §6.

## 7. Manques trouvés par cette vérification et corrections

| # | Manque | Correction apportée |
|---|---|---|
| 1 | A03 exige de consulter la copie mémoire du contexte IA à la décision **et juste avant l'ordre** ; le plan ne recontrôlait que la permission fondamentale | Document 01, §4.3, étape 4.d, et document 02, §6.4 (`coordinateur`) : recontrôle de la permission et du contexte IA juste avant l'envoi |
| 2 | Taux de réussite et R moyen réalisé, attendus par la skill d'expert, absents des métriques | Document 02, §6.8 (`metriques`) : indicateurs rapportés, jamais des critères de décision |
| 3 | Les sept mesures séparées de C09 n'étaient pas énumérées | Document 02, §6.8 (`metriques`) |
| 4 | C10 : effet propre du fondamental, fréquences brutes avant filtrage, comparaison aux journaux de démonstration, pertes et arrêts de chaque perturbation | Document 02, §6.8 (`rapports`) |
| 5 | A02 : le service écrit sous `XPBOTS_COMMON_FILES_DIR`, qui doit désigner le dossier commun lu par le robot | Document 01, §2 : contrôle au démarrage et alerte en cas d'écart ; un snapshot absent ou périmé laisse le complément `NEUTRAL` |
| 6 | A13.10 et A12 : mécanisme de suspension des vetos d'un fournisseur en dérive non décrit | Document 02, §6.11 : le service cesse de publier les vetos de ce fournisseur et poursuit l'observation dans son journal |
| 7 | Les exports de ticks réellement disponibles (terminal MT5, source tierce) ne sont pas au format canonique exigé par le rejeu ; aucun convertisseur n'était prévu | Document 02, §6.14 : artefact `donnees-historiques`, construit en sous-étape 13.3 au vu des exports réels ; sondes S-09 et S-10 (document 01, §10) ; tests (document 03, §7) ; procédure H-09 |
| 8 | Les actions humaines étaient citées sans procédure ni comportement prévu en leur absence | [Document 07](07_procedures_humaines.md), procédures H-01 à H-12 ; plan directeur, §5 |
| 9 | Les refus D-10 et D-17 pouvaient se lire comme des décisions en attente | Plan directeur, §3 (statut « Arrêtée : refus ») et §2.4 (complétude) |
| 10 | Les phases 11 et 12 attendaient des actions humaines (poste, compte, sondes, autorisation des API) : l'implémentation n'était pas exécutable sans l'utilisateur avant la qualification | Infrastructure et service construits dans le conteneur contre des contrats finalisés tôt ; actions H-02 à H-12 regroupées en phase 13 (plan directeur, §2.3 et §5 ; document 04, phases 11 à 13 ; document 07) ; risque R-18 ; contrôle mécanique |
| 11 | Les contrats des frontières MT5 n'étaient qu'esquissés (fonctions, champs, requêtes, codes de retour, erreurs) | [Document 08](08_contrats_frontieres.md), §2, établi par l'examen du paquet officiel `MetaTrader5` 5.0.6231 |
| 12 | Les aides `Buy`, `Sell` et `Close` du paquet renvoient d'elles-mêmes un ordre refusé, ce que C08 exclut | Document 08, §2.1 (interdits) ; document 01, §10 |
| 13 | Les caractéristiques du symbole n'exposent pas les commissions exigées par C04 | Document 08, §2.8 : lecture dans les transactions, comparaison à la fiche publiée du compte (sonde S-07) |
| 14 | Le paquet exige `numpy` et ne s'installe que sous Windows, ce qui empêchait de tester l'infrastructure dans le conteneur | `requirements-windows.txt` (D-05 ; document 08, §2.1) ; import du module par la seule enveloppe `assemblage` et faux module injecté (document 02, §6.9 ; document 03, §7) |
| 15 | Rien n'empêchait une commande de démonstration de s'exécuter sur un compte réel connecté par erreur | Garde du type de compte (document 08, §2.3 ; document 04, phase 11, étape 5 ; procédure H-03) |

## 8. Application de la skill `xp-bots-mcl-robot-planning`, étape par étape

| Id | Étape ou garde-fou de la skill | Application dans le plan | Preuve |
|---|---|---|---|
| M-01 | Périmètre : artefact, échelle ; système complet en mode composite ; ordre de livraison venant du guide | Application en mode composite : onze artefacts construits en phases 2 à 12, puis `donnees-historiques` et `moteur-london-v1` en phase 13 ; ordre du guide | Plan directeur, §2 ; [document 02](02_cartographie_mcl.md), §1, §3 et §5 |
| M-02 | Décisions ouvertes : plateforme, langage et répertoire des sources demandés à l'humain avant toute carte | Questions posées le 05/11/2026 ; réponses consignées | Plan directeur, §3, D-01 et D-02 |
| M-03 | Applicabilité : test en trois questions ; spécification figée applicable, recherche de variante exclue | Verdict applicable, sondes jetables pour l'adaptateur MT5 | Document 02, §1 |
| M-04 | Initialiser les dossiers MCL en mode écriture seulement ; en planification, ne rien écrire | Aucun dossier `mcl/` créé pendant la planification ; initialisation en phase 0 | [Document 04](04_phases.md), phase 0 |
| M-05 | Cartographier : unités candidates recoupées avec la spécification, question-test, `analyser` jusqu'à zéro divergence | Unités de chaque artefact ; cartes simulées par `mcl.py analyser` | Document 02, §5 et §6 |
| M-06 | Frontières et contrats : port, doublure, infrastructure réelle, test de contrat ; esquisse de tous les contrats | Table des frontières ; contrats esquissés ; contrats de toutes les frontières externes finalisés tôt (exception MCL), confrontés au réel en phase 13 | Document 02, §6 et §7 ; [document 01](01_architecture.md), §2.1 et §2.2 ; document 08 ; contrôle mécanique |
| M-07 | Affecter les cas d'acceptation C11, S02.6 et A14 aux couches et aux catégories ; aucun cas sans couche | Quarante cas affectés | [Document 03](03_acceptation_et_tests.md), §5 ; contrôle mécanique |
| M-08 | Plan de gate : catégorie 1, catégorie 2, régression intégrale avec `python tools/verify_project.py` | Commandes de gate et de gel | Document 03, §3 ; document 04, gabarit commun |
| M-09 | Présenter avant la couche 0 : applicabilité, carte avec groupes parallèles, frontières, décisions, coûts | Plan directeur et documents 02 et 05 ; arrêt avant la phase 0 | Plan directeur, §1 et §2 ; [document 05](05_expert_risques_tracabilite.md), §3 |
| G-01 | Paramètres chargés depuis `config/`, jamais recopiés en dur ni optimisés | Chargement strict, contrôle d'empreinte, test de non-recopie | Document 01, §1 et §6 ; document 03, §8 |
| G-02 | Le code de `reference/` est un oracle, pas une couche | `reference` interdit dans toutes les cartes du code | Document 01, §5 ; document 02, §8 |
| G-03 | Ordre de dépendance, jamais ordre du flux ; types du flux en couche 0, adaptateur réel en infrastructure | Types du flux dans le noyau, flux MT5 dans `infrastructure` | Document 02, §5 et §6 |
| G-04 | Doublures seulement aux frontières externes ; même moteur pour le rejeu et la plateforme | Doublures limitées aux frontières ; cœur unique | Document 02, §7 ; document 01, §1 |
| G-05 | `mcl.py` n'analyse pas MQL5 : convention de modules et revue de code, à signaler | Service MQL5 isolé, contrôlé par convention, revue et tests de format | Document 02, §6.12 |
| G-06 | Les deux méthodes restent deux artefacts ; seul le coordinateur de compte est partagé | Moteurs London, V1 et futur EMA parallèles ; stratégies injectées | Document 02, §5 ; plan directeur, D-18 |

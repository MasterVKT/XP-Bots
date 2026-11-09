# Plan d'implémentation intégrale — Robot 1 `EMA_V3` (Triple EMA + RSI + repli M15)

## 0. Contexte

Le dépôt XP-Bots contient la spécification autonome 3.1.0 du robot 1
(`livrables/strategies_m15/01_Triple_EMA_RSI_Repli_M15_Specification_IA.md`, sections C01–C11, S01, A01–A15),
ses exports figés (`config/parametres_figes_v3.json` blocs `common` + `ema`, `config/parametres_IA_integration_v1.json`,
`schemas/`, `prompts/`) et des fonctions de référence (`reference/technical.py`, `reference/llm_contracts.py`).
Ce contexte décrit l’état initial de planification. Depuis, les deux lignées possèdent leur moteur pur
et leurs socles. Au 06/11/2026, les calculs du coordinateur commun sont figés dans
[london-execution-coordinateur](../../mcl/london-execution-coordinateur/PLAN-MCL.md), avec adaptation typée EMA.
Ce plan doit consommer cette unique implémentation ; l’ancienne esquisse `mcl/execution-coordinateur/`
n’autorise pas de doublon. Depuis la phase 6 London, le cycle C08, les sorties, la reprise et l’enveloppe communes sont aussi figés. Leur intégration au robot EMA et l’adaptateur courtier restent à construire. Ce plan organise la construction complète et vérifiable du robot 1, sans modifier aucune règle,
aucun seuil, aucun export, aucune référence, aucune preuve (`.agents/PROJECT_RULES.md` §4).

Résultat visé : un robot Python qui, sur les mêmes ticks, prend les mêmes décisions en rejeu et en direct
(C11.14), applique intégralement S01 + C03–C09 + A07/A10/A12, journalise selon C09, se qualifie sur un compte
MT5 démo (C04), et un service IA partagé (A04–A11) en dernière phase. **La rentabilité reste non validée** :
elle relève du protocole C10/A13 sur les données réelles de l'utilisateur.

Avancement : **phases 0, 1, 2 et 3 terminées le 2026-11-05** (cartographie confirmée par `mcl.py`, squelette composite, artefact `donnees-temps` figé et branché, artefact `moteur-ema` figé et branché, décisions R1–R18 prises par délégation dans `mcl/robot-ema-v3/INTERPRETATIONS.md` ; tableau de suivi dans `mcl/robot-ema-v3/PLAN-MCL.md`). Chaque phase suivante ne démarre que sur
demande explicite de l'utilisateur.

## 1. Décisions arrêtées

| Id | Décision | Conséquences |
|---|---|---|
| D1 | Python **3.13** ; MT5 via le paquet officiel `MetaTrader5` (v5.0.6231 du 27/09/2026, wheels Windows x86-64 seulement) | Import autorisé **uniquement** dans `src/xpbots/infrastructure/mt5/` ; pin dans un fichier séparé `requirements-mt5.txt` (pas dans `requirements-dev.txt`, pour garder la CI Linux) |
| D2 | Périmètre : robot 1 complet + service IA partagé en dernière phase | Exclus : moteur London (robot 2), module fondamental externe (seule son interface est construite), conclusion économique, compte réel |
| D3 | Code dans `src/xpbots/`, tests dans `tests/robot/`, états MCL dans `mcl/` | Un sous-paquet par artefact MCL, **un module par couche** |
| D4 | Tests en `unittest` (bibliothèque standard), aucune dépendance de test ajoutée | Lanceur `tools/run_robot_tests.py` (stdlib) |
| D5 | Moteur et coordinateur : bibliothèque standard seule (`decimal`, `zoneinfo` + `tzdata` déjà déclaré, `json`) | `numpy`/`pandas` restent cantonnés à `reference/` et `tests/check_*.py` ; `sqlite3`, `urllib`, fichiers et horloge système seulement en infrastructure |
| D6 | Modes : `PAPER` (données réelles, exécution simulée, défaut de `common.default_mode`) → `DEMO` (ordres réels sur compte démo, après go/no-go) ; `REEL` hors périmètre ; IA en `PAPER_AB` | Aucun agent n'ouvre de compte ni ne passe d'ordre réel (C01) |

Décisions encore ouvertes, à trancher au plus tard à la phase indiquée : courtier et serveur MT5 (phase 9) ;
source du calendrier HIGH et transport des permissions fondamentales (phase 6, cf. R12–R13) ; points du
registre d'interprétation §10 (phase 0, avant le code concerné).

## 2. Verdict MCL (skill `xp-bots-mcl-robot-planning` + `mcl-matryoshka-construction-layers`)

| Question | Réponse | Justification |
|---|---|---|
| Structure connaissable ? | oui | Spécification déterministe figée, unités nommées par C03–C09/S01 |
| Contrats stabilisables tôt ? | oui | Seuils et formules gelés ; exports JSON ; fonctions de référence |
| Construire pour comprendre ? | non | Aucune recherche d'avantage : la variante est imposée |

- **Verdict : applicable.** Chercher une variante plus rentable serait exploratoire et reste hors plan.
- **Échelle : application** (squelette + huit artefacts de chair) → **mode composite** : squelette déployable outside-in, puis un
  artefact MCL de chair par composant, branché en remplaçant un segment minimal.
- **Bénéfice dégradé assumé** : frontières externes dominantes (courtier, flux, calendrier, permissions, API LLM,
  IPC, horloge, stockage) → nombreuses doublures ; risque de dérive de fidélité traité par une même suite de
  tests de contrat exécutée contre la doublure (CI Linux) et contre le réel (MT5 démo, poste Windows).
- **Coûts annoncés** : gate croissant (~N²/2 en régression intégrale), sérialisation des couches dépendantes,
  risque de contrat spéculatif (contrats finalisés un niveau d'avance seulement), retour bout en bout couvert
  par le squelette.
- **Signaux de mauvais domaine à surveiller** : divergences répétées carte/code, défigeages en chaîne → suspendre,
  re-cartographier, informer l'utilisateur.

## 3. Lecture d'expert scalper M15 (skill `anthropic-skills:expert-scalper-m15`)

Rappel unique : le scalping Forex est à haut risque ; ce plan est de l'ingénierie logicielle, pas un conseil
financier ; aucune rentabilité n'est promise ; démonstration obligatoire avant tout capital réel.

- **Codifiabilité** : aucune règle discrétionnaire résiduelle dans S01. Les seuls flous sont des points
  d'implémentation (registre §10), qui seront figés par test **après validation de l'utilisateur**, jamais
  arbitrés en silence (C02).
- **Scénarios de test inspirés du terrain** (ils testent la règle écrite, sans la changer) : élargissement du spread
  à l'ouverture de Londres (08:00) au-dessus du plafond ; pic d'annonce avec fenêtre ±900 s ; mèche sous l'EMA50
  sans clôture sous EMA50−0,25 A (piège de « fausse cassure ») ; bougie de reprise géante > 2,5 A ; vendredi
  15:45 puis sortie forcée 16:00 ; jours de changement d'heure ; deux positions EURUSD et GBPUSD corrélées USD
  (plafond commun de 1 % testé).
- **Indicateurs de journal** (bins fixés avant analyse, A11) : âge du repli 1–8, tranche horaire Londres
  (08–10, 10–12, 12–14, 14–16), ATR et distance du stop (bins fixés sur le bloc de développement), motif de refus,
  R net, gagnants bloqués, coût.
- **Observations d'expert non intégrées** (la spécification est figée ; toute évolution = nouvelle version) :
  biais H1/H4, break-even, sortie partielle, « troisième repli fatigué », filtres lundi matin/vendredi soir,
  compte ECN. Poids du coût : dans S01.5, le spread (1 pip) représente ~15 % de D = 6,5 pips ; c'est précisément
  la question économique de C10. Ces observations peuvent devenir des hypothèses de recherche A11 (3/mois max).

## 4. Architecture cible

### 4.1 Arborescence

| Chemin | Contenu |
|---|---|
| `src/xpbots/noyau/` | Squelette : types de couture, ports, motifs, schéma C09, JSON canonique, chargeur de configuration |
| `src/xpbots/donnees_temps/` | Artefact A : sessions, bougies, indicateurs, état récursif |
| `src/xpbots/moteur_ema/` | Artefact B : méthode S01 |
| `src/xpbots/execution/` | Artefact D : C06–C09 (cotation, prix, risque, réservations, ordres, sorties, coordinateur) |
| `src/xpbots/fondamental/` | Artefact E : C05 |
| `src/xpbots/contexte_ia/` | Artefact F : lecture du snapshot, cache des vetos, A07/A10/A12 |
| `src/xpbots/journal_rejeu/` | Artefact H : simulateur d'exécution, rejeu, métriques, bootstrap, PAPER_AB |
| `src/xpbots/service_ia/` | Artefact G : logique du service IA (A04–A11), sans E/S réelle |
| `src/xpbots/infrastructure/` | Artefact I : adaptateurs réels (`mt5/`, `fichiers/`, `sqlite/`, `http/`, `horloge/`) |
| `src/xpbots/app/` | Points d'entrée et câblage : `rejeu`, `paper`, `demo`, `qualification`, `service_ia` |
| `tests/robot/<paquet>/test_c<couche>_cat<1|2>_<sujet>.py` | Tests par couche et catégorie MCL |
| `tests/robot/doublures/` | Doublures des seules frontières externes (courtier scripté, calculs courtier, horloge contrôlée, stockage mémoire, transport HTTP factice, système de fichiers temporaire) |
| `tests/robot/fixtures/` | Générateurs déterministes de ticks synthétiques ; fichiers < 1 Mio (`verify_project.py`), JSON strict, LF ; **aucun prix réel** |
| `tools/run_robot_tests.py` | Lanceur stdlib : ajoute `src` au chemin, filtres `--artefact`, `--couche`, `--categorie`, `--contrat-mt5-demo` |
| `mcl/robot-ema-v3/` | Dossier MCL composite (carte des artefacts, `COUTURES.md`, `INTERPRETATIONS.md`, plan maître) |
| `mcl/<artefact>/` | Un dossier MCL par artefact (carte, journal, contrats de couche, PLAN-MCL) |
| `deploiement/environnement.exemple.json` | Gabarit non secret des réglages d'exploitation (R15) ; valeurs réelles sous `runtime/` (ignoré) |
| `.github/workflows/robot-ci.yml` | CI Linux : tests robot + `tools/verify_project.py` + `mcl.py verifier` |

### 4.2 Règles transverses de codage (testées)

1. **Paramètres** : toute valeur normative se lit dans `config/` via le chargeur du noyau ; un test « anti-recopie »
   recherche dans `src/` les littéraux des seuils figés (0.65, 7200, 0.00015…) avec liste d'exceptions justifiées.
2. **Temps** : instants = entiers en millisecondes UTC + séquence de départage stable ; Londres via
   `zoneinfo('Europe/London')`, jamais un décalage fixe. Aucun appel d'horloge (`time.time`, `datetime.now`,
   `time.monotonic`) hors `infrastructure/horloge/` (test de recherche textuelle + règle `externes` de mcl.py).
3. **Nombres** : indicateurs en flottants 64 bits, récurrences dans l'ordre de C03 (moyenne de graine = somme
   séquentielle gauche→droite / n) ; prix, volumes et argent en `Decimal` sur la grille native ; conversion d'un
   flottant courtier par sa représentation la plus courte ; contrôle d'erreur avant arrondi identique à
   `rounded_levels` (rapport au tick à 1e-8 près ramené à l'entier). Inégalités strictes ou larges exactement
   celles du texte, sans tolérance.
4. **Motifs** : énumération fermée = liste C09 (extraite du texte de la spécification par un test anti-dérive)
   + `AI_CONTEXT_VETO` (A07) + `ENVIRONMENT_NOT_READY` (C04). Tout ajout passe par le registre §10.
5. **Sécurité par défaut** : toute exception ou donnée inconnue sur le chemin d'entrée produit un refus ; sur le
   chemin de sortie, la sortie est réessayée ; les protections natives ne sont jamais retirées.
6. **Persistance** : tout état devant survivre au redémarrage passe par le port `Stockage` (doublure mémoire en
   test, SQLite transactionnel en infrastructure) ; idempotence par clé d'intention C08.
7. **Journal** : JSONL UTF-8 LF en ajout seul ; aucun secret, aucun numéro de compte, aucun solde dans les rapports
   partagés.
8. **Frontières** : `MetaTrader5` seulement dans `infrastructure/mt5/` ; `sqlite3` seulement dans
   `infrastructure/sqlite/` ; `urllib`/`http`/`ssl`/`socket` seulement dans `infrastructure/http/` ; aucun appel
   réseau dans le chemin signal → ordre (A03).

## 5. Carte composite (niveau application, `mcl/robot-ema-v3/carte.json`)

| Prof. | Artefact (paquet) | Dépend de | Phase |
|---|---|---|---|
| 0 | `noyau` (squelette) | — | 1 |
| 1a | `donnees_temps` | noyau | 2 |
| 1b | `contexte_ia` | noyau | 7 |
| 2a | `moteur_ema` | noyau, donnees_temps | 3 |
| 2b | `execution` | noyau, donnees_temps | 4–5 |
| 2c (profondeur 3 du bloc commun) | `fondamental` | noyau canonique, execution (port partagé) | 6 |
| 2d | `service_ia` | noyau, contexte_ia (format du snapshot) | 10 |
| 3 | `journal_rejeu` | noyau, profondeurs 1–2 | 8 |
| 4 | `infrastructure` | noyau, execution (types C04), contexte_ia, journal_rejeu (schéma) | 9 (segments minimaux dès la phase 1) |
| 5 | `app` | tout | 1 (minimal), enrichi à chaque phase |

Le coordinateur ne connaît la stratégie, les permissions et le contexte IA qu'à travers les **ports du noyau**
(`Strategie`, `ControleFondamental`, `ContexteIA`) : D peut donc être livré avant E et F, conformément à l'ordre
produit du guide (`docs/architecture/GUIDE_IMPLEMENTATION.md`), en consommant des segments minimaux **conformes à
la spécification** (fondamental absent = refus `FUNDAMENTAL_INVALID` ; IA absente = `NEUTRAL`, A12).

### Frontières externes

| Frontière | Port (noyau) | Doublure (tests) | Adaptateur réel (phase 9/10) | Test de contrat |
|---|---|---|---|---|
| Flux de ticks MT5 | `FluxTicks` | flux rejoué depuis générateur | `copy_ticks_from/range` (COPY_TICKS_ALL, `time_msc`) | ordre, frontières, UTC (R14) |
| Exécution courtier | `Courtier` | courtier scripté (accusés, refus, partiels, timeouts) | `order_send`, `positions_get`, `history_deals_get`, `history_orders_get`, `TRADE_ACTION_SLTP` | même suite, démo |
| Calculs courtier | `CalculCourtier` | formules déterministes contrat USD | `order_calc_profit`, `order_calc_margin`, `order_check`, `symbol_info`, `account_info` | écarts formule/natif |
| Horloge | `Horloge` | horloge contrôlée | horloge système UTC ms | monotonie |
| Stockage d'état | `Stockage` | dictionnaire transactionnel mémoire | SQLite `BEGIN IMMEDIATE` | atomicité, reprise |
| Journal | `Journal` | liste mémoire | fichier JSONL `fsync` | ajout seul |
| Permissions fondamentales | `SourcePermissions` | messages scénarisés avec `known_at` | selon R13 | schéma C05 |
| Calendrier HIGH | `SourceCalendrier` | versions scénarisées | selon R12 (exportateur MQL5 ou module fondamental) | conversion heure serveur |
| Snapshot IA (IPC) | `LecteurSnapshotIA` | fichiers temporaires | `terminal_info().commondata_path`/`XPBots/ai/v1/context_latest.json` ou `XPBOTS_COMMON_FILES_DIR` | remplacement atomique |
| Ticks historiques | `SourceTicksHistoriques` | générateur | CSV/CSV.gz du cahier de données §2 + manifeste (Parquet seulement si `pyarrow` approuvé) | empreintes |
| API LLM, RSS (service IA) | `TransportHTTP` | transport factice | `urllib` HTTPS (Groq, Gemini, OpenAI optionnel, Fed/BCE/BoE) | conformité manuelle, clés de l'utilisateur |

## 6. Squelette composite (phase 1)

Chemin minimal, code de production durable : **ticks de fixture → bougie M15 → stratégie neutre (`NO_SETUP`) →
coordinateur (refus explicite) → exécution papier → journal C09**.

- `noyau` : `Instant` (ms UTC + séquence, ordre total) ; `Tick` (symbole canonique et courtier, Bid/Ask finis
  positifs) ; `Bougie` (période, ouverture, OHLC Bid, validité, nombre de ticks) ; `Cotation` ; `Signal`
  (stratégie, symbole, clôture UTC, sens, clôture Bid, `A_t`, `B_SL`, multiple k, état du détecteur) ;
  `ResultatTechnique` (exactement un signal ou un motif) ; `IssueSignal` (rempli avec volume/prix/instant, ou
  refus définitif avec motif) ; `DecisionFondamentale` ; `DecisionContexteIA` (BLOCK ou NEUTRAL) ; `CleIntention`
  `(deployment_id, strategy_id, symbole, cloture_M15_UTC, sens)` ; `MotifRefus` ; schéma des enregistrements C09 ;
  JSON canonique strict (refus des doublons et des non-finis, empreinte = `reference.technical.canonical_hash`) ;
  chargeur de `config/` ; ports (protocoles `typing`) nécessaires au squelette : `SourceTicksHistoriques`,
  `Journal`, `Strategie`, `ControleFondamental`, `ContexteIA` ; les autres ports de §5 arrivent avec leur premier
  consommateur (contrat un niveau d'avance seulement).
- Segments minimaux dans `app/segments_minimaux.py`, chacun remplacé plus tard (`COUTURES.md` décrit entrée,
  sortie, invariants et artefact remplaçant) : agrégateur M15 sans gestion de trou (couverture lue dans le
  manifeste de fixture) → A ; stratégie neutre → B ; coordinateur de refus → D ; fondamental absent → E ;
  contexte IA neutre → F ; exécution papier sans ordre → H/I.
- Infrastructure minimale, elle aussi dans `app/segments_minimaux.py` (le paquet `infrastructure` est construit
  au protocole MCL en phase 9) : lecteur CSV de fixture, écrivain JSONL.
- Point d'entrée : `python -m xpbots.app.rejeu --ticks <csv> --manifeste <json> --journal <jsonl>`, avec `src`
  dans `PYTHONPATH` ; fixture synthétique versionnée `tests/robot/fixtures/squelette_ticks.csv`.
- Gate du squelette = sa CI (`.github/workflows/robot-ci.yml`) : suite robot + `python tools/verify_project.py` + `mcl.py verifier` composite et par artefact ; le gate global est aussi tracé dans `mcl/robot-ema-v3/journal.jsonl`.

## 7. Cartes des couches par artefact

Chaque ligne = une unité ; « Cat. 1 » = contrat propre de la couche (externes doublés) ; « Cat. 2 » = jonction
sur le bloc réel `{0 → k}` sans doublure interne. Couches de même profondeur (1a, 1b…) = **groupe parallèle**,
contrats finalisés ensemble, gates et gels séparés.

### 7.A `donnees_temps` (C03) — phase 2

| Couche | Unité (module) | Contrat | Cat. 1 | Cat. 2 |
|---|---|---|---|---|
| 0 | `parametres_techniques`, `calendrier_seances` (`c0_parametres_seances`) | bloc `common` → objet immuable ; clés exactes, types, aucune valeur nulle ; empreinte du bundle pour le journal + séances natives du symbole (C04, jamais devinées) | clés manquantes/en trop, types, empreinte | — |
| 1a | `sessions_londres` (`c1a_sessions`) | jour Londres, jour UTC, jour ouvré 0–4 ; bougie (ouverture ≥ début, clôture < fin, même jour Londres) dans la fenêtre d'un bloc ; instant UTC de l'heure de sortie forcée d'un jour ; appartenance au blackout `[21:00,23:00)` UTC | changements d'heure 2025/2026 (08:00 Londres = 07:00 UTC l'été, 08:00 l'hiver), première clôture 08:15, dernière 15:45, 16:00 exclue, week-end exclu, jour UTC ≠ jour Londres, concordance `local_decision_in_window` | avec 1b et 1c |
| 1b | `constructeur_bougies` (`c1b_bougies`) | ticks ordonnés + événements de couverture + séances natives → M15/H1 clôturées `[T,T+d)` alignées sur l'époque UTC, OHLC Bid, validité ; événements de trou | tick à T+900 dans la bougie suivante, égalités de ms départagées par séquence, minute inchangée ≠ trou, fermeture officielle ≠ trou, interruption inexpliquée = trou, H1 invisible avant clôture, clôture déclenchée par l'horloge sans tick, bougie sans Bid (R4) | — |
| 1c | `indicateurs` (`c1c_indicateurs`) | états incrémentaux EMA(n) graine SMA, RSI Wilder (50/100/0), TR (premier = H−L), ATR Wilder, `A_t` = ATR de t−1, historique EMA50 sur 4 bougies | valeurs = `reference.technical` (`ema`, `wilder`, `rsi`, `add_indicators`) à 1e-12 près et **mêmes comparaisons de seuil** ; indisponibilité avant graine ; cas RSI nuls | — |
| 2 | `etat_indicateurs` (`c2_etat_indicateurs`) | préchargement ≥ `warmup_closed_m15_bars` M15 (H1 inutile pour EMA) → état + empreinte (premier horodatage, SHA-256) ; persistance via `Stockage` ; reprise sur les seules nouvelles bougies ; trou → R6′ | préchargement insuffisant = `WARMUP` ; préchargement différent journalisé | redémarrage = flux continu |
| 3 | `pipeline_marche` (`c3_pipeline`) | par symbole : ticks + couverture + horloge → `BougieEnrichie` (bougie, indicateurs, `A_t`, jour Londres, statut OK/WARMUP/DATA_GAP) ou événement de trou | statuts, effacement après trou (R5, R6′) | **C11.1** préfixe causal ; trou puis récupération ; changement d'heure |

### 7.B `moteur_ema` (S01) — phase 3

| Couche | Unité | Contrat | Cat. 1 |
|---|---|---|---|
| 0 | `parametres_ema` | bloc `ema` validé ; refus de démarrer si un drapeau a une valeur non implémentée (`h1_directional_filter_enabled`, `require_signal_touch`, `require_directional_body`) | clés, drapeaux |
| 1a | `tendance_ema` | E15>E25>E50 et E50>E50(t−4) → long ; symétrique → court ; sinon 0 | **EMA égales ou pente nulle : aucun armement** (C11.2, S01.6) |
| 1b | `conditions_repli` | contexte d'armement (C vs E15, RSI ≥50/≤50) ; validité du repli (C ≥ E50−0,25A et RSI ≥40 en long, symétrique) ; contact `[L,H] ∩ [min(E15,E50),max(E15,E50)]` | RSI de repli 40 admis ; mèche sous EMA50 sans clôture au-delà de 0,25A n'annule pas |
| 1c | `bougie_reprise` | R>0, TR ≤2,5A, C>E15, C>O, RSI ≥50, (C−L)/R ≥0,65 (symétrique) | signal RSI 49,999 refusé, 50 admis ; O=C refusé ; TR >2,5A refusé ; 0,65 exactement admis |
| 1d | `stop_objectif_ema` | buffer = max(tick, 0,10A) ; `B_SL` long = min(bas du repli − buffer, C − 0,80A), court symétrique ; refus `STOP_TOO_WIDE` si distance >2,5A ; k = 1,5 | extrême de la bougie de signal inclus ; S01.5 (B_SL 1,09945 / 1,10055) |
| 2 | `machine_etats_ema` | états `IDLE`, `ARMED_*`, `PULLBACK_*`, `COOLDOWN`, `OWNED_POSITION` ; champs persistés : jour Londres, début et extrêmes du repli, compteur de fills du jour, référence de position, bougie de cooldown | une transition par incrément (ci-dessous) |
| 3 | `moteur_ema` (port `Strategie`) | `sur_cloture` → signal ou motif technique (`OUTSIDE_SESSION`, `WARMUP`, `DATA_GAP`, `NO_SETUP`, `STOP_TOO_WIDE`, `DAILY_ENTRY_CAP`) + état du détecteur pour C09 ; `appliquer_issue` ; `notifier_sortie` | ordre des traitements, motifs |

Machine à états (composante fortement connexe condensée, croissance transition par transition, une passe de
gate par incrément) : T1 armement depuis `IDLE` (la bougie d'armement n'est jamais repli ni signal) ; T2 premier
contact → repli âge 1 ; T3 repli âge t−début+1, extrêmes de **toutes** les bougies, signal compris ; T4
violation → annulation puis réarmement possible sans entrée ; T5 âge 9 → annulation, réarmement sans entrée ;
T6 reprise complète → signal (consomme le repli même si stop trop large ou refus) ; T7 issue refus → `COOLDOWN`
d'exactement une clôture puis `IDLE` ; T8 issue fill (même partiel) → `OWNED_POSITION`, compteur +1 ; T9 sortie →
`COOLDOWN`, première clôture strictement postérieure ignorée, aucune entrée à l'instant exact de sortie (R1) ;
T10 hors fenêtre, changement de jour Londres, trou → effacement armement/repli ; T11 six fills max par jour
Londres, remise à zéro au changement de jour et jamais au redémarrage ; T12 issue différée (R2).

Cat. 2 (bloc A+B réel) : équivalence avec `reference.technical.ema_setups` sur séries synthétiques (issues
« toujours refusé ») — signaux non `STOP_TOO_WIDE` identiques champ par champ (instant, sens, clôture, `A_t`,
`B_SL`, âge) ; tous les cas **S01.6** ; C11.4 (aucune entrée dominicale, changement d'heure).

### 7.D `execution` (C06–C09) — phases 4 (couches 0–3) et 5 (couches 4–6)

| Couche | Unité | Contrat | Cas clés |
|---|---|---|---|
| 0 | `types_execution` | `ProfilInstrument` (tous les champs C04 ; absent = inconnu, jamais zéro), `PositionPossedee`, `Reservation`, `EtatCompte`, paramètres d'exécution du bloc `common` | champ manquant → `ENVIRONMENT_NOT_READY` |
| 1a | `garde_cotation` | cotation valide non croisée (R3), âge ≤2 s, spread ≤ plafond du symbole (inclus), \|Bid − C_signal\| ≤0,25A, TTL `[T, T+5 s)` ; attente d'une cotation conforme dans le TTL | spread au plafond admis ; TTL exactement 5 s expiré (**C11.2**) ; première cotation après clôture seule exécutable (**C11.3**) |
| 1b | `prix_executables` | E = Ask (achat) / Bid (vente) ; SL achat = plancher de B_SL au tick ; SL vente = plafond de B_SL+S ; D>0 ; TP = E + sens·k·D (plafond achat, plancher vente) ; contraintes natives SL/TP (stops/freeze) → refus avant ordre (R7) | S01.5 : E 1,10010, SL 1,09945, D 0,00065, TP **1,10108** ; vente SL 1,10065, TP **1,09902** ; concordance `rounded_levels` ; spread compté une fois (**C11.5**) |
| 1c | `gardes_compte` | base des fonds propres à 00:00 UTC ; ≤98 % → `DAILY_LOSS_LOCK` jusqu'au jour UTC suivant ; pic depuis activation ; ≤90 % → `GLOBAL_DRAWDOWN_HALT` persistant, levée seulement par décision de déploiement tracée ; neutralisation des flux externes | seuils exacts, pertes flottantes et frais inclus, redémarrage sans remise à zéro (**C11.13**) |
| 1d | `registre_reservations` | intention et réservation enregistrées atomiquement avant envoi ; idempotence par clé ; réserve liée à la position jusqu'à sa clôture | message répété sans doublon |
| 2a | `risque_all_in` | g = max(tick, 0,05A) ; entrée E+sens·g, sortie SL−sens·g ; perte via `CalculCourtier` ; + frais aller-retour non inclus dans les prix (minimum par ordre, paliers) | g = 0,000025 et distance budgétée 0,00070 (S01.5) ; frais non linéaires (**C11.7**) |
| 2b | `arbitrage` | même instant : priorité `simultaneous_strategy_priority` puis `universe_priority` ; réévaluation après chaque réservation ; une position par sous-jacent ; ni fusion ni couverture | signaux `LONDON_V3` synthétiques simultanés (**C11.10**, R17) |
| 3 | `dimensionnement` | plus grand volume de la grille (min, pas, max, limite agrégée) respectant les 5 contraintes C07, arrondi vers le bas ; motifs `MIN_VOLUME_OR_RISK_REJECT`, `ACCOUNT_RISK_CAP`, `MARGIN_REJECT`, `SYMBOL_BUSY` ; positions externes → R8 | 0,01 lot de 100 000 → 0,70 USD > 0,50 refusé (**C11.6**) ; micro 1 000 unités, min 0,1 lot → 0,07 USD admis ; marge cumulée ≤ Eqt/3 |
| 4 | `cycle_ordre` | ordre protégé (SL+TP attachés, tolérance g) ; accusé 5 s ; réponse inconnue → verrou du symbole, rapprochement 1 s pendant 30 s puis 5 s sans limite, alerte >30 s, aucune retransmission ; fill partiel → annulation du reliquat, une entrée comptée ; TP recalculé au prix réel, 3 corrections (0,25/1/3 s, échéance 15 s) ; SL absent → clôture d'urgence immédiate ; TP déjà dépassé → clôture ; risque recalculé avec la seule réserve de sortie, réduction ou clôture | **C11.11**, **C11.12** (doublure scénarisée) |
| 5 | `sorties_obligatoires` | première échéance : SL/TP natif, 7 200 s après le premier fill, 16:00 Londres, début de fenêtre d'annonce, FLATTEN, gardes de perte, 60 s avant fermeture native, début du blackout ; réessai chaque seconde quand négociable ; toute clôture en attente bloque les entrées du symbole | égalités d'échéances ; flux absent à l'heure de sortie |
| 6 | `coordinateur` | ordre C08 par événement : rapprochement → sorties obligatoires → bougie et état technique → limites de méthode → fondamental et calendrier → contexte IA mémoire → cotation, stop, taille, marge, réservations → ordre protégé → issue au moteur ; second contrôle fondamental et IA juste avant envoi ; journal C09 de chaque décision ; redémarrage : journal rechargé, positions rapprochées, compteurs et risques restaurés avant toute décision ; verrou exclusif de propriété en netting ; jamais de clôture d'une position d'un autre propriétaire | **C11.11** redémarrage après envoi, position préexistante inconnue |

Cat. 2 de fin de phase 5 : bloc A+B+D réel avec le scénario nommé `TECHNICAL_CONTROL_NEUTRAL` (C05, explicitement
nommé, journalisé, interdit en `DEMO`) et un courtier scripté : cycle complet signal → ordre → fill → TP, SL,
sortie 16:00 ou 7 200 s ; septième entrée du jour refusée ; signal refusé à l'exécution → cooldown.

### 7.E `fondamental` (C05) — phase 6

Disponibilité commune depuis la phase 7 London : les cinq couches C05 sont figées dans
`mcl/london-controles-fondamentaux/`, sources `xpbots.fondamental`. L'esquisse EMA historique est
préservée ; sa consommation future passe par les ports et types canoniques communs. Cette
disponibilité ne déclare pas achevée la phase 6 EMA et ne modifie pas son squelette.

| Couche | Unité | Contrat |
|---|---|---|
| 0 | `types_fondamentaux` | message `fundamental-permission-v1`, événement de calendrier `(event_id, devise, instant, impact, known_at, version)`, table devises par symbole (R10) |
| 1a | `message_permission` | clés exactes, énumérations, `issued_at ≤ known_at ≤ maintenant`, `issued_at ≤ valid_from ≤ maintenant < valid_until`, durée positive ≤900 s, aucun instant futur, réception locale ≥ `known_at` |
| 1b | `garde_annonces` | calendrier mis à jour depuis ≤86 400 s et couvrant ≥172 800 s ; HIGH des devises du symbole ; aucune entrée dans `[N−900 s, N+900 s)` ; clôture envoyée à N−900 s ; annonce apprise tardivement = blocage et clôture immédiats ; versions conservées, passé jamais réécrit |
| 2 | `etat_permissions` | dernière permission valide par symbole, séquence strictement croissante, expiration, heartbeat 60 s (minute manquée journalisée), persistance |
| 3 | `permissions` (port `ControleFondamental`) | autorisation avec direction, ou `FUNDAMENTAL_INVALID` / `FUNDAMENTAL_DIRECTION` / `NEWS_WINDOW` ; demandes de sortie FLATTEN et annonce ; aucun signal refusé n'est renvoyé plus tard |

Cas : **C11.8** (expirée, future, incompatible ; neutre explicitement valide admis ; FLATTEN prioritaire, cat. 2
avec D), **C11.9** (début inclus, fin exclue, calendrier révisé tardivement). Remplace le segment « fondamental
absent ».

### 7.F `contexte_ia` (A07, A10, A12) — phase 7

| Couche | Unité | Contrat |
|---|---|---|
| 0 | `format_snapshot` | paramètres IA (âge 90 s, 32 Kio, poll 1 s, fournisseurs autorisés, empreinte d'intégration) ; JSON canonique du snapshot `xp-ai-context-v1` |
| 1 | `snapshot` | rejet : taille >32 Kio, doublons JSON, hash, schéma, version d'intégration, séquence en recul (minimum = dernière persistée), instant futur, âge >90 s, événement mal formé ; concordance avec `reference.llm_contracts.overlay_decision` |
| 2 | `cache_vetos` | vetos acceptés conservés jusqu'à leur échéance propre, dernier numéro et heure acceptée persistés ; snapshot périmé : aucun ajout, aucune révocation |
| 3 | `contexte` (port `ContexteIA`) | `BLOCK` ou `NEUTRAL`, jamais `ALLOW` ; lecture en mémoire seulement ; rechargement par timer 1 s hors chemin de décision ; bras A/B ; en réel, `NEUTRAL` sans validation financière |

Insertion A07 (cat. 2 avec B+D) : veto après la reprise complète et avant l'ordre → `AI_CONTEXT_VETO`, repli
consommé, cooldown d'une bougie, aucun fill compté, ancien repli jamais exécuté à l'expiration ; veto expiré à
publication + 900 s exactement ; réponse postérieure à la décision sans effet. Remplace le segment « IA neutre ».

### 7.H `journal_rejeu` (C09, C10, A13) — phase 8

| Couche | Unité | Contrat |
|---|---|---|
| 0 | `types_rejeu` | scénarios (référence, stress, perturbations nommées R16, `TECHNICAL_CONTROL_NEUTRAL`), blocs de dates C10, manifeste de données |
| 1a | `journal` | validation et sérialisation des enregistrements C09 : version/empreinte des règles, courtier/contrat/volume, horodatages, OHLC, `A_t`, indicateurs, état du détecteur, niveaux, permission connue, version du calendrier, snapshot IA et preuves, bras A/B, coût IA alloué, Bid/Ask, frais, budget/réserves/marge, motif, requêtes, réponses, exécutions |
| 1b | `simulateur_execution` (port `Courtier`) | référence : délai 250 ms, premier tick après délai + un tick adverse (R9) à l'entrée et aux sorties marché/stop ; TP/limite au niveau ou mieux si exécutable ; protections natives avant sorties logicielles ; gaps subis ; stress : Ask = Bid + 1,25 × spread, 1 000 ms, deux ticks adverses ; ordre intrabougie depuis les ticks |
| 1c | `import_ticks` | CSV/CSV.gz du cahier de données §2 → ticks ordonnés + manifeste (source, fuseau, précision, trous connus, SHA-256) ; refus sans manifeste de couverture (R5) |
| 2a | `metriques` | configurations, signaux, refus, fills, positions closes, P&L net, espérance, profit factor (pas de PF infini sur petit effectif), drawdown de fonds propres, fréquence avec jours à zéro, rétention N/A si référence nulle, faible si <50 |
| 2b | `rejeu` | expériences par bloc (100 USD, préchargement sur le seul passé, arrêts non réinitialisés) et rejeu continu 01/01/2020–03/11/2026 ; robot seul puis compte commun |
| 3a | `bootstrap` | blocs de 5 jours de marché contigus, 10 000 réplications, graine 20261104, percentiles 2,5/97,5 interpolation linéaire, réplications sans trade comptées |
| 3b | `paper_ab` | deux portefeuilles complets indépendants à 100 USD (référence, référence + veto), réponses IA archivées rejouées, coût IA déduit une fois |
| 4 | `rapport_validation` | rapports C10/A13 sous `.local/reports/`, sans secret ni numéro de compte ; précision JSON jamais présentée comme taux de réussite |

Cas : **C11.12** (gap au stop, SL/TP même milliseconde, flux absent), **C11.14** (journaux de décision
identiques entre `app.rejeu` et la boucle `app.paper` alimentée par les mêmes ticks via doublures), A14 « comptes
A/B séparés », « précision JSON jamais présentée comme taux de réussite ».

### 7.I `infrastructure` — phase 9 (segments minimaux dès la phase 1)

Couches confirmées : 0a fichiers et horloge, 0b SQLite du robot, 0c connexion MT5, 0d HTTP, 0e SQLite du service IA, 1a adaptateurs MT5, 1b adaptateurs IA, 2 qualification C04 (phase 9 : 0a, 0b, 0c, 1a, 2 ; phase 10 : 0d, 0e, 1b). Unités : `mt5/flux_ticks`, `mt5/courtier` (magic par stratégie, commentaire = empreinte courte de la clé
d'intention, `type_filling` lu du symbole, rapprochement par historique), `mt5/calcul_courtier`, `mt5/compte`
(netting/hedging, levier, stop-out), `mt5/qualification_c04` (fiche d'environnement horodatée sous
`.local/reports/` sans numéro de compte, faisabilité du volume minimal à 0,5 %, règle de liaison d'un symbole par
sous-jacent, `ENVIRONMENT_NOT_READY` motivé, contrôle empirique de l'heure des ticks R14), `sqlite/stockage`,
`fichiers/journal`, `fichiers/ipc_snapshot` (fermeture immédiate), `fichiers/source_permissions` et
`source_calendrier` (selon R12–R13 ; exportateur MQL5 `mql5/ExportCalendrier.mq5` si retenu, compilé par
l'utilisateur), `fichiers/ticks_historiques`, `horloge/systeme`. Points d'entrée `app.paper`, `app.demo`,
`app.qualification`. Même suite de contrats contre doublures (CI) et contre MT5 démo (`--contrat-mt5-demo`,
lecture seule par défaut ; ordres démo seulement après accord explicite).

### 7.G `service_ia` (A04–A11) — phase 10

Couches confirmées : 0 paramètres ; 1a normalisation, 1b tokens, 1c validateurs, 1d budget ; 2a veto, 2b routeur ; 3a écrivain du snapshot, 3b planificateur ; 4 service. Unités, de l'intérieur vers l'extérieur : paramètres et secrets lus de l'environnement (jamais journalisés) ;
normalisation des textes RSS (item_id, URL canonique, SHA-256, `published_at`/`first_seen`/`fetched_at`, date
absente ou future → pas de veto) ; borne de tokens (octets UTF-8 + 512, ≤4 096) ; validateurs A05/A11 (portage de
`parse_model_output`, `parse_advisory_output`) ; constructeur d'événement A06 (`build_policy_event`) avec table
versionnée issuer/type `POLICY_DECISION` ±3 600 s ; registre de budget (transaction exclusive, `Decimal`, 3 USD
payant, 15 USD global, 24 tentatives et 18 classifications/jour UTC, 150 000 tokens réservés, coût inconnu =
réserve conservée) ; routeur Groq → Gemini → OpenAI facultatif (20 s, pauses 1 puis 2 s, échéance 75 s, 60 s entre
deux requêtes, 401/403 désactive, 429 Retry-After, 5xx/timeout au suivant) ; écrivain atomique du snapshot
(temporaire + fsync + remplacement, réessais 0,05/0,10/0,25 s, heartbeat 30 s, séquence persistée) ; planificateur
Londres (07:45 briefing, 16:15 journal, vendredi 16:45 revue, priorités A09, pas de rafale au redémarrage) ;
dérive hebdomadaire (12 cas). Adaptateurs réels en infrastructure : RSS (60 s, ETag/Last-Modified, 10 s, 1 Mio,
600 s de repli, ≤3 redirections HTTPS vers domaines officiels, refus des DTD/entités), clients HTTP des trois API,
SQLite avec tables A10 et FTS5. Aucun test n'appelle une API ; la qualification sémantique A13 (200 textes annotés
par un humain) reste une tâche de l'utilisateur.

## 8. Affectation des cas d'acceptation

| Cas | Artefact / couche | Cat. | Phase |
|---|---|---|---|
| C11.1 | A 1b, 3 ; B cat. 2 ; H 2b | 1, 2 | 2, 3, 8 |
| C11.2 | D 1a (spread, TTL) ; A 1a (fin de fenêtre) ; B 1a (EMA égales) | 1 | 2–4 |
| C11.3 | A 1b ; D 1a | 1 | 2, 4 |
| C11.4 | A 1a ; B cat. 2 | 1, 2 | 2, 3 |
| C11.5 | D 1b, 2a ; H 1b | 1 | 4, 8 |
| C11.6 | D 3 | 1 | 4 |
| C11.7 | D 2a, 3 ; I qualification micro | 1, 2 | 4, 9 |
| C11.8 | E 1a–3 ; D 6 (FLATTEN prioritaire) | 1, 2 | 6 |
| C11.9 | E 1b | 1 | 6 |
| C11.10 | D 2b, 6 | 1, 2 | 4, 5 |
| C11.11 | D 4, 6 ; I rapprochement démo | 1, 2 | 5, 9 |
| C11.12 | D 4, 5 ; H 1b | 2 | 5, 8 |
| C11.13 | D 1c, 5, 6 | 1, 2 | 4, 5 |
| C11.14 | H 2b + app (rejeu vs paper) ; I (démo vs rejeu des ticks enregistrés) | 2 | 8, 9 |
| S01.6 (7 points) | B 1a–3 ; D cat. 2 (refus à l'exécution, 6ᵉ/7ᵉ entrée) | 1, 2 | 3, 5 |
| A14 — chemin du robot (appel lent sans blocage, réponse tardive, veto expiré, panne neutre vs C05 bloquant, risque identique, A07, snapshot invalide et reprise) | F 1–3 ; D 6 ; E | 1, 2 | 6, 7 |
| A14 — service (conditionnel/historique, citation inventée, discours, calendrier programmé, deux robots sans second appel, budget concurrent, coût inconnu, bornes 24/150 000/3/15, aucun modèle local ni outil) | G ; I (SQLite concurrent) | 1, 2 | 10 |
| A14 — comptes A/B, précision JSON | H 3b, 4 | 2 | 8 |

## 9. Phases d'exécution (arrêt obligatoire à la fin de chacune)

Déroulé commun à chaque phase : orchestrateur et skills de la phase → finalisation des contrats des couches de la
phase → par couche dans l'ordre de `mcl.py statut` : implémenter, tests cat. 1, intégrer, tests cat. 2, régression
intégrale, gate, gel → checkpoint MCL tous les 2–3 niveaux → `tools/verify_project.py` et suite de gouvernance →
commit et push sur `claude/epic-edison-4lurlt` → rapport (unités, contrats, résultats réels des gates, écarts) →
pied d'audit et marqueur → **arrêt**.

| Phase | Contenu | Livrables et critère de sortie | Skills |
|---|---|---|---|
| **0 — Cadrage** | Relevé initial (`git status`, `verify_project`, gouvernance) ; `mcl.py init` composite et par artefact ; `carte.json` (unités et externes de §5–7), `analyser --ecrire` puis `analyser` jusqu'à zéro divergence ; esquisse de tous les contrats de couche ; `COUTURES.md` ; registre `INTERPRETATIONS.md` (§10) | Cartes sans divergence, contrats esquissés, registre soumis à l'utilisateur ; aucun code produit | mcl-robot-planning, mcl, specification-consistency, ema-rsi-repli |
| **1 — Squelette** | `noyau`, segments minimaux, infrastructure minimale, `tools/run_robot_tests.py`, CI, point d'entrée `app.rejeu` | Le squelette produit un journal C09 depuis une fixture ; CI verte | mcl, market-data-causality, risk-execution-contracts |
| **2 — Données et temps (A)** | Couches 0 → {1a, 1b, 1c} → 2 → 3 ; remplacement de l'agrégateur minimal | A figé ; C11.1/3/4 et concordance des indicateurs verts | market-data-causality, ema-rsi-repli, mcl |
| **3 — Moteur EMA (B)** | Couches 0 → {1a–1d} → 2 (T1–T12) → 3 ; remplacement de la stratégie neutre | B figé ; S01.6 et équivalence `ema_setups` verts ; signaux visibles dans le journal, refusés par le segment fondamental | ema-rsi-repli, expert-scalper-m15, mcl |
| **4 — Exécution, partie 1 (D 0–3)** | Types, cotation, prix, gardes de compte, risque, réservations, dimensionnement, arbitrage | Chiffres S01.5 reproduits ; C11.2/5/6/7/10/13 (cat. 1) verts | risk-execution-contracts, broker-account-qualification |
| **5 — Exécution, partie 2 (D 4–6)** | Cycle d'ordre, sorties obligatoires, coordinateur ; intégration B+D ; scénario `TECHNICAL_CONTROL_NEUTRAL` | Cycle de trade complet en rejeu avec courtier scripté ; C11.10–13 verts | risk-execution-contracts |
| **6 — Fondamental (E)** | Décision R12–R13 en début de phase ; couches 0 → {1a, 1b} → 2 → 3 ; remplacement du segment fondamental | C11.8/9 verts ; FLATTEN prioritaire | fundamental-permissions |
| **7 — Contexte IA (F)** | Couches 0 → 3 ; insertion A07 ; remplacement du segment IA | A14 côté robot verts | llm-integration-contracts, ema-rsi-repli |
| **8 — Journal et rejeu (H)** | Couches 0 → 4 ; import des ticks et manifeste | C11.12/14 verts ; rapport de rejeu synthétique sous `.local/reports/` | validation-replay, market-data-causality |
| **9 — Infrastructure et plateforme (I)** | Adaptateurs réels, SQLite, journal fichier, IPC, sources fondamentales, qualification C04, `app.paper`/`app.demo` ; choix du courtier | Contrats verts contre doublures en CI ; procédure de contrat MT5 démo remise à l'utilisateur (exécution sur son poste Windows) ; checklist go/no-go PAPER | broker-account-qualification, deployment-readiness, risk-execution-contracts |
| **10 — Service IA (G)** | Logique du service puis adaptateurs HTTP/RSS/SQLite ; point d'entrée `app.service_ia` | A14 côté service verts sans aucun appel d'API ; procédure de test de conformité manuel avec les clés de l'utilisateur | llm-integration-contracts |
| **11 — Préparation de la validation et de la démo** | Procédures C10 (blocs, référence, stress, perturbations, bootstrap) et PAPER_AB prospectif ; contrôles des données fournies ; checklist go/no-go démo | Outils et procédures prêts ; aucune conclusion économique sans les données réelles et la V1 (R11) | validation-replay, deployment-readiness |

Lacune de skill possible : adaptateur Python MetaTrader5 (non couvert explicitement par une skill) → évaluée en
phase 9 avec `xp-bots-skill-gap-detector`.

## 10. Registre des points d'interprétation (décidés par délégation de l'utilisateur en phase 3)

Lecture littérale proposée ; chaque point devient un test nommé. L'utilisateur a délégué les décisions le
2026-11-05 (critère : potentiel de rentabilité, sans toucher `config/` ni le texte normatif) ; le registre faisant
foi est `mcl/robot-ema-v3/INTERPRETATIONS.md`.

| Id | Point | Proposition |
|---|---|---|
| R1 | Sortie exactement à un instant de clôture M15 (S01.2.1) | Cette clôture n'est pas « strictement postérieure » : aucune préparation ni entrée ; la clôture suivante est ignorée ; `IDLE` ensuite |
| R2 | Issue de signal inconnue au-delà de la clôture suivante (accusé ambigu, C08) | Sous-état technique d'attente sans préparation de repli ; fill confirmé → `OWNED_POSITION` ; refus → `COOLDOWN` d'une clôture à partir de la résolution |
| R3 | « Cotation non croisée » | Bid ≤ Ask (spread nul admis) ; Bid > Ask refusé |
| R4 | Bougie sans aucun Bid en séance, couverture établie | Bougie invalide traitée comme un trou (`DATA_GAP`) |
| R5 | Détection des trous en rejeu (aucun seuil dans C03) | Couverture déclarée par le manifeste des données ; sans manifeste, rejeu refusé ; aucun seuil inventé |
| R6′ | Reprise après trou inexpliqué (R6 révisé en phase 3) | Récupération des ticks manquants ; à défaut, recalcul sur les seules bougies valides, sans nouveau préchauffage (décidé par délégation, registre) |
| R7 | Motif quand une contrainte native SL/TP invalide le plan (C06) | `PROTECTION_ERROR` |
| R8 | Motif quand des positions externes empêchent la coordination (C07) | `ENVIRONMENT_NOT_READY` |
| R9 | « Un tick adverse » (C10) | Un `tick_size` défavorable ajouté au prix du premier tick après le délai |
| R10 | Devises par symbole (C05) et symboles par issuer (A06), absents des exports | Table codée depuis le texte, avec test de concordance sur la spécification |
| R11 | Comparaison V1 (C10) : spécification V1 absente du dépôt | Rétention `N/A` jusqu'à fourniture de la V1 ; aucune conclusion économique |
| R12 | Calendrier : le paquet Python MetaTrader5 n'expose aucune fonction Calendar | Décidé (phase 3, délégation) : exportateur MQL5 minimal du calendrier natif MT5 (CSV versionné vers `Common/Files`) ; calendrier livré par le module fondamental admis en alternative |
| R13 | Transport des permissions fondamentales (non spécifié) | Fichiers JSONL écrits atomiquement dans un dossier dédié ; à confirmer avec le module externe |
| R14 | Heure des ticks MT5 : documentation = UTC, rapports contradictoires (heure serveur) | Contrôle empirique obligatoire en qualification ; écart non expliqué → `ENVIRONMENT_NOT_READY` |
| R15 | Réglages d'exploitation non normatifs (intervalle de scrutation ≤250 ms, chemins, `deployment_id`, magic) | Hors `config/` figé : gabarit `deploiement/environnement.exemple.json`, valeurs dans `runtime/` |
| R16 | Six perturbations C10 | Scénarios nommés réservés au rejeu, jamais chargeables en `PAPER`/`DEMO` |
| R17 | Priorité LONDON avant EMA sans robot 2 | Coordinateur générique testé avec des signaux `LONDON_V3` synthétiques |
| R18 | Seuil RSI d'armement (S01.2 point 4) sans clé dédiée | Clés `long_signal_rsi_min` / `short_signal_rsi_max` (décidé en phase 3) |

## 11. Vérification

- Lanceur : `python tools/run_robot_tests.py` (toute la suite) ; filtres `--artefact <paquet> --couche <id>
  --categorie 1|2`.
- Gate d'une couche : `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier
  mcl/<artefact> gate --couche <id> --unitaire "<lanceur cat. 1>" --integration "<lanceur cat. 2>" --regression
  "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"`, puis `figer --couche <id>` sans
  rien modifier entre les deux ; `verifier --mode strict` par artefact et sur la carte composite.
- Fin de phase : `python tools/verify_project.py`,
  `python .agents/skills/xp-bots-maintain-agent-skills/scripts/run_governance_suite.py`, `mcl.py statut`, CI verte.
- Bout en bout : après la phase 5, `python -m xpbots.app.rejeu` avec `TECHNICAL_CONTROL_NEUTRAL` montre dans le
  journal un cycle signal → ordre → fill → sortie ; après la phase 8, rapport de rejeu synthétique ; après la
  phase 9, sur le poste Windows : qualification C04 sur compte démo, boucle `PAPER` d'une session, puis
  comparaison au rejeu des ticks enregistrés (C11.14).

## 12. Limites et risques

- Contrôles verts ≠ rentabilité ni comportement prouvé chez un courtier réel ; verdict par défaut « non validé ».
- Données à fournir par l'utilisateur pour C10 : ticks Bid/Ask des symboles exacts (02/12/2019–03/11/2026),
  historique des conditions de contrat, calendrier avec `known_at`, permissions historiques, spécification V1.
- À 100 USD et 0,5 %, le contrat standard est souvent infinançable (S01.5) : contrats micro vérifiés nécessaires,
  sinon « compte incompatible avec la fréquence visée ».
- MT5 Python : Windows seulement, scrutation (pas d'événement `OnTick`), aucun calendrier, horodatage à qualifier ;
  aucun test réel MT5 possible dans cet environnement Linux ; le testeur de stratégie MT5 n'est pas utilisé (rejeu
  propre par ticks).
- Performances Python d'un rejeu multi-annuel par ticks : acceptables hors ligne ; toute optimisation se fait à
  comportement constant sous harnais complet.

# 08 — Contrats des frontières externes, finalisés tôt

Retour au [plan directeur](README.md). MCL finalise tôt les contrats des frontières externes, parce que les
doublures des couches internes en dépendent (exception de la skill `mcl-matryoshka-construction-layers`, étape 6).
Ce document fixe ces contrats pour que toute l'implémentation (phases 0 à 12) se fasse dans le conteneur, sans le
poste Windows. Chaque contrat est ensuite confronté à la réalité par une sonde ou un test de contrat en
sous-étape 13.1 ; une divergence ouvre un défigeage formel « correction » de la seule couche concernée.

## 1. Correspondance avec les frontières du document 02

| Frontière (document 02, §7) | Contrat | Vérification réelle |
|---|---|---|
| Flux de ticks MT5 | §2.1, §2.4 (ticks), §5 | Sondes S-01, S-08 |
| Exécution du courtier | §2.1, §2.2, §2.5, §2.6, §2.7 | Sondes S-02 à S-06 |
| Calculs du courtier | §2.1, §2.4, §2.8 | Sonde S-07 |
| Horloge | §2.9 | Dérive mesurée en 13.1 |
| Stockage d'état | §8 | Arrêt brutal puis reprise, sous Windows |
| Journal | §7 | Relecture canonique identique |
| Snapshot IA | §10 | Écriture et lecture concurrentes sous Windows |
| Fichiers de ticks | §6 | Validation d'un jeu réel en 13.3 |
| Exports de ticks (S-09, S-10) | §6.4 | Sondes S-09, S-10 |
| Dossier d'échange des permissions (D-11) | §3 | Séance complète avec le vrai module |
| Export MQL5 du calendrier et des séances (D-12) | §4 | Export réel comparé au terminal |
| API LLM | §10 | Requêtes de conformité si D-17 est accordée |
| Flux RSS | §10 | Lecture réelle Fed et BCE |
| SQLite du service | §8, §10 | Concurrence des réservations |

## 2. API Python `MetaTrader5` 5.0.6231

Constats établis le 05/11/2026 par lecture, sans exécution, du paquet officiel téléchargé depuis PyPI (fichier
`__init__.py` et chaînes du module compilé `_core`). La documentation en ligne de MQL5 n'était pas joignable
depuis le conteneur ; les points qu'elle seule tranche sont qualifiés par sonde.

### 2.1 Fonctions

Le module expose 32 fonctions : `initialize`, `login`, `shutdown`, `version`, `last_error`, `account_info`,
`terminal_info`, `symbols_total`, `symbols_get`, `symbol_info`, `symbol_info_tick`, `symbol_select`,
`market_book_add`, `market_book_get`, `market_book_release`, `copy_rates_from`, `copy_rates_from_pos`,
`copy_rates_range`, `copy_ticks_from`, `copy_ticks_range`, `orders_total`, `orders_get`, `order_calc_margin`,
`order_calc_profit`, `order_check`, `order_send`, `positions_total`, `positions_get`, `history_orders_total`,
`history_orders_get`, `history_deals_total`, `history_deals_get`. Aucune ne fournit le calendrier économique ni
les horaires de séance (les champs `session_*` des symboles sont des statistiques de séance), d'où D-12.

| Fonction | Usage dans le robot | Couche | En cas d'échec |
|---|---|---|---|
| `initialize` (sans identifiants) | S'attacher au terminal déjà connecté | `mt5_session` | Pas de démarrage, alerte |
| `version`, `terminal_info`, `account_info` | Version, connexion, droits, dossier commun ; compte (C04) | `mt5_session`, `mt5_specifications` | `ENVIRONMENT_NOT_READY` |
| `symbol_select`, `symbol_info` | Rendre le symbole visible ; caractéristiques C04, relues avant chaque ordre | `mt5_specifications` | `ENVIRONMENT_NOT_READY` |
| `symbol_info_tick` | Contrôle de vivacité seulement ; les décisions utilisent les ticks du flux | `mt5_flux` | État de connexion dégradé |
| `copy_ticks_from`, `copy_ticks_range` | Flux incrémental et rattrapage, avec `COPY_TICKS_ALL` | `mt5_flux` | Trou de couverture (P-01, P-03) |
| `order_calc_profit`, `order_calc_margin`, `order_check` | Port de calcul (C07) | `mt5_calculs` | `ENVIRONMENT_NOT_READY` |
| `order_send` | Entrée protégée, ajustement du TP, clôture | `mt5_execution` | Classement du §2.6 |
| `positions_get`, `orders_get`, `history_orders_get`, `history_deals_get` | Rapprochement, propriété, positions externes, commissions réelles | `mt5_execution`, `mt5_calculs` | Rapprochement repris à la cadence suivante |
| `last_error` | Code d'erreur après un résultat `None` | toutes | Journalisé |
| `shutdown` | Arrêt propre | `mt5_session` | — |

**Interdits** : `login` (les identifiants restent dans le terminal) ; les aides `Buy`, `Sell` et `Close` du paquet,
qui renvoient jusqu'à dix fois un ordre refusé pour requote ou prix invalide, ce que C08 interdit
(« aucune retransmission aveugle ») ; `copy_rates_*` pour décider (les bougies sont reconstruites depuis les
ticks ; les bougies natives ne servent qu'à une comparaison, P-01) ; tout appel depuis le cœur.

**Dépendance** : le paquet exige `numpy` (déjà épinglée dans `requirements-dev.txt`) ; le fichier
`requirements-windows.txt`, écrit en phase 11 et installé en 13.1, épingle donc `MetaTrader5` 5.0.6231 (marqueur
`sys_platform == "win32"`), `numpy` et `tzdata` aux versions de `requirements-dev.txt`. Les tableaux renvoyés
sont convertis en objets du noyau dans l'infrastructure, jamais transmis au cœur. Le module n'est importé que par
la fabrique de l'enveloppe `assemblage`, puis injecté (document 02, §6.9).

### 2.2 Constantes utilisées

Toujours lues depuis le module (`MetaTrader5.<NOM>`), jamais recopiées en nombres ; le faux module des tests
reproduit les noms et les valeurs du fichier `__init__.py` de la version 5.0.6231.

| Famille | Constantes |
|---|---|
| Copie de ticks et drapeaux | `COPY_TICKS_ALL`, `TICK_FLAG_BID`, `TICK_FLAG_ASK` |
| Ordres | `TRADE_ACTION_DEAL`, `TRADE_ACTION_SLTP`, `ORDER_TYPE_BUY`, `ORDER_TYPE_SELL`, `ORDER_FILLING_FOK`, `ORDER_FILLING_IOC`, `ORDER_FILLING_RETURN`, `ORDER_TIME_GTC` |
| Symbole | `SYMBOL_CALC_MODE_FOREX`, `SYMBOL_TRADE_MODE_FULL` et autres modes de négociation, `SYMBOL_TRADE_EXECUTION_MARKET` et autres modes d'exécution, `SYMBOL_CHART_MODE_BID` |
| Compte | `ACCOUNT_TRADE_MODE_DEMO`, `ACCOUNT_TRADE_MODE_REAL`, `ACCOUNT_MARGIN_MODE_RETAIL_NETTING`, `ACCOUNT_MARGIN_MODE_RETAIL_HEDGING`, `ACCOUNT_STOPOUT_MODE_PERCENT`, `ACCOUNT_STOPOUT_MODE_MONEY` |
| Transactions | `DEAL_ENTRY_IN`, `DEAL_ENTRY_OUT`, `DEAL_REASON_SL`, `DEAL_REASON_TP`, `DEAL_REASON_SO`, `DEAL_TYPE_BUY`, `DEAL_TYPE_SELL` |
| Codes de retour | `TRADE_RETCODE_*` du §2.6 ; erreurs de fonction `RES_*` du §2.7 |

### 2.3 Garde du type de compte

`account_info().trade_mode` doit valoir `ACCOUNT_TRADE_MODE_DEMO` en mode `DEMO` et `ACCOUNT_TRADE_MODE_REAL` en
mode `REEL` ; tout autre cas interdit le démarrage. Les procédures humaines ne peuvent ainsi jamais faire envoyer un
ordre réel par erreur.

### 2.4 Champs lus

| Structure | Champs | Destination |
|---|---|---|
| `terminal_info()` | `connected`, `trade_allowed`, `tradeapi_disabled`, `commondata_path`, `build` | Connexion, droits, dossier commun (§3, §4, §10) |
| `account_info()` | `trade_mode`, `leverage`, `margin_mode`, `currency`, `balance`, `equity`, `margin`, `margin_free`, `margin_level`, `margin_so_mode`, `margin_so_call`, `margin_so_so`, `trade_allowed`, `trade_expert`, `limit_orders`, `company`, `server` ; `login` jamais journalisé | Profil de compte, fonds propres, marge (C04, C07) |
| `symbol_info()` | `trade_tick_size`, `point`, `digits`, `trade_contract_size`, `trade_tick_value`, `volume_min`, `volume_max`, `volume_step`, `volume_limit`, `trade_stops_level`, `trade_freeze_level`, `filling_mode`, `order_mode`, `trade_mode`, `trade_exemode`, `trade_calc_mode`, `currency_base`, `currency_profit`, `currency_margin`, `chart_mode`, `margin_initial`, `margin_maintenance`, `spread_float` | Profil d'instrument (C04) |
| Ticks (`copy_ticks_*`) | `time_msc`, `bid`, `ask`, `flags` ; `time`, `last`, `volume`, `volume_real` ignorés | Événements tick (C03) ; heure convertie par la table du §5 |
| Positions et ordres | `ticket`, `identifier`, `type`, `magic`, `comment`, `symbol`, `volume`, `price_open`, `sl`, `tp`, `time_msc`, `reason` | Rapprochement, propriété (C08) |
| Transactions (`history_deals_get`) | `ticket`, `order`, `position_id`, `type`, `entry`, `reason`, `magic`, `comment`, `volume`, `price`, `commission`, `swap`, `fee`, `profit`, `time_msc` | Remplissages, sorties SL/TP natives, frais réels |

### 2.5 Requêtes d'ordre

- **Entrée protégée** : `action` = `TRADE_ACTION_DEAL` ; `symbol` ; `volume` (décimal sur la grille, converti en
  flottant à l'envoi) ; `type` = `ORDER_TYPE_BUY` ou `ORDER_TYPE_SELL` ; `price` = Ask ou Bid de la cotation retenue ;
  `sl` et `tp` du plan C06 dans la **même** requête (S-02) ; `deviation` = g exprimée en points, utilisée seulement
  par les modes d'exécution qui l'honorent ; `type_filling` = mode qualifié par S-04, de préférence un mode qui
  annule le reliquat ; `type_time` = `ORDER_TIME_GTC` ; `magic` et `comment` selon D-08.
- **Ajustement du TP** : `action` = `TRADE_ACTION_SLTP`, `position` = ticket, `sl` inchangé, `tp` recalculé.
- **Clôture** : `action` = `TRADE_ACTION_DEAL`, sens opposé, `position` = ticket, volume de la position possédée.
- **Contrôle préalable** : `order_check` avec la requête exacte avant chaque envoi ; un refus vaut refus définitif
  motivé (marge, volume, droits), sans envoi.

### 2.6 Classement des codes de retour de `order_send`

Classement littéral de C06 : seuls les refus de fondamental, de risque, de volume, de calendrier ou de droits sont
permanents ; un refus lié au prix peut attendre une nouvelle cotation conforme jusqu'au TTL, après un nouveau
contrôle complet. Une réponse dont l'issue est incertaine n'est jamais un rejet (C08).

| Codes | Classe | Effet dans le cœur |
|---|---|---|
| `TRADE_RETCODE_DONE` | Exécuté | Remplissage ; issue « rempli » au premier volume non nul |
| `TRADE_RETCODE_DONE_PARTIAL` | Exécuté partiellement | Reliquat annulé, partie exécutée gérée (C08) |
| `TRADE_RETCODE_PLACED` | Accepté non exécuté | Rapprochement avant toute autre décision |
| `TRADE_RETCODE_REQUOTE`, `TRADE_RETCODE_PRICE_CHANGED`, `TRADE_RETCODE_PRICE_OFF`, `TRADE_RETCODE_TOO_MANY_REQUESTS` | Refus non permanent | Attente d'une cotation conforme jusqu'au TTL ; nouvelle requête après contrôle complet ; `SIGNAL_EXPIRED` au TTL (P-08) |
| `TRADE_RETCODE_INVALID_VOLUME`, `TRADE_RETCODE_LIMIT_VOLUME` | Refus permanent (volume) | `MIN_VOLUME_OR_RISK_REJECT` |
| `TRADE_RETCODE_NO_MONEY` | Refus permanent (risque) | `MARGIN_REJECT` |
| `TRADE_RETCODE_INVALID_STOPS` | Refus permanent (contrainte native) | `PROTECTION_ERROR`, détail `CONTRAINTE_NATIVE_AVANT_ORDRE` |
| `TRADE_RETCODE_LIMIT_POSITIONS`, `TRADE_RETCODE_LIMIT_ORDERS` | Refus permanent (risque du compte) | `ACCOUNT_RISK_CAP` |
| `TRADE_RETCODE_MARKET_CLOSED`, `TRADE_RETCODE_TRADE_DISABLED`, `TRADE_RETCODE_CLIENT_DISABLES_AT`, `TRADE_RETCODE_SERVER_DISABLES_AT`, `TRADE_RETCODE_LONG_ONLY`, `TRADE_RETCODE_SHORT_ONLY`, `TRADE_RETCODE_CLOSE_ONLY`, `TRADE_RETCODE_ONLY_REAL`, `TRADE_RETCODE_INVALID_FILL` | Refus permanent (droits ou environnement) | `ENVIRONMENT_NOT_READY` et alerte |
| `TRADE_RETCODE_TIMEOUT`, `TRADE_RETCODE_CONNECTION`, absence de réponse dans `request_ack_timeout_seconds` | Issue inconnue | `UNKNOWN_ORDER_STATE` : verrou et rapprochement (C08) |
| Tout autre code | Issue inconnue par prudence | `UNKNOWN_ORDER_STATE` et alerte |

### 2.7 Erreurs des fonctions

Un résultat `None` est suivi de `last_error()`. `RES_E_AUTO_TRADING_DISABLED` → `ENVIRONMENT_NOT_READY` et alerte
(trading algorithmique désactivé, procédure H-03) ; `RES_E_AUTH_FAILED`, `RES_E_INVALID_VERSION`,
`RES_E_UNSUPPORTED` → arrêt du démarrage ; erreurs de communication internes (`RES_E_INTERNAL_FAIL*`) et
`RES_E_FAIL` → issue inconnue si une requête d'ordre était en cours, sinon nouvelle tentative à la cadence
suivante ; `RES_E_NOT_FOUND` sur l'historique → trou de couverture.

### 2.8 Données que l'API n'expose pas

| Donnée (C04) | Source | Contrôle |
|---|---|---|
| Commissions et frais par ordre | Fiche publiée du compte, relevée en H-03 et datée | Égalité avec `commission` et `fee` des transactions de démonstration (sonde S-07) ; zéro seulement si confirmé |
| Horaires de cotation et de négociation | Service MQL5, `seances_<symbole>.json` (§4.2) | Comparaison avec la fiche du symbole |
| Calendrier HIGH | Service MQL5, `calendrier.json` (§4.1) | Comparaison avec la vue calendrier du terminal |
| Fermetures exceptionnelles | Fichier tenu par l'humain (§4.3) | Validation au démarrage |
| Convention de déclenchement SL/TP | Sonde S-03 | Preuve consignée au rapport de qualification |

### 2.9 Horloge

L'horloge système (UTC en millisecondes) date la réception des événements et pilote les délais ; un temps monotone
mesure les durées. Son écart à l'heure des ticks est mesuré en 13.1 et consigné ; il ne corrige jamais l'heure des
ticks, qui suit la table du §5.

## 3. Dossier d'échange des permissions (D-11)

Emplacement, écriture et lecture : [document 01](01_architecture.md), §2.1. Un fichier contient exactement un
message JSON strict (UTF-8, clés uniques, aucun nombre non fini) aux champs de C05 :

| Champ | Type | Contrainte |
|---|---|---|
| `schema` | texte | Exactement `fundamental-permission-v1` |
| `canonical_symbol` | texte | Symbole de l'univers figé, identique au nom du fichier |
| `sequence` | entier | Strictement croissant par symbole |
| `issued_at_utc`, `known_at_utc`, `valid_from_utc`, `valid_until_utc` | texte | ISO-8601 UTC à la milliseconde, suffixe `Z` ; ordre et durées de C05 |
| `direction` | texte | `ANY`, `LONG_ONLY` ou `SHORT_ONLY` |
| `risk_state` | texte | `ALLOW`, `NO_NEW` ou `FLATTEN` |
| `model_version`, `input_snapshot_id` | texte | Non vides, conservés au journal |

Aucune autre clé n'est admise.

## 4. Exports du service MQL5 (D-12)

Fichiers JSON stricts en UTF-8 sous `XPBots/export/v1/` du dossier commun, écrits par fichier temporaire puis
remplacement ([document 01](01_architecture.md), §2.2). Les heures du serveur sont des textes
`AAAA.MM.JJ HH:MM:SS` ; leur conversion en UTC suit la table du §5.

### 4.1 `calendrier.json`

| Champ | Type | Contenu |
|---|---|---|
| `schema` | texte | `xp-export-calendrier-v1` |
| `version` | entier | Strictement croissant à chaque export |
| `export_serveur`, `export_gmt` | texte | Heure du serveur et heure GMT du terminal au moment de l'export |
| `fenetre_debut_serveur`, `fenetre_fin_serveur` | texte | Fenêtre couverte (document 01, §2.2) |
| `evenements` | liste | Un objet par valeur d'événement d'importance haute des devises USD, EUR et GBP |
| `evenements[].id_valeur`, `evenements[].id_evenement` | entier | Identifiants natifs du calendrier |
| `evenements[].code`, `evenements[].nom` | texte | Code et nom natifs de l'événement |
| `evenements[].devise` | texte | Devise du pays de l'événement |
| `evenements[].importance` | texte | Importance native (seule la haute est exportée) |
| `evenements[].type`, `evenements[].secteur` | texte | Type et secteur natifs, utiles à la table des décisions de politique monétaire (A06) |
| `evenements[].heure_serveur` | texte | Heure prévue de l'événement |
| `evenements[].revision` | entier | Révision native de la valeur |

Le robot fixe l'heure de connaissance d'un événement à la première lecture où il apparaît ou change (heure,
importance, révision) et conserve toutes les versions (C05).

### 4.2 `seances_<symbole>.json`

| Champ | Type | Contenu |
|---|---|---|
| `schema` | texte | `xp-export-seances-v1` |
| `version`, `export_serveur`, `export_gmt` | entier, texte | Comme au §4.1 |
| `symbole` | texte | Nom exact du symbole chez le courtier |
| `jours` | liste de 7 objets | Un par jour de semaine du serveur, du dimanche au samedi (`DAY_OF_WEEK_*`) |
| `jours[].cotation`, `jours[].negociation` | listes d'intervalles | Début et fin en heure du serveur, tels que rendus par `SymbolInfoSessionQuote` et `SymbolInfoSessionTrade` |

### 4.3 `fermetures_exceptionnelles.json`

| Champ | Type | Contenu |
|---|---|---|
| `schema` | texte | `xp-fermetures-v1` |
| `version` | entier | Croissant à chaque modification |
| `date_releve` | texte | Date UTC du dernier relevé des avis du courtier |
| `fermetures` | liste | Éventuellement vide |
| `fermetures[].symbole` | texte | Nom exact chez le courtier |
| `fermetures[].debut_utc`, `fermetures[].fin_utc` | texte | ISO-8601 UTC |
| `fermetures[].nature` | texte | `FERMETURE` ou `SEANCE_REDUITE` |
| `fermetures[].source` | texte | Lien ou date de l'avis |

## 5. Table de conversion heure du serveur → UTC

Établie par la sonde S-01, versionnée et datée : `schema` = `xp-heure-serveur-v1` ; nom du serveur ; liste de
segments `debut_utc`, `fin_utc`, `decalage_secondes` (décalage entier, éventuellement nul si les ticks sont déjà en
UTC) ; mesures qui la justifient. Un instant hors de tout segment est refusé (`ENVIRONMENT_NOT_READY`).

## 6. Fichiers de ticks

### 6.1 Format canonique

Format des [données requises](../../data/03_Donnees_Historiques_Requises_et_Validation.md), §2 : colonnes
`canonical_symbol`, `broker_symbol`, `time_utc_ms`, `sequence`, `bid`, `ask` ; CSV UTF-8 compressé gzip, un fichier
par symbole et par mois, `data/raw/ticks/<SYMBOLE>/<AAAA-MM>.csv.gz`. Le Parquet exigerait une dépendance
nouvelle : il n'est pas lu.

### 6.2 Manifeste

`manifeste.json` par symbole : pour chaque fichier, nom, SHA-256, nombre de lignes, premier et dernier
`time_utc_ms`, source, fuseau d'origine, date de récupération, booléen `contrefactuel`.

### 6.3 Registre des trous

`trous.json` par symbole : intervalles `debut_ms`, `fin_ms` et motif déclarés par la source ; c'est lui qui établit
la couverture historique (P-01).

### 6.4 Exports bruts

Formats relevés par les sondes S-09 (export du terminal) et S-10 (source tierce), décrits dans l'unité
`formats_exports` de l'artefact `donnees-historiques` ; ils ne sont jamais lus par le rejeu directement.

## 7. Journaux

Format arrêté par D-07 ; esquisse détaillée, finalisée avec la couche `journal` du noyau.

- **Enveloppe commune** de chaque ligne : `type`, `version_schema`, `deploiement`, `bras`, `mode`,
  `instant_utc_ms`, `numero` (croissant), `empreinte_regles` (empreintes des deux configurations).
- **Types et champs propres** : le [document 01](01_architecture.md), §9.1, liste les contenus de `CLOTURE`,
  `INTENTION`, `ORDRE`, `REPONSE`, `EXECUTION`, `PROTECTION`, `CLOTURE_POSITION`, `COMPTE`, `ALERTE`,
  `DEMARRAGE`, `ARRET`, `RAPPROCHEMENT`, avec `motif` et `detail` (§9.3).
- **Journal d'entrées** : `numero`, `instant_reception_utc_ms`, `type_evenement`, `contenu` (forme canonique de
  l'événement ou du résultat de calcul).
- Fichiers quotidiens `logs/<deployment_id>/decisions_<AAAA-MM-JJ>.jsonl` et `entrees_<AAAA-MM-JJ>.jsonl`.

## 8. État persistant SQLite

Esquisse finalisée avec la couche `depot_sqlite` : table `meta` (version du schéma, identifiant de déploiement,
empreintes) ; table `etat` (espace, clé, valeur JSON canonique, instant de mise à jour) pour les espaces du
[document 01](01_architecture.md), §7.1 ; table `intentions` (clé d'intention unique, état, contenu, instant) ;
table `reservations` (clé d'intention, risque réservé, volume, instant) ; table `arrets` (bras, type, actif,
depuis, décision qui l'a levé). Transactions `BEGIN IMMEDIATE`, journal WAL, une écriture par événement avant
toute commande (§7.2 du document 01). Le registre de budget du service IA a sa propre base (A09, A10).

## 9. Rapport de qualification et registre de déploiement

- **Rapport de qualification** (`.local/reports/qualification/`) : date, versions (terminal, paquet), serveur,
  type de compte (démo ou réel), devise, levier, mode de marge ; par symbole, tous les champs du §2.4 et du §2.8 ;
  résultat de chaque sonde ; liste `ENVIRONMENT_NOT_READY` ; jamais de numéro de compte ni d'identifiant.
- **Registre de déploiement** (`runtime/<deployment_id>/registre.json`) : identifiant, mode, symboles liés et
  justification de la règle de liaison (C04), empreintes des configurations, commit du code, constantes
  d'ingénierie (D-09, plafond du dossier d'échange, cadences d'export), table de conversion horaire retenue,
  statut A13, décisions humaines datées (H-12).

## 10. Frontières déjà fixées par la spécification

- **Snapshot IA** : format, écriture et lecture exacts de A10 ; validation de l'unité `snapshot` de `contexte-ia`.
- **API LLM** : gabarits de requête et lecture des réponses de A08, schémas et prompts exportés dans `schemas/` et
  `prompts/`.
- **Flux RSS** : collecte et normalisation de A04.
- **SQLite du service** : tables minimales de A10, transactions de A09.

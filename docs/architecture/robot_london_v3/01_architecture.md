# 01 — Architecture cible du robot London (`LONDON_V3`)

Retour au [plan directeur](README.md). Les règles métier citées viennent de la
[spécification 02](../../../livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md) ; les valeurs
sont lues dans les [paramètres techniques](../../../config/parametres_figes_v3.json) et les
[paramètres IA](../../../config/parametres_IA_integration_v1.json), jamais recopiées dans le code.

## 1. Principes directeurs

| # | Principe | Énoncé opérationnel | Source |
|---|---|---|---|
| 1 | Un seul moteur de décision | Le même code Python décide en rejeu, papier, `PAPER_AB`, démonstration et réel ; seule la coquille (adaptateurs, horloge, stockage) change | C11.14 ; skill de planification, garde-fous |
| 2 | Cœur déterministe sans entrée-sortie | Les composants de décision reçoivent des événements horodatés et rendent des commandes et des enregistrements. Ils ne lisent ni horloge, ni fichier, ni réseau, ne dorment jamais et n'attendent aucune réponse | A03, A14 point 1, C06 |
| 3 | Causalité par construction | Toute donnée porte son instant de disponibilité réelle ; une unité ne lit jamais une donnée indisponible à l'instant de décision ; une H1 partielle n'est jamais exposée | C03.1, C03.4, S02.1 |
| 4 | Configuration figée chargée, jamais recopiée | Lecture stricte des deux exports, contrôle de leur empreinte contre [conservation_ressources.json](../../validation/conservation_ressources.json), refus de démarrer si une option désactivée est activée | C01, C02, règles du projet §2 |
| 5 | Échec sûr | Toute inconnue bloque les nouvelles entrées sans inventer de permission ; sorties et protections passent avant toute entrée | C04, C05, C08, A12 |
| 6 | Persistance avant action | Intention et réservation validées en base avant l'envoi de l'ordre ; quotas écrits au premier remplissage ; restauration avant toute décision | C08, S02.4 |
| 7 | Indépendance des méthodes | Le moteur London ignore coordinateur et courtier ; le coordinateur ne connaît que les signaux et issues définis dans le noyau ; l'orchestration reçoit les stratégies par injection, sans les importer (D-18) | C08, règles du projet §2 |
| 8 | Numérique explicite | Flottants 64 bits pour indicateurs et formules de signal ; décimal sur la grille native pour niveaux exécutables, volumes et montants | C03.12 |
| 9 | Observabilité complète | Journal C09 à chaque clôture et pour chaque intention ; journal d'entrées permettant un rejeu exact | C09, C11.14 |
| 10 | Dépendances confinées | Bibliothèque standard dans le cœur ; `MetaTrader5`, SQLite, système de fichiers, réseau et horloge seulement dans l'infrastructure, vérifié par les cartes MCL | MCL règle 3 ; règles du projet §4 |

Conséquence directe du principe 2 : l'interdiction d'appel LLM, HTTP ou d'attente réseau entre le signal et
l'ordre (A03) devient une propriété de structure, contrôlée par les cartes MCL (imports interdits) et par un
test de pureté du code source (document 03, §8).

## 2. Processus et échanges sur le poste Windows

```text
Poste Windows de l'utilisateur
  Terminal MT5 (compte de démonstration, puis réel après décision)
      ▲ ordres, requêtes                 │ ticks, spécifications, compte, positions, transactions
      │                                  ▼
  Robot XP-Bots : python -m xpbots.app.robot --mode PAPER | PAPER_AB | DEMO
      coquille : adaptateur MT5, horloge système, SQLite (runtime/), journaux (logs/), alertes locales
      cœur     : donnees-temps -> moteur-london -> coordinateur (+ contrôles C05, contexte IA A07)
      ▲ lecture chaque seconde (les trois échanges, sous le dossier commun du terminal)
  XPBots/ai/v1/context_latest.json    XPBots/fondamental/v1/permission_*.json    XPBots/export/v1/*.json
      ▲ écriture atomique, 30 s       ▲ module fondamental externe (D-11)        ▲ service MQL5 XPBotsExport (D-12)
  Service IA : python -m xpbots.service_ia  --HTTPS-->  Groq, Gemini (OpenAI facultatif, désactivé)
                                            --HTTPS-->  RSS officiels Fed, BCE, BoE
  Module fondamental externe (fourni par l'utilisateur, hors de ce plan)
```

| Échange | Producteur | Consommateur | Emplacement | Règles |
|---|---|---|---|---|
| Snapshot IA | Service IA | Robot | `XPBots/ai/v1/context_latest.json` sous le chemin réel `terminal_info().commondata_path` (jamais déduit du nom d'utilisateur) | Écriture atomique, au plus `snapshot_max_bytes`, lecture toutes les `ea_snapshot_poll_seconds` (A10) |
| Permissions fondamentales | Module externe | Robot | `XPBots/fondamental/v1/permission_<SYMBOLE>.json` sous le dossier commun | Schéma `fundamental-permission-v1`, heartbeat attendu `fundamental_expected_heartbeat_seconds` (C05) ; contrat au §2.1 |
| Calendrier HIGH, horaires de séance | Service MQL5 `XPBotsExport` | Robot, service IA (A06) | `XPBots/export/v1/calendrier.json`, `XPBots/export/v1/seances_<symbole>.json` | Versions et heures de connaissance conservées (C05, C04) ; contrat au §2.2 |
| Fermetures exceptionnelles | Humain, d'après les avis du courtier | Robot | `XPBots/export/v1/fermetures_exceptionnelles.json` | Fichier versionné obligatoire, liste éventuellement vide avec date de relevé (C04) |
| État persistant | Robot | Robot | `runtime/<deployment_id>/etat.sqlite` | Transactions exclusives (§7) |
| Journaux | Robot | Rejeu, rapports | `logs/<deployment_id>/` | JSON Lines canonique (§9) |
| Ticks historiques | Humain | Rejeu | `data/raw/ticks/<symbole>/<AAAA-MM>.csv.gz` | Format des [données requises](../../data/03_Donnees_Historiques_Requises_et_Validation.md), §2 ; manifeste SHA-256 |
| Rapports de qualification | Robot (CLI) | Humain | `.local/reports/qualification/` | Hors des preuves historiques ; sans secret ni numéro de compte |

Les emplacements du dépôt sont déjà exclus par `.gitignore` (`runtime/`, `logs/`, `data/raw/`, `.local/`) ; les
échanges vivent hors du dépôt, dans le dossier commun du terminal.

**Contrôle du dossier commun au démarrage** : le service IA écrit sous `XPBOTS_COMMON_FILES_DIR` (A02) et le robot
lit sous `terminal_info().commondata_path`. Si la variable est définie dans l'environnement du robot, elle doit
désigner le même dossier ; sinon, alerte locale déterministe. Dans tous les cas, un snapshot absent ou périmé
laisse le complément IA `NEUTRAL` (A12) et déclenche une alerte, sans effet sur les règles du socle.

### 2.1 Dossier d'échange des permissions fondamentales (D-11)

- **Emplacement** : `XPBots/fondamental/v1/` sous le dossier commun réel du terminal
  (`terminal_info().commondata_path`), même racine que le snapshot IA ; chemin effectif consigné au registre de
  déploiement, jamais déduit du nom d'utilisateur.
- **Fichiers** : un par symbole canonique (`permission_EURUSD.json`, `permission_GBPUSD.json`,
  `permission_XAUUSD.json`) ; chacun contient exactement **un** message `fundamental-permission-v1` (C05), en
  UTF-8 et en JSON strict.
- **Écriture par le module externe** : fichier temporaire dans le même dossier, vidage et synchronisation sur
  disque, puis remplacement atomique ; nouvelle tentative en cas de refus de partage sous Windows ; une séquence
  publiée n'est jamais réécrite. Ces règles sont transmises au fournisseur du module : le robot ne peut pas les
  imposer, il les vérifie.
- **Lecture par le robot** : chaque seconde ; fichier fermé aussitôt lu ; plafond de taille d'ingénierie de
  4 096 octets, consigné au registre de déploiement ; heure de réception = instant UTC de la lecture du nouveau
  contenu, conservée à côté de `known_at` (C05).
- **Acceptation** : validation complète par `message_permission` ; séquence strictement croissante par symbole ;
  un contenu relu avec la même séquence est ignoré et ne renouvelle rien ; une séquence inférieure, un fichier
  tronqué, illisible ou invalide est rejeté et journalisé, sans changement d'état ; l'absence de fichier vaut
  absence de message, donc blocage dès l'expiration du dernier message valide.
- **Interdits** : le robot n'écrit, ne déplace ni ne supprime rien dans ce dossier ; l'écriture est réservée au
  module et au compte de l'utilisateur, comme pour A10.
- **Rejeu** : l'historique des permissions est fourni en JSON Lines avec `known_at` ; chaque message est livré
  au cœur à son heure de réception enregistrée, ou à `known_at` à défaut, jamais plus tôt.
- **Journal d'entrées** : chaque nouveau contenu lu y est écrit avec son heure de lecture (C11.14).

### 2.2 Service MQL5 d'export du calendrier et des séances (D-12)

- **Composant** : programme de type service du terminal, `XPBotsExport`, source `mql5/Services/XPBotsExport.mq5`
  dans le dépôt ; seul code MQL5 du projet ; compilé dans MetaEditor et installé dans le terminal par l'humain.
  `mcl.py` n'analysant pas MQL5, sa structure est contrôlée par convention de module et revue de code ; son
  format de sortie est contrôlé par des tests Python sur fixtures, puis par un test de contrat sur le poste.
- **Sorties**, dans `XPBots/export/v1/` du dossier commun, écrites par fichier temporaire puis remplacement :
  - `calendrier.json` : numéro de version strictement croissant ; heure du serveur et heure GMT du terminal à
    l'export ; fenêtre couverte, du début du jour UTC précédent jusqu'à au moins l'instant d'export plus
    `news_forward_coverage_seconds` ; événements d'importance haute des devises USD, EUR et GBP, avec
    identifiants d'événement et de valeur, code d'événement, devise, type, secteur, heure de l'événement et heure
    de dernière mise à jour, en heure du serveur ;
  - `seances_<symbole_courtier>.json` : numéro de version, heures d'export, et pour chaque jour de semaine les
    intervalles de cotation et de négociation en heure du serveur.
- **Cadence** : calendrier chaque minute, séances au démarrage puis chaque heure (constantes d'ingénierie
  consignées au registre de déploiement). Une annonce modifiée tardivement est ainsi connue du robot au plus tard
  environ une minute après sa mise à jour dans le terminal ; elle déclenche alors blocage et clôture immédiats
  si elle tombe dans sa fenêtre (C05).
- **Fermetures exceptionnelles** : MQL5 ne les fournit pas. L'humain tient
  `XPBots/export/v1/fermetures_exceptionnelles.json`, versionné et daté d'après les avis du courtier (liste
  éventuellement vide avec date de relevé). Fichier absent → `ENVIRONMENT_NOT_READY` (C04 : aucun champ manquant
  ne vaut zéro).
- **Lecture et conversion par le robot** : contrôle d'une nouvelle version chaque seconde ; conversion heure
  serveur → UTC par la table qualifiée de la sonde S-01 ; heure de connaissance d'un événement = instant de la
  première lecture où il apparaît ou change (heure, importance) ; toutes les versions conservées (C05) ; table
  d'importance et de types (décisions de politique monétaire par issuer, utiles à A06) versionnée et relue par
  l'humain ; calendrier périmé si la dernière version lue date de plus de `news_calendar_max_age_seconds` ou si sa
  couverture est insuffisante. Le service IA lit le même export pour l'appariement de A06.
- **Historique de C10** : exporter aujourd'hui l'historique du calendrier produit un calendrier enrichi après
  coup ; son usage en rejeu est déclaré comme approximation exposée à une fuite d'information
  ([données requises](../../data/03_Donnees_Historiques_Requises_et_Validation.md), §4). La collecte prospective
  des versions commence dès la première séance sur le poste (sous-étape 13.1).

## 3. Modes d'exécution

| Mode | Ticks | Exécution | Comptes | Permissions C05 | Veto IA | Usage | Garde d'activation |
|---|---|---|---|---|---|---|---|
| `REJEU` | Fichiers historiques | Simulateur C10 (référence ou stress) | Un compte fictif de 100 USD par expérience | Historique causal, ou scénario explicitement nommé `TECHNICAL_CONTROL_NEUTRAL` | Réponses archivées seulement, jamais réinférées | C10, C11, A13 | — |
| `PAPER` (défaut technique `common.default_mode`) | Flux MT5 direct | Simulateur | Un compte fictif | Fournisseur externe réel | Aucun (`NEUTRAL`) | Contrôle en direct | Robot construit, C11 et A14 verts |
| `PAPER_AB` (défaut IA `default_evaluation_mode`) | Flux MT5 direct | Deux simulateurs | Bras `REFERENCE` et bras `IA`, 100 USD chacun | Mêmes permissions dans les deux bras | Bras `IA` seulement | A13 | Service IA en marche, appels d'API autorisés (D-17) |
| `DEMO` | Flux MT5 direct | Ordres réels sur compte de démonstration | Compte démo | Fournisseur externe réel | Désactivé tant que A13 n'est pas établi | Démonstration prospective C10 | Qualification C04, décision humaine |
| `REEL` | Flux MT5 direct | Ordres réels | Compte réel | Fournisseur externe réel | Seulement après validation financière A13 | Exploitation | Verrouillé : décision de déploiement tracée, critères C10 (skill `xp-bots-deployment-readiness`) |

Le scénario `TECHNICAL_CONTROL_NEUTRAL` est refusé au démarrage en `DEMO` et en `REEL` : il n'existe que pour un
contrôle technique isolé explicitement nommé (C05).

## 4. Événements, commandes et ordre de traitement

### 4.1 Événements d'entrée du cœur

- **Tick reçu** : symbole canonique, symbole du courtier, heure fournisseur convertie en UTC (milliseconde, par
  la table de conversion qualifiée), heure de réception UTC, numéro de réception, Bid, Ask, drapeaux natifs.
- **État de connexion** : terminal ou symbole, connecté ou non, instant.
- **Minuterie** : instant ; émise chaque seconde et aux instants que le cœur a demandés (fin de TTL, délais de
  correction des protections, échéances de sortie, scrutations de rapprochement).
- **Réponse du courtier** : accusé ; exécution (volume, prix moyen, instant, ticket) ; refus (code natif,
  caractère définitif) ; absence de réponse dans le délai ; résultat de rapprochement (positions, ordres,
  transactions) ; état des protections d'une position.
- **Message de permission** : octets reçus et heure de réception locale.
- **Version de calendrier** : identifiant de version, heure de connaissance, événements.
- **Octets du snapshot IA** : contenu lu et heure de lecture.

### 4.2 Commandes rendues par le cœur

- **Envoyer une entrée protégée** : clé d'intention, symbole du courtier, sens, volume, SL, TP, déviation
  demandée, mode de remplissage, numéro magique, commentaire.
- **Ajuster le TP** d'une position, SL inchangé.
- **Clôturer** une position (volume, motif, priorité).
- **Annuler le reliquat** d'un ordre partiellement rempli.
- **Rapprocher** : interroger ordres, positions et transactions pour une clé ou un symbole sur une fenêtre de
  temps.
- **Alerter** : code déterministe, gravité, message sans secret (A11).
- **Planifier une minuterie** à un instant donné.
- **Journaliser** des enregistrements C09.

### 4.3 Ordre de traitement d'un événement (C08, A07)

Pour chaque événement, dans chaque bras d'expérience, le cœur applique strictement :

1. **Exécutions et protections natives** : intégrer les réponses du courtier ; un SL ou un TP déjà exécuté fait
   foi.
2. **Clôtures obligatoires**, dans l'ordre : sécurité du compte (garde quotidienne, arrêt global), `FLATTEN`
   externe, début de fenêtre d'annonce (N − `news_before_seconds`), heure de sortie de la méthode
   (`london.force_exit_local`), durée limite (`max_position_wallclock_seconds` après le premier remplissage),
   fermeture native proche (`native_market_close_guard_seconds`), début du blackout UTC. Toute clôture en
   attente bloque les nouvelles entrées sur les symboles concernés.
3. **Bougies** : finaliser la ou les bougies clôturées, mettre à jour les indicateurs (artefact
   `donnees-temps`) puis l'état technique London (range, gel de A_H1, fenêtre).
4. **Admission de chaque nouveau signal**, dans l'ordre de priorité du §4.6 :
   a. limites de la méthode (quotas S02.4, une position London par symbole), appliquées par le moteur avant
   d'émettre ;
   b. permission fondamentale et calendrier (C05), contrôlés au signal ;
   c. contexte IA en mémoire (A07) : pour London, après validation de la cassure et du stop local, avant la
   réservation ;
   d. cotation, stop et TP exécutables, taille, marge et réservations (C06, C07) ; la permission fondamentale
   (C05) et la copie mémoire du contexte IA (A03) sont **recontrôlées juste avant l'envoi**, avec les seules
   informations alors reçues.
5. **Envoi de l'entrée protégée** ; confirmation de la position, du volume et des protections réellement
   créés ; le signal est consommé, même en cas de refus définitif.

Un contexte IA neutre ne lève jamais un refus du socle ; le contexte IA ne peut qu'ajouter un refus (A07, A12).

### 4.4 Clôture des bougies, instant de décision et TTL

- Une bougie `[T, T+900 s)` est close par le **premier événement d'heure fournisseur ≥ T+900 s** ; cet événement
  appartient à la bougie suivante et peut fournir la première cotation d'entrée (C03.2, C11.3). Même règle pour
  `[T, T+3600 s)` en H1, qui n'est disponible qu'à sa clôture et à partir de la réception de son événement de
  clôture (C03.4).
- L'instant de décision est la **clôture théorique** de la bougie de signal ; le TTL expire à cette clôture
  plus `entry_signal_ttl_seconds`, borne exclue (C06), même si l'événement de clôture arrive tard.
- Si aucun événement n'arrive avant la fin du TTL, la configuration technique est tout de même calculée et
  journalisée au premier événement suivant (« configuration potentielle »), et le coordinateur consigne
  `SIGNAL_EXPIRED` : C09 exige de compter séparément configurations, signaux en état négociable et refus.

### 4.5 Un seul port synchrone : les calculs du courtier

Le cœur n'appelle aucune entrée-sortie, sauf un port synchrone unique, le **port de calcul du courtier** :
profit d'une position fictive, marge d'un ordre isolé, contrôle natif d'un ordre, spécifications courantes d'un
symbole, état du compte. Il est nécessaire parce que le dimensionnement doit utiliser les fonctions du courtier
(C04, C07) à l'intérieur du TTL. Il a deux implémentations réelles : l'adaptateur MT5 (`order_calc_profit`,
`order_calc_margin`, `order_check`, `symbol_info`, `account_info`) et le simulateur C10 (formules vérifiées
contre MT5 par la sonde S-07, en sous-étape 13.1). Chaque appel et son résultat sont écrits dans le journal d'entrées, pour que le rejeu
d'une séance réelle rende exactement les mêmes décisions (C11.14).

### 4.6 Simultanéité et priorités

- Ordre stable des événements : numéro de réception (en direct, attribué par la coquille à la réception ; en
  rejeu, ordre du fichier, qui conserve l'ordre natif à milliseconde égale) (C03.1).
- Signaux d'une même clôture : ordre de `common.simultaneous_strategy_priority`, puis de
  `common.universe_priority` ; après chaque réservation atomique, les signaux restants sont réévalués (C08).
  Aucun score combinant les signaux, aucune couverture opposée sur un même sous-jacent.

### 4.7 Temporisations

| Temporisation | Clé de configuration | Rôle | Artefact |
|---|---|---|---|
| Validité du signal | `entry_signal_ttl_seconds` | Fin d'admission, borne exclue | `execution-coordinateur` |
| Âge de cotation | `quote_max_age_seconds` | Cotation admissible | `execution-coordinateur` |
| Accusé d'ordre | `request_ack_timeout_seconds` | Bascule en état inconnu | `execution-coordinateur` |
| Rapprochement | `reconcile_fast_poll_seconds`, `reconcile_fast_window_seconds`, `reconcile_slow_poll_seconds` | Scrutation après réponse inconnue, alerte après la fenêtre rapide | `execution-coordinateur` |
| Correction des protections | `protective_update_max_attempts`, `protective_update_retry_delays_seconds`, `protective_update_deadline_seconds` | Ajustement du TP après remplissage | `execution-coordinateur` |
| Réessai de sortie | `exit_retry_interval_seconds` | Clôture sans cotation | `execution-coordinateur` |
| Fermeture native | `native_market_close_guard_seconds` | Clôture avant pause ou fermeture | `execution-coordinateur` |
| Blackout de rollover | `rollover_blackout_utc_start`, `rollover_blackout_utc_end` | Clôture et interdiction d'entrée | `execution-coordinateur` |
| Durée maximale | `max_position_wallclock_seconds` | Clôture après le premier remplissage | `execution-coordinateur` |
| Annonces | `news_before_seconds`, `news_after_seconds`, `news_calendar_max_age_seconds`, `news_forward_coverage_seconds` | Fenêtres et validité du calendrier | `controles-fondamentaux` |
| Permissions | `fundamental_max_validity_seconds`, `fundamental_expected_heartbeat_seconds`, `fundamental_timestamp_future_tolerance_seconds` | Validité des messages | `controles-fondamentaux` |
| Snapshot IA | `ea_snapshot_poll_seconds`, `snapshot_max_age_seconds`, `snapshot_max_bytes` | Lecture et validité | `contexte-ia`, `infrastructure` |
| Boucle en direct | D-09 (constante d'ingénierie) | Scrutation des ticks et minuteries fines | `points-entree` |

## 5. Arborescence cible du dépôt

```text
src/xpbots/
  __init__.py                       version du paquet, aucune logique
  noyau/                            artefact noyau
    c0a_temps/ c0b_nombres/ c0c_configuration/ c1a_marche/ c1b_instrument/ c1c_domaine/ c2_journal/
  donnees/                          artefact donnees-temps
    c0a_types/ c0b_sessions/ c1a_constructeur/ c1b_indicateurs/ c1c_couverture/
    c2a_validation/ c2b_etat_indicateurs/ c3_flux/
  london/                           artefact moteur-london
    c0a_parametres/ c0b_types/ c1a_range/ c1b_gel_atr_h1/ c1c_cassure/ c1d_stop/ c1e_quotas/ c2_moteur/
  london_v1/                        artefact moteur-london-v1 (sous-étape 13.4, rejeu de comparaison seulement)
  execution/                        artefact execution-coordinateur
    c0a_types/ c0b_ports_controles/ c0c_garde_cotation/ c0d_prix/ c0e_echeances/
    c1a_port_calcul/ c1b_gardes_compte/ c1c_reservations/ c2a_risque/ c2b_arbitrage/
    c3_dimensionnement/ c4_cycle_ordre/ c5a_sorties/ c5b_reprise/ c6_coordinateur/
  fondamental/                      artefact controles-fondamentaux
  contexte_ia/                      artefact contexte-ia
  orchestration/                    artefact orchestration
  rejeu/                            artefact journal-rejeu
  infra/                            artefact infrastructure : seul lieu des entrées-sorties réelles
  app/                              artefact points-entree : robot, rejeu, qualification, rapports
  service_ia/                       artefact service-ia : processus séparé
  donnees_historiques/              artefact donnees-historiques (sous-étape 13.3) : exports de ticks → format canonique
tests/robot/
  outils/                           fabriques synthétiques, courtier scénarisé, faux module MetaTrader5
  squelette/                        segments minimaux S1 à S7 et test de bout en bout du squelette
  transverses/                      gardes transverses : lanceur, pureté du cœur, carte composite
  noyau/ donnees_temps/ moteur_london/ execution_coordinateur/ controles_fondamentaux/
  contexte_ia/ orchestration/ journal_rejeu/ infrastructure/ points_entree/ service_ia/
  moteur_london_v1/ donnees_historiques/
mql5/Services/XPBotsExport.mq5      service MQL5 d'export du calendrier et des séances (D-12), seul code MQL5
requirements-windows.txt            exigences d'exécution du poste : MetaTrader5, numpy, tzdata (D-05)
tools/run_robot_tests.py            lanceur unique des tests du robot (bibliothèque standard)
mcl/<artefact>/                     carte.json, journal.jsonl, contrats/, PLAN-MCL.md
mcl/squelette/COUTURES.md           registre des coutures du squelette
```

- Chaque couche MCL est un sous-paquet : `__init__.py` porte **l'interface publique** (types publics,
  signatures, docstrings de contrat), `_impl.py` l'implémentation interne, révisable sous harnais complet. Les
  noms définitifs des couches suivent le résultat de `mcl.py analyser` (zéro divergence).
- Exécution sans installation ni outil d'empaquetage : le lanceur de tests ajoute lui-même `src` au chemin
  d'import ; pour les commandes `python -m xpbots...`, la variable `PYTHONPATH` désigne `src`
  (PowerShell : `$env:PYTHONPATH = "src"`). Aucune dépendance de construction n'est ajoutée (D-04, D-05).
- Les tests existants `tests/check_technical.py` et `tests/check_llm.py` restent inchangés ; le lanceur du robot
  ne les remplace pas.
- `reference/` n'est jamais importé par `src/xpbots/` ; seuls les tests l'importent comme oracle.

## 6. Politique numérique

| Grandeur | Représentation | Règle | Source |
|---|---|---|---|
| Instants | Entier de millisecondes UTC | Ordre stable par numéro de réception ; conversions Londres par `zoneinfo` (`Europe/London`, base IANA ; `tzdata` sous Windows) ; jamais un décalage constant | C03.1, C03.3 |
| OHLC, TR, ATR, formules de signal, stop technique `B_SL` | Flottant 64 bits | Récurrences dans l'ordre écrit ; moyenne initiale par somme séquentielle dans l'ordre des bougies ; inégalités strictes ou larges exactement écrites, sans tolérance | C03.8 à C03.12 |
| Prix exécutables E, SL, TP, spread S | Décimal sur la grille de `tick_size` | Prix du courtier convertis par leur représentation décimale la plus courte, jamais par leur développement binaire ; contrôle d'erreur flottante avant arrondi avec ε = 1e−8 unité de grille, valeur utilisée par `rounded_levels` | C03.12, C06 |
| Arrondis | — | SL achat vers le bas ; SL vente vers le haut après ajout de S ; TP achat vers le haut, TP vente vers le bas ; volume vers le bas sur la grille native | C06, C07 |
| Volumes, fonds propres, risque, frais, marge | Décimal | Contextes décimaux locaux, modes d'arrondi explicites, jamais de contexte global modifié | C07 |
| Seuils de stratégie | Valeurs chargées | Jamais recopiées ; les tests de bornes calculent leurs cas à partir des valeurs chargées | Règles du projet |

La moyenne initiale de `numpy.mean` (référence) peut différer d'un ulp d'une somme séquentielle : les
comparaisons à l'oracle utilisent une tolérance explicite sur les valeurs, et les cas d'égalité aux seuils sont
testés avec l'arithmétique du robot (document 03, §1).

## 7. Persistance, reprise et idempotence

### 7.1 État persistant

| Espace | Contenu | Écrit |
|---|---|---|
| `deploiement` | Identifiant, mode, symboles liés (règle de liaison C04), empreintes des deux configurations, version du code (commit) | Au démarrage |
| `donnees/<symbole>` | États récursifs ATR M15 et H1, identifiant et empreinte du préchargement, compteurs de bougies valides, dernier instant traité | Après chaque bougie close |
| `london/<bras>/<symbole>` | Jour Londres, range, gel de A_H1 et heure de disponibilité, quotas, position London possédée | À chaque changement ; quotas au premier remplissage non nul |
| `coordinateur/<bras>` | Intentions et états, réservations, positions possédées, verrous de symbole | Avant tout envoi, à chaque réponse |
| `compte/<bras>` | Base du jour UTC, pic des fonds propres, garde quotidienne, arrêt global persistant | À 00:00 UTC, à chaque nouveau pic, à tout déclenchement |
| `fondamental` | Dernière séquence par symbole, message courant, fenêtres `FLATTEN`, version de calendrier | À chaque message accepté |
| `contexte_ia` | Dernière séquence acceptée et son heure, cache des vetos validés | À chaque snapshot accepté |

### 7.2 Règle d'écriture

La coquille valide en base l'état produit par un événement **avant** d'exécuter les commandes de cet événement.
Pour une entrée, la transaction contenant l'intention et sa réservation doit réussir avant l'envoi ; un échec
d'écriture interdit l'envoi et déclenche une alerte.

### 7.3 Redémarrage (C08)

1. Charger et contrôler les deux configurations (empreintes) ; refuser de démarrer en cas d'écart.
2. Recharger l'état et la fin du journal ; constater le mode et le bras.
3. Rapprocher le courtier : positions, ordres et transactions depuis le dernier état ; identifier les positions
   possédées par numéro magique et commentaire ; toute position d'origine inconnue est externe et bloque les
   nouvelles entrées ; en netting, verrou exclusif de propriété par compte et symbole, aucune position agrégée
   d'origine inconnue n'est attribuée au robot.
4. Restaurer compteurs, quotas, réservations, gardes et arrêts ; un arrêt global ne se lève jamais par
   redémarrage.
5. Rattraper les bougies manquantes depuis l'historique de ticks du courtier ; un manque non récupérable suit
   l'arbitrage P-03.
6. Seulement ensuite, accepter de nouvelles décisions ; aucune entrée rétroactive après une interruption.

### 7.4 Idempotence

La clé d'intention `(deployment_id, strategy_id, symbole, clôture M15 UTC, sens)` est unique en base. Un message
réseau répété, une réponse dupliquée ou un rejeu du journal d'entrées ne créent jamais une seconde entrée.

## 8. Identification chez le courtier et propriété

- Numéro magique déterministe par couple (déploiement, stratégie) ; commentaire formé d'un préfixe fixe et
  d'une empreinte courte de la clé d'intention, dans la longueur que la sonde S-05 aura qualifiée.
- Une position sans numéro magique du déploiement est externe : elle compte dans les fonds propres et la marge,
  et bloque les nouvelles entrées faute de coordination fiable (C07). Le robot ne clôture jamais une position
  d'un autre propriétaire.

## 9. Journal C09, journal d'entrées et motifs

### 9.1 Enregistrements de décision

- **Clôture de bougie** (une par M15 close, par symbole, par stratégie et par bras) : version et empreinte des
  règles, déploiement, mode et bras, symbole, OHLC, validité, TR, ATR, référence de A_t, état London (H, L, W,
  A_H1 et son heure de disponibilité, rapport W/A_H1, fenêtre, quotas), signal ou motif et détail, permission
  fondamentale réellement connue (séquence, direction, état de risque, validité), version du calendrier,
  identifiant du snapshot IA et de ses preuves.
- **Intention** (une par signal présenté au coordinateur) : clé, tentatives avec cotation, spread, écart
  d'entrée, niveaux exécutables, volume, risque all-in, frais calculés, budget B, réserves avant et après, marge,
  positions externes, issue (admission ou motif et détail), coût IA alloué en `PAPER_AB`.
- **Ordre, réponse, exécution, protection, clôture de position** : requêtes, réponses, remplissages et
  reliquats, corrections du TP, clôtures et leurs motifs.
- **Compte** : fonds propres, base du jour UTC, pic, gardes, arrêts.
- **Alerte, démarrage, arrêt, rapprochement** : événements d'exploitation, sans secret ni numéro de compte.

Sérialisation canonique : clés triées, séparateurs sans espace, UTF-8, aucun nombre non fini ; une ligne par
enregistrement.

### 9.2 Journal d'entrées

Toutes les entrées du cœur, dans l'ordre de traitement : ticks avec numéro de réception, minuteries, réponses du
courtier, appels au port de calcul et leurs résultats, messages de permission, versions de calendrier, octets
des snapshots. Rejouer ce journal dans le même cœur doit reproduire à l'identique commandes et enregistrements
(C11.14) ; c'est aussi la base du rejeu d'incident.

### 9.3 Correspondance des motifs (arrêtée par P-07 et P-08 le 05/11/2026)

| Situation | `motif` | `detail` proposé | Source |
|---|---|---|---|
| Bougie hors fenêtre ou jour inactif | `OUTSIDE_SESSION` | `HORS_FENETRE`, `JOUR_INACTIF` | S02.2, C03.3 |
| Préchargement insuffisant ou ATR M15 indisponible | `WARMUP` | `M15_INSUFFISANTES`, `ATR_M15_INDISPONIBLE` | C03.7, C03.11 |
| A_t nul ou négatif | `NO_SETUP` | `ATR_NON_POSITIF` | C03.11 |
| Trou de données actif ou recalcul en attente | `DATA_GAP` | `TROU_ACTIF`, `ATTENTE_RECALCUL` | C03.6 |
| Range incomplet ou bougie de range invalide | `NO_SETUP` (`DATA_GAP` si la cause est un trou) | `RANGE_INCOMPLET`, `RANGE_BOUGIE_INVALIDE` | S02.1 |
| Largeur hors bornes | `NO_SETUP` | `RANGE_HORS_BORNES` | S02.1 |
| A_H1 indisponible (moins de 300 H1, non positive, trop ancienne) | `WARMUP` | `ATR_H1_INDISPONIBLE` | S02.1 |
| A_H1 disponible seulement après la décision | `NO_SETUP` | `GEL_ATR_H1_POSTERIEUR` | S02.1 |
| Pas de cassure, bougie plate, corps, clôture, TR | `NO_SETUP` | `PAS_DE_CASSURE`, `BOUGIE_PLATE`, `CORPS_INSUFFISANT`, `CLOTURE_ELOIGNEE`, `TR_EXCESSIF` | S02.3 |
| Sens déjà rempli ou deux entrées remplies | `DAILY_ENTRY_CAP` | `SENS_DEJA_REMPLI`, `MAXIMUM_JOURNALIER` | S02.4 |
| Distance technique au-delà du maximum | `STOP_TOO_WIDE` | — | S02.4, C06 |
| Position London ouverte, symbole occupé ou verrouillé | `SYMBOL_BUSY` | `POSITION_METHODE`, `POSITION_AUTRE_METHODE`, `ETAT_ORDRE_INCONNU`, `CLOTURE_EN_ATTENTE`, `VERROU_PROPRIETE` | S02.4, C07, C08 |
| Permission absente, périmée, invalide, interruption | `FUNDAMENTAL_INVALID` | `ABSENTE`, `PERIMEE`, `INVALIDE`, `INTERRUPTION` | C05 |
| Direction incompatible | `FUNDAMENTAL_DIRECTION` | `LONG_ONLY`, `SHORT_ONLY` | C05 |
| État `NO_NEW` ou `FLATTEN` | `FUNDAMENTAL_DIRECTION` (retenu) | `RISK_STATE_NO_NEW`, `RISK_STATE_FLATTEN` | C05 |
| Fenêtre d'annonce, calendrier périmé ou couverture insuffisante | `NEWS_WINDOW` | `ANNONCE_HIGH`, `CALENDRIER_PERIME`, `COUVERTURE_INSUFFISANTE` | C05 |
| Veto IA validé | `AI_CONTEXT_VETO` | identifiant de l'événement | A07 |
| Spread au-dessus du plafond (tentative) | `SPREAD_CAP` | — | C06 |
| Écart d'entrée au-dessus du maximum (tentative) | `ENTRY_GAP` | — | C06 |
| TTL atteint sans cotation conforme | `SIGNAL_EXPIRED` | dernière cause (P-08) : `SPREAD_CAP`, `ENTRY_GAP`, `COTATION_INVALIDE`, ou `AUCUNE_COTATION` si aucune cotation n'est arrivée | C06 |
| Contrainte native de SL/TP rendant le plan invalide | `PROTECTION_ERROR` (retenu) | `CONTRAINTE_NATIVE_AVANT_ORDRE` | C06 |
| Volume minimal au-delà du budget | `MIN_VOLUME_OR_RISK_REJECT` | — | C07 |
| Réserve totale ou nombre de positions | `ACCOUNT_RISK_CAP` | `RESERVE_TOTALE`, `NOMBRE_POSITIONS` | C07 |
| Positions externes non coordonnées | `ACCOUNT_RISK_CAP` (retenu) | `POSITIONS_EXTERNES` | C07 |
| Marge | `MARGIN_REJECT` | `MARGE_TIERS`, `CONTROLE_NATIF` | C07 |
| Caractéristique inconnue, fonction de calcul en erreur, profil non prêt | `ENVIRONMENT_NOT_READY` | champ ou fonction concerné | C04 |
| Réponse d'ordre inconnue | `UNKNOWN_ORDER_STATE` | — | C08 |
| SL absent, TP non rétabli ou dépassé | `PROTECTION_ERROR` | `SL_ABSENT`, `TP_NON_RETABLI`, `TP_DEPASSE` | C08 |
| Garde quotidienne | `DAILY_LOSS_LOCK` | — | C07 |
| Arrêt global | `GLOBAL_DRAWDOWN_HALT` | — | C07 |
| Stratégie minimale du squelette (segment S3, sans signal) | `NO_SETUP` | `SEGMENT_MINIMAL_S3` | Plan, phase 1 |
| Coordinateur minimal du squelette (segment S4, refus de tout signal) | `ENVIRONMENT_NOT_READY` | `SEGMENT_MINIMAL_S4` | Plan, phase 1 |

Ces détails forment l'énumération versionnée de la couche `domaine` du noyau (version 1) ; un test la compare à ce
tableau dans les deux sens.

## 10. Particularités MT5 relevées et à qualifier

Constats de la recherche du 5 novembre 2026 et de l'examen du paquet `MetaTrader5` 5.0.6231
([document 08](08_contrats_frontieres.md), §2), à confirmer par des **sondes jetables** : S-01 à S-08 en
sous-étape 13.1, sur le poste ; S-09 et S-10 en sous-étape 13.3, sur des exports réels. L'infrastructure est
construite avant, en phase 11, contre les contrats du document 08 ; un écart révélé par une sonde ouvre un
défigeage « correction » de la couche concernée, avec un test qui capture le cas. Le code des sondes se jette ;
seules leurs preuves sont conservées dans le rapport de qualification.

| Sonde | Point | Constat de recherche | Conséquence si la sonde échoue |
|---|---|---|---|
| S-01 | Base horaire des ticks (`time`, `time_msc`) | Les sources du forum MQL5 se contredisent (UTC ou heure du serveur) | Table de conversion versionnée heure serveur → UTC, tenant compte des changements d'heure du serveur ; flux refusé tant que l'écart n'est pas qualifié |
| S-02 | SL et TP attachés à l'ordre de marché (`TRADE_ACTION_DEAL`) | Généralement admis, refus possible par le serveur | Profil « non prêt pour V3 » (C06) ; **jamais** de pose différée du SL |
| S-03 | Déclenchement SL/TP | Consensus : achat sur Bid, vente sur Ask, à vérifier | Adaptateur de preuve d'équivalence avant admissibilité (C06) |
| S-04 | Modes de remplissage et remplissages partiels | FOK, IOC, RETURN selon le symbole ; en exécution au marché, prix et déviation sont ignorés | Choix du mode qui annule le reliquat ; annulation explicite en RETURN (C08) |
| S-05 | Commentaire et numéro magique | Longueur limitée, conservation à vérifier sur positions et transactions | Format d'empreinte raccourci |
| S-06 | `order_send` bloquant | Appel synchrone ; durée et comportement en déconnexion inconnus ; appels concurrents non documentés | Exécutant dédié avec délai de 5 s, rapprochement possible pendant un envoi bloqué, ou repli documenté |
| S-07 | `order_calc_margin`, `order_calc_profit`, `order_check` | `OrderCalcMargin` évalue un ordre isolé (C04) | Marge totale = marge du compte + marge du nouvel ordre + contrôle natif |
| S-08 | `copy_ticks_from` | Date de départ à la seconde ; ticks de même milliseconde possibles ; profondeur d'historique propre au courtier | Dédoublonnage par `time_msc` et ordre natif ; préchargement en bougies natives Bid seulement après comparaison (P-01) |
| S-09 | Export de ticks du terminal (Affichage, Symboles, onglet Ticks) | Fichier texte en heure du serveur ; colonnes, séparateur et traitement d'un Bid ou d'un Ask inchangé à relever sur un export réel | Unités `formats_exports` et `conversion_exports_ticks` de l'artefact `donnees-historiques` écrites pour le format relevé ; un tick sans Bid ni Ask connu est écarté et journalisé, jamais complété par une valeur inventée |
| S-10 | Export de la source tierce de ticks (D-14) | Format à relever (colonnes, fuseau, précision) sur un fichier réel avant conversion | Description et conversion dédiées dans `donnees-historiques` ; la source reste déclarée contrefactuelle |

Le paquet Python ne fournit ni le calendrier économique ni les horaires de séance : D-12 retient le service MQL5
d'export du §2.2. Le chemin du dossier commun vient de `terminal_info().commondata_path`. Les aides `Buy`, `Sell`
et `Close` du paquet sont interdites : elles renvoient d'elles-mêmes un ordre refusé, ce que C08 exclut. Les
commissions ne figurent pas dans les caractéristiques du symbole ; elles se lisent dans les transactions
(`commission`, `fee`) et se comparent à la fiche publiée du compte. Le type de compte est contrôlé au démarrage
(démonstration en `DEMO`, réel en `REEL`). Détails : document 08, §2.1, §2.3 et §2.8.

## 11. Sécurité, secrets et confidentialité

- Les identifiants MT5 restent dans le terminal ; la coquille s'attache au terminal ouvert sans mot de passe.
- Les clés d'API ne vivent que dans `.env`, lues par le seul service IA ; jamais dans le snapshot, les prompts,
  les journaux ou les rapports (A02, A08).
- Les journaux et rapports ne contiennent ni solde nominatif détaillé destiné à la publication, ni numéro de
  compte, ni secret ; ils restent dans des dossiers ignorés par Git.

## 12. Performance du rejeu

Le coût par tick est constant (mise à jour de bougie, cotation, positions ouvertes) ; la logique de stratégie
ne s'exécute qu'aux clôtures M15. Un rejeu complet de 2020 à 2026 représente plusieurs centaines de millions de
ticks par symbole : la durée est mesurée en phase 10, et toute optimisation (par exemple bougies précalculées
avec empreinte, balayage des ticks limité aux TTL et aux positions ouvertes) se fait **à comportement constant**,
sous harnais complet, avec preuve d'égalité des décisions.

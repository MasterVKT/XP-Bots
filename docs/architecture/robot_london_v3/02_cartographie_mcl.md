# 02 — Cartographie MCL du robot London (`LONDON_V3`)

Retour au [plan directeur](README.md). Méthode : skill `mcl-matryoshka-construction-layers` (protocole) et
skill [xp-bots-mcl-robot-planning](../../../.agents/skills/xp-bots-mcl-robot-planning/SKILL.md) (contexte
XP-Bots). La carte ci-dessous **affine l'hypothèse** de la
[cartographie de référence](../../../.agents/skills/xp-bots-mcl-robot-planning/references/cartographie-xp-bots.md) ;
elle reste une hypothèse que `mcl.py analyser` tranchera unité par unité (zéro divergence avant toute couche).

## 1. Applicabilité (phase 0 de MCL)

| Question | Réponse | Justification |
|---|---|---|
| 1. La structure est-elle connaissable avant construction ? | Oui | Spécification déterministe figée, fonctions de référence, pile dérivée « robot de trading » de la skill MCL, cartographie XP-Bots |
| 2. Les contrats internes sont-ils stabilisables tôt ? | Oui | Règles et valeurs figées (C01, C02) ; types aux coutures déterminés par C06–C09 |
| 3. Faut-il construire pour comprendre ? | Non pour le cœur ; partiellement pour l'adaptateur MT5 | Base horaire des ticks, SL au moment de l'entrée, modes de remplissage, appels bloquants : faisabilité technique à sonder (sondes S-01 à S-08) avant les couches d'infrastructure |

- **Verdict** : applicable. Échelle **application**, donc **mode composite** : squelette déployable, puis un
  artefact MCL par composant. Les inconnues MT5 suivent la combinaison « sonde jetable puis reconstruction au
  protocole » ; le code des sondes n'est jamais promu en couche.
- **Bénéfice dégradé assumé** : `infrastructure` et `service-ia` sont dominés par leurs frontières externes ;
  l'économie de doublures y est plus faible.
- **Signaux de mauvais domaine à surveiller** : divergences répétées entre carte et code réel, défigeages en
  chaîne dès les premières couches. Réponse : suspendre, sonder, re-cartographier, et le signaler à l'humain.
- **Hors domaine** : chercher une variante plus rentable est exploratoire et hors de ce plan.

## 2. Étape 1 — Comprendre la cible (seul moment outside-in)

1. **Finalité** : exécuter S02 sur les ticks Bid/Ask réels d'un compte standard USD de 100 USD, avec le risque
   de C07, la coordination de C08, la permission externe obligatoire de C05 et le veto IA facultatif de A07 ;
   produire un journal C09 rejouable ; reproduire en rejeu le protocole C10.
2. **Entrées de l'enveloppe** : ticks horodatés, états de connexion, caractéristiques C04 du compte et des
   symboles, réponses du courtier, permissions fondamentales, calendrier versionné, snapshot IA, horloge.
   **Sorties** : ordres d'entrée protégés, ajustements de TP, clôtures, alertes, journal C09 et journal
   d'entrées, rapports C10, A11 et A13.
3. **Contraintes** : Python 3.13 ; bibliothèque standard dans le cœur ; `MetaTrader5` sous Windows dans
   l'infrastructure seulement ; TTL de 5 s sans appel réseau ; développement et intégration continue sous
   Linux, exploitation sur le poste Windows de l'utilisateur.
4. **Nature** : projet neuf (greenfield) ; `reference/` sert d'oracle de comparaison.

## 3. Mode composite : le squelette

Le squelette est **hors protocole MCL** : c'est du code de production minimal, déployable dès la phase 1, dont
la discipline est de rester vert en intégration continue. Chaque artefact de chair remplace un segment minimal
en respectant le contrat de la couture.

### 3.1 Segments

| Segment | Entrée → sortie | Comportement minimal | Remplacé par | Phase |
|---|---|---|---|---|
| S1 Source de ticks | Fichier synthétique → ticks ordonnés | Lecture d'un fichier de démonstration généré par la fabrique de tests | `journal-rejeu` (analyse des ticks) et `infrastructure` (lecteurs de fichiers et flux MT5) | 10, 11 |
| S2 Agrégation | Ticks → bougies M15 closes | Agrégation Bid sans trous ni H1 | `donnees-temps` | 3 |
| S3 Stratégie | Bougie close → résultat technique | Toujours `NO_SETUP` | `moteur-london` | 4 |
| S4 Coordinateur | Résultat technique → décision | Refus explicite et journalisé, jamais d'ordre | `execution-coordinateur` puis `orchestration` | 6, 9 |
| S5 Exécution papier | Commandes → réponses | Remplissage au marché au premier tick suivant, sans coût, protections natives sur Bid/Ask | `journal-rejeu` (simulateur C10) | 10 |
| S6 Journal | Décisions → lignes JSON | Un enregistrement par bougie close avec motif | `noyau` (format) puis `infrastructure` (écriture) | 2, 11 |
| S7 Point d'entrée | Ligne de commande → code de sortie | `python -m xpbots.app.rejeu_squelette` sur la fixture | `points-entree` | 11 |

Test de bout en bout du squelette : une journée Londres synthétique d'EURUSD produit un enregistrement par
bougie M15 close, avec un motif conforme, et un code de sortie nul. Ce test fait partie de la régression
intégrale de **chaque** gate du plan.

### 3.2 Coutures

`mcl/squelette/COUTURES.md` décrit chaque couture (types et comportements échangés, artefact propriétaire,
statut minimal ou remplacé). Toute modification d'une couture est un **changement de contrat tracé** : date,
nature (extension ou modification), artefact, justification, gate vert de la CI du squelette.

## 4. Conventions communes des cartes MCL

- **Un dossier par artefact** : `mcl/<artefact>/` (carte, journal, contrats, `PLAN-MCL.md`), initialisé par
  `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/<artefact> init --nom <artefact> --langage python --echelle composant --mode pur --sources src`.
  Le dossier composite `mcl/robot-london-v3/` est initialisé avec `--echelle application --mode composite`.
- **Une couche = un sous-paquet** : `chemins` = répertoire du sous-paquet ; imports Python déduits ;
  `contrats` = fiche `mcl/<artefact>/contrats/couche-<id>.md`, `__init__.py` de la couche (interface publique)
  et fichiers de tests de la couche. `_impl.py` reste hors contrat : révisable à comportement constant.
- **Unités** : `depend_de` ne cite que des unités du même artefact ou des frontières déclarées. Les artefacts
  amont, déjà figés, forment le contexte stable : ils ne sont pas déclarés ; leur statut figé est contrôlé au
  début de chaque phase par `mcl.py --dossier mcl/<amont> statut`.
- **Frontières (`externes`)** : (a) frontières réelles, autorisées seulement dans les couches d'infrastructure
  désignées ; (b) **interdits** déclarés avec `couches_autorisees` vide, pour rendre l'indépendance des
  méthodes et la pureté du cœur vérifiables (§8).
- **Règles** : celles par défaut de `mcl.py` (`invariant`, `paralleles`, `externes`, `cycles`,
  `contrats_figes` strictes ; `divergence` en avertissement, à zéro avant toute construction) ;
  `checkpoint_tous_les` : 2.
- **Gate et gel** : commandes au [document 03](03_acceptation_et_tests.md), §3 ; rien n'est modifié entre un
  gate vert et le gel.

## 5. Dépendances inter-artefacts et ordre de construction

| Artefact | Dépend de (imports autorisés) | Profondeur dans la carte composite |
|---|---|---|
| `noyau` | — | 0 |
| `donnees-temps` | `noyau` | 1 |
| `moteur-london` | `noyau`, `donnees-temps` | 2 |
| `execution-coordinateur` | `noyau`, `donnees-temps` (sessions) | 2 |
| `controles-fondamentaux` | `noyau`, `execution-coordinateur` (port fondamental) | 3 |
| `contexte-ia` | `noyau`, `execution-coordinateur` (port du contexte IA) | 3 |
| `infrastructure` | `noyau`, `execution-coordinateur` (protocole du courtier et port de calcul) | 3 |
| `moteur-london-v1` | `noyau`, `donnees-temps` (artefact de comparaison, sous-étape 13.4) | 2 |
| `orchestration` | `noyau`, `donnees-temps`, `execution-coordinateur`, `controles-fondamentaux`, `contexte-ia` ; les stratégies sont **injectées** (D-18) | 4 |
| `service-ia` | `noyau`, `contexte-ia` (format du snapshot) | 4 |
| `journal-rejeu` | `noyau`, `execution-coordinateur`, `orchestration`, `moteur-london` (fabrique de stratégie) ; `moteur-london-v1` à partir de 13.4 | 5 |
| `points-entree` | `noyau`, `orchestration`, `journal-rejeu`, `infrastructure`, `moteur-london` (fabrique de stratégie) | 6 |

Une simulation de cette carte composite avec `mcl.py analyser` (5 novembre 2026, hors du dépôt) rend exactement
ces profondeurs, sans divergence ni cycle, avec ou sans `moteur-london-v1` (qui prend la couche parallèle 2c) ;
son unique alerte, « plusieurs racines (`service_ia`, `app`) », est attendue : le robot et le service IA sont
deux processus distincts. Les cartes prévues de `noyau`, `donnees-temps`, `moteur-london`,
`execution-coordinateur`, `controles-fondamentaux`, `journal-rejeu` et `infrastructure` ont été simulées de
même : les couches calculées sont celles des tableaux du §6.

Les artefacts de même profondeur sont **parallèles** : aucune dépendance mutuelle n'est permise. En
particulier, `moteur-london`, `moteur-london-v1` et `execution-coordinateur` ne s'importent jamais l'un l'autre
(indépendance des méthodes, C08) ; `infrastructure` ne lit que des octets pour les permissions, le calendrier et
le snapshot, sans importer `controles-fondamentaux` ni `contexte-ia`. L'orchestration n'importe **aucune**
stratégie : les points de composition (`journal-rejeu` pour le rejeu, `points-entree` pour le direct) lui
fournissent les fabriques de stratégie par la configuration de déploiement (D-18). Le moteur V1 et le futur
robot EMA s'y branchent donc sans défiger l'orchestration.

**Ordre de construction** (ordre produit du guide, compatible avec les dépendances) : `noyau` (phase 2),
`donnees-temps` (3), `moteur-london` (4), `execution-coordinateur` (5 et 6), `controles-fondamentaux` (7),
`contexte-ia` (8), `orchestration` (9), `journal-rejeu` (10), `infrastructure` et `points-entree` (11),
`service-ia` (12), `moteur-london-v1` (13.4). `infrastructure` pourrait techniquement venir plus tôt ; elle
attend la phase 11 parce qu'elle exige le poste Windows et le compte de démonstration.

`controles-fondamentaux` et `contexte-ia` implémentent les ports déclarés par `execution-coordinateur` : ils
viennent donc après lui, ce qui respecte aussi l'ordre produit du guide (« brancher » le calendrier et les
permissions après le coordinateur). D'ici là, le coordinateur fonctionne avec les deux implémentations neutres
nommées de son port (§6.4).

## 6. Artefacts

Légende des tableaux : **Couche** = identifiant prévu (profondeur et indice parallèle) ; **Amont** = artefacts
figés utilisés. Les esquisses de contrat décrivent la responsabilité et la forme des interfaces ; la
finalisation se fait au début de chaque couche, dans `mcl/<artefact>/contrats/couche-<id>.md`.

### 6.1 Artefact `noyau` (paquet `xpbots.noyau`, phase 2)

Rôle : types et règles partagés, purs, sans entrée-sortie, réutilisables par le futur robot EMA ; lecture
stricte des deux configurations figées à partir d'octets fournis par la coquille. Point d'insertion : types
minimaux du squelette (S1, S6).

| Unité | Couche | Responsabilité | Entrée → sortie | Dépend de | Sources |
|---|---|---|---|---|---|
| `instant` | 0a | Représenter un instant UTC en millisecondes entières et ordonner les événements de façon stable | texte ISO-8601 UTC, horodatage conscient, entier → instant ; instant → texte ISO ; alignement sur une durée | — | C03.1, C03.2 |
| `nombres` | 0b | Convertir les flottants du courtier en décimaux sûrs et ramener une valeur sur une grille avec contrôle d'erreur | flottant, pas, sens d'arrondi → décimal sur la grille | — | C03.12 |
| `configuration` | 0c | Valider les octets des deux exports figés et exposer des paramètres typés immuables | octets des exports et de la preuve de conservation → configuration figée typée et empreintes | — | C01, C02, A02 |
| `marche` | 1a | Représenter ticks, cotations et bougies Bid | champs → tick, cotation, bougie validés | `instant`, `nombres` | C03.2, C03.5, C06 |
| `instrument` | 1b | Représenter et valider les profils d'instrument et de compte de C04 | champs lus → profils, horaires de cotation, liste des champs manquants | `instant`, `nombres`, `configuration` | C04 |
| `domaine` | 1c | Définir sens, signal technique, clé d'intention, issues, décisions des contrôles et motifs | champs → types validés | `instant` | C05, C06, C08, C09, A07 |
| `journal` | 2 | Définir les enregistrements C09 et leur sérialisation canonique | objets → lignes JSON canoniques validées | `marche`, `instrument`, `domaine`, `configuration` | C09 |

Carte prévue : couches parallèles 0a, 0b, 0c ; couches parallèles 1a, 1b, 1c ; couche 2 (enveloppe).

Esquisses de contrat :

- `instant` : refuse un texte sans fuseau ou avec un décalage non nul (comme `utc()` de la référence) ;
  précision milliseconde ; alignement `floor(t / durée) × durée` sur l'époque UTC ; clé d'ordre
  (instant, numéro de réception).
- `nombres` : conversion par la représentation décimale la plus courte ; refus de NaN et d'infini ; arrondi
  vers le bas ou vers le haut sur une grille avec ε = 1e−8 unité de grille ; test d'appartenance à la grille.
- `configuration` : JSON strict (clé dupliquée ou nombre non fini refusés) ; empreinte SHA-256 des octets égale
  à `frozen_technical_file_sha256` et `frozen_ai_file_sha256` de la preuve de conservation ; empreinte
  canonique exposée (égale au `design_sha256` du diagnostic) ; **chaque clé** du bloc `common` typée, clé
  inconnue ou manquante refusée ; valeurs non prises en charge refusées au démarrage : `bar_price` autre que
  `BID`, `bar_alignment` autre que `UTC`, `atr_method` autre que `WILDER`, `atr_signal_reference` autre que
  `PREVIOUS_CLOSED_M15`, `fundamental_mode` autre que `EXTERNAL_REQUIRED`, toute option `allow_*`,
  `*_enabled`, `mandatory_retest` ou `new_indicator_vote_score` à vrai.
- `marche` : tick (symboles canonique et courtier, heures fournisseur et réception, numéro, Bid, Ask,
  drapeaux) ; cotation (Bid et Ask décimaux sur la grille, spread S, heures) ; bougie (symbole, durée,
  ouverture, OHLC, nombre d'événements, validité et motif, instant de disponibilité).
- `instrument` : tous les champs de C04 sont obligatoires ; **aucun champ manquant ne vaut zéro** ; commission
  nulle admise seulement si confirmée ; drapeaux qualifiés (SL/TP attachables à l'entrée, convention de
  déclenchement vérifiée, modes de remplissage) ; horaires de cotation avec dates d'effet et fermetures
  exceptionnelles, questions « ouvert à t ? » et « prochaine fermeture après t ? » ; profil de compte
  confronté à `account_currency` et `account_leverage`.
- `domaine` : sens ; clé d'intention et son empreinte courte ; signal technique (stratégie, symbole, clôture,
  sens, C_t, A_t, B_SL, multiple d'objectif, contexte immuable pour le journal) ; issues (rempli au premier
  volume non nul, refus définitif motivé, expiré, position clôturée) ; décision fondamentale (autorisée ou
  refus motivé, clôtures obligatoires) ; décision de contexte IA (`BLOCK` ou `NEUTRAL`, jamais `ALLOW`) ; motifs
  fermés (C09, `ENVIRONMENT_NOT_READY`, `AI_CONTEXT_VETO`) et détails énumérés selon P-07.
- `journal` : types d'enregistrements du [document 01](01_architecture.md), §9.1, champs obligatoires par
  type, sérialisation canonique ; aucune écriture.

### 6.2 Artefact `donnees-temps` (paquet `xpbots.donnees`, phase 3)

Rôle : transformer les ticks en bougies M15 et H1 Bid validées et causales, enrichies de TR, ATR, A_t et des
repères de session ; précharger, persister (par export) et reprendre les états. Point d'insertion : segment S2.

| Unité | Couche | Responsabilité | Entrée → sortie | Dépend de | Amont | Sources |
|---|---|---|---|---|---|---|
| `types_donnees` | 0a | Définir les objets intermédiaires du flux de données | — | — | noyau | C03 |
| `sessions_londres` | 0b | Calculer jours et heures de Londres, fenêtres, jour UTC et blackout | instant, date, heure locale → booléens, instants, dates | — | noyau | C03.3, S02.1, S02.2, C08 |
| `constructeur_bougies` | 1a | Agréger les ticks en M15 et H1 brutes, clore à l'événement de frontière, signaler les intervalles vides | ticks ordonnés → bougies brutes, intervalles vides | `types_donnees` | noyau | C03.2, C11.3 |
| `indicateurs` | 1b | Calculer TR, ATR14 Wilder et A_t par récurrence incrémentale | bougie valide et état → TR, ATR, nouvel état | `types_donnees` | noyau | C03.10, C03.11 |
| `couverture_flux` | 1c | Classer un intervalle en couvert, fermeture officielle ou trou | connexions, horaires, registre de trous → statut | `types_donnees` | noyau | C03.5, P-01 |
| `validation_bougies` | 2a | Combiner bougie brute et couverture en bougie valide ou invalide motivée, et signaler les trous | bougie brute et statut → bougie, signalement | `constructeur_bougies`, `couverture_flux` | noyau | C03.5, C03.6, P-02 |
| `etat_indicateurs` | 2b | Tenir les chaînes d'indicateurs par symbole et unité de temps, le préchargement, les compteurs et la reprise | bougies validées → bougies enrichies ; export et import d'état | `indicateurs` | noyau | C03.7, P-03, P-10 |
| `flux_bougies` | 3 | Enveloppe : ticks et connexions → bougies M15 et H1 enrichies et état de trou par symbole | événements → bougies enrichies, changements d'état | `validation_bougies`, `etat_indicateurs`, `sessions_londres` | noyau | C03 |

Carte prévue : 0a ∥ 0b ; 1a ∥ 1b ∥ 1c ; 2a ∥ 2b ; 3.

Esquisses de contrat :

- `sessions_londres` : date et heure locales par `zoneinfo` ; instant d'une heure locale d'un jour Londres
  (02:00, 07:00, 08:00, 11:00, 12:00), avec refus explicite d'une heure inexistante ou ambiguë (les changements
  d'heure britanniques tombent le dimanche à 01:00 UTC, jamais un jour actif, vérifié de 2019 à 2027) ; liste
  des ouvertures du range, qui doit compter exactement `expected_range_m15_bars` éléments ; décision dans la
  fenêtre avec la sémantique exacte de `local_decision_in_window` (même date locale à l'ouverture et à la
  clôture, jour actif, ouverture ≥ début, clôture < fin exclue) ; jour UTC ; appartenance au blackout
  `[début, fin)` UTC et prochain début.
- `constructeur_bougies` : intervalles alignés sur l'époque UTC ; le premier événement d'heure ≥ fin de bougie
  la clôt et appartient à la suivante ; OHLC sur le Bid de tous les événements de cotation de l'intervalle ;
  intervalles sans événement émis comme vides ; événement antérieur à l'ouverture courante = anomalie de
  données signalée ; disponibilité = heure de réception de l'événement de clôture.
- `indicateurs` : TR de la première bougie du préchargement = H − L ; ensuite
  `max(H − L, |H − C_préc|, |L − C_préc|)` ; ATR initial = moyenne séquentielle des `atr_period` premiers TR ;
  ensuite lissage de Wilder ; A_t = ATR de t − 1 ; une bougie invalide n'entre pas dans la chaîne (P-03).
- `couverture_flux` et `validation_bougies` : selon P-01 et P-02 ; début et fin d'un état `DATA_GAP` ;
  aucune bougie synthétique.
- `etat_indicateurs` : rangs de bougies valides depuis le début du préchargement (P-10) ; identité du
  préchargement (instant de la première bougie, nombre, SHA-256 de la liste canonique) ; export et import
  d'état contrôlés par l'empreinte de configuration ; un préchargement différent est une initialisation
  différente, journalisée.
- `flux_bougies` : par symbole ; bougie enrichie = bougie + TR, ATR, A, rang, jour Londres, heures locales
  d'ouverture et de clôture, jour UTC ; une H1 n'est émise qu'à sa clôture ; aucune donnée partielle exposée.

### 6.3 Artefact `moteur-london` (paquet `xpbots.london`, phase 4)

Rôle : appliquer S02 aux bougies enrichies d'un symbole et rendre, à chaque clôture M15, un signal technique ou
un motif ; appliquer les issues reçues. Point d'insertion : segment S3. Le moteur ne connaît ni coordinateur ni
courtier.

| Unité | Couche | Responsabilité | Entrée → sortie | Dépend de | Amont | Sources |
|---|---|---|---|---|---|---|
| `parametres_london` | 0a | Valider et typer le bloc `london` | configuration figée → paramètres London | — | noyau | C02, S02 |
| `types_london` | 0b | Définir range, gel de A_H1, quotas, état du jour et résultat technique | — | — | noyau | S02 |
| `range_londres` | 1a | Construire le range des 20 M15 de `[02:00, 07:00)` et sa validité | bougies du jour → range | `parametres_london`, `types_london` | donnees-temps | S02.1 |
| `gel_atr_h1` | 1b | Figer A_H1 sur la dernière H1 valide clôturée au plus tard à 07:00, avec son heure de disponibilité | H1 enrichies → gel | `parametres_london`, `types_london` | donnees-temps | S02.1, P-09 |
| `bougie_cassure` | 1c | Tester cassure, buffer, corps, clôture et TR d'une bougie de signal | bougie, range, `tick_size` → sens ou motif | `parametres_london`, `types_london` | noyau | S02.3 |
| `stop_local` | 1d | Calculer B_SL à trois composantes, refuser au-delà du maximum, fixer le multiple d'objectif | bougie, range, sens, A, `tick_size` → B_SL et k, ou `STOP_TOO_WIDE` | `parametres_london`, `types_london` | noyau | S02.4, C06 |
| `quotas_london` | 1e | Compter les entrées remplies par jour Londres et par sens, au premier remplissage non nul | issues → quotas ; « ce sens est-il admissible ? » | `parametres_london`, `types_london` | noyau | S02.4 |
| `moteur_london` | 2 | Enveloppe : combiner admissibilité du range, fenêtre, cassure, stop et quotas ; rendre signal ou motif ; appliquer les issues | bougies M15 et H1 enrichies, issues → résultats techniques | 1a, 1b, 1c, 1d, 1e | donnees-temps, noyau | S02, A07, C08 |

Carte prévue : 0a ∥ 0b ; 1a ∥ 1b ∥ 1c ∥ 1d ∥ 1e ; 2.

Esquisses de contrat :

- `parametres_london` : chaque clé typée ; `fresh_close_cross_required`, `h1_directional_filter_enabled` et
  `exit_on_close_back_inside_range_enabled` doivent rester faux (options non implémentées : refus au
  démarrage sinon) ; cohérence `expected_range_m15_bars` = durée du range / `timeframe_seconds` ; ordre
  début de séance < fin d'entrée ≤ sortie forcée.
- `range_londres` : uniquement les ouvertures de `sessions_londres` ; toutes présentes et valides ; H = max des
  H, L = min des L, W = H − L > 0 ; une bougie ouverte à 07:00 ou après n'est jamais lue ; range disponible à
  l'instant de disponibilité de la bougie de 06:45 ; motifs d'invalidité détaillés (P-07).
- `gel_atr_h1` : instant de gel F = 07:00 Londres ; candidate = dernière H1 valide de clôture ≤ F et datant
  d'au plus 3 600 s ; ATR > 0 ; au moins `warmup_closed_h1_bars` H1 valides jusqu'à elle (P-10) ; première
  version valide figée, disponibilité = réception de son événement de clôture ; aucune mise à jour ensuite
  (P-09) ; toute décision antérieure à cette disponibilité est refusée.
- Admissibilité (dans l'enveloppe) : `range_min_h1_atr` × A_H1 ≤ W ≤ `range_max_h1_atr` × A_H1, bornes incluses.
- `bougie_cassure` : A fini et > 0 ; R = H − L > 0 ; TR ≤ `maximum_signal_true_range_atr` × A ;
  |C − O| / R ≥ `signal_body_fraction_min` ; b = max(`tick_size`, `breakout_buffer_atr` × A) ; achat :
  C > H_range + b, C > O, (C − L) / R ≥ `signal_close_location_min` ; vente symétrique ; l'égalité au niveau plus
  buffer n'est pas une cassure ; aucun franchissement récent exigé.
- `stop_local` : guard = max(`tick_size`, `structural_buffer_atr` × A) ; achat :
  B_SL = min(L_t − guard, H_range − `boundary_stop_inside_atr` × A, C_t − `minimum_chart_stop_atr` × A) ;
  vente : max(H_t + guard, L_range + `boundary_stop_inside_atr` × A, C_t + `minimum_chart_stop_atr` × A) ;
  0 < sens × (C_t − B_SL) ≤ `maximum_chart_stop_atr` × A, sinon `STOP_TOO_WIDE` sans plafonnement ;
  k = `take_profit_gross_price_r`.
- `quotas_london` : total du jour < `max_filled_entries_per_symbol_local_day` et total du sens <
  `max_filled_entries_per_direction_local_day` ; enregistrement au premier remplissage non nul, idempotent par
  clé d'intention ; remise à zéro seulement au changement de jour Londres ; un refus sans remplissage ne
  consomme rien.
- `moteur_london` : par symbole et par bras ; à chaque M15 close, un résultat (journalisé par le coordinateur)
  dans cet ordre d'évaluation : trou actif → hors fenêtre ou jour inactif → préchargement et A → validité du
  range → disponibilité du gel → admissibilité → position London possédée sur le symbole → cassure → quota du
  sens → stop ; sinon signal technique avec son contexte (H, L, W, A_H1, rapport W/A_H1, disponibilité du gel,
  mesures de la bougie). Issue « rempli » : quotas et position possédée ; « refus » ou « expiré » : rien ;
  « position clôturée » : la position possédée est levée, une seconde direction n'est possible que sur un
  nouveau signal clos. Jamais deux signaux pour une même bougie, jamais de rattrapage sur une bougie ancienne.
  Changement de jour Londres : range, gel et quotas réinitialisés.

### 6.4 Artefact `execution-coordinateur` (paquet `xpbots.execution`, phases 5 et 6)

Rôle : transformer des signaux techniques en ordres d'entrée protégés et dimensionnés, ou en refus motivés,
puis gérer chaque position jusqu'à sa clôture, pour toutes les méthodes d'un compte. Point d'insertion :
segment S4. Les profondeurs ci-dessous sont celles que donnent les dépendances internes.

| Unité | Couche | Responsabilité | Entrée → sortie | Dépend de | Amont | Sources |
|---|---|---|---|---|---|---|
| `types_execution` | 0a | Définir réservations, intentions et états, positions possédées, commandes et réponses du courtier, état du compte | — | — | noyau | C07, C08 |
| `ports_controles` | 0b | Déclarer les ports des contrôles fondamentaux et du contexte IA, avec leurs deux implémentations neutres nommées | — | — | noyau | C05, A12 |
| `garde_cotation` | 0c | Décider si une cotation permet d'entrer, d'attendre ou si le signal expire | signal, cotation, instant → admissible, attente motivée, expiré | — | noyau | C06, P-04, P-05 |
| `prix_executables` | 0d | Convertir B_SL en SL exécutable, choisir E, calculer D et TP, vérifier les contraintes natives | signal, cotation, profil → niveaux ou refus | — | noyau | C06 |
| `echeances_sortie` | 0e | Calculer la première échéance horaire de sortie d'une position | position, profil, sessions → instant et motif | — | donnees-temps, noyau | C08, S02.2 |
| `port_calcul` | 1a | Déclarer le port synchrone de calcul du courtier | — | `types_execution` | noyau | C04, C07 |
| `gardes_compte` | 1b | Tenir base UTC, pic, garde quotidienne et arrêt global persistant | fonds propres, instant → état, déclenchements | `types_execution` | noyau | C07, P-12 |
| `registre_reservations` | 1c | Réserver et libérer risque et places de façon atomique et idempotente | intention, état du compte → réservation ou refus | `types_execution` | noyau | C07, C08 |
| `risque_all_in` | 2a | Calculer la perte pessimiste et les frais d'un volume | niveaux, volume, profil → risque décimal | `prix_executables`, `port_calcul` | noyau | C07 |
| `arbitrage` | 2b | Ordonner les signaux simultanés et réévaluer après chaque réservation | signaux d'une clôture → séquence d'admission | `registre_reservations` | noyau | C08 |
| `dimensionnement` | 3 | Retenir le plus grand volume admissible sous les cinq contraintes | signal, niveaux, état → volume ou refus | `risque_all_in`, `registre_reservations`, `gardes_compte` | noyau | C07, P-06 |
| `cycle_ordre` | 4 | Machine à états d'une intention, de l'envoi à la clôture | réponses, minuteries → transitions, commandes | `dimensionnement`, `prix_executables`, `port_calcul` | noyau | C08 |
| `sorties_obligatoires` | 5a | Déclencher les clôtures prioritaires et les réessais sans cotation | état, instant, contrôles → commandes de clôture | `cycle_ordre`, `echeances_sortie`, `gardes_compte`, `ports_controles` | noyau | C05, C07, C08 |
| `reprise_rapprochement` | 5b | Reconstituer positions, réservations et verrous au redémarrage et après réponse inconnue | état restauré, rapprochement → état cohérent | `cycle_ordre`, `registre_reservations`, `gardes_compte` | noyau | C08 |
| `coordinateur` | 6 | Enveloppe : appliquer l'ordre C08 pour un compte et journaliser chaque décision | signaux, réponses, cotations, minuteries → commandes, enregistrements, issues | toutes les unités | noyau | C06 à C09, A07 |

Carte prévue : 0a ∥ 0b ∥ 0c ∥ 0d ∥ 0e ; 1a ∥ 1b ∥ 1c ; 2a ∥ 2b ; 3 ; 4 ; 5a ∥ 5b ; 6. Phase 5 : couches 0 à 3 ;
phase 6 : couches 4 à 6.

Esquisses de contrat :

- `types_execution` : états d'intention `EN_ATTENTE_COTATION`, `RESERVEE`, `ENVOYEE`, `INCONNUE`,
  `REMPLIE_PARTIELLE`, `OUVERTE`, `CLOTURE_DEMANDEE`, `CLOTUREE`, `REFUSEE`, `EXPIREE` ; commandes et réponses
  du [document 01](01_architecture.md), §4.1 et §4.2.
- `ports_controles` : port fondamental (évaluer un symbole, un sens et un instant ; lister les clôtures
  obligatoires) et son implémentation nommée `TECHNICAL_CONTROL_NEUTRAL` (ANY/ALLOW à chaque décision, réservée
  au contrôle technique isolé) ; port du contexte IA et son implémentation « complément absent » (`NEUTRAL`).
- `garde_cotation` : cotation valide (P-04, P-05) ; S ≤ `max_spread_price` du symbole, borne incluse ;
  |Bid − C_t| ≤ `max_entry_bid_gap_atr` × A_t, borne incluse ; instant < clôture + TTL ; issues : admissible,
  attendre (`SPREAD_CAP`, `ENTRY_GAP`, cotation invalide), expiré.
- `prix_executables` : achat E = Ask, SL = arrondi vers le bas de B_SL ; vente E = Bid, SL = arrondi vers le
  haut de B_SL + S ; D = sens × (E − SL) > 0 ; TP = E + sens × k × D, achat vers le haut, vente vers le bas ;
  contrainte native (distance minimale, gel) qui invalide le plan → refus avant ordre, sans déplacer le stop ;
  après remplissage, TP recalculé depuis le prix moyen réel, SL inchangé ; prédicat « TP déjà dépassé ».
- `echeances_sortie` : premier remplissage + `max_position_wallclock_seconds` ; `london.force_exit_local` du jour
  Londres ; prochaine fermeture ou pause native − `native_market_close_guard_seconds` ; prochain début de
  blackout ; la plus proche l'emporte.
- `port_calcul` : profit d'une position fictive (sens, volume, prix d'ouverture et de clôture) ; marge d'un
  ordre isolé ; contrôle natif d'un ordre (marge requise, marge libre, code) ; spécifications courantes ; état
  du compte (fonds propres, solde, marge utilisée, positions et propriétaires) ; toute erreur →
  `ENVIRONMENT_NOT_READY`.
- `gardes_compte` : base mémorisée à 00:00 UTC (P-12) ; garde quand fonds propres ≤ (1 −
  `daily_equity_loss_limit_fraction`) × base : clôture des positions possédées, annulation des intentions,
  blocage jusqu'au jour UTC suivant ; pic depuis l'activation ; arrêt quand fonds propres ≤ (1 −
  `peak_equity_drawdown_halt_fraction`) × pic : clôture et arrêt persistant, levé seulement par une décision de
  déploiement tracée ; flux externes identifiés et neutralisés avant reprise.
- `registre_reservations` : somme des réserves initiales, nouvelle comprise, ≤
  `account_max_initial_reserved_risk_fraction` × Eqt ; positions et réservations ≤ `account_max_positions` ;
  au plus `max_positions_per_canonical_symbol` par symbole canonique, méthodes et contrats confondus ; verrous
  de symbole ; libération seulement à la clôture ; les profits flottants ne libèrent rien ; idempotence par clé.
- `risque_all_in` : g = max(`tick_size`, `slippage_budget_atr_per_leg` × A_t) ; entrée pessimiste E + sens × g ;
  sortie pessimiste SL − sens × g ; perte = max(0, −profit du port) ; frais aller-retour non inclus dans les prix
  (commission par côté, minimum par ordre, autres frais, conversion USD) ; le spread n'est jamais ajouté à
  nouveau ; variante après remplissage : prix réel et seule la réserve de sortie.
- `arbitrage` : `simultaneous_strategy_priority` puis `universe_priority` ; réévaluation après chaque
  réservation ; ni fusion, ni score, ni couverture opposée sur un sous-jacent.
- `dimensionnement` : B = `risk_fraction_per_entry` × Eqt de l'instantané, gelé pour la tentative ; balayage de
  la grille native du plus grand volume admissible vers le minimum ; contraintes simultanées (risque ≤ B,
  réserve totale, positions, marge totale après ordre ≤ fraction × Eqt avec contrôle natif, bornes et droits) ;
  arrondi vers le bas ; aucun volume ≥ minimum → `MIN_VOLUME_OR_RISK_REJECT` ; positions externes → blocage ;
  calcul de réduction après remplissage.
- `cycle_ordre` : composante cyclique construite par couverture incrémentale des transitions (cycle minimal
  envoi → remplissage → clôture, puis refus, partiel, inconnu et rapprochement, protections, réduction) ; délai
  d'accusé ; réponse inconnue = verrou et rapprochement selon les cadences configurées, alerte après la
  fenêtre rapide, jamais de retransmission aveugle ; partiel : reliquat annulé, entrée comptée au premier volume
  non nul, jamais de complément automatique ; protections vérifiées, TP recalculé et ajusté dans la limite des
  tentatives, des délais et de l'échéance ; SL absent → clôture d'urgence immédiate ; TP non rétabli → clôture ;
  TP dépassé → clôture au prix disponible ; risque après remplissage au-delà des limites → réduction ou clôture.
- `sorties_obligatoires` : priorités du [document 01](01_architecture.md), §4.3, étape 2 ; une clôture en
  attente bloque les entrées du symbole ; sans cotation, la demande reste prioritaire et se réessaie selon
  `exit_retry_interval_seconds` dès que le marché est négociable ; aucune entrée rétroactive.
- `reprise_rapprochement` : étapes 3 et 4 du [document 01](01_architecture.md), §7.3.
- `coordinateur` : réception des réponses, événements de marché et minuteries, soumission des signaux ;
  pipeline d'admission du §4.3, étapes 4 et 5, avec recontrôle fondamental juste avant l'envoi ; un veto IA
  refuse la seule bougie courante (issue « refus définitif » avec `AI_CONTEXT_VETO`, aucun quota consommé) ;
  enregistrements C09 complets ; issues rendues aux stratégies.

### 6.5 Artefact `controles-fondamentaux` (paquet `xpbots.fondamental`, phase 7)

Rôle : valider les permissions externes et le calendrier, puis implémenter le port fondamental du
coordinateur. Point d'insertion : remplace l'implémentation neutre du port, hors scénario de contrôle technique.

| Unité | Couche | Responsabilité | Entrée → sortie | Dépend de | Amont | Sources |
|---|---|---|---|---|---|---|
| `types_fondamental` | 0 | Définir message, version de calendrier, annonce, devises par symbole et table d'importance versionnée | — | — | noyau | C05 |
| `message_permission` | 1a | Valider un message `fundamental-permission-v1` et ses heures | octets, réception, instant → message valide ou motif | `types_fondamental` | noyau | C05 |
| `garde_annonces` | 1b | Valider le calendrier, calculer les fenêtres interdites et les clôtures à N − 900 s | versions connues, symbole, instant → interdiction, clôtures | `types_fondamental` | noyau | C05 |
| `etat_permissions` | 2 | Tenir par symbole le dernier message valide, la séquence, l'expiration, le heartbeat et l'état `FLATTEN` | messages valides, instants → état | `message_permission` | noyau | C05 |
| `permissions` | 3 | Enveloppe : implémenter le port fondamental | symbole, sens, instant → décision ; clôtures obligatoires | `etat_permissions`, `garde_annonces` | execution-coordinateur, noyau | C05, C08 |

Esquisses de contrat :

- `message_permission` : clés et types exacts ; énumérations `ANY`, `LONG_ONLY`, `SHORT_ONLY` et `ALLOW`,
  `NO_NEW`, `FLATTEN` ; symbole de l'univers ; `issued_at ≤ known_at ≤ maintenant` ;
  `issued_at ≤ valid_from ≤ maintenant < valid_until` ; durée positive ≤ `fundamental_max_validity_seconds` ;
  aucun horodatage futur au-delà de `fundamental_timestamp_future_tolerance_seconds` ; réception locale ≥
  `known_at`, les deux conservées.
- `etat_permissions` : séquence strictement croissante par symbole ; dernier message utilisable jusqu'à son
  expiration ; minute de heartbeat manquée journalisée, blocage à l'expiration ; `FLATTEN` : clôture des
  positions possédées du symbole puis blocage pendant sa validité ; changement de direction sans clôture.
- `garde_annonces` : événements HIGH d'un fournisseur et d'une table d'importance versionnés ; devises par
  symbole selon C05 (EUR et USD pour EURUSD, GBP et USD pour GBPUSD, USD pour XAUUSD), table codée avec un test
  qui cite C05 ; fenêtre `[N − news_before_seconds, N + news_after_seconds)`, début inclus, fin exclue ;
  clôture des positions concernées à N − `news_before_seconds` ; calendrier actualisé depuis au plus
  `news_calendar_max_age_seconds` et couvrant `news_forward_coverage_seconds`, sinon aucune nouvelle entrée,
  sans liquidation pour la seule péremption ; annonce apprise tardivement dans sa fenêtre : blocage et clôture
  immédiats ; décisions prises sur les seules versions connues à l'instant ; historique jamais réécrit.
- `permissions` : contrôle au signal et juste avant l'ordre (deux appels du coordinateur) ; motifs
  `FUNDAMENTAL_INVALID`, `FUNDAMENTAL_DIRECTION`, `NEWS_WINDOW` et détails (P-07) ; jamais compensé par l'IA.

### 6.6 Artefact `contexte-ia` (paquet `xpbots.contexte_ia`, phase 8)

Rôle : valider le snapshot IA, conserver les vetos validés et implémenter le port du contexte IA. Comparaison :
`overlay_decision` de [llm_contracts.py](../../../reference/llm_contracts.py).

| Unité | Couche | Responsabilité | Entrée → sortie | Dépend de | Amont | Sources |
|---|---|---|---|---|---|---|
| `types_contexte` | 0 | Définir enveloppe, événement de veto et état du lecteur | — | — | noyau | A10 |
| `snapshot` | 1 | Valider taille, JSON strict, empreinte canonique, schéma, séquence, âge, empreinte de configuration et événements | octets, instant, dernière séquence → snapshot accepté ou rejet motivé | `types_contexte` | noyau | A10, A12 |
| `cache_vetos` | 2 | Conserver les vetos validés jusqu'à leur échéance propre, redémarrage compris | snapshots acceptés, instant → cache | `snapshot` | noyau | A10, A12 |
| `contexte_ia` | 3 | Enveloppe : implémenter le port du contexte IA, `BLOCK` ou `NEUTRAL`, jamais `ALLOW` | symbole, instant, politique du bras → décision | `cache_vetos` | execution-coordinateur, noyau | A06, A07, A12, A13 |

Esquisses de contrat : taille contrôlée avant analyse (`snapshot_max_bytes`) ; enveloppe limitée à `payload` et
`sha256` ; empreinte du JSON canonique du `payload` ; clés exactes ; schéma `xp-ai-context-v1` ; empreinte de
la configuration IA égale ; séquence entière ≥ max(1, dernière séquence persistée) ; horodatage non futur et âge
≤ `snapshot_max_age_seconds` ; événements à clés exactes, motif `OFFICIAL_UNSCHEDULED_POLICY`, fournisseur de
la liste autorisée, `valid_from` ≤ génération. Un snapshot périmé n'ajoute rien mais ne révoque pas un veto
déjà validé ; une séquence neuve ne prolonge aucun événement ; décision `BLOCK` si un veto du cache couvre le
symbole et `valid_from ≤ instant < valid_until` ; bras de référence et complément absent : `NEUTRAL` ; en
démonstration ou en réel, tant que `live_veto_requires_financial_validation` n'est pas satisfait : `NEUTRAL`.

### 6.7 Artefact `orchestration` (paquet `xpbots.orchestration`, phase 9)

Rôle : le moteur de décision événementiel, identique en rejeu et en direct, qui applique l'ordre de C08 à chaque
événement pour tous les bras. Point d'insertion : remplace l'enchaînement minimal du squelette.

| Unité | Couche | Responsabilité | Entrée → sortie | Dépend de | Amont | Sources |
|---|---|---|---|---|---|---|
| `contrats_orchestration` | 0 | Déclarer le contrat structurel d'une stratégie, la configuration de déploiement (avec ses fabriques de stratégie) et les enveloppes d'entrée et de sortie | — | — | noyau | C08, A13 |
| `bras` | 1 | Composer un bras : instances de stratégie par symbole créées par les fabriques injectées, coordinateur, politique IA | configuration de bras → bras ; export et import d'état | `contrats_orchestration` | execution-coordinateur, contexte-ia | A01, A13 |
| `moteur_decision` | 2 | Enveloppe : appliquer l'ordre C08 à chaque événement pour tous les bras, à partir d'entrées identiques | événement → commandes par bras, enregistrements, minuteries | `bras` | donnees-temps, controles-fondamentaux, noyau | C08, A07, C11.14 |

Esquisses de contrat : les bougies sont construites une seule fois et partagées ; l'état des permissions est
commun (entrées identiques) mais ses clôtures s'appliquent à chaque bras ; chaque bras possède ses propres
instances de stratégie (les quotas London dépendent de ses propres remplissages), son coordinateur et son
compte ; le bras IA utilise `contexte-ia`, le bras de référence le complément absent ; sorties étiquetées par
bras ; même séquence d'entrées → mêmes sorties. Le contrat structurel de stratégie (protocole Python) est
satisfait par le moteur London sans que celui-ci l'importe ; le moteur V1 de comparaison et le futur moteur EMA
le satisferont de même. Les tests de catégorie 2 de l'orchestration utilisent le vrai moteur London, artefact
amont figé, injecté comme en production.

### 6.8 Artefact `journal-rejeu` (paquet `xpbots.rejeu`, phase 10)

Rôle : simulateur d'exécution C10 (qui implémente le protocole du courtier et le port de calcul), rejeu des
périodes, métriques, bootstrap et rapports ; cœur pur qui reçoit des lignes de fichiers et rend des résultats.

| Unité | Couche | Responsabilité | Entrée → sortie | Dépend de | Amont | Sources |
|---|---|---|---|---|---|---|
| `types_rejeu` | 0a | Définir modèles d'exécution, comptes simulés, trades, jours de marché, perturbations et blocs | — | — | noyau | C10 |
| `protocole_c10` | 0b | Exposer blocs de dates, scénarios de coûts et seuils tels qu'écrits | configuration IA → protocole typé | — | noyau | C10, A13 |
| `analyse_ticks` | 1a | Analyser et valider des lignes de ticks dans l'ordre natif | lignes de texte, manifeste → ticks, registre de trous | `types_rejeu` | noyau | C10, données §2 |
| `simulateur_execution` | 1b | Exécuter les commandes sur ticks selon le modèle de référence ou de stress et fournir le port de calcul | commandes, ticks → réponses, état du compte | `types_rejeu` | execution-coordinateur, noyau | C10, C11.12, P-11 |
| `metriques` | 1c | Calculer effectifs, espérance, profit factor, drawdown de fonds propres, rétention et fréquence | trades, courbe, jours → métriques | `types_rejeu` | noyau | C09, C10, A13 |
| `bootstrap` | 1d | Bootstrap de blocs de cinq journées, graine et réplications de l'export, percentiles | sommes journalières → intervalles | `types_rejeu`, `protocole_c10` | noyau | C10, A13.7 |
| `executeur_rejeu` | 2 | Rejouer une période : analyse, orchestration, simulateur ; blocs, rejeu continu, bras, perturbations, verrou du test réservé | périodes, ticks, configuration → résultats | `analyse_ticks`, `simulateur_execution`, `protocole_c10` | orchestration, moteur-london (fabrique), noyau ; moteur-london-v1 à partir de 13.4 | C10, A13 |
| `rapports` | 3 | Produire les rapports C10, A11 London et A13 | résultats → rapports structurés | `metriques`, `bootstrap`, `executeur_rejeu` | noyau | C10, A11, A13, A14 |

Esquisses de contrat :

- `protocole_c10` : les valeurs qui n'existent que dans le texte de C10 (dates des blocs, délais de 250 ms et
  1 000 ms, un et deux ticks adverses, facteur de spread de stress) sont codées une fois, avec un test qui
  vérifie leur présence dans la spécification ; les seuils `financial_*` et `bootstrap_*` sont lus dans la
  configuration IA.
- `simulateur_execution` : ordre au marché envoyé à t, exécuté au premier tick d'heure ≥ t + délai, à l'Ask
  pour un achat et au Bid pour une vente, dégradé du nombre de ticks adverses (P-11) ; stress : Ask = Bid +
  1,25 × spread historique, Bid technique inchangé ; TP limite exécuté au niveau ou mieux seulement s'il est
  exécutable, jamais pénalisé sous son prix limite ; protections natives traitées avant les sorties
  logicielles ; stops subissant les gaps ; SL et TP de même milliseconde départagés par la séquence ; profit
  des symboles cotés en USD = écart de prix × volume × taille de contrat, vérifié contre `order_calc_profit` en
  phase 11 ; fonds propres = solde + flottant (achat au Bid, vente à l'Ask) ; aucun apport ni retrait ; une
  position qui chevaucherait le blackout est une erreur de code ; mode scénarisé (partiels, délais) pour les
  tests.
- `metriques` : par méthode, symbole, bras et bloc ; profit factor sans perte → non applicable signalé ;
  drawdown sur la courbe de fonds propres ; fréquence par jour de marché au sens de C09, jours à zéro inclus ;
  rétention N/A si référence nulle, « trop faible » sous 50 trades ; ratio de configurations rapporté à part.
- `bootstrap` : algorithme exact de C10 et A13.7 (blocs contigus dans chaque période continue, tirage avec
  remise de ⌈n/5⌉ blocs, concaténation, troncature, sommes journalières de P&L net et de trades clos au jour de
  sortie, espérance = somme / nombre, indices appariés, réplications sans trade comptées) ; générateur
  `random.Random(graine)` de la bibliothèque standard, seul usage autorisé de `random`.
- `executeur_rejeu` : expérience autonome à 100 USD par bloc, préchargement sur son seul passé ; rejeu continu
  du 01/01/2020 au 03/11/2026 avec arrêts persistants ; jamais de courbes additionnées ; référence et stress ;
  bras A/B ; contrôle technique neutre nommé ou permissions historiques ; six perturbations exécutées comme
  diagnostics séparés par un objet d'écart explicite, journalisé, refusé hors rejeu ; verrou du test réservé
  (refus de la période 01/01/2025–30/04/2026 sans empreinte de robot figé, option explicite et
  journalisation) ; période 01/05–03/11/2026 étiquetée diagnostic.
- `rapports` : tableau des critères face aux seuils fixés a priori ; ventilation A11 London (par W/ATR_H1,
  heure de première cassure, sens, stop local, coût, nouveau signal après veto : performance, gagnants bloqués,
  opportunités tardives, ratio de remplissage) ; rapport A/B ; garde « une précision JSON n'est pas un taux de
  réussite de trades ».

### 6.9 Artefact `infrastructure` (paquet `xpbots.infra`, phase 11)

Rôle : seules implémentations réelles des frontières externes. Précédé des sondes jetables S-01 à S-08.

| Unité | Couche | Responsabilité | Entrée → sortie | Dépend de | Frontière réelle | Sources |
|---|---|---|---|---|---|---|
| `types_infra` | 0a | Définir la table versionnée heure serveur → UTC et les correspondances des structures MT5 | — | — | — | C03.1, A04 |
| `horloge_systeme` | 0b | Fournir l'instant UTC et un temps monotone pour les délais | — → instants | — | `time` | C03 |
| `depot_sqlite` | 0c | Stocker l'état par transactions exclusives | états → base | — | `sqlite3` | C07, C08 |
| `journal_fichiers` | 0d | Écrire journal de décisions et journal d'entrées en JSON Lines | enregistrements → fichiers | — | système de fichiers | C09, C11.14 |
| `lecteur_snapshot` | 0e | Lire les octets du snapshot IA au chemin réel, avec plafond de taille | chemin → octets, heure de lecture | — | système de fichiers | A10 |
| `lecteur_ticks` | 0f | Lire en flux les fichiers de ticks mensuels et calculer leur empreinte | fichiers → lignes, SHA-256 | — | système de fichiers | C10 |
| `sources_controles` | 0g | Lire le dossier d'échange des permissions (D-11), les exports MQL5 du calendrier et des séances et le fichier des fermetures exceptionnelles (D-12) | fichiers → octets horodatés à la lecture | — | système de fichiers | C04, C05 |
| `mt5_session` | 1 | S'attacher au terminal, lire version, état, compte et dossier commun | — → session et informations | `types_infra` | `MetaTrader5` | C04 |
| `mt5_specifications` | 2a | Lire et contrôler les caractéristiques C04 et produire les profils | symbole → profils, liste `ENVIRONMENT_NOT_READY` | `mt5_session` | `MetaTrader5` | C04 |
| `mt5_flux` | 2b | Récupérer les ticks incrémentalement, convertir l'heure, signaler la connexion | symbole, curseur → ticks, états de connexion | `mt5_session`, `types_infra` | `MetaTrader5` | C03, S-01, S-08 |
| `mt5_calculs` | 2c | Implémenter le port de calcul avec les fonctions natives | requêtes → résultats | `mt5_session` | `MetaTrader5` | C04, C07, S-07 |
| `mt5_execution` | 2d | Exécuter les commandes d'ordre avec délai d'accusé et rapprochement | commandes → réponses | `mt5_session` | `MetaTrader5`, `threading` | C08, S-02 à S-06 |
| `courtier_mt5` | 3 | Composer les adaptateurs MT5 en exécutant de commandes et en qualification de l'environnement au démarrage et avant ordre | commandes, contrôles → réponses, rapports | 2a, 2b, 2c, 2d | — | C04, C08 |
| `assemblage` | 4 | Enveloppe : fournir à la coquille l'ensemble configuré des adaptateurs réels | configuration d'exécution → adaptateurs prêts | 0b à 0g, 3 | — | C08, A10 |

Chaque adaptateur feuille déclare sa frontière réelle dans `depend_de` (horloge, SQLite, système de fichiers,
`MetaTrader5`) : une simulation de cette carte avec `mcl.py analyser` donne alors une racine unique,
`assemblage`, et aucune unité isolée.

Esquisses de contrat : entrée au marché avec `sl` et `tp` dans la même requête, numéro magique et commentaire,
mode de remplissage qualifié ; délai d'accusé de `request_ack_timeout_seconds` par un exécutant dédié ;
ajustement du TP par `TRADE_ACTION_SLTP` ; clôture par transaction opposée sur le ticket ; rapprochement par
`positions_get`, `orders_get`, `history_orders_get`, `history_deals_get` filtrés ; spécifications relues
avant chaque ordre (C04) ; aucun secret journalisé.

### 6.10 Artefact `points-entree` (paquet `xpbots.app`, phase 11)

| Unité | Couche | Responsabilité | Entrée → sortie | Dépend de | Amont | Sources |
|---|---|---|---|---|---|---|
| `configuration_application` | 0 | Lire arguments, chemins, mode, identifiant et registre de déploiement | arguments, fichiers → configuration d'exécution | — | noyau | C01, A01 |
| `boucle_direct` | 1a | Démarrer, rapprocher, scruter, planifier, exécuter les commandes après écriture de l'état, s'arrêter proprement | configuration → exécution continue | `configuration_application` | infrastructure, orchestration, moteur-london (fabrique) | C08, A03, A10 |
| `cli_rejeu` | 1b | Lancer un rejeu C10 | arguments → résultats et rapports | `configuration_application` | journal-rejeu, infrastructure | C10 |
| `cli_qualification` | 1c | Qualifier l'environnement C04 et exécuter les contrôles de qualification | arguments → rapport | `configuration_application` | infrastructure | C04 |
| `cli_rapports` | 1d | Produire les rapports à partir des journaux | journaux → rapports | `configuration_application` | journal-rejeu, infrastructure | C09, A11 |
| `principal` | 2 | Points d'entrée `python -m` et refus des modes non autorisés | arguments → code de sortie | 1a, 1b, 1c, 1d | — | C01 |

### 6.11 Artefact `service-ia` (paquet `xpbots.service_ia`, phase 12, processus séparé)

Comparaison : fonctions de [llm_contracts.py](../../../reference/llm_contracts.py). Carte indicative : comme pour
tout artefact, `mcl.py analyser` fixe les profondeurs définitives avant la première couche.

| Unité | Couche | Responsabilité | Dépend de | Frontière réelle | Sources |
|---|---|---|---|---|---|
| `types_service` | 0a | Définir éléments sources, travaux, résultats, événements, budget et instantané | — | — | A04 à A10 |
| `borne_tokens` | 0b | Borner les tokens d'entrée et raccourcir un dossier sans couper une négation ni une condition | — | — | A09 |
| `validateur_sortie` | 0c | Valider strictement les sorties d'extraction et informatives | — | — | A05, A11 |
| `normalisation_rss` | 1a | Normaliser et dédoublonner les textes officiels, première heure de connaissance conservée | `types_service` | — | A04 |
| `constructeur_veto` | 1b | Construire un événement `OFFICIAL_UNSCHEDULED_POLICY` si toutes les conditions sont réunies | `types_service`, `validateur_sortie` | — | A06 |
| `registre_budget` | 1c | Réserver et rapprocher les coûts par transaction exclusive en décimal | `types_service` | `sqlite3` | A09 |
| `clients_fournisseurs` | 1d | Construire les requêtes Groq, Gemini et OpenAI et lire leurs réponses et leur usage | `types_service` | `urllib` | A08 |
| `collecteur_rss` | 2a | Interroger les flux officiels (requêtes conditionnelles, délais, plafonds, reprises, redirections bornées) | `normalisation_rss` | `urllib` | A04 |
| `routeur` | 2b | Choisir la route, appliquer délais, quotas, reprises et échéance | `clients_fournisseurs`, `registre_budget`, `borne_tokens` | — | A08, A09 |
| `ecrivain_snapshot` | 2c | Écrire le snapshot de façon atomique, séquence persistée | `types_service` | système de fichiers | A10 |
| `planificateur` | 3 | Planifier briefing, classification, journal, revue et cas de dérive sous les plafonds | `routeur`, `collecteur_rss`, `constructeur_veto` | — | A09, A11, A13 |
| `service` | 4 | Enveloppe : heartbeat indépendant, travailleur d'inférence unique, collecteur séparé | `planificateur`, `ecrivain_snapshot` | — | A03, A10 |

### 6.12 Composant MQL5 `XPBotsExport` (phase 11, hors carte `mcl.py`)

Rôle : exporter le calendrier HIGH et les horaires de séance que le paquet Python `MetaTrader5` n'expose pas
(D-12). Contrat de sortie : [document 01](01_architecture.md), §2.2. `mcl.py` n'analyse pas MQL5 : le composant
reste volontairement minuscule et sans logique de décision.

| Module | Responsabilité | Fonctions natives | Contrôle |
|---|---|---|---|
| Export du calendrier | Lire les événements d'importance haute des devises suivies sur la fenêtre requise et écrire `calendrier.json` | Fonctions `Calendar*` (pays, événements, valeurs, détection des changements) | Fixtures Python du format ; comparaison sur le poste avec la vue calendrier du terminal |
| Export des séances | Lire les séances de cotation et de négociation de chaque symbole lié et écrire `seances_<symbole>.json` | `SymbolInfoSessionQuote`, `SymbolInfoSessionTrade` | Fixtures Python ; comparaison avec la fiche du symbole |
| Écriture atomique | Écrire un fichier temporaire du dossier commun, le vider, puis le substituer au fichier publié | `FileOpen` avec `FILE_COMMON`, `FileFlush`, `FileMove` avec remplacement | Lecture concurrente par le robot sans fichier tronqué |
| Boucle du service | Exporter le calendrier chaque minute et les séances chaque heure, journaliser les erreurs du terminal | Service MQL5, minuterie | Compilation sans avertissement dans MetaEditor ; journal du terminal |

Règles : une convention de module (un fichier par module, aucune variable globale partagée hors de la boucle),
une revue de code obligatoire, aucune décision de trading, aucune écriture hors de `XPBots/export/v1/`.

### 6.13 Artefact `moteur-london-v1` (paquet `xpbots.london_v1`, sous-étape 13.4)

Rôle : porter les règles V1 London fournies par l'utilisateur (D-15) sur le même moteur d'exécution, le même
compte, les mêmes coûts et les mêmes permissions que V3, pour la seule rétention `N_V3 / N_V1` de C10.

- Construction MCL complète, avec sa propre carte ; unités cartographiées à partir de la spécification V1 une
  fois fournie (elle est d'abord versée dans `docs/references/` comme contexte, avec son empreinte SHA-256, et
  ne devient jamais normative pour V3).
- Le moteur satisfait le contrat structurel de stratégie de l'orchestration ; il est injecté seulement par
  l'exécuteur de rejeu ; tout mode autre que `REJEU` le refuse au démarrage.
- Il réutilise les unités de `donnees-temps` ; il n'importe ni `moteur-london` ni `execution-coordinateur`
  (couche parallèle 2c de la carte composite).
- Aucune règle de V3 n'est modifiée ; un écart de comportement V1 qui exigerait de changer le noyau ou le
  coordinateur est signalé comme défaut avant toute adaptation.

## 7. Frontières externes et doublures

| Frontière | Contrat attendu | Doublure minimale (tests) | Couches qui l'utilisent doublée | Implémentation réelle | Test de contrat |
|---|---|---|---|---|---|
| Flux de ticks MT5 | Événements tick et connexion poussés par la coquille | Fabrique de ticks synthétiques | `donnees-temps`, `moteur-london`, `orchestration`, `journal-rejeu` | `infrastructure` 2b | S-01, S-08 sur compte démo |
| Exécution du courtier | Protocole commandes et réponses (`execution-coordinateur` 0a) | Courtier scénarisé | `execution-coordinateur`, `orchestration` | `infrastructure` 2d ; simulateur en rejeu et papier | S-02 à S-06 sur compte démo |
| Calculs du courtier | Port de calcul (`execution-coordinateur` 1a) | Calculateur paramétré en mémoire | `execution-coordinateur`, `orchestration` | `infrastructure` 2c ; simulateur | S-07 : égalité simulateur et MT5 |
| Horloge | Instants portés par les événements | Instants scénarisés | Tout le cœur | `infrastructure` 0b | Dérive mesurée face à l'heure du courtier |
| Stockage d'état | Export et import d'état par la coquille | SQLite en mémoire | `points-entree` | `infrastructure` 0c | Reprise après arrêt brutal |
| Journal | Enregistrements C09 et d'entrées | Liste en mémoire | `points-entree` | `infrastructure` 0d | Relecture canonique identique |
| Snapshot IA | Octets et heure de lecture | Octets fabriqués | `contexte-ia` | `infrastructure` 0e | Écriture et lecture concurrentes sous Windows |
| Fichiers de ticks | Lignes de texte et manifeste | Lignes fabriquées | `journal-rejeu` | `infrastructure` 0f | Empreintes et ordre natif |
| Dossier d'échange des permissions (D-11) | Octets de messages et heure de lecture | Messages scénarisés avec `known_at` ; fichiers écrits par un module factice | `controles-fondamentaux` | `infrastructure` 0g | Remplacement concurrent par le vrai module, sous Windows |
| Export MQL5 du calendrier et des séances (D-12) | Versions horodatées | Versions scénarisées ; fixtures JSON du format | `controles-fondamentaux`, `execution-coordinateur`, `service-ia` | `infrastructure` 0g et service MQL5 | Export réel comparé à la vue du terminal |
| API LLM | Requêtes et réponses HTTPS | Ouvreur HTTP factice | `service-ia` | `service-ia` 1d | Conformité A08, avec accord explicite de l'humain |
| Flux RSS | XML sur HTTPS | XML fabriqué | `service-ia` | `service-ia` 2a | Lecture réelle Fed et BCE ; BoE refusé en 403 lors de l'examen |
| SQLite du service | Registre et cache | Base en mémoire | `service-ia` | `service-ia` 1c | Concurrence des réservations |

## 8. Imports interdits par carte

| Cartes | Interdits (déclarés en `externes` avec `couches_autorisees` vide) |
|---|---|
| `noyau`, `donnees-temps`, `moteur-london`, `moteur-london-v1`, `execution-coordinateur`, `controles-fondamentaux`, `contexte-ia`, `orchestration` | `time`, `os`, `pathlib`, `io`, `socket`, `http`, `urllib`, `sqlite3`, `threading`, `subprocess`, `random`, `MetaTrader5`, `reference`, et tous les paquets `xpbots` en aval ou parallèles (pour `orchestration` : aussi `xpbots.london` et `xpbots.london_v1`) |
| `journal-rejeu` | Les mêmes, sauf `random`, autorisé dans la seule couche `bootstrap` |
| `infrastructure` | `reference`, `xpbots.app`, `xpbots.service_ia` ; chaque frontière réelle autorisée dans ses seules couches |
| `points-entree` | `reference` et les frontières réelles directes (toujours par `xpbots.infra`) |
| `service-ia` | `MetaTrader5`, `reference`, et les paquets du robot autres que `xpbots.noyau` et le format de `xpbots.contexte_ia` |

Un test transversal de pureté (document 03, §8) complète ces règles : aucun appel à l'horloge système, à
`datetime.now` ou à `date.today` dans les paquets du cœur.

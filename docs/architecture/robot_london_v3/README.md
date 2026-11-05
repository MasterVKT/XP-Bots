# Plan d'implémentation intégrale du robot 2 — London Breakout M15 (`LONDON_V3`)

> Plan directeur, version **1.2.0** du **5 novembre 2026**. Statut : **validé par l'utilisateur le
> 05/11/2026** ; couverture vérifiée mécaniquement par `python tools/verifier_plan_london.py`
> ([document 06](06_verification_exhaustive.md)). Toutes les décisions de conception et les douze arbitrages de spécification sont arrêtés ; il
> ne reste que des **actions humaines** datées par phase (§5). Aucune ligne de code du robot n'existe encore.
> Ce plan organise la construction ; il n'ajoute, ne retire et ne modifie aucune règle métier, aucun seuil et
> aucun coût.

## 0. Autorité, portée et lecture

- **Autorité métier** : la [spécification 02 London Breakout 3.1.0](../../../livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md)
  (C01–C11, S02, A01–A15) et ses exports : [paramètres techniques](../../../config/parametres_figes_v3.json),
  [paramètres IA](../../../config/parametres_IA_integration_v1.json),
  [schéma d'extraction](../../../schemas/schema_extraction_LLM_v1.json),
  [schéma des notes](../../../schemas/schema_notes_IA_v1.json) et [prompts](../../../prompts/prompts_IA_v1.json).
  En cas de contradiction entre ce plan et ces sources, **les sources prévalent** et la contradiction devient un
  défaut de spécification signalé (C02), jamais un arbitrage improvisé.
- **Règles transversales** : [AGENTS.md](../../../AGENTS.md) et [règles du projet](../../../.agents/PROJECT_RULES.md).
  **Ordre produit** des composants : [guide d'implémentation](../GUIDE_IMPLEMENTATION.md), section « Ordre de
  construction et de qualification ».
- **Méthode** : MCL (Matryoshka Construction Layers) appliquée par la skill
  [xp-bots-mcl-robot-planning](../../../.agents/skills/xp-bots-mcl-robot-planning/SKILL.md) et sa
  [cartographie de référence](../../../.agents/skills/xp-bots-mcl-robot-planning/references/cartographie-xp-bots.md) ;
  méthode S02 par la skill [xp-bots-london-breakout](../../../.agents/skills/xp-bots-london-breakout/SKILL.md) ;
  regard d'expert M15 par la skill `anthropic-skills:expert-scalper-m15`, appliquée **sans jamais modifier une
  valeur figée** (voir [document 05](05_expert_risques_tracabilite.md)).
- **Fonctions de référence** : [reference/](../../../reference/README.md) est un **oracle de comparaison** pour
  les tests, jamais une couche du robot ni un composant opérationnel.
- **Avertissement** : la rentabilité n'est pas validée (C01). Le trading de change à effet de levier est à haut
  risque. Ce plan est de l'ingénierie logicielle et de l'analyse technique éducative, pas un conseil financier.
  Aucune mise en service réelle n'intervient sans démonstration prospective et décision humaine tracée
  (C10, A13).

### Documents du plan

| Document | Contenu |
|---|---|
| Ce fichier | Règle d'exécution par phases, synthèse, décisions, arbitrages, actions humaines restantes, hors périmètre |
| [01 — Architecture cible](01_architecture.md) | Principes, processus, contrats d'échange (permissions, export MQL5), modes, événements, ordre de traitement, arborescence, numérique, persistance, journal, particularités MT5 |
| [02 — Cartographie MCL](02_cartographie_mcl.md) | Applicabilité, squelette composite, conventions des cartes, artefacts, unités, couches, contrats esquissés, frontières et doublures |
| [03 — Acceptation et tests](03_acceptation_et_tests.md) | Catégories de tests, lanceur, commandes de gate, affectation des cas C11, S02.6 et A14, scénarios London détaillés |
| [04 — Phases d'exécution](04_phases.md) | Phases 0 à 13 : objectifs, prérequis, étapes, livrables, critères de sortie, points d'arrêt |
| [05 — Expert, risques, traçabilité](05_expert_risques_tracabilite.md) | Lecture d'expert M15, registre des risques, coûts et garanties MCL, matrice spécification → plan |
| [06 — Vérification exhaustive](06_verification_exhaustive.md) | Rattachement de chaque paramètre (163 clés), de chaque exigence (155 lignes, 46 sections) et de chaque consigne d'expert (71) à un emplacement du plan ; contrôle de codifiabilité ; manques trouvés et corrigés |

## 1. Règle d'exécution par phases (demande explicite de l'utilisateur)

1. Le plan s'exécute **une phase à la fois**, dans l'ordre du [document 04](04_phases.md), à partir de la
   phase 0.
2. À la fin **intégrale** d'une phase, l'agent : exécute le gate global de l'artefact et la vérification du
   projet, commite et pousse sur la branche de travail, remet un **rapport de phase** (unités construites,
   contrats figés, effectifs des tests de catégorie 1 et 2, résultat de la régression intégrale, défauts
   trouvés, limites), puis **s'arrête**.
3. L'agent ne commence la phase suivante **que sur demande explicite** de l'humain (par exemple « passe à la
   phase 3 »). Aucune anticipation : seule la préparation du contrat de la couche suivante est permise
   **à l'intérieur** d'une même phase (tuilage MCL).
4. Une phase qui attend une action humaine (§5) s'arrête sur une question explicite, avec le marqueur de
   blocage du cycle de gouvernance.
5. À l'intérieur d'une phase, chaque couche suit la boucle MCL complète : contrat finalisé → implémentation →
   tests de catégorie 1 → validation → intégration → tests de catégorie 2 → régression intégrale → gel.

## 2. Synthèse

### 2.1 Ce qui sera construit

- Un robot Python (paquet `xpbots`, sous `src/xpbots/`) qui applique **exactement** S02 sur EURUSD et GBPUSD
  (XAUUSD reste techniquement pris en charge, sans être retenu comme praticable à 100 USD), avec le risque de
  C07, la coordination de compte de C08, les permissions fondamentales obligatoires de C05 et le veto IA
  facultatif de A07.
- **Un seul moteur de décision** pour le rejeu, le papier, `PAPER_AB`, la démonstration et le réel (C11.14) :
  le cœur est déterministe, piloté par événements, sans entrée-sortie ; seule la coquille change ; les
  stratégies y sont **injectées**, ce qui permet de brancher le moteur V1 de comparaison puis le robot EMA sans
  défiger l'orchestration.
- Un adaptateur MT5 fondé sur le paquet officiel `MetaTrader5` (Windows), un **service MQL5 d'export** du
  calendrier et des horaires de séance, un **dossier d'échange JSON** pour les permissions du module fondamental
  externe, un stockage d'état SQLite, un journal C09 rejouable, un lecteur du snapshot IA.
- Un simulateur d'exécution C10 (référence et stress), un moteur de rejeu, les métriques et le bootstrap de
  C10/A13, les rapports A11, et le moteur V1 London porté pour la seule comparaison de rétention.
- Le service IA partagé (A04–A11), processus séparé, facultatif pour le cœur et nécessaire au bras IA de
  `PAPER_AB`.
- Les composants partagés (noyau, données, coordinateur, contrôles, orchestration) sont conçus pour recevoir
  plus tard le robot EMA **sans le construire maintenant** : deux artefacts distincts, seul le coordinateur
  de compte est partagé.

### 2.2 Schéma d'ensemble

```text
ticks Bid/Ask ──► donnees-temps (C03) ──► moteur-london (S02) ──► signal technique
                                                                      │
  dossier d'échange C05 ──► controles-fondamentaux ──┐                ▼
  export MQL5 (calendrier)                           ├──► execution-coordinateur (C06–C08)
  snapshot IA A10 ──► contexte-ia (A07/A12) ─────────┤                │ commandes
                       orchestration (ordre C08, bras A/B, stratégies injectées)
                                                                      ▼
                       simulateur C10 (rejeu, papier) ou adaptateur MT5 (démo, réel)
                                                                      │
                                         journal C09 + journal d'entrées ──► rejeu, rapports
```

### 2.3 Phases et points d'arrêt

| Phase | Objet | Artefact MCL | Actions humaines requises | Arrêt |
|---|---|---|---|---|
| 0 | Mise en place : dossier MCL composite, carte composite, mise à jour du guide et des règles du projet | — | — | Oui |
| 1 | Squelette composite déployable et lanceur de tests (sans intégration continue distante, D-10) | `squelette` (hors protocole) | — | Oui |
| 2 | Noyau partagé : temps, nombres, configuration figée, marché, instrument, domaine, journal | `noyau` | — | Oui |
| 3 | Données et temps (C03) | `donnees-temps` | — | Oui |
| 4 | Moteur London (S02) | `moteur-london` | — | Oui |
| 5 | Exécution et coordinateur : calculs purs (C06, C07) | `execution-coordinateur`, couches 0 à 3 | — | Oui |
| 6 | Exécution et coordinateur : cycle d'ordre, sorties, reprise (C08) | `execution-coordinateur`, couches 4 à 6 | — | Oui |
| 7 | Contrôles fondamentaux et annonces (C05) | `controles-fondamentaux` | — | Oui |
| 8 | Lecteur du contexte IA (A07, A10, A12) | `contexte-ia` | — | Oui |
| 9 | Orchestration : moteur de décision événementiel, bras A/B | `orchestration` | — | Oui |
| 10 | Simulateur C10, rejeu, métriques, bootstrap, rapports | `journal-rejeu` | — | Oui |
| 11 | Infrastructure réelle (MT5, export MQL5, dossier d'échange, SQLite, journaux) et points d'entrée | `infrastructure`, `points-entree`, service MQL5 | Accès au poste Windows, compte démo Deriv MT5, compilation du service MQL5, configuration du module fondamental | Oui |
| 12 | Service IA partagé (A04–A11) | `service-ia` | Autorisation des appels d'API réels, clés des routes gratuites | Oui |
| 13 | Qualification et validation (sous-étapes 13.1 à 13.7) | `moteur-london-v1` en 13.4 | Données, fichier V1, annotation, décisions | Oui, à chaque sous-étape |

Les phases 0 à 10 ne requièrent aucune action humaine autre que la demande de passage à la phase suivante.

## 3. Décisions (section 2 du plan MCL)

| Id | Décision | Statut | Justification | Utile à partir de |
|---|---|---|---|---|
| D-01 | Plateforme et langage : **Python 3.13 + MT5** piloté par le paquet officiel `MetaTrader5` (version 5.0.6231 du 27/09/2026 relevée sur PyPI : roues Windows x64 de Python 3.6 à 3.14) | Arrêtée par l'utilisateur le 05/11/2026 | Un seul moteur pour rejeu et plateforme (C11.14) ; service IA déjà en Python (A01) ; oracles de `reference/` en Python | — |
| D-02 | Sources dans **`src/xpbots/`** (paquet unique), tests dans `tests/robot/`, dossiers MCL dans `mcl/<artefact>/` | Arrêtée par l'utilisateur le 05/11/2026 | Noyau partagé entre les deux robots ; analyse des imports Python par `mcl.py` | — |
| D-03 | Architecture « noyau déterministe piloté par événements + coquille impérative » ([document 01](01_architecture.md), §1) | Arrêtée (approuvée le 05/11/2026) | A03, C06, C08, C11.14 | Phase 1 |
| D-04 | Tests : bibliothèque standard `unittest` et lanceur `tools/run_robot_tests.py` ; aucun `pytest` | Arrêtée (approuvée le 05/11/2026) | Aucune dépendance nouvelle (règles du projet, §4) | Phase 1 |
| D-05 | Dépendances : cœur en bibliothèque standard ; à l'exécution Windows, `tzdata` (déjà épinglée dans `requirements-dev.txt`) et `MetaTrader5` dans un fichier d'exigences Windows distinct ; rien d'autre | **Autorisée** par l'utilisateur le 05/11/2026 pour `MetaTrader5` | Règles du projet, §4 | Phase 11 |
| D-06 | État persistant en SQLite (bibliothèque standard), dans `runtime/` ignoré par Git, transactions exclusives | Arrêtée (approuvée le 05/11/2026) | C07, C08 (réservation et intention persistées avant envoi) | Phase 11 |
| D-07 | Journal C09 en JSON Lines canonique quotidien et journal d'entrées rejouable, dans `logs/` ignoré par Git | Arrêtée (approuvée le 05/11/2026) | C09, C11.14 | Phase 2 (format), 11 (écriture) |
| D-08 | Identification des ordres : numéro magique par couple (déploiement, stratégie) ; commentaire = préfixe et empreinte courte de la clé d'intention (longueur maximale qualifiée par la sonde S-05) | Arrêtée (approuvée le 05/11/2026) | C08 (clé persistante, propriété, positions externes) | Phase 6 |
| D-09 | Période de la boucle en direct : constante d'ingénierie de 100 ms, consignée au registre de déploiement, jamais réglée sur un résultat | Arrêtée (approuvée le 05/11/2026) | TTL de 5 s, cotation âgée d'au plus 2 s, délais de correction de 0,25 s | Phase 11 |
| D-10 | Intégration continue distante (GitHub Actions) et porte `robot-suite` du cycle de vie | **Non autorisée** au 05/11/2026 | Sans elle : la suite du robot s'exécute à chaque gate MCL et avant chaque commit ; les écarts propres à Windows ne se révèlent qu'en phase 11, sur le poste ; peut être redemandée | Phase 1 |
| D-11 | Transport des permissions du module fondamental externe : **dossier d'échange JSON** à écriture atomique, un fichier par symbole, lu chaque seconde ([document 01](01_architecture.md), §2.1) | Arrêtée par l'utilisateur le 05/11/2026 | Même mécanisme éprouvé que le snapshot IA (A10) ; aucun réseau | Phase 7 (format), 11 (lecture) |
| D-12 | Calendrier HIGH et horaires de séance : **service MQL5 d'export** vers le dossier commun du terminal, seul composant MQL5 du projet ([document 01](01_architecture.md), §2.2) ; fermetures exceptionnelles tenues dans un fichier versionné | Arrêtée par l'utilisateur le 05/11/2026 | Le paquet Python `MetaTrader5` n'expose ni le calendrier ni les séances ; A04 autorise le calendrier natif MT5 | Phase 7 (format), 11 (service) |
| D-13 | Courtier du compte de démonstration : **Deriv MT5** | Arrêtée par l'utilisateur le 05/11/2026 | Symboles micro listés dans le [snapshot public](../../validation/snapshot_public_Deriv_2026-11-04.json) ; disponibilité sur le compte standard à vérifier en 13.1 | Phase 11 |
| D-14 | Ticks historiques C10 : ticks exacts du symbole lié chez le courtier s'ils couvrent la période ; à défaut, source tierce (par exemple Dukascopy) **déclarée contrefactuelle** | Arrêtée par l'utilisateur le 05/11/2026 | C10 ; [données requises](../../data/03_Donnees_Historiques_Requises_et_Validation.md) | Sous-étape 13.3 |
| D-15 | Règles V1 London : **fournies par l'utilisateur** depuis l'archive locale (voir le [registre de nettoyage](../../maintenance/NETTOYAGE_ET_MERGE.md)) avant la sous-étape 13.4 ; portées dans l'artefact distinct `moteur-london-v1`, réservé au rejeu, sans modifier V3 | Arrêtée par l'utilisateur le 05/11/2026 | C10 (comparaison sur le même moteur) | Sous-étape 13.4 |
| D-16 | Calendrier du protocole C10 : la démonstration prospective prévue « à partir du 05/11/2026 » ne peut commencer qu'après le gel du robot ; le bilan du 04/02/2027 se tiendra avec les effectifs disponibles et le protocole se prolongera jusqu'aux effectifs requis ; aucune date normative n'est modifiée | Note | C10 | Phase 13 |
| D-17 | Appels réels aux API LLM (conformité et fonctionnement du service) | **Non autorisés** au 05/11/2026 ; redemandés au début de la phase 12 | Sans autorisation : service construit et testé hors ligne, bras IA `NEUTRAL` | Phase 12 |
| D-18 | Stratégies injectées dans l'orchestration par la configuration de déploiement (contrat structurel), sans import direct du moteur London | Arrêtée : détail de conception découlant de D-03, introduit le 05/11/2026 pour D-15 | Moteur V1 et futur robot EMA branchés sans défigeage ; simulation de la carte composite inchangée en profondeurs | Phase 9 |

## 4. Arbitrages de spécification (défauts signalés, C02)

Chaque point ci-dessous est une ambiguïté réelle relevée en recoupant le texte, le JSON normatif et
`reference/technical.py`. **Le 05/11/2026, l'utilisateur a retenu la proposition recommandée de chacun des douze
points.** Ces lectures sont littérales ou prudentes ; aucune ne change une règle, un seuil ou un coût. Elles
entrent dans les contrats des couches indiquées.

| Id | Sections | Question | Décision retenue | Alternative écartée | Couche |
|---|---|---|---|---|---|
| P-01 | C03.5, C03.7, S02.1 | Comment établir la « couverture du flux » d'un intervalle antérieur au démarrage (préchargement, reprise, rejeu) ? | En direct : journal de connexion du robot sur toute la partie ouverte de l'intervalle. En historique : absence de trou dans le registre des trous de la source (données §2, « trous connus ») et séance native ouverte ; une source sans registre ne permet pas d'établir la couverture | Toute bougie historique contenant au moins un Bid est réputée couverte | `donnees-temps` 1c |
| P-02 | C03.5 | Un intervalle couvert, marché ouvert, sans aucun événement : bougie invalide ? trou bloquant ? | Bougie invalide (aucun Bid, aucun remplissage synthétique), détail `AUCUN_BID`, sans état `DATA_GAP` ; elle invalide un range qui la contient | Traiter l'intervalle comme un trou bloquant | `donnees-temps` 2a |
| P-03 | C03.6, C03.10, S02.1 | Récurrences et reprise après une bougie invalide ou un trou | Une bougie invalide n'entre dans aucune récurrence ; la suivante calcule TR avec la dernière clôture valide, comme après une fermeture. « Récupération » = flux rétabli puis historique manquant rechargé s'il existe ; « recalcul » = états recalculés sur les seules bougies valides. Le range en attente est effacé au début du trou et recalculé après récupération si ses 20 bougies sont valides ; sinon il reste invalide pour la journée. Les entrées reprennent à la première clôture M15 valide après récupération | Réinitialisation complète (nouveau préchargement de 1 000 M15 et 300 H1 valides) après tout trou non récupéré | `donnees-temps` 2b, `moteur-london` 2 |
| P-04 | C06, C03.1 | Âge de la cotation mesuré sur l'heure du fournisseur ou sur l'heure de réception ? | Les deux âges (instant de décision moins heure fournisseur convertie en UTC, et moins heure de réception) restent au plus `quote_max_age_seconds` ; en rejeu, réception = heure fournisseur | Heure fournisseur seule | `execution-coordinateur` 0c |
| P-05 | C06 | Une cotation à spread nul (Bid = Ask) est-elle « non croisée » ? | Lecture littérale : admise si Bid > 0, Ask > 0 et Ask ≥ Bid ; refus si Bid > Ask ou si un côté manque | Exiger Ask > Bid | `execution-coordinateur` 0c |
| P-06 | C07, C02 | Plafond de marge « Eqt/3 » (texte) contre `max_margin_fraction_of_equity` (JSON normatif) | Comparer en décimal `marge totale ≤ Eqt × fraction`, fraction lue dans la configuration ; un test vérifie que cette valeur est la représentation binaire de 1/3 | Comparer `3 × marge totale ≤ Eqt` | `execution-coordinateur` 3 |
| P-07 | C09, C04, A07, C05 | Situations sans code nommé (range invalide, A_H1 indisponible, cotation invalide, contrainte native de SL/TP, positions externes, clôture en attente, calendrier périmé, `NO_NEW`, `FLATTEN`, A_t non positif) | Champ `motif` limité aux codes de C09, à `ENVIRONMENT_NOT_READY` (C04) et à `AI_CONTEXT_VETO` (A07) ; champ `detail` énuméré et versionné ; table de correspondance du [document 01](01_architecture.md), §9.3 | Ajouter des codes primaires | `noyau` 1c, `noyau` 2 |
| P-08 | C06, C09 | Motif final d'un signal non exécuté avant le TTL alors que spread ou écart d'entrée bloquaient | Chaque tentative journalisée avec sa cause (`SPREAD_CAP`, `ENTRY_GAP`, cotation invalide) ; motif final `SIGNAL_EXPIRED`, `detail` = dernière cause bloquante | Motif final = dernière cause | `execution-coordinateur` 6 |
| P-09 | S02.1 | Une correction de la H1 après le gel remplace-t-elle A_H1 ? Quelle H1 retenir si la plus récente est invalide ? | Aucune mise à jour après la première version valide figée ; correction journalisée comme anomalie. « Dernière H1 clôturée » = dernière H1 **valide** clôturée au plus tard à 07:00 et datant d'au plus une heure (lecture de `london_setups`) | La correction reçue avant la première décision remplace la valeur | `moteur-london` 1b |
| P-10 | C03.7 | Le préchargement de 1 000 M15 inclut-il la bougie de signal ? | Aligné sur la référence (`t ≥ 999`) : décision sur la bougie t seulement si au moins 1 000 M15 valides clôturées, t comprise, depuis le début du préchargement ; 300 H1 valides jusqu'à la H1 figée comprise | 1 000 M15 strictement antérieures à t | `donnees-temps` 2b |
| P-11 | C10 | « Un tick adverse » : incrément de prix ou tick suivant du flux ? | Un incrément de `tick_size` dans le sens défavorable, appliqué au prix du premier tick disponible après le délai ; stress : deux incréments | Prix du tick suivant du flux | `journal-rejeu` 1b |
| P-12 | C07 | Base quotidienne de 00:00 UTC quand le robot ne tourne pas à cette heure | Base reconstituée depuis l'historique des transactions du courtier (solde à 00:00 UTC ; aucune position possédée n'est ouverte à cette heure, le blackout 21:00–23:00 UTC imposant les clôtures et les fenêtres d'entrée étant diurnes) ; reconstitution journalisée ; pic hors fonctionnement borné par le solde | Base = premiers fonds propres observés du jour UTC | `execution-coordinateur` 1b |

## 5. Actions humaines restantes (ce ne sont plus des décisions)

| Moment | Action | Effet si elle manque |
|---|---|---|
| Fin de chaque phase | Demander explicitement la phase suivante | Aucune phase suivante |
| Phase 11 | Donner à l'agent l'accès au poste Windows (dossier partagé) ou exécuter les commandes qu'il fournit ; ouvrir un **compte de démonstration Deriv MT5** standard en USD ; compiler et lancer le service MQL5 d'export ; configurer le module fondamental pour écrire dans le dossier d'échange ; tenir à jour le fichier des fermetures exceptionnelles | Infrastructure non qualifiable : la phase s'arrête sur question |
| Phase 12 | Autoriser les appels d'API réels (D-17) ; placer les clés des routes gratuites dans `.env` | Service construit et testé hors ligne seulement ; bras IA `NEUTRAL` |
| Sous-étape 13.3 | Fournir les ticks historiques (D-14), les caractéristiques et coûts datés, le calendrier historique et, s'il existe, l'historique des permissions | Rejeux C10 impossibles, ou limités au contrôle technique neutre |
| Sous-étape 13.4 | Copier la spécification V1 London depuis l'archive locale (D-15) | Rétention déclarée non applicable |
| Sous-étape 13.6 | Annoter les 200 textes de la qualification sémantique A13 | Fournisseur `NON_QUALIFIE` ; aucun veto réel possible |
| Sous-étape 13.7 | Décider du passage en démonstration, puis éventuellement en réel | Aucun passage en réel |

## 6. Hors périmètre et interdits

- Aucune modification de paramètre figé, de section normative, de schéma, de prompt, d'empreinte ou de preuve
  de `docs/validation/` ; toute évolution de règle crée une autre version (C01).
- Aucune recherche de variante plus rentable : c'est un travail exploratoire distinct ; les six perturbations
  de C10 sont des contrôles de fragilité, jamais des candidats.
- Le robot EMA (S01) n'est pas construit ; seules les interfaces partagées sont prêtes à le recevoir. Le moteur
  V1 London n'est porté que pour la comparaison de C10 et n'est jamais déployable.
- Le module fondamental externe n'est pas construit : le robot consomme ses permissions (C05).
- Aucune inférence locale, aucun appel LLM ou réseau entre signal et ordre (A03), aucun veto réel avant A13.
- Aucun agent n'ouvre de compte, ne connecte d'identifiants ni ne passe d'ordre réel ; les essais d'adaptateur
  se font sur compte de démonstration, par l'humain ou sous son contrôle.
- Aucun prix brut, secret, mot de passe ou numéro de compte n'est commité.

## 7. Journal des révisions du plan

| Version | Date | Changement |
|---|---|---|
| 1.0.0 | 05/11/2026 | Création : décisions D-01 et D-02 arrêtées par l'utilisateur, plan complet en six documents |
| 1.1.0 | 05/11/2026 | Validation par l'utilisateur : douze arbitrages tranchés (recommandations retenues), D-03 à D-09 approuvées, `MetaTrader5` autorisée, intégration continue distante et appels d'API non autorisés, D-11 à D-15 arrêtées ; contrats du dossier d'échange et de l'export MQL5 ; stratégies injectées (D-18) ; moteur V1 de comparaison ; sous-étapes 13.1 à 13.7 |
| 1.2.0 | 05/11/2026 | Vérification exhaustive (document 06) et script `tools/verifier_plan_london.py` ; six manques corrigés : recontrôle du contexte IA juste avant l'ordre (A03), mesures séparées de C09, indicateurs descriptifs de la lecture d'expert, éléments de rapport C10, contrôle du dossier commun (A02), suspension pour dérive (A13.10) |

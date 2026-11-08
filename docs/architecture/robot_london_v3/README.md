# Plan d'implémentation intégrale du robot 2 — London Breakout M15 (`LONDON_V3`)

> Plan directeur, version **1.4.7** du **8 novembre 2026**. Statut : **validé par l'utilisateur le
> 05/11/2026** ; couverture vérifiée mécaniquement par `python tools/verifier_plan_london.py`
> ([document 06](06_verification_exhaustive.md)). Toutes les décisions de conception et les douze arbitrages de
> spécification sont arrêtés. Les phases 0 à 12 s'exécutent entièrement dans le conteneur de développement, sans
> autre action humaine que la demande de passage à la phase suivante ; les autres **actions humaines** (§5) sont
> regroupées dans la phase 13. Phases 0, 1 et 2 terminées le 05/11/2026, phases 3 et 4 le 06/11/2026, phase 5 le 07/11/2026 (structure MCL
> composite dans [`mcl/robot-london-v3/`](../../../mcl/robot-london-v3/PLAN-MCL.md), squelette déployable,
> [registre des coutures](../../../mcl/squelette/COUTURES.md), noyau figé dans [`mcl/noyau/`](../../../mcl/noyau/PLAN-MCL.md),
> bougies M15 et H1 causales et enrichies figées dans [`mcl/london-donnees-temps/`](../../../mcl/london-donnees-temps/PLAN-MCL.md),
> méthode S02 pure figée dans [`mcl/moteur-london/`](../../../mcl/moteur-london/PLAN-MCL.md) et couture S3 réalisée) ;
> les quinze couches du coordinateur commun sont figées dans [`mcl/london-execution-coordinateur/`](../../../mcl/london-execution-coordinateur/PLAN-MCL.md). La phase 6 a construit le cycle d’ordre, les sorties et la reprise, puis remplacé S4 ; le rejeu papier exécute les vrais ordres London. Ce plan organise la construction ;
> il n'ajoute, ne retire et ne modifie aucune règle métier, aucun seuil et aucun coût.

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
| [06 — Vérification exhaustive](06_verification_exhaustive.md) | Rattachement de chaque paramètre (163 clés), de chaque exigence (155 lignes, 46 sections) et de chaque consigne d'expert (71) à un emplacement du plan ; contrôle de codifiabilité ; application étape par étape de la skill de planification ; manques trouvés et corrigés |
| [07 — Procédures humaines](07_procedures_humaines.md) | Procédure détaillée, critère de vérification et comportement prévu en cas d'absence pour chacune des douze actions réservées à l'humain (H-01 à H-12) |
| [08 — Contrats des frontières externes](08_contrats_frontieres.md) | Contrats finalisés tôt de chaque frontière, contre lesquels l'infrastructure est construite dans le conteneur : API `MetaTrader5` 5.0.6231 (fonctions, interdits, constantes, champs, requêtes, codes de retour, erreurs), dossier d'échange, exports MQL5, table horaire, fichiers de ticks, journaux, état SQLite, rapports ; vérification réelle prévue pour chacun |

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
4. Une sous-étape de la phase 13 qui attend une action humaine (§5) s'arrête sur une question explicite, avec
   le marqueur de blocage du cycle de gouvernance. Aucune phase de 0 à 12 n'en attend.
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
  C10/A13, les rapports A11, le convertisseur des exports de ticks historiques et le moteur V1 London porté pour
  la seule comparaison de rétention.
- Le service IA partagé (A04–A11), processus séparé, facultatif pour le cœur et nécessaire au bras IA de
  `PAPER_AB`.
- Les composants partagés (noyau, données, coordinateur, contrôles, orchestration) sont conçus pour recevoir
  plus tard le robot EMA **sans le construire maintenant** : deux artefacts distincts, seul le coordinateur
  de compte est partagé.

### 2.2 Schéma d'ensemble

```text
ticks Bid/Ask ──► london-donnees-temps (C03) ──► moteur-london (S02) ──► signal technique
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
| 3 | Données et temps (C03) | `london-donnees-temps` | — | Oui |
| 4 | Moteur London (S02) | `moteur-london` | — | Oui |
| 5 | Exécution et coordinateur : calculs purs (C06, C07) | `execution-coordinateur`, couches 0 à 3 | — | Oui |
| 6 | Exécution et coordinateur : cycle d'ordre, sorties, reprise (C08) | `execution-coordinateur`, couches 4 à 6 | — | Oui |
| 7 | Contrôles fondamentaux et annonces (C05) | `controles-fondamentaux` | — | Oui |
| 8 | Lecteur du contexte IA (A07, A10, A12) | `contexte-ia` | — | Oui |
| 9 | Orchestration : moteur de décision événementiel, bras A/B | `orchestration` | — | Oui |
| 10 | Simulateur C10, rejeu, métriques, bootstrap, rapports | `journal-rejeu` | — | Oui |
| 11 | Infrastructure réelle (MT5, dossier d'échange, exports MQL5, SQLite, journaux), construite contre les contrats du document 08 avec un faux module `MetaTrader5` ; source du service MQL5 ; points d'entrée ; répétition générale `PAPER` | `infrastructure`, `points-entree`, service MQL5 (source) | — | Oui |
| 12 | Service IA partagé (A04–A11), construit et testé hors ligne | `service-ia` | — | Oui |
| 13 | Qualification et validation (sous-étapes 13.1 à 13.7) : poste et compte démo, sondes et tests de contrat, données, V1, rejeux C10, IA réelle, collecte prospective | `donnees-historiques` en 13.3, `moteur-london-v1` en 13.4 | H-02 à H-12 | Oui, à chaque sous-étape |

Les phases 0 à 12 se déroulent entièrement dans le conteneur de développement et ne requièrent aucune action
humaine autre que la demande de passage à la phase suivante (H-01). Les gestes réservés à l'humain (poste,
compte, terminal, données, autorisation des API, annotation, mise en service) sont tous en phase 13.

### 2.4 Complétude du plan

Le plan est complet au sens suivant, et chaque point est vérifiable :

1. **Aucune décision ouverte** : les décisions D-01 à D-18 ont toutes le statut « Arrêtée », « Autorisée » ou
   « Note » (§3). Les refus D-10 et D-17 sont des décisions de l'utilisateur dont les conséquences sont
   entièrement planifiées.
2. **Aucune ambiguïté de spécification non tranchée** : P-01 à P-12 sont arbitrés (§4).
3. **Couverture totale des sources** : chaque paramètre figé, chaque section de la spécification, chaque motif de
   C09, chaque cas d'acceptation et chaque consigne de la skill d'expert est rattaché à un emplacement du plan ;
   `python tools/verifier_plan_london.py` le contrôle et échoue au moindre manque
   ([document 06](06_verification_exhaustive.md)).
4. **Chaque phase est exécutable** : objectif, prérequis, ordre des couches, tests clés, coutures, livrables,
   critères de sortie et point d'arrêt ([document 04](04_phases.md)).
5. **Les phases 0 à 12 sont exécutables par l'agent seul**, dans le conteneur : chacune de leurs entrées est
   dans le dépôt ou dans ce plan. Les frontières externes sont construites contre des contrats finalisés tôt
   ([document 08](08_contrats_frontieres.md)), établis par l'examen du paquet officiel `MetaTrader5` ; chacun est
   confronté au réel en phase 13, un écart ouvrant un défigeage « correction » tracé de la seule couche concernée.
6. **Chaque action humaine est spécifiée** : procédure, vérification et comportement prévu en son absence
   ([document 07](07_procedures_humaines.md)). Ce sont des gestes que les règles du projet réservent à l'humain
   (compte, identifiants, poste, données privées, annotation, mise en service), pas des inconnues de conception.
7. **Ce que le plan ne peut pas contenir d'avance**, par nature : résultats des sondes S-01 à S-10, contenu des
   données privées, règles V1 conservées dans l'archive locale. Chacun est produit à une sous-étape précise de la
   phase 13, avec un comportement prévu s'il manque. Le convertisseur des exports de ticks ne s'écrit qu'au vu
   d'un export réel (13.3) et le moteur V1 qu'au vu de ses règles (13.4) ; aucun des deux ne conditionne une
   phase de 0 à 12.
8. **Contrôle mécanique de ces propriétés** : le script vérifie aussi qu'aucune phase de 0 à 12 n'exige d'action
   humaine, que les actions H-02 à H-12 se situent toutes en phase 13 et que chaque frontière du document 02
   a son contrat au document 08.

## 3. Décisions (section 2 du plan MCL)

| Id | Décision | Statut | Justification | Utile à partir de |
|---|---|---|---|---|
| D-01 | Plateforme et langage : **Python 3.13 + MT5** piloté par le paquet officiel `MetaTrader5` (version 5.0.6231 du 27/09/2026 relevée sur PyPI : roues Windows x64 de Python 3.6 à 3.14) | Arrêtée par l'utilisateur le 05/11/2026 | Un seul moteur pour rejeu et plateforme (C11.14) ; service IA déjà en Python (A01) ; oracles de `reference/` en Python | — |
| D-02 | Sources dans **`src/xpbots/`** (paquet unique), tests dans `tests/robot/`, dossiers MCL dans `mcl/<artefact>/` | Arrêtée par l'utilisateur le 05/11/2026 | Noyau partagé entre les deux robots ; analyse des imports Python par `mcl.py` | — |
| D-03 | Architecture « noyau déterministe piloté par événements + coquille impérative » ([document 01](01_architecture.md), §1) | Arrêtée (approuvée le 05/11/2026) | A03, C06, C08, C11.14 | Phase 1 |
| D-04 | Tests : bibliothèque standard `unittest` et lanceur `tools/run_london_tests.py` ; aucun `pytest` | Arrêtée (approuvée le 05/11/2026) | Aucune dépendance nouvelle (règles du projet, §4) | Phase 1 |
| D-05 | Dépendances : cœur en bibliothèque standard ; à l'exécution Windows, `requirements-windows.txt` épingle `MetaTrader5` 5.0.6231, `numpy` qu'il exige et `tzdata` (ces deux dernières aux versions déjà épinglées dans `requirements-dev.txt`) ; rien d'autre | **Autorisée** par l'utilisateur le 05/11/2026 pour `MetaTrader5` | Règles du projet, §4 ; [document 08](08_contrats_frontieres.md), §2.1 | Phase 11 (fichier), 13.1 (installation) |
| D-06 | État persistant en SQLite (bibliothèque standard), dans `runtime/` ignoré par Git, transactions exclusives | Arrêtée (approuvée le 05/11/2026) | C07, C08 (réservation et intention persistées avant envoi) | Phase 11 |
| D-07 | Journal C09 en JSON Lines canonique quotidien et journal d'entrées rejouable, dans `logs/` ignoré par Git | Arrêtée (approuvée le 05/11/2026) | C09, C11.14 | Phase 2 (format), 11 (écriture) |
| D-08 | Identification des ordres : numéro magique par couple (déploiement, stratégie) ; commentaire = préfixe et empreinte courte de la clé d'intention (longueur maximale qualifiée par la sonde S-05) | Arrêtée (approuvée le 05/11/2026) | C08 (clé persistante, propriété, positions externes) | Phase 6 |
| D-09 | Période de la boucle en direct : constante d'ingénierie de 100 ms, consignée au registre de déploiement, jamais réglée sur un résultat | Arrêtée (approuvée le 05/11/2026) | TTL de 5 s, cotation âgée d'au plus 2 s, délais de correction de 0,25 s | Phase 11 |
| D-10 | Intégration continue distante (GitHub Actions) et porte `robot-suite` du cycle de vie : **refusées** | Arrêtée : refus de l'utilisateur le 05/11/2026, révisable à sa seule demande | Conséquences planifiées : la suite du robot s'exécute à chaque gate MCL, à chaque fin de phase et avant chaque commit ; les écarts propres à Windows se révèlent en sous-étape 13.1, sur le poste (risque R-12) | Phase 1 |
| D-11 | Transport des permissions du module fondamental externe : **dossier d'échange JSON** à écriture atomique, un fichier par symbole, lu chaque seconde ([document 01](01_architecture.md), §2.1) | Arrêtée par l'utilisateur le 05/11/2026 | Même mécanisme éprouvé que le snapshot IA (A10) ; aucun réseau | Phase 7 (format), 11 (lecture) |
| D-12 | Calendrier HIGH et horaires de séance : **service MQL5 d'export** vers le dossier commun du terminal, seul composant MQL5 du projet ([document 01](01_architecture.md), §2.2) ; fermetures exceptionnelles tenues dans un fichier versionné | Arrêtée par l'utilisateur le 05/11/2026 | Le paquet Python `MetaTrader5` n'expose ni le calendrier ni les séances ; A04 autorise le calendrier natif MT5 | Phase 7 (format), 11 (source du service), 13.1 (compilation) |
| D-13 | Courtier du compte de démonstration : **Deriv MT5** | Arrêtée par l'utilisateur le 05/11/2026 | Symboles micro listés dans le [snapshot public](../../validation/snapshot_public_Deriv_2026-11-04.json) ; disponibilité sur le compte standard à vérifier en 13.1 | Sous-étape 13.1 |
| D-14 | Ticks historiques C10 : ticks exacts du symbole lié chez le courtier s'ils couvrent la période ; à défaut, source tierce (par exemple Dukascopy) **déclarée contrefactuelle** | Arrêtée par l'utilisateur le 05/11/2026 | C10 ; [données requises](../../data/03_Donnees_Historiques_Requises_et_Validation.md) | Sous-étape 13.3 |
| D-15 | Règles V1 London : **fournies par l'utilisateur** depuis l'archive locale (voir le [registre de nettoyage](../../maintenance/NETTOYAGE_ET_MERGE.md)) avant la sous-étape 13.4 ; portées dans l'artefact distinct `moteur-london-v1`, réservé au rejeu, sans modifier V3 | Arrêtée par l'utilisateur le 05/11/2026 | C10 (comparaison sur le même moteur) | Sous-étape 13.4 |
| D-16 | Calendrier du protocole C10 : la démonstration prospective prévue « à partir du 05/11/2026 » ne peut commencer qu'après le gel du robot ; le bilan du 04/02/2027 se tiendra avec les effectifs disponibles et le protocole se prolongera jusqu'aux effectifs requis ; aucune date normative n'est modifiée | Note | C10 | Phase 13 |
| D-17 | Appels réels aux API LLM (conformité et fonctionnement du service) : **refusés** à ce jour | Arrêtée : refus de l'utilisateur le 05/11/2026 ; l'agent redemande l'autorisation au début de la sous-étape 13.6 (H-08) | Conséquences planifiées dans les deux cas : le service est construit et testé hors ligne en phase 12 ; sans autorisation, il reste arrêté et le bras IA est `NEUTRAL` ; avec autorisation, procédure H-08 puis fonctionnement réel en 13.6 | Phase 12 (hors ligne), 13.6 (réel) |
| D-18 | Stratégies injectées dans l'orchestration par la configuration de déploiement (contrat structurel), sans import direct du moteur London | Arrêtée : détail de conception découlant de D-03, introduit le 05/11/2026 pour D-15 | Moteur V1 et futur robot EMA branchés sans défigeage ; simulation de la carte composite inchangée en profondeurs | Phase 9 |

## 4. Arbitrages de spécification (défauts signalés, C02)

Chaque point ci-dessous est une ambiguïté réelle relevée en recoupant le texte, le JSON normatif et
`reference/technical.py`. **Le 05/11/2026, l'utilisateur a retenu la proposition recommandée de chacun des douze
points.** Ces lectures sont littérales ou prudentes ; aucune ne change une règle, un seuil ou un coût. Elles
entrent dans les contrats des couches indiquées.

| Id | Sections | Question | Décision retenue | Alternative écartée | Couche |
|---|---|---|---|---|---|
| P-01 | C03.5, C03.7, S02.1 | Comment établir la « couverture du flux » d'un intervalle antérieur au démarrage (préchargement, reprise, rejeu) ? | En direct : journal de connexion du robot sur toute la partie ouverte de l'intervalle. En historique : absence de trou dans le registre des trous de la source (données §2, « trous connus ») et séance native ouverte ; une source sans registre ne permet pas d'établir la couverture | Toute bougie historique contenant au moins un Bid est réputée couverte | `london-donnees-temps` 1c |
| P-02 | C03.5 | Un intervalle couvert, marché ouvert, sans aucun événement : bougie invalide ? trou bloquant ? | Bougie invalide (aucun Bid, aucun remplissage synthétique), détail `AUCUN_BID`, sans état `DATA_GAP` ; elle invalide un range qui la contient | Traiter l'intervalle comme un trou bloquant | `london-donnees-temps` 2a |
| P-03 | C03.6, C03.10, S02.1 | Récurrences et reprise après une bougie invalide ou un trou | Une bougie invalide n'entre dans aucune récurrence ; la suivante calcule TR avec la dernière clôture valide, comme après une fermeture. « Récupération » = flux rétabli puis historique manquant rechargé s'il existe ; « recalcul » = états recalculés sur les seules bougies valides. Le range en attente est effacé au début du trou et recalculé après récupération si ses 20 bougies sont valides ; sinon il reste invalide pour la journée. Les entrées reprennent à la première clôture M15 valide après récupération | Réinitialisation complète (nouveau préchargement de 1 000 M15 et 300 H1 valides) après tout trou non récupéré | `london-donnees-temps` 2b, `moteur-london` 2 |
| P-04 | C06, C03.1 | Âge de la cotation mesuré sur l'heure du fournisseur ou sur l'heure de réception ? | Les deux âges (instant de décision moins heure fournisseur convertie en UTC, et moins heure de réception) restent au plus `quote_max_age_seconds` ; en rejeu, réception = heure fournisseur | Heure fournisseur seule | `execution-coordinateur` 0c |
| P-05 | C06 | Une cotation à spread nul (Bid = Ask) est-elle « non croisée » ? | Lecture littérale : admise si Bid > 0, Ask > 0 et Ask ≥ Bid ; refus si Bid > Ask ou si un côté manque | Exiger Ask > Bid | `execution-coordinateur` 0c |
| P-06 | C07, C02 | Plafond de marge « Eqt/3 » (texte) contre `max_margin_fraction_of_equity` (JSON normatif) | Comparer en décimal `marge totale ≤ Eqt × fraction`, fraction lue dans la configuration ; un test vérifie que cette valeur est la représentation binaire de 1/3 | Comparer `3 × marge totale ≤ Eqt` | `execution-coordinateur` 3 |
| P-07 | C09, C04, A07, C05 | Situations sans code nommé (range invalide, A_H1 indisponible, cotation invalide, contrainte native de SL/TP, positions externes, clôture en attente, calendrier périmé, `NO_NEW`, `FLATTEN`, A_t non positif) | Champ `motif` limité aux codes de C09, à `ENVIRONMENT_NOT_READY` (C04) et à `AI_CONTEXT_VETO` (A07) ; champ `detail` énuméré et versionné ; table de correspondance du [document 01](01_architecture.md), §9.3 | Ajouter des codes primaires | `noyau` 1c, `noyau` 2 |
| P-08 | C06, C09 | Motif final d'un signal non exécuté avant le TTL alors que spread ou écart d'entrée bloquaient | Chaque tentative journalisée avec sa cause (`SPREAD_CAP`, `ENTRY_GAP`, cotation invalide) ; motif final `SIGNAL_EXPIRED`, `detail` = dernière cause bloquante | Motif final = dernière cause | `execution-coordinateur` 6 |
| P-09 | S02.1 | Une correction de la H1 après le gel remplace-t-elle A_H1 ? Quelle H1 retenir si la plus récente est invalide ? | Aucune mise à jour après la première version valide figée ; correction journalisée comme anomalie. « Dernière H1 clôturée » = dernière H1 **valide** clôturée au plus tard à 07:00 et datant d'au plus une heure (lecture de `london_setups`) | La correction reçue avant la première décision remplace la valeur | `moteur-london` 1b |
| P-10 | C03.7 | Le préchargement de 1 000 M15 inclut-il la bougie de signal ? | Aligné sur la référence (`t ≥ 999`) : décision sur la bougie t seulement si au moins 1 000 M15 valides clôturées, t comprise, depuis le début du préchargement ; 300 H1 valides jusqu'à la H1 figée comprise | 1 000 M15 strictement antérieures à t | `london-donnees-temps` 2b |
| P-11 | C10 | « Un tick adverse » : incrément de prix ou tick suivant du flux ? | Un incrément de `tick_size` dans le sens défavorable, appliqué au prix du premier tick disponible après le délai ; stress : deux incréments | Prix du tick suivant du flux | `journal-rejeu` 1b |
| P-12 | C07 | Base quotidienne de 00:00 UTC quand le robot ne tourne pas à cette heure | Base reconstituée depuis l'historique des transactions du courtier (solde à 00:00 UTC ; aucune position possédée n'est ouverte à cette heure, le blackout 21:00–23:00 UTC imposant les clôtures et les fenêtres d'entrée étant diurnes) ; reconstitution journalisée ; pic hors fonctionnement borné par le solde | Base = premiers fonds propres observés du jour UTC | `execution-coordinateur` 1b |

## 5. Actions humaines restantes (ce ne sont plus des décisions)

Procédure complète de chacune : [document 07](07_procedures_humaines.md).

| Id | Moment | Action | Effet si elle manque |
|---|---|---|---|
| H-01 | Fin de chaque phase et de chaque sous-étape | Demander explicitement la phase suivante | Aucune phase suivante |
| H-02 | Début de la sous-étape 13.1 | Préparer le poste Windows (Python 3.13 x64, environnement, accès de l'agent) | La sous-étape 13.1 s'arrête sur question ; le code des phases 0 à 12 reste complet et vérifié dans le conteneur |
| H-03 | Début de la sous-étape 13.1 | Ouvrir le compte de démonstration Deriv MT5 standard en USD et autoriser le trading algorithmique | Aucune sonde ni test de contrat MT5 ; aucune qualification C04 |
| H-04 | Sous-étape 13.1 | Compiler et lancer le service MQL5 `XPBotsExport` | Aucune nouvelle entrée (calendrier périmé) ; `ENVIRONMENT_NOT_READY` (séances) |
| H-05 | Sous-étape 13.1, puis à chaque avis du courtier | Tenir le fichier des fermetures exceptionnelles | `ENVIRONMENT_NOT_READY` |
| H-06 | Sous-étape 13.1 | Brancher le module fondamental externe sur le dossier d'échange | Toutes les nouvelles entrées refusées (`FUNDAMENTAL_INVALID`) |
| H-07 | Sous-étape 13.1 | Exécuter les sondes S-01 à S-08 et les tests de contrat sur le poste | Infrastructure non qualifiée : aucune séance sur le terminal ni démonstration |
| H-08 | Début de la sous-étape 13.6 | Autoriser ou non les appels d'API ; fournir les clés gratuites dans `.env` | Service arrêté ; bras IA `NEUTRAL` ; fournisseurs `NON_QUALIFIE` |
| H-09 | Sous-étape 13.3 | Fournir les données historiques de C10 et un extrait de chaque export pour les sondes S-09 et S-10 | Aucun rejeu C10 |
| H-10 | Avant la sous-étape 13.4 | Fournir la spécification V1 London | Rétention déclarée non applicable |
| H-11 | Sous-étape 13.6 | Annoter les 200 textes de la qualification A13 | Fournisseurs `NON_QUALIFIE` ; aucun veto réel |
| H-12 | Sous-étape 13.7 | Décider des mises en service | Aucun passage en démonstration prospective ni en réel |

## 6. Hors périmètre et interdits

- Aucune modification de paramètre figé, de section normative, de schéma, de prompt, d'empreinte ou de preuve
  de `docs/validation/` ; toute évolution de règle crée une autre version (C01).
- Aucune recherche de variante plus rentable : c'est un travail exploratoire distinct ; les six perturbations
  de C10 sont des contrôles de fragilité, jamais des candidats.
- Le moteur EMA (S01) existe dans sa propre lignée. Le coordinateur de compte sera unique ; ses calculs purs sont partagés depuis la phase 5. Le moteur
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
| 1.3.0 | 05/11/2026 | Procédures des douze actions humaines (document 07) ; statuts de D-10 et D-17 explicités comme refus arrêtés ; définition de la complétude du plan (§2.4) ; convertisseurs des exports de ticks (MT5 et source tierce) et sondes S-09, S-10 ; application étape par étape de la skill de planification (document 06, §8) ; contrôles mécaniques étendus aux décisions, aux actions humaines et à cette application |
| 1.4.0 | 05/11/2026 | Phases 0 à 12 exécutables sans action humaine : contrats des frontières externes finalisés tôt (document 08), d'après l'examen du paquet officiel `MetaTrader5` 5.0.6231 ; infrastructure construite contre ces contrats avec un faux module injecté et répétition générale `PAPER` dans le conteneur ; sondes S-01 à S-08, compilation MQL5, tests de contrat et première séance sur le terminal regroupés en 13.1 ; convertisseurs des exports de ticks déplacés dans l'artefact `donnees-historiques` (13.3) ; autorisation des API redemandée en 13.6 ; `requirements-windows.txt` avec `numpy` ; risque R-18 ; contrôles mécaniques étendus (phases autonomes, moments des actions humaines, frontières contractualisées) |
| 1.4.1 | 05/11/2026 | Phase 0 exécutée : dossier MCL composite `mcl/robot-london-v3/` (carte au grain des paquets, divergence en mode strict, frontières externes et couches autorisées) ; guide, règles du projet, README et skill de planification alignés sur D-01 et D-02 ; phrases périmées corrigées (document 02 : sondes et intégration continue ; document 03 : vérification d'architecture ; document 04 : commande de la carte composite et suivi des phases) |
| 1.4.2 | 05/11/2026 | Phase 1 exécutée : squelette composite déployable (segments S1 à S7, lanceur `tools/run_london_tests.py`, fabrique de ticks, test de bout en bout, gardes de pureté et de carte composite, registre des coutures) ; document 01, §5 (dossier `tests/robot/transverses/`) et document 03, §2 et §8 (options du lanceur, garde de pureté étendue au chargement dynamique de modules) |
| 1.4.3 | 05/11/2026 | Phase 2 exécutée : artefact `noyau` (sept couches figées) et couture du squelette ; document 01, §9.3 : causes finales de `SIGNAL_EXPIRED` énumérées (`COTATION_INVALIDE`, `AUCUNE_COTATION`, P-08) et détails réservés aux segments S3 et S4 du squelette, l'énumération versionnée du noyau étant comparée à ce tableau dans les deux sens |
| 1.4.4 | 06/11/2026 | Phase 3 exécutée : artefact `london-donnees-temps` (huit couches figées, défigeage `extension` de 1a pour la reprise exacte, défigeage `correction` de 2b pour l'empreinte chaînée) et couture S2 ; contrat de stratégie du squelette `sur_bougie(BougieEnrichie)` ; document 02, §6.2 : dépendances directes réelles des unités 2a, 2b et 3 déclarées, export d'état de `constructeur_bougies` et sortie de `etat_indicateurs` précisés |
| 1.4.5 | 06/11/2026 | Phase 4 exécutée : artefact `moteur-london`, huit couches figées, checkpoint après le niveau 1 ; méthode S02 pure comparée aux oracles et vérifiée par mutations ; couture S3 avec vraies cassures sur ticks après préchargement, refusées sans ordre par S4 ; protocole de stratégie étendu par `sur_issue`, taille de tick explicitement fournie par symbole à S7 ; document 02, §6.3, aligné sur les dépendances directes et les sorties réelles ; passation préparée pour la phase 5 |
| 1.4.6 | 07/11/2026 | Phase 5 exécutée : onze couches 0a à 3 du coordinateur commun figées dans `london-execution-coordinateur`, checkpoints après les niveaux 1 et 3 ; arbitrage R4/R5 et adaptateurs typés EMA, risque all-in, gardes et dimensionnement ; aucune couture S4 ; bilan, dépendances réelles, guide et passation alignés sur la phase 6 |
| 1.4.7 | 08/11/2026 | Phase 6 exécutée : couches 4, 5a, 5b et 6 du coordinateur commun figées, checkpoint 6 ; cycle C08, sorties, reprise sur preuves natives et couture S4 avec vrais ordres papier ; profils synthétiques et scénario neutre explicites ; bilan, tests, mutations et passation alignés sur la phase 7 |

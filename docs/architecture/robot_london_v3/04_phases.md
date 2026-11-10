# 04 — Phases d'exécution du plan

Retour au [plan directeur](README.md). Une phase se termine **intégralement**, puis l'agent s'arrête et attend une
demande explicite pour la suivante (plan directeur, §1). Les identifiants de couches renvoient au
[document 02](02_cartographie_mcl.md) ; les cas et scénarios au [document 03](03_acceptation_et_tests.md). Toutes
les décisions et tous les arbitrages sont arrêtés depuis le 05/11/2026 (plan directeur, §3 et §4). Les phases 0 à
12 s'exécutent entièrement dans le conteneur de développement, sans autre action humaine que la demande de
passage à la phase suivante (H-01) : les frontières externes y sont construites contre les contrats finalisés tôt
du [document 08](08_contrats_frontieres.md). Toutes les autres actions humaines du plan directeur, §5, sont
regroupées dans la phase 13.

## Gabarit commun à toutes les phases

**À l'entrée d'une phase**

1. Appliquer l'orchestrateur de skills du dépôt (cycle obligatoire d'`AGENTS.md`) ; charger les skills
   métier de la phase (indiquées dans chaque fiche).
2. Vérifier que les artefacts amont sont figés : `mcl.py --dossier mcl/<amont> statut`. En phase 13 seulement,
   vérifier aussi que les actions humaines de la sous-étape sont accomplies ; à défaut, s'arrêter sur une
   question.
3. Relever l'état initial : `git status --short`, `python tools/run_london_tests.py` (à partir de la phase 1),
   `python tools/verify_project.py` ; tout échec préexistant est documenté avant le moindre changement.

**Pendant la phase (artefact MCL)**

4. Initialiser `mcl/<artefact>/` ; reporter dans son `PLAN-MCL.md` les sections du document 02 qui le concernent
   (périmètre, applicabilité, étape 1, unités, carte, frontières) et les arbitrages qui s'y appliquent ;
   renseigner `unites` et `externes` de la carte ; `mcl.py analyser --ecrire`, puis compléter `chemins`,
   `imports` et `contrats` ; `mcl.py analyser` jusqu'à zéro divergence ; esquisser tous les contrats de couche.
5. Pour chaque couche, dans l'ordre que donne `mcl.py statut` (colonne « constructible maintenant ») :
   finaliser le contrat, implémenter, tests de catégorie 1, valider, intégrer, tests de catégorie 2,
   régression intégrale (gate), figer. Une seule évolution par gate ; les couches parallèles peuvent s'écrire
   dans la même passe, chacune avec son gate et son gel.
6. Brancher l'enveloppe sur le squelette en remplaçant le segment minimal ; consigner la couture dans
   `mcl/squelette/COUTURES.md` ; le test de bout en bout du squelette reste vert.

**À la sortie de la phase**

7. Gate global de l'artefact ; checkpoint si `statut` le signale ; `mcl.py verifier` de la carte composite
   (`mcl.py --dossier mcl/robot-london-v3 verifier`) ; ligne de la phase ajoutée au suivi des phases de
   `mcl/robot-london-v3/PLAN-MCL.md`, §7.
8. `python tools/run_london_tests.py`, `python tools/verify_project.py` et `python tools/verifier_plan_london.py`
   (couverture du plan, à garder verte quand le plan évolue) ; l'intégration continue distante n'est pas
   autorisée (D-10) ; suite de gouvernance si un fichier de gouvernance a changé.
9. Commit et push sur la branche de travail, sans réécriture d'historique.
10. **Rapport d'arrêt** : unités et couches figées, contrats, effectifs des tests par catégorie, résultat de la
    régression intégrale, coutures modifiées, défauts trouvés et leur traitement, limites, prérequis de la
    phase suivante. Puis arrêt.

---

## Phase 0 — Mise en place MCL composite

- **Objectif** : poser la structure MCL composite et aligner les documents du dépôt sur les décisions du
  05/11/2026.
- **Skills** : `xp-bots-mcl-robot-planning`, `mcl-matryoshka-construction-layers`,
  `xp-bots-specification-consistency`, `xp-bots-maintain-agent-skills` (étape 4).
- **Prérequis** : aucun (décisions et arbitrages arrêtés).
- **Étapes**
  1. Initialiser le dossier composite :
     `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/robot-london-v3 init --nom robot-london-v3 --langage python --echelle application --mode composite --sources src`.
  2. Renseigner son `PLAN-MCL.md` : sections 0 à 2 reprises de ce plan (périmètre, applicabilité, étape 1,
     décisions D-01 à D-18 en section 2), renvoi au document 02 pour la cartographie.
  3. Renseigner la **carte composite au grain des paquets** : une unité et une couche par artefact
     (`xpbots.noyau`, `xpbots.donnees`, `xpbots.london`, `xpbots.execution`, `xpbots.fondamental`,
     `xpbots.contexte_ia`, `xpbots.orchestration`, `xpbots.rejeu`, `xpbots.infra`, `xpbots.app`,
     `xpbots.service_ia` ; `xpbots.donnees_historiques` sera ajouté en 13.3 et `xpbots.london_v1` en 13.4),
     avec les dépendances du tableau du
     document 02, §5 ; `mcl.py analyser` jusqu'à zéro divergence. Les couches parallèles (`xpbots.london` et
     `xpbots.execution`, par exemple) rendent mécaniquement détectable toute dépendance mutuelle. Cette carte sert
     à `analyser` et `verifier`, jamais à `figer`.
  4. Mettre à jour, par la skill de gouvernance, les phrases du guide d'implémentation et des règles du projet
     qui disent que langage et plateforme ne sont pas arrêtés : décisions D-01 et D-02 du 05/11/2026 pour le
     robot 2 et les composants partagés, avec lien vers ce plan ; suite de gouvernance verte.
- **Livrables** : `mcl/robot-london-v3/` (carte composite, `PLAN-MCL.md`, journal) ; guide et règles mis à jour.
- **Critères de sortie** : analyse composite sans divergence ; `tools/verify_project.py` et suite de gouvernance
  verts.
- **Exclu** : tout code du robot.

## Phase 1 — Squelette composite déployable

- **Objectif** : un chemin de bout en bout minimal, en code de production destiné à durer, déployable dès le
  départ et vérifié à chaque gate.
- **Skills** : `xp-bots-mcl-robot-planning`, MCL.
- **Prérequis** : phase 0.
- **Étapes**
  1. Écrire `tools/run_london_tests.py` (document 03, §2), avec un test qui prouve qu'un test en échec rend un code
     de sortie non nul.
  2. Écrire la première fabrique de ticks synthétiques (`tests/robot/outils/`).
  3. Écrire les segments minimaux S1 à S7 (document 02, §3.1) dans leurs paquets définitifs, chacun documenté
     comme « segment minimal du squelette, remplacé en phase N ».
  4. Écrire le test de bout en bout : une journée Londres synthétique d'EURUSD rejouée par
     `python -m xpbots.app.rejeu_squelette` (avec `PYTHONPATH` sur `src`) dans un dossier temporaire ; un
     enregistrement par M15 close, motif conforme, code de sortie nul.
  5. Écrire le premier test de pureté du cœur (document 03, §8).
  6. Créer `mcl/squelette/COUTURES.md` : contrat minimal de chaque couture, propriétaire futur, statut.
  7. `mcl.py verifier` avec la carte composite.
- **Sans intégration continue distante (D-10)** : aucun workflow GitHub Actions ni porte `robot-suite` ; la
  suite du robot s'exécute à chaque gate MCL, à chaque fin de phase et avant chaque commit ; la limite est
  rappelée dans chaque rapport de phase.
- **Livrables** : lanceur, fabrique, segments minimaux, test de bout en bout, garde de pureté, registre des
  coutures.
- **Critères de sortie** : test de bout en bout vert ; vérification du projet verte ; commande de démonstration
  documentée dans le rapport.
- **Exclu** : toute logique S02, C05 à C08.

## Phase 2 — Artefact `noyau`

- **Objectif** : types et règles partagés, et lecture stricte des configurations figées (document 02, §6.1).
- **Skills** : `xp-bots-specification-consistency`, `xp-bots-risk-execution-contracts` (motifs), MCL.
- **Prérequis** : phase 1. Arbitrage intégré aux contrats : P-07 (couches 1c et 2).
- **Ordre des couches** : 0a ∥ 0b ∥ 0c, puis 1a ∥ 1b ∥ 1c, puis 2 ; checkpoint après le niveau 1.
- **Tests clés** : JSON strict (clé dupliquée, nombre non fini) ; empreinte des octets contre la preuve de
  conservation ; empreinte canonique égale au `design_sha256` du diagnostic ; clé inconnue ou manquante ; option
  désactivée activée ; instants refusés sans fuseau ou avec décalage ; arrondis sur grille comparés à la
  sémantique de `rounded_levels` ; profil incomplet → liste `ENVIRONMENT_NOT_READY` ; motifs fermés et détails
  de la table du document 01, §9.3 ; sérialisation canonique du journal.
- **Couture** : les types minimaux du squelette sont remplacés (extension tracée de S1 et S6).
- **Critères de sortie** : sept unités figées ; bout en bout vert ; gate global vert.

## Phase 3 — Artefact `london-donnees-temps`

- **Objectif** : bougies M15 et H1 causales, validées et enrichies (document 02, §6.2 ; C03).
- **Skills** : `xp-bots-market-data-causality`, `xp-bots-london-breakout`, MCL.
- **Prérequis** : phase 2. Arbitrages intégrés aux contrats : P-01 (1c), P-02 (2a), P-03 et P-10 (2b).
- **Ordre des couches** : 0a ∥ 0b, puis 1a ∥ 1b ∥ 1c, puis 2a ∥ 2b, puis 3 ; checkpoints après les niveaux 1 et 3.
- **Tests clés** : correspondances Londres et UTC sur les jours de référence (y compris ceux de
  `tests/check_technical.py`) ; 20 ouvertures de range en été et en hiver ; égalité avec
  `local_decision_in_window` sur une grille d'instants de 2019 à 2027 ; tick de frontière ; intervalles vides ;
  TR et ATR comparés à `wilder` et `add_indicators` ; A_t = ATR de t − 1 ; invariance par préfixe (C11.1) ; H1
  jamais partielle ; reprise après export et import d'état ; préchargement différent journalisé ; bougie sans
  tick (P-02) et trou suivi de récupération (P-03).
- **Couture** : remplacement de S2.
- **Critères de sortie** : huit unités figées ; bout en bout vert avec les vraies bougies.

## Phase 4 — Artefact `moteur-london`

- **Objectif** : la méthode S02 complète, pure et indépendante (document 02, §6.3).
- **Skills** : `xp-bots-london-breakout`, `anthropic-skills:expert-scalper-m15` (lecture critique des cas, sans
  changer une règle), MCL.
- **Prérequis** : phase 3. Arbitrage intégré au contrat : P-09 (1b).
- **Ordre des couches** : 0a ∥ 0b, puis 1a ∥ 1b ∥ 1c ∥ 1d ∥ 1e, puis 2 ; checkpoint après le niveau 1.
- **Tests clés** : S02.6 complet et scénarios L-01 à L-13 ; égalité de `bougie_cassure` et `stop_local` avec
  `london_signal` sur des cas synthétiques ; égalité des signaux de l'enveloppe avec `london_setups` quand aucun
  remplissage n'est rapporté (les quotas ne lient alors jamais) ; causalité par préfixe ; état du jour
  réinitialisé au changement de jour Londres ; non-recopie des seuils ; conformité structurelle au contrat de
  stratégie que l'orchestration déclarera (D-18).
- **Couture** : remplacement de S3 ; le squelette journalise désormais de vrais signaux London, refusés
  explicitement par le coordinateur minimal.
- **Critères de sortie** : huit unités figées ; bout en bout vert.

## Phase 5 — Artefact `execution-coordinateur`, couches 0 à 3

Réalisation au 07/11/2026 : onze couches figées dans `mcl/london-execution-coordinateur/`.
Ce dossier suit le coordinateur commun, selon l’arbitrage R4/R5 ; l’ancienne esquisse EMA
`mcl/execution-coordinateur/` ne doit pas produire une seconde implémentation. La phase 6 poursuit
la même carte avec 4, 5a, 5b et 6 ; aucune couture n’a lieu en phase 5.

- **Objectif** : calculs purs de C06 et C07 : cotation, niveaux exécutables, échéances, gardes, réservations,
  risque all-in, arbitrage, dimensionnement (document 02, §6.4).
- **Skills** : `xp-bots-risk-execution-contracts`, `xp-bots-broker-account-qualification` (frais, micro, marge),
  MCL.
- **Prérequis** : phase 4. Arbitrages intégrés aux contrats : P-04 et P-05 (0c), P-12 (1b), P-06 (3).
- **Ordre des couches** : 0a ∥ 0b ∥ 0c ∥ 0d ∥ 0e, puis 1a ∥ 1b ∥ 1c, puis 2a ∥ 2b, puis 3 ; checkpoints après les
  niveaux 1 et 3.
- **Tests clés** : C11.2 (spread au plafond, TTL exact), C11.5, C11.6, C11.7 et C11.10 au niveau des calculs ;
  comparaison à `rounded_levels` (S02.5) ; frais minimaux non linéaires ; marge cumulée ; positions externes ;
  gardes quotidienne et globale aux seuils exacts ; base quotidienne reconstituée (P-12) ; arbitrage `LONDON_V3`
  puis `EMA_V3`, EURUSD puis GBPUSD puis XAUUSD.
- **Couture** : aucune (S4 sera remplacé en phase 6).
- **Critères de sortie** : couches 0 à 3 figées ; régression verte.

## Phase 6 — Artefact `execution-coordinateur`, couches 4 à 6

Réalisation achevée le 08/11/2026 : quatre nouvelles couches figées dans le dossier actif commun,
checkpoint 6, couture S4 achevée. Le [bilan](../../../mcl/london-execution-coordinateur/PLAN-MCL.md)
décrit les contrats, corrections, preuves de reprise et mutations. Les journées synthétiques d'été
et d'hiver passent par le vrai moteur London, le coordinateur et les commandes C08 du modèle papier.
Le scénario neutre, le contrat et la grille synthétiques sont explicites ; la persistance est mémoire.

- **Objectif** : cycle de vie des intentions, sorties obligatoires, reprise et enveloppe du coordinateur.
- **Skills** : `xp-bots-risk-execution-contracts`, `xp-bots-deployment-readiness` (arrêts persistants,
  alertes), MCL.
- **Prérequis** : phase 5. Décision et arbitrage intégrés aux contrats : D-08 (4), P-08 (6).
- **Ordre des couches** : 4, puis 5a ∥ 5b, puis 6 ; checkpoint après le niveau 6.
- **Construction de la couche 4** : composante cyclique, par couverture incrémentale des transitions : cycle
  minimal vivant (envoi, remplissage total, clôture), puis refus, remplissage partiel, réponse inconnue et
  rapprochement, protections, réduction après remplissage ; un gate de catégorie 1 après chaque transition
  ajoutée.
- **Tests clés** : C11.11, C11.12 (côté coordinateur), C11.13 ; protections (SL absent, TP non rétabli, TP
  dépassé) ; délais de correction et échéance ; fenêtre rapide puis lente de rapprochement et alerte ; aucune
  retransmission aveugle ; redémarrage après envoi ; scénarios L-12 à L-14 et L-17 à L-19 avec le courtier
  scénarisé ; ports en implémentations neutres nommées.
- **Couture** : remplacement de S4 ; le squelette rejoue la journée de démonstration avec de vrais ordres
  exécutés par l'exécution papier minimale S5.
- **Critères de sortie** : couches 4 à 6 figées ; bout en bout vert avec ordres, remplissages et sorties.

## Phase 7 — Artefact `controles-fondamentaux`

Réalisée le 09/11/2026 : les cinq couches du dossier actif partagé
[`london-controles-fondamentaux`](../../../mcl/london-controles-fondamentaux/PLAN-MCL.md) sont
figées après leurs gates et CP2. La couture utilise le vrai port C05 avec arrivées scénarisées ;
L-14 est vérifié au vrai moteur London en été et en hiver. Les lectures physiques restent en phase 11.

- **Objectif** : permissions externes et garde d'annonces (document 02, §6.5 ; C05).
- **Skills** : `xp-bots-fundamental-permissions`, MCL.
- **Prérequis** : phase 6.
- **Ordre des couches** : 0, puis 1a ∥ 1b, puis 2, puis 3 ; checkpoint après le niveau 2.
- **Tests clés** : C11.8, C11.9, A14-6 (côté socle), A14-8 (côté socle) ; heartbeat manqué journalisé ; blocage à
  l'expiration ; `FLATTEN` ; annonce apprise tardivement ; calendrier périmé sans liquidation ; table des
  devises par symbole conforme à C05 ; scénario L-14 (clôture à N − 900 s) ; messages et versions de calendrier
  pris dans des fixtures au **format exact** du dossier d'échange (D-11) et de l'export MQL5 (D-12), décrits au
  document 01, §2.1 et §2.2 (la lecture des fichiers réels vient en phase 11).
- **Couture** : le coordinateur utilise l'implémentation réelle du port, sauf dans un rejeu explicitement nommé
  `TECHNICAL_CONTROL_NEUTRAL`.
- **Critères de sortie** : cinq unités figées ; bout en bout vert avec permissions scénarisées.

## Phase 8 — Artefact `contexte-ia`

Réalisée le 09/11/2026 : quatre couches communes figées dans
[`london-contexte-ia`](../../../mcl/london-contexte-ia/PLAN-MCL.md), CP2 et couture du vrai port.
Les 58 tests propres et 11 nouveaux tests du squelette couvrent les cas ci-dessous, dont L-15
sur le vrai moteur London été/hiver. La comparaison d'oracle explicite son retour prématuré sur
les listes mixtes malformées ; le lecteur rejette le snapshot entier selon A10/A12. La référence
conserve le complément absent. L'orchestration A/B complète reste l'objet de la phase 9.

- **Objectif** : lecture du snapshot, cache des vetos, port `BLOCK` ou `NEUTRAL` (document 02, §6.6).
- **Skills** : `xp-bots-llm-integration-contracts`, MCL.
- **Prérequis** : phase 7.
- **Ordre des couches** : 0, 1, 2, 3 ; checkpoint après le niveau 2.
- **Tests clés** : A14-2, A14-7, A14-8, A14-16 ; égalité avec `overlay_decision` sur des snapshots valides et
  altérés ; scénario L-15 ; persistance du cache et de la dernière séquence par export et import.
- **Couture** : le bras IA utilise ce port ; le bras de référence garde le complément absent.
- **Critères de sortie** : quatre unités figées ; bout en bout vert.

## Phase 9 — Artefact `orchestration`

Réalisée le 09/11/2026 : trois couches communes figées dans `mcl/orchestration/`,
CP2 et moteur unique derrière S4. Les 50 tests propres (44 catégorie 1, 6 catégorie 2)
et sept nouveaux tests de couture vérifient les critères ci-dessous : journal avec
calculs exactement rejoué sur backend interdit, comptes et stratégies indépendants,
C11.10, priorité native et FLATTEN, panne de stockage, L-15 été/hiver et CLI PAPER_AB.
La suite du squelette compte 67 tests. Le simulateur C10 n’est pas commencé.

- **Objectif** : moteur de décision événementiel unique, bras A/B, stratégies injectées (document 02, §6.7 ;
  D-18).
- **Skills** : `xp-bots-london-breakout`, `xp-bots-risk-execution-contracts`, `xp-bots-llm-integration-contracts`,
  MCL.
- **Prérequis** : phase 8.
- **Ordre des couches** : 0, 1, 2.
- **Tests clés** : ordre C08 sur des événements combinés (réponse, clôture obligatoire, bougie, signal) ; mêmes
  entrées → mêmes sorties (rejeu d'un journal d'entrées synthétique) ; bras indépendants (quotas, positions,
  comptes) sur entrées identiques ; A14-9, A14-17 ; C11.10 au niveau du moteur ; injection du vrai moteur London
  par la configuration de déploiement, et carte vérifiant qu'aucun import de `xpbots.london` n'existe dans
  `xpbots.orchestration`.
- **Couture** : l'enchaînement minimal du squelette est remplacé par le moteur de décision ; le squelette
  rejoue désormais une journée en `PAPER_AB` sur fixtures.
- **Critères de sortie** : trois unités figées ; bout en bout vert en mode simple et en `PAPER_AB`.

## Phase 10 — Artefact `journal-rejeu`

Réalisée le 10/11/2026 : huit unités communes figées dans [london-journal-rejeu](../../../mcl/london-journal-rejeu/PLAN-MCL.md), checkpoints 1 et 3, remplacement S1/S5 et adaptation S7. La mesure d’un mois synthétique et les contrôles sont détaillés au bilan ; aucune donnée réelle ni qualification de rentabilité.

- **Objectif** : simulateur C10, analyse des ticks, rejeu, métriques, bootstrap et rapports (document 02, §6.8).
- **Skills** : `xp-bots-validation-replay`, `xp-bots-market-data-causality`, MCL.
- **Prérequis** : phase 9. Arbitrage intégré au contrat : P-11 (1b).
- **Ordre des couches** : 0a ∥ 0b, puis 1a ∥ 1b ∥ 1c ∥ 1d, puis 2, puis 3 ; checkpoints après les niveaux 1 et 3.
- **Tests clés** : modèles de référence et de stress (délais, ticks adverses, spread de stress) ; TP limite
  jamais pénalisé ; protections natives avant sorties logicielles ; gap au stop ; SL et TP de même milliseconde
  (C11.12) ; fonds propres et drawdown ; métriques sur des cas calculés à la main ; bootstrap sur un petit
  panel calculé à la main (graine et percentiles) ; rétention N/A et « trop faible » ; verrou du test réservé ;
  valeurs textuelles de C10 présentes dans la spécification ; mesure de la durée d'un mois synthétique de ticks
  pour estimer le coût d'un rejeu complet.
- **Couture** : remplacement de S5 (exécution papier par le simulateur) et de l'analyse des lignes de S1.
- **Critères de sortie** : huit unités figées ; bout en bout vert ; aucune donnée réelle utilisée à ce stade.

## Phase 11 — Infrastructure réelle, source du service MQL5 et points d'entrée

- **Objectif** : implémentations réelles des frontières, construites dans le conteneur contre les contrats
  finalisés tôt du [document 08](08_contrats_frontieres.md) ; source du service MQL5 d'export ; points d'entrée
  (document 02, §6.9, §6.10 et §6.12).
- **Skills** : `xp-bots-broker-account-qualification`, `xp-bots-deployment-readiness`,
  `xp-bots-market-data-causality`, MCL.
- **Prérequis** : phase 10. Aucune action humaine : le poste Windows, le compte de démonstration et le terminal
  ne servent qu'à partir de la sous-étape 13.1. La dépendance `MetaTrader5` est autorisée (D-05) mais n'est pas
  installable dans le conteneur (roues Windows seulement) : le faux module la remplace dans tous les tests.
- **Étapes**
  1. Écrire le faux module `MetaTrader5` de `tests/robot/outils/` d'après le document 08, §2 : constantes,
     signatures, structures nommées et scénarios (réponses, codes de retour, `None` suivi de `last_error`, appel
     bloquant, déconnexion) ; ajouter le test qui compare ses constantes à la liste du document 08.
  2. Écrire `requirements-windows.txt` (document 08, §2.1) et le test qui vérifie que ses versions de `numpy` et
     de `tzdata` égalent celles de `requirements-dev.txt`.
  3. Écrire le service MQL5 `mql5/Services/XPBotsExport.mq5` (document 02, §6.12) selon les schémas du
     document 08, §4, et les tests Python de format sur fixtures. Compilation et comparaison aux vues du terminal
     en sous-étape 13.1. `mcl.py` n'analysant pas MQL5, la convention de module et la revue de code sont
     rappelées dans le rapport.
  4. Construire `infrastructure` couche par couche (dossier d'échange D-11, exports D-12 et table horaire du
     document 08, §5, compris) : catégories 1 et 2 avec le faux module, des dossiers temporaires et SQLite en
     fichier temporaire ; écrire avec chaque couche ses tests de contrat (document 03, §7), ignorés hors du poste ;
     geler chaque couche sur la foi des contrats du document 08, dont la confrontation au réel est planifiée en
     13.1 (risque R-18).
  5. Construire `points-entree` : boucle en direct (D-09), commandes de rejeu, de qualification (rapport du
     document 08, §9) et de rapports ; injection du moteur London ; garde du type de compte (document 08, §2.3) ;
     refus de `TECHNICAL_CONTROL_NEUTRAL` en démonstration et en réel ; refus du mode réel sans décision de
     déploiement tracée ; gabarits du registre de déploiement (sans secret, avec les constantes d'ingénierie
     D-09, plafond du dossier d'échange et cadences d'export) et du fichier des fermetures exceptionnelles
     (document 08, §4.3) ; procédure d'exploitation (accusé inconnu, SL absent, garde, arrêt global, redémarrage,
     coupure réseau, mise à jour des fermetures exceptionnelles).
  6. **Répétition générale dans le conteneur** : une séance London `PAPER` complète à travers la vraie boucle en
     direct, le faux module servant un flux de ticks scénarisé, le dossier d'échange et les exports étant écrits
     dans un dossier commun temporaire ; journaux complets ; rejeu du journal d'entrées identique (C11.14).
- **Coutures** : remplacement de S6 (écriture réelle), S7 (points d'entrée) et S1 en direct (flux MT5, servi ici
  par le faux module).
- **Critères de sortie** : couches figées ; suite complète verte dans le conteneur ; tests de contrat écrits et
  recensés dans le rapport, avec la sous-étape qui les exécutera ; répétition générale identique à son rejeu.
- **Exclu** : tout appel au vrai terminal et tout ordre, même de démonstration, avant la sous-étape 13.1 ; tout
  ordre sur compte réel.

## Phase 12 — Artefact `service-ia`

- **Objectif** : service IA partagé, en arrière-plan, sans inférence locale (document 02, §6.11 ; A04 à A11).
- **Skills** : `xp-bots-llm-integration-contracts`, MCL.
- **Prérequis** : phase 11. Aucune action humaine et aucun appel réseau réel : les appels d'API ne sont pas
  autorisés (D-17) ; leur autorisation sera redemandée en sous-étape 13.6. Les clients des fournisseurs et le
  collecteur RSS sont testés avec un ouvreur HTTP factice, des réponses fabriquées aux gabarits de A08 et des flux
  XML fabriqués au format de A04. La route payante reste désactivée sauf décision explicite.
- **Ordre des couches** : selon `mcl.py analyser` (carte indicative du document 02).
- **Tests clés** : A14-3 à A14-6 et A14-11 à A14-16 ; égalité avec `parse_model_output`,
  `parse_advisory_output`, `build_policy_event`, `make_snapshot`, `reserve_cost_usd` et `budget_admits` ;
  plafonds aux bornes ; transaction de budget concurrente ; reprise sans réinférence ; écriture atomique (le
  comportement propre à Windows est confirmé en 13.6) ; lecture de l'export MQL5 du calendrier pour
  l'appariement A06 ; tests de contrat API et RSS écrits, ignorés sans `XPBOTS_CONTRATS_API=1`.
- **Essai de bout en bout dans le conteneur** : le service, lancé avec l'ouvreur factice, écrit son snapshot
  (heartbeat, événements fabriqués) que `contexte-ia` lit pendant une séance `PAPER_AB` rejouée ; le bras IA
  bloque exactement les signaux visés par un veto fabriqué valide et reste `NEUTRAL` sans snapshot.
- **Critères de sortie** : couches figées ; suite complète verte hors ligne ; essai de bout en bout conforme.

## Phase 13 — Qualification et validation

Chaque sous-étape est un point d'arrêt. Aucune ne valide une rentabilité par elle-même. C'est la seule phase qui
requiert des actions humaines ([document 07](07_procedures_humaines.md)) ; chaque sous-étape commence par
vérifier les siennes et s'arrête sur une question si l'une manque.

| Sous-étape | Objet | Prérequis et actions humaines | Sortie |
|---|---|---|---|
| 13.1 | **Qualification de l'infrastructure sur le poste**, puis qualification C04. (1) Installation de `requirements-windows.txt` et suite complète verte sur le poste ; service MQL5 compilé sans avertissement et lancé (H-04) ; fichier des fermetures exceptionnelles (H-05) et module fondamental (H-06) en place. (2) Sondes S-01 à S-08 et tests de contrat MT5, fichiers, SQLite, dossier d'échange et export MQL5 (document 03, §7) ; garde du type de compte. (3) Toute divergence avec le document 08 : défigeage « correction » de la couche concernée, test qui capture le cas, nouveau gel, régression intégrale ; si l'entrée protégée n'est pas attachable (S-02), profil « non prêt pour V3 » (C06) et arrêt sur décision humaine. (4) Qualification C04 sur le compte démo Deriv : fiche d'environnement, règle de liaison d'un symbole par sous-jacent, disponibilité des contrats micro, levier du compte, faisabilité du volume minimal à 0,5 %, liste `ENVIRONMENT_NOT_READY` vide pour EURUSD et GBPUSD. (5) Une séance London `PAPER` sur le terminal démo sans erreur, journaux complets, rejeu identique de son journal d'entrées (premier contrôle réel de C11.14) ; écart d'horloge mesuré et consigné ; début de la collecte prospective des versions du calendrier | Phase 12 ; H-02 à H-07 | Rapport de qualification ; profil admissible, ou verdict « compte incompatible avec la fréquence visée » (C10), sans déformer le risque |
| 13.2 | Acceptation sur plateforme : cas C11 qui exigent le courtier (5, 7, 11, 12, 13), en démo ; égalité C11.14 par rejeu des journaux d'entrées de plusieurs séances | 13.1 ; terminal démo ouvert (H-03) | Rapport d'acceptation |
| 13.3 | Données historiques (D-14). (1) Exports fournis par l'humain : ticks du 02/12/2019 au 03/11/2026 (ceux de Deriv s'ils couvrent toute la période, sinon la source tierce pour toute la période, déclarée contrefactuelle, sans mélange d'historiques), caractéristiques et coûts datés, permissions historiques causales si elles existent. (2) Sondes S-09 et S-10 sur ces exports. (3) Construction de l'artefact `donnees-historiques` au protocole MCL (document 02, §6.14). (4) Conversion et validation : ordre, couverture, registres de trous, manifeste SHA-256, calendrier avec heures de connaissance (approximation déclarée pour l'historique) | 13.1 ; H-09 | Artefact `donnees-historiques` figé ; données validées dans `data/raw/` (jamais commitées) |
| 13.4 | Portage de la V1 London (D-15) : spécification fournie par l'humain, versée en contexte avec son empreinte, puis artefact `moteur-london-v1` construit au protocole MCL (document 02, §6.13) et injecté dans le seul rejeu | Phase 12 ; H-10 | Moteur V1 figé, refusé hors rejeu |
| 13.5 | Rejeux C10 : contrôle d'implémentation 2020–2022, validation 2023–2024, rejeu continu 2020–2026, stress, six perturbations, compte London seul ; comparaison V3/V1 sur le même moteur ; ouverture **unique** du test réservé après gel du robot (empreinte consignée) ; période 01/05–03/11/2026 en diagnostic | 13.3, 13.4 | Rapport C10 ; « non validé » si un critère manque, sans retouche |
| 13.6 | **IA réelle et qualification sémantique A13.** (1) L'agent redemande l'autorisation des appels d'API réels (D-17). (2) Avec autorisation : clés gratuites placées par l'humain dans `.env` (jamais lues ni affichées par l'agent), tests de contrat API et RSS, écriture atomique du snapshot confirmée sous Windows, service en marche au moins une journée de marché (heartbeat régulier, registre de budget cohérent, aucune route payante appelée, snapshot lu par le robot en `PAPER_AB`) ; puis 200 textes annotés par un humain, seuils `model_min_material_event_precision` et `model_min_material_event_recall`, zéro citation non vérifiée ; comparaison gratuit et payant seulement si le payant est configuré. (3) Sans autorisation : service laissé arrêté, bras IA de `PAPER_AB` à `NEUTRAL`, fournisseurs `NON_QUALIFIE` | 13.1 ; H-08, H-11 | `QUALIFIE` ou `NON_QUALIFIE` par fournisseur |
| 13.7 | Collecte prospective `PAPER_AB` puis démonstration : effectifs minimaux de A13 et de C10 ; checklist go/no-go (`xp-bots-deployment-readiness`) ; le veto réel reste désactivé sans validation financière A13 ; le réel n'est décidé que par l'humain | 13.1 à 13.6 ; H-12 | Décision tracée de l'humain (H-12) |

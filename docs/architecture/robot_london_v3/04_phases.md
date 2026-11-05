# 04 — Phases d'exécution du plan

Retour au [plan directeur](README.md). Une phase se termine **intégralement**, puis l'agent s'arrête et attend une
demande explicite pour la suivante (plan directeur, §1). Les identifiants de couches renvoient au
[document 02](02_cartographie_mcl.md) ; les cas et scénarios au [document 03](03_acceptation_et_tests.md).

## Gabarit commun à toutes les phases

**À l'entrée d'une phase**

1. Appliquer l'orchestrateur de skills du dépôt (cycle obligatoire d'`AGENTS.md`) ; charger les skills
   métier de la phase (indiquées dans chaque fiche).
2. Vérifier que les artefacts amont sont figés : `mcl.py --dossier mcl/<amont> statut` ; vérifier que les
   décisions et arbitrages qui bloquent la phase sont arrêtés (plan directeur, §3 et §4). À défaut, s'arrêter
   sur une question.
3. Relever l'état initial : `git status --short`, `python tools/run_robot_tests.py`,
   `python tools/verify_project.py` ; tout échec préexistant est documenté avant le moindre changement.

**Pendant la phase (artefact MCL)**

4. Initialiser `mcl/<artefact>/` ; reporter dans son `PLAN-MCL.md` les sections du document 02 qui le concernent
   (périmètre, applicabilité, étape 1, unités, carte, frontières) ; renseigner `unites` et `externes` de la
   carte ; `mcl.py analyser --ecrire`, puis compléter `chemins`, `imports` et `contrats` ; `mcl.py analyser`
   jusqu'à zéro divergence ; esquisser tous les contrats de couche.
5. Pour chaque couche, dans l'ordre que donne `mcl.py statut` (colonne « constructible maintenant ») :
   finaliser le contrat, implémenter, tests de catégorie 1, valider, intégrer, tests de catégorie 2,
   régression intégrale (gate), figer. Une seule évolution par gate ; les couches parallèles peuvent s'écrire
   dans la même passe, chacune avec son gate et son gel.
6. Brancher l'enveloppe sur le squelette en remplaçant le segment minimal ; consigner la couture dans
   `mcl/squelette/COUTURES.md` ; le test de bout en bout du squelette reste vert.

**À la sortie de la phase**

7. Gate global de l'artefact ; checkpoint si `statut` le signale ; `mcl.py verifier` de la carte composite.
8. `python tools/verify_project.py` ; suite de gouvernance si un fichier de gouvernance a changé.
9. Commit et push sur la branche de travail, sans réécriture d'historique.
10. **Rapport d'arrêt** : unités et couches figées, contrats, effectifs des tests par catégorie, résultat de la
    régression intégrale, coutures modifiées, défauts trouvés et leur traitement, limites, prérequis de la
    phase suivante. Puis arrêt.

---

## Phase 0 — Cadrage, décisions et arbitrages

- **Objectif** : lever toutes les décisions qui bloquent les phases 1 à 4 et poser la structure MCL composite.
- **Skills** : `xp-bots-mcl-robot-planning`, `mcl-matryoshka-construction-layers`, `xp-bots-london-breakout`,
  `xp-bots-specification-consistency`, `xp-bots-maintain-agent-skills` (pour l'étape 5).
- **Prérequis humains** : réponses aux arbitrages P-01 à P-12 et aux décisions D-03, D-04, D-07, D-08, D-09,
  D-10.
- **Étapes**
  1. Présenter les arbitrages par groupes cohérents (données et temps : P-01, P-02, P-03, P-10 ; London : P-09 ;
     exécution : P-04, P-05, P-06, P-08, P-12 ; journal : P-07 ; rejeu : P-11), recommandation en tête,
     alternative et conséquence. Un arbitrage qui changerait une règle, un seuil ou un coût est refusé : il
     exigerait une nouvelle version de la spécification.
  2. Consigner les réponses dans le plan directeur (§3 et §4 : statut « arrêtée », date, auteur) et dans le
     journal des révisions du plan.
  3. Initialiser le dossier composite :
     `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/robot-london-v3 init --nom robot-london-v3 --langage python --echelle application --mode composite --sources src`.
  4. Renseigner la **carte composite au grain des paquets** : une unité et une couche par artefact
     (`xpbots.noyau`, `xpbots.donnees`, `xpbots.london`, `xpbots.execution`, `xpbots.fondamental`,
     `xpbots.contexte_ia`, `xpbots.orchestration`, `xpbots.rejeu`, `xpbots.infra`, `xpbots.app`,
     `xpbots.service_ia`) avec les dépendances du tableau du document 02, §5 ; `mcl.py analyser` jusqu'à zéro
     divergence.
     `moteur-london` et `execution-coordinateur` y sont des couches parallèles : toute dépendance mutuelle sera
     détectée mécaniquement. Cette carte sert à `analyser` et `verifier`, jamais à `figer`.
  5. Mettre à jour, par la skill de gouvernance, les phrases du guide d'implémentation et des règles du projet
     qui disent que langage et plateforme ne sont pas arrêtés : décision D-01 du 05/11/2026 pour le robot 2 et
     les composants partagés, avec lien vers ce plan ; suite de gouvernance verte.
- **Livrables** : plan directeur mis à jour ; `mcl/robot-london-v3/` (carte composite, `PLAN-MCL.md`, journal) ;
  guide et règles mis à jour.
- **Critères de sortie** : chaque arbitrage tranché ou explicitement reporté avec la couche qu'il bloque ;
  analyse composite sans divergence ; `tools/verify_project.py` et suite de gouvernance verts.
- **Exclu** : tout code du robot.

## Phase 1 — Squelette composite déployable

- **Objectif** : un chemin de bout en bout minimal, en code de production destiné à durer, déployable et vérifié
  par l'intégration continue dès le départ.
- **Skills** : `xp-bots-mcl-robot-planning`, `xp-bots-maintain-agent-skills` (porte de cycle de vie, si D-10 est
  approuvée).
- **Prérequis** : phase 0 ; D-03 et D-04 arrêtées ; D-10 approuvée (sinon intégration continue locale seulement,
  consignée comme limite).
- **Étapes**
  1. Écrire `tools/run_robot_tests.py` (document 03, §2), avec un test qui prouve qu'un test en échec rend un code
     de sortie non nul.
  2. Écrire la première fabrique de ticks synthétiques (`tests/robot/outils/`).
  3. Écrire les segments minimaux S1 à S7 (document 02, §3.1) dans leurs paquets définitifs, chacun documenté
     comme « segment minimal du squelette, remplacé en phase N ».
  4. Écrire le test de bout en bout : une journée Londres synthétique d'EURUSD rejouée par
     `python -m xpbots.app.rejeu_squelette` dans un dossier temporaire ; un enregistrement par M15 close, motif
     conforme, code de sortie nul.
  5. Écrire le premier test de pureté du cœur (document 03, §8).
  6. Si D-10 est approuvée : workflow `.github/workflows/robot.yml` (Ubuntu et Windows, Python 3.13 :
     installation de `requirements-dev.txt`, `python tools/run_robot_tests.py`, `python tools/verify_project.py`)
     et porte `robot-suite` dans `.agents/hooks/lifecycle.json` (motifs `src/**`, `tests/robot/**`,
     `tools/run_robot_tests.py`), avec ses tests de gouvernance.
  7. Créer `mcl/squelette/COUTURES.md` : contrat minimal de chaque couture, propriétaire futur, statut.
  8. `mcl.py verifier` avec la carte composite.
- **Livrables** : lanceur, fabrique, segments minimaux, test de bout en bout, garde de pureté, registre des
  coutures, intégration continue (si approuvée).
- **Critères de sortie** : test de bout en bout vert en local (et en CI si approuvée) ; vérification du projet et
  gouvernance verts ; commande de démonstration documentée dans le rapport.
- **Exclu** : toute logique S02, C05 à C08.

## Phase 2 — Artefact `noyau`

- **Objectif** : types et règles partagés, et lecture stricte des configurations figées (document 02, §6.1).
- **Skills** : `xp-bots-specification-consistency`, `xp-bots-risk-execution-contracts` (motifs), MCL.
- **Prérequis** : phase 1 ; P-07 tranché avant les couches 1c et 2.
- **Ordre des couches** : 0a ∥ 0b ∥ 0c, puis 1a ∥ 1b ∥ 1c, puis 2 ; checkpoint après le niveau 1.
- **Tests clés** : JSON strict (clé dupliquée, nombre non fini) ; empreinte des octets contre la preuve de
  conservation ; empreinte canonique égale au `design_sha256` du diagnostic ; clé inconnue ou manquante ; option
  désactivée activée ; instants refusés sans fuseau ou avec décalage ; arrondis sur grille comparés à la
  sémantique de `rounded_levels` ; profil incomplet → liste `ENVIRONMENT_NOT_READY` ; motifs fermés ;
  sérialisation canonique du journal.
- **Couture** : les types minimaux du squelette sont remplacés (extension tracée de S1 et S6).
- **Critères de sortie** : sept unités figées ; bout en bout vert ; gate global vert.

## Phase 3 — Artefact `donnees-temps`

- **Objectif** : bougies M15 et H1 causales, validées et enrichies (document 02, §6.2 ; C03).
- **Skills** : `xp-bots-market-data-causality`, `xp-bots-london-breakout`, MCL.
- **Prérequis** : phase 2 ; P-01 (avant 1c), P-02 (avant 2a), P-03 et P-10 (avant 2b) tranchés.
- **Ordre des couches** : 0a ∥ 0b, puis 1a ∥ 1b ∥ 1c, puis 2a ∥ 2b, puis 3 ; checkpoint après le niveau 1 et après
  le niveau 3.
- **Tests clés** : correspondances Londres et UTC sur les jours de référence (y compris ceux de
  `tests/check_technical.py`) ; 20 ouvertures de range en été et en hiver ; égalité avec
  `local_decision_in_window` sur une grille d'instants de 2019 à 2027 ; tick de frontière ; intervalles vides ;
  TR et ATR comparés à `wilder` et `add_indicators` ; A_t = ATR de t − 1 ; invariance par préfixe (C11.1) ; H1
  jamais partielle ; reprise après export et import d'état ; préchargement différent journalisé.
- **Couture** : remplacement de S2.
- **Critères de sortie** : huit unités figées ; bout en bout vert avec les vraies bougies.

## Phase 4 — Artefact `moteur-london`

- **Objectif** : la méthode S02 complète, pure et indépendante (document 02, §6.3).
- **Skills** : `xp-bots-london-breakout`, `anthropic-skills:expert-scalper-m15` (lecture critique des cas, sans
  changer une règle), MCL.
- **Prérequis** : phase 3 ; P-09 tranché avant 1b.
- **Ordre des couches** : 0a ∥ 0b, puis 1a ∥ 1b ∥ 1c ∥ 1d ∥ 1e, puis 2 ; checkpoint après le niveau 1.
- **Tests clés** : S02.6 complet et scénarios L-01 à L-13 ; égalité de `bougie_cassure` et `stop_local` avec
  `london_signal` sur des cas synthétiques ; égalité des signaux de l'enveloppe avec `london_setups` quand aucun
  remplissage n'est rapporté (les quotas ne lient alors jamais) ; causalité par préfixe ; état du jour
  réinitialisé au changement de jour Londres ; non-recopie des seuils.
- **Couture** : remplacement de S3 ; le squelette journalise désormais de vrais signaux London, refusés
  explicitement par le coordinateur minimal.
- **Critères de sortie** : huit unités figées ; bout en bout vert.

## Phase 5 — Artefact `execution-coordinateur`, couches 0 à 3

- **Objectif** : calculs purs de C06 et C07 : cotation, niveaux exécutables, échéances, gardes, réservations,
  risque all-in, arbitrage, dimensionnement (document 02, §6.4).
- **Skills** : `xp-bots-risk-execution-contracts`, `xp-bots-broker-account-qualification` (frais, micro, marge),
  MCL.
- **Prérequis** : phase 4 ; P-04 et P-05 (avant 0c), P-12 (avant 1b), P-06 (avant 3) tranchés.
- **Ordre des couches** : 0a ∥ 0b ∥ 0c ∥ 0d ∥ 0e, puis 1a ∥ 1b ∥ 1c, puis 2a ∥ 2b, puis 3 ; checkpoints après les
  niveaux 1 et 3.
- **Tests clés** : C11.2 (spread au plafond, TTL exact), C11.5, C11.6, C11.7 et C11.10 au niveau des calculs ;
  comparaison à `rounded_levels` (S02.5) ; frais minimaux non linéaires ; marge cumulée ; positions externes ;
  gardes quotidienne et globale aux seuils exacts ; arbitrage `LONDON_V3` puis `EMA_V3`, EURUSD puis GBPUSD puis
  XAUUSD.
- **Couture** : aucune (S4 sera remplacé en phase 6).
- **Critères de sortie** : couches 0 à 3 figées ; régression verte.

## Phase 6 — Artefact `execution-coordinateur`, couches 4 à 6

- **Objectif** : cycle de vie des intentions, sorties obligatoires, reprise et enveloppe du coordinateur.
- **Skills** : `xp-bots-risk-execution-contracts`, `xp-bots-deployment-readiness` (arrêts persistants,
  alertes), MCL.
- **Prérequis** : phase 5 ; D-08 (avant 4) et P-08 (avant 6) arrêtés.
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

- **Objectif** : permissions externes et garde d'annonces (document 02, §6.5 ; C05).
- **Skills** : `xp-bots-fundamental-permissions`, MCL.
- **Prérequis** : phase 6.
- **Ordre des couches** : 0, puis 1a ∥ 1b, puis 2, puis 3 ; checkpoint après le niveau 2.
- **Tests clés** : C11.8, C11.9, A14-6 (côté socle), A14-8 (côté socle) ; heartbeat manqué journalisé ; blocage à
  l'expiration ; `FLATTEN` ; annonce apprise tardivement ; calendrier périmé sans liquidation ; table des
  devises par symbole conforme à C05 ; scénario L-14 (clôture à N − 900 s).
- **Couture** : le coordinateur utilise l'implémentation réelle du port, sauf dans un rejeu explicitement nommé
  `TECHNICAL_CONTROL_NEUTRAL`.
- **Critères de sortie** : cinq unités figées ; bout en bout vert avec permissions scénarisées.

## Phase 8 — Artefact `contexte-ia`

- **Objectif** : lecture du snapshot, cache des vetos, port `BLOCK` ou `NEUTRAL` (document 02, §6.6).
- **Skills** : `xp-bots-llm-integration-contracts`, MCL.
- **Prérequis** : phase 7.
- **Ordre des couches** : 0, 1, 2, 3 ; checkpoint après le niveau 2.
- **Tests clés** : A14-2, A14-7, A14-8, A14-16 ; égalité avec `overlay_decision` sur des snapshots valides et
  altérés ; scénario L-15 ; persistance du cache et de la dernière séquence par export et import.
- **Couture** : le bras IA utilise ce port ; le bras de référence garde le complément absent.
- **Critères de sortie** : quatre unités figées ; bout en bout vert.

## Phase 9 — Artefact `orchestration`

- **Objectif** : moteur de décision événementiel unique, bras A/B (document 02, §6.7).
- **Skills** : `xp-bots-london-breakout`, `xp-bots-risk-execution-contracts`, `xp-bots-llm-integration-contracts`,
  MCL.
- **Prérequis** : phase 8.
- **Ordre des couches** : 0, 1, 2.
- **Tests clés** : ordre C08 sur des événements combinés (réponse, clôture obligatoire, bougie, signal) ; mêmes
  entrées → mêmes sorties (rejeu d'un journal d'entrées synthétique) ; bras indépendants (quotas, positions,
  comptes) sur entrées identiques ; A14-9, A14-17 ; C11.10 au niveau du moteur.
- **Couture** : l'enchaînement minimal du squelette est remplacé par le moteur de décision ; le squelette
  rejoue désormais une journée en `PAPER_AB` sur fixtures.
- **Critères de sortie** : trois unités figées ; bout en bout vert en mode simple et en `PAPER_AB`.

## Phase 10 — Artefact `journal-rejeu`

- **Objectif** : simulateur C10, analyse des ticks, rejeu, métriques, bootstrap et rapports (document 02, §6.8).
- **Skills** : `xp-bots-validation-replay`, `xp-bots-market-data-causality`, MCL.
- **Prérequis** : phase 9 ; P-11 tranché avant 1b.
- **Ordre des couches** : 0a ∥ 0b, puis 1a ∥ 1b ∥ 1c ∥ 1d, puis 2, puis 3 ; checkpoint après les niveaux 1 et 3.
- **Tests clés** : modèles de référence et de stress (délais, ticks adverses, spread de stress) ; TP limite
  jamais pénalisé ; protections natives avant sorties logicielles ; gap au stop ; SL et TP de même milliseconde
  (C11.12) ; fonds propres et drawdown ; métriques sur des cas calculés à la main ; bootstrap sur un petit
  panel calculé à la main (graine et percentiles) ; rétention N/A et « trop faible » ; verrou du test réservé ;
  valeurs textuelles de C10 présentes dans la spécification ; mesure de la durée d'un mois synthétique de ticks
  pour estimer le coût d'un rejeu complet.
- **Couture** : remplacement de S5 (exécution papier par le simulateur) et de l'analyse des lignes de S1.
- **Critères de sortie** : huit unités figées ; bout en bout vert ; aucune donnée réelle utilisée à ce stade.

## Phase 11 — Artefacts `infrastructure` et `points-entree`

- **Objectif** : implémentations réelles des frontières et points d'entrée (document 02, §6.9 et §6.10).
- **Skills** : `xp-bots-broker-account-qualification`, `xp-bots-deployment-readiness`,
  `xp-bots-market-data-causality`, MCL.
- **Prérequis humains** : approbation de la dépendance `MetaTrader5` (D-05) ; décisions D-11, D-12, D-13 ; poste
  Windows avec Python 3.13 x64, terminal MT5 installé et connecté à un **compte de démonstration** ; accès de
  l'agent au poste (dossier partagé) ou exécution des commandes par l'humain.
- **Étapes**
  1. **Sondes jetables** S-01 à S-08 (document 01, §10), exécutées sur le poste Windows, code placé dans un
     dossier ignoré par Git et supprimé ensuite ; preuves dans `.local/reports/qualification/`. Toute sonde en
     échec est rapportée avant de construire la couche concernée ; si l'entrée protégée n'est pas attachable,
     le profil est déclaré non prêt (C06) et la phase s'arrête sur décision humaine.
  2. Ajouter, après approbation, un fichier d'exigences d'exécution distinct qui épingle `MetaTrader5`
     (marqueur `sys_platform == "win32"`) et `tzdata`.
  3. Construire `infrastructure` couche par couche ; catégorie 1 avec le faux module `MetaTrader5`, des
     dossiers temporaires et SQLite en mémoire ; tests de contrat sur le poste Windows.
  4. Si D-12 retient l'export MQL5 : écrire le service MQL5 d'export (calendrier et horaires de séance vers
     `Common/Files`), compilé et testé par l'humain dans MetaEditor ; format d'export validé par des tests Python
     sur fixtures. `mcl.py` n'analyse pas MQL5 : convention de module et revue de code, signalées dans le
     rapport.
  5. Construire `points-entree` : boucle en direct (D-09), commandes de rejeu, de qualification et de
     rapports ; refus de `TECHNICAL_CONTROL_NEUTRAL` en démonstration et en réel ; refus du mode réel sans
     décision de déploiement tracée ; gabarit du registre de déploiement (sans secret) ; procédure
     d'exploitation (accusé inconnu, SL absent, garde, arrêt global, redémarrage, coupure réseau).
- **Coutures** : remplacement de S6 (écriture réelle), S7 (points d'entrée) et S1 en direct (flux MT5).
- **Critères de sortie** : couches figées ; tests de contrat MT5 verts sur compte démo ; une séance London en
  mode `PAPER` sur le terminal démo sans erreur, journaux complets ; rejeu du journal d'entrées de cette séance
  identique (premier contrôle de C11.14).
- **Exclu** : tout ordre sur compte réel.

## Phase 12 — Artefact `service-ia`

- **Objectif** : service IA partagé, en arrière-plan, sans inférence locale (document 02, §6.11 ; A04 à A11).
- **Skills** : `xp-bots-llm-integration-contracts`, MCL.
- **Prérequis humains** : décision d'activer `PAPER_AB` ; clés des routes gratuites dans `.env` (jamais lues ni
  affichées par l'agent) ; approbation explicite des requêtes réelles de conformité ; route payante désactivée
  sauf décision.
- **Ordre des couches** : selon `mcl.py analyser` (carte indicative du document 02).
- **Tests clés** : A14-3 à A14-6 et A14-11 à A14-16 ; égalité avec `parse_model_output`,
  `parse_advisory_output`, `build_policy_event`, `make_snapshot`, `reserve_cost_usd` et `budget_admits` ;
  plafonds aux bornes ; transaction de budget concurrente ; reprise sans réinférence ; écriture atomique sous
  Windows.
- **Critères de sortie** : service en marche au moins une journée de marché avec heartbeat régulier, registre de
  budget cohérent, aucune route payante appelée ; le robot lit le snapshot en `PAPER_AB`.

## Phase 13 — Qualification et validation

Chaque sous-étape est un point d'arrêt. Aucune ne valide une rentabilité par elle-même.

| Sous-étape | Objet | Prérequis | Sortie |
|---|---|---|---|
| 13.1 | Qualification C04 sur compte démo : fiche d'environnement, règle de liaison d'un symbole par sous-jacent, disponibilité des contrats micro, faisabilité du volume minimal à 0,5 %, liste `ENVIRONMENT_NOT_READY` vide pour EURUSD et GBPUSD | Phase 11 | Profil admissible, ou verdict « compte incompatible avec la fréquence visée » (C10), sans déformer le risque |
| 13.2 | Acceptation sur plateforme : cas C11 qui exigent le courtier (5, 7, 11, 12, 13), en démo ; égalité C11.14 par rejeu des journaux d'entrées de plusieurs séances | 13.1 | Rapport d'acceptation |
| 13.3 | Données historiques (D-14) : ticks du 02/12/2019 au 03/11/2026, caractéristiques et coûts datés, calendrier avec heures de connaissance, permissions historiques causales si elles existent ; formats, registres de trous, empreintes | Décision D-14 | Données validées dans `data/raw/` (jamais commitées) |
| 13.4 | Rejeux C10 : contrôle d'implémentation 2020–2022, validation 2023–2024, rejeu continu 2020–2026, stress, six perturbations, compte London seul ; ouverture **unique** du test réservé après gel du robot (empreinte consignée) ; période 01/05–03/11/2026 en diagnostic ; comparaison V1 si D-15 est résolue | 13.3 | Rapport C10 ; « non validé » si un critère manque, sans retouche |
| 13.5 | Qualification sémantique A13 : 200 textes annotés par un humain, seuils `model_min_material_event_precision` et `model_min_material_event_recall`, zéro citation non vérifiée ; comparaison gratuit et payant seulement si le payant est configuré | Phase 12, annotateur humain | `QUALIFIE` ou `NON_QUALIFIE` par fournisseur |
| 13.6 | Collecte prospective `PAPER_AB` puis démonstration : effectifs minimaux de A13 et de C10 ; checklist go/no-go (`xp-bots-deployment-readiness`) ; le veto réel reste désactivé sans validation financière A13 ; le réel n'est décidé que par l'humain | 13.1 à 13.5 | Décision tracée de l'humain |

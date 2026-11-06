# Registre des coutures du squelette composite

> Squelette **hors protocole MCL** (règles de couture de la skill `mcl-matryoshka-construction-layers`) : code
> de production minimal, déployable dès la phase 1, jamais figé. Sa discipline : rester vert dans la suite
> locale complète (`python tools/run_london_tests.py`), rejouée à chaque gate, à chaque fin de phase et avant
> chaque commit (pas d'intégration continue distante, D-10). Segments décrits au
> [document 02, §3](../../docs/architecture/robot_london_v3/02_cartographie_mcl.md) ; carte composite :
> [plan MCL composite](../robot-london-v3/PLAN-MCL.md).

## 1. Coutures

Chaque artefact de chair remplace son segment en respectant le contrat ci-dessous. Toute modification d'un
contrat de couture est un changement tracé au §3 (date, nature, artefact, justification, test de bout en bout
vert).

| Segment | Module(s) | Contrat de la couture (entrée → sortie) | Comportement minimal | Propriétaire futur | Phase | Statut |
|---|---|---|---|---|---|---|
| S1 Source de ticks | `xpbots.infra.squelette` (`lire_lignes`, `lire_octets`, `lire_configuration`) ; `xpbots.rejeu.squelette` (`analyser_lignes_ticks`, `hypotheses_marche_squelette`) | Chemin d'un fichier CSV UTF-8 à en-tête `canonical_symbol,broker_symbol,time_utc_ms,sequence,bid,ask` → suite de `Tick` du noyau (`c1a_marche` : heures fournisseur et réception égales en rejeu, P-04 ; numéro = séquence) strictement ordonnée par instant puis séquence ; toute anomalie lève `ErreurDonnees` (sous-classe de `ValueError`). Hypothèse de marché : ticks → par symbole, `HorairesCotation` et périodes couvertes (`Intervalle` du noyau, `c1b_instrument`) | Lecture ligne à ligne, sans compression ; Bid et Ask finis et strictement positifs ; chaque symbole réputé coté et couvert de l'heure UTC pleine de son premier tick à l'heure pleine qui suit son dernier (aucun horaire de séance ni registre de trous historique) | `journal-rejeu` (analyse des ticks, registre de couverture et horaires historiques) ; `infrastructure` (lecteurs de fichiers et flux MT5) | 10, 11 | Minimal |
| S2 Bougies | `xpbots.donnees.c3_flux` (`FluxBougies`, artefact `london-donnees-temps`, figé) | `Tick` du noyau d'un symbole, dans l'ordre, avec horaires de cotation et source de couverture (1c) → `BougieEnrichie` M15 et H1 (`xpbots.donnees.c0a_types` : bougie du noyau valide ou invalide motivée, TR, ATR, A, rang, jour et heures de Londres, jour UTC), `ChangementTrou`, `AnomalieDonnees` ; contrat : [couche 3](../london-donnees-temps/contrats/couche-3.md) | Remplacé : C03 complet (tick de frontière, H1 à la clôture, intervalles vides invalides `AUCUN_BID`, trous signalés, jamais comblés, P-01 à P-03, P-10, reprise exacte) | `london-donnees-temps` | 3 | Remplacé |
| S3 Stratégie | `xpbots.london.squelette` (`StrategieMinimale`, `fabriquer_strategie(ConfigurationFigee)`) | Contrat structurel : attribut `identifiant` (`london.strategy_id`) et `sur_bougie(BougieEnrichie) → ResultatTechnique \| None` : un `ResultatTechnique` du noyau (`SignalTechnique` ou `AbsenceDeSignal`, `c1c_domaine`) pour chaque M15 close, valide ou non, et rien pour une H1 (reçue avant la M15 de même fin) | Toujours `NO_SETUP`, détail `SEGMENT_MINIMAL_S3`, pour une M15 ; rien pour une H1 | `moteur-london` | 4 | Minimal |
| S4 Coordinateur | `xpbots.execution.squelette` (`CoordinateurMinimal`, `Decision`, `CommandeEntree`, `CommandeCloture`) ; enchaînement `xpbots.orchestration.squelette` (`MoteurMinimal`, `fabriquer_moteur_minimal(strategie, ConfigurationFigee, mode, deploiement='squelette', *, horaires, periodes_couvertes)`) | `ResultatTechnique → Decision` (motif du noyau, détail, commandes) ; moteur : `traiter_tick(Tick) → SortieMoteur` (enregistrements `Enregistrement` du noyau, commandes), stratégie injectée (D-18), un `FluxBougies` par symbole construit sur `horaires[symbole]` et `RegistreCouverture(periodes_couvertes[symbole])`, déploiement `squelette`, bras `REFERENCE` ; symbole inconnu, mappages discordants ou résultat de stratégie hors contrat → `ValueError` | Tout signal refusé : enregistrement `INTENTION` d'issue `REFUSEE`, motif `ENVIRONMENT_NOT_READY`, détail `SEGMENT_MINIMAL_S4`, aucune commande ; une absence de signal garde son motif dans l'enregistrement `CLOTURE` ; changement d'état de trou et anomalie de données journalisés en `ALERTE` | `execution-coordinateur`, puis `orchestration` | 6, 9 | Minimal |
| S5 Exécution papier | `xpbots.rejeu.squelette` (`ExecutionPapierMinimale`, `rejouer`) | `soumettre(commandes)` ; `sur_tick(Tick) → réponses` (remplissage, sortie de protection, clôture, refus) ; boucle : exécution, puis moteur, puis soumission | Entrée au tick suivant, achat à l'Ask et vente au Bid, sans coût ; SL et TP contrôlés dès le tick suivant le remplissage, achat sur Bid et vente sur Ask ; clôture au tick suivant | `journal-rejeu` (simulateur C10) | 10 | Minimal |
| S6 Journal | Format : `xpbots.noyau.c2_journal` (`serialiser`, schéma `xp-journal-v1`, enveloppe du document 08, §7) ; écriture : `xpbots.infra.squelette` (`ecrire_journal`) | `Enregistrement` du noyau → ligne JSON canonique (clés triées, sans espace, UTF-8, aucun nombre non fini, décimaux en texte) → `<sortie>/decisions.jsonl` écrit par fichier temporaire puis remplacement | Un enregistrement `CLOTURE` par M15 close (bougie, validité et motif d'invalidité, indicateurs `tr`, `atr`, `a`, `rang` si elle est valide), un `INTENTION` par signal, un `ALERTE` par changement d'état de trou (`DATA_GAP`, `DEBUT` ou `FIN`) ou anomalie de données ; motifs et détails contrôlés par le noyau (P-07) | Format : `noyau` (fait, phase 2) ; écriture : `infrastructure` (journaux quotidiens) | 2, 11 | Format remplacé ; écriture minimale |
| S7 Point d'entrée | `xpbots.app.rejeu_squelette` (`main`) | `--ticks`, `--sortie`, `--racine-depot` (défaut `.`) → résumé JSON sur la sortie standard ; code 0 (rejeu complet), 1 (donnée, configuration ou fichier refusés, dont une empreinte d'export différente de la preuve de conservation ; message sur la sortie d'erreur ; aucun journal partiel), 2 (usage) | Composition : configuration figée chargée par le chargeur de production du noyau, ticks lus par l'infrastructure puis matérialisés, hypothèse de marché du squelette, moteur minimal, exécution papier, journal | `points-entree` | 11 | Minimal |

Types partagés des coutures : ceux du noyau figé (phase 2) — `Tick` et `Bougie` (`c1a_marche`), `HorairesCotation` et
`Intervalle` (`c1b_instrument`), `SignalTechnique`,
`AbsenceDeSignal`, `Motif`, `Sens`, `CleIntention`, `Issue` (`c1c_domaine`), `ConfigurationFigee` (`c0c_configuration`),
`Enregistrement` et `Enveloppe` (`c2_journal`). Ils ont remplacé les types minimaux de `xpbots.noyau.squelette`,
supprimé ; depuis la phase 3, `BougieEnrichie`, `UniteTemps`, `ChangementTrou` et `AnomalieDonnees` de
`london-donnees-temps` (`xpbots.donnees.c0a_types`), importables par `moteur-london` et `orchestration` seulement (carte
composite). `common.timeframe_seconds`, `common.h1_seconds`, `common.atr_period` et `london.strategy_id` sont lus
dans la configuration figée, jamais recopiés.

## 2. Test de bout en bout et commande de démonstration

- Test : `tests/robot/squelette/test_bout_en_bout.py`. Une journée Londres synthétique d'EURUSD (été et hiver),
  produite par la fabrique `tests/robot/outils/fabrique_ticks.py` dans un dossier temporaire, est rejouée par la
  vraie commande ; attendus : code de sortie nul, un enregistrement par bougie M15 close (96 pour une journée de
  24 heures), forme canonique, OHLC identiques aux bougies voulues, motif admis par C09. Il fait partie de la
  régression intégrale de chaque gate.
- Démonstration (PowerShell, depuis la racine du dépôt, avec un fichier de ticks au format canonique) :
  `$env:PYTHONPATH = "src"` puis
  `python -m xpbots.app.rejeu_squelette --ticks <fichier.csv> --sortie <dossier>`.

## 3. Journal des changements de couture

| Date | Segment | Nature | Artefact | Justification | Bout en bout |
|---|---|---|---|---|---|
| 05/11/2026 | S1 à S7 | Création | squelette | Phase 1 du plan : chemin de bout en bout minimal | Vert |
| 05/11/2026 | S1, S6 ; S3, S4, S7 par conséquence | Extension (types du noyau) | noyau | Phase 2 : types minimaux remplacés par ceux du noyau figé ; journal au schéma `xp-journal-v1` avec enveloppe et empreintes des règles ; signal refusé tracé par un enregistrement `INTENTION` ; S7 charge la configuration par le chargeur de production (option `--racine-depot` à la place de `--configuration`) | Vert |
| 06/11/2026 | S2 ; S1, S3, S4, S6, S7 par conséquence | Remplacement (S2) ; extension (S1, S3, S4, S6, S7) | london-donnees-temps | Phase 3 : `xpbots.donnees.squelette` supprimé, le moteur minimal passe par `FluxBougies` (un flux par symbole) ; contrat de stratégie `sur_bougie(BougieEnrichie)` (M15 et H1) au lieu de `sur_cloture(Bougie)` ; hypothèse de marché du squelette (horaires et couverture sur l'étendue du fichier, alignée sur H1) fournie par S1 et composée par S7 ; indicateurs dans `CLOTURE` ; trous et anomalies journalisés en `ALERTE` | Vert |

# Registre des coutures du squelette composite

> Squelette **hors protocole MCL** (règles de couture de la skill `mcl-matryoshka-construction-layers`) : code
> de production minimal, déployable dès la phase 1, jamais figé. Sa discipline : rester vert dans la suite
> locale complète (`python tools/run_robot_tests.py`), rejouée à chaque gate, à chaque fin de phase et avant
> chaque commit (pas d'intégration continue distante, D-10). Segments décrits au
> [document 02, §3](../../docs/architecture/robot_london_v3/02_cartographie_mcl.md) ; carte composite :
> [plan MCL composite](../robot-london-v3/PLAN-MCL.md).

## 1. Coutures

Chaque artefact de chair remplace son segment en respectant le contrat ci-dessous. Toute modification d'un
contrat de couture est un changement tracé au §3 (date, nature, artefact, justification, test de bout en bout
vert).

| Segment | Module(s) | Contrat de la couture (entrée → sortie) | Comportement minimal | Propriétaire futur | Phase | Statut |
|---|---|---|---|---|---|---|
| S1 Source de ticks | `xpbots.infra.squelette` (`lire_lignes`, `lire_octets`) ; `xpbots.rejeu.squelette` (`analyser_lignes_ticks`) | Chemin d'un fichier CSV UTF-8 à en-tête `canonical_symbol,broker_symbol,time_utc_ms,sequence,bid,ask` → suite de `Tick` (symbole, symbole du courtier, instant UTC en ms, séquence, Bid, Ask) strictement ordonnée par instant puis séquence ; toute anomalie lève `ErreurDonnees` | Lecture ligne à ligne, sans compression ; Bid et Ask finis et strictement positifs | `journal-rejeu` (analyse des ticks) ; `infrastructure` (lecteurs de fichiers et flux MT5) | 10, 11 | Minimal |
| S2 Agrégation | `xpbots.donnees.squelette` (`AgregateurM15`) | `Tick` d'un symbole, dans l'ordre → `Bougie` Bid close `[debut, fin)` de durée `common.timeframe_seconds`, rendue par le premier tick d'instant ≥ fin (tick de frontière, C03.2) | OHLC du Bid, sans H1, sans indicateur, sans traitement des trous ni des intervalles vides | `donnees-temps` | 3 | Minimal |
| S3 Stratégie | `xpbots.london.squelette` (`StrategieMinimale`, `fabriquer_strategie`) | Contrat structurel : attribut `identifiant` (`london.strategy_id`) et `sur_cloture(Bougie) → ResultatTechnique` (sens, ou motif et détail) | Toujours `NO_SETUP`, détail `SEGMENT_MINIMAL_S3` | `moteur-london` | 4 | Minimal |
| S4 Coordinateur | `xpbots.execution.squelette` (`CoordinateurMinimal`, `Decision`, `CommandeEntree`, `CommandeCloture`) ; enchaînement `xpbots.orchestration.squelette` (`MoteurMinimal`, `fabriquer_moteur_minimal`) | `ResultatTechnique → Decision` (motif, détail, commandes) ; moteur : `traiter_tick(Tick) → SortieMoteur` (enregistrements, commandes), stratégie injectée (D-18), un agrégateur par symbole | Tout signal refusé : `ENVIRONMENT_NOT_READY`, détail `SEGMENT_MINIMAL_S4`, aucune commande ; un résultat sans signal garde son motif | `execution-coordinateur`, puis `orchestration` | 6, 9 | Minimal |
| S5 Exécution papier | `xpbots.rejeu.squelette` (`ExecutionPapierMinimale`, `rejouer`) | `soumettre(commandes)` ; `sur_tick(Tick) → réponses` (remplissage, sortie de protection, clôture, refus) ; boucle : exécution, puis moteur, puis soumission | Entrée au tick suivant, achat à l'Ask et vente au Bid, sans coût ; SL et TP contrôlés dès le tick suivant le remplissage, achat sur Bid et vente sur Ask ; clôture au tick suivant | `journal-rejeu` (simulateur C10) | 10 | Minimal |
| S6 Journal | `xpbots.noyau.squelette` (`serialiser_enregistrement`) ; `xpbots.infra.squelette` (`ecrire_journal`) | Enregistrement `CLOTURE` (schéma `squelette-1` : type, mode, numéro, instant, stratégie, symbole, bougie, signal, motif, détail) → ligne JSON canonique (clés triées, sans espace, UTF-8, aucun nombre non fini) → `<sortie>/decisions.jsonl` écrit par fichier temporaire puis remplacement | Un enregistrement par bougie close ; motif admis par C09 (P-07) | `noyau` (format complet du document 08, §7) puis `infrastructure` (journaux quotidiens) | 2, 11 | Minimal |
| S7 Point d'entrée | `xpbots.app.rejeu_squelette` (`main`) | `--configuration`, `--ticks`, `--sortie` → résumé JSON sur la sortie standard ; code 0 (rejeu complet), 1 (donnée ou fichier refusé, message sur la sortie d'erreur, aucun journal partiel), 2 (usage) | Composition : configuration et ticks lus par l'infrastructure, moteur minimal, exécution papier, journal | `points-entree` | 11 | Minimal |

Types partagés des coutures (`Tick`, `Bougie`, `ResultatTechnique`, `ConfigurationSquelette`, `ErreurDonnees`) :
`xpbots.noyau.squelette`, remplacés en phase 2 par extension tracée de S1 et S6. La configuration minimale lit
`common.timeframe_seconds` et `london.strategy_id` dans l'export figé, jamais recopiés.

## 2. Test de bout en bout et commande de démonstration

- Test : `tests/robot/squelette/test_bout_en_bout.py`. Une journée Londres synthétique d'EURUSD (été et hiver),
  produite par la fabrique `tests/robot/outils/fabrique_ticks.py` dans un dossier temporaire, est rejouée par la
  vraie commande ; attendus : code de sortie nul, un enregistrement par bougie M15 close (96 pour une journée de
  24 heures), forme canonique, OHLC identiques aux bougies voulues, motif admis par C09. Il fait partie de la
  régression intégrale de chaque gate.
- Démonstration (PowerShell, depuis la racine du dépôt, avec un fichier de ticks au format canonique) :
  `$env:PYTHONPATH = "src"` puis
  `python -m xpbots.app.rejeu_squelette --configuration config/parametres_figes_v3.json --ticks <fichier.csv> --sortie <dossier>`.

## 3. Journal des changements de couture

| Date | Segment | Nature | Artefact | Justification | Bout en bout |
|---|---|---|---|---|---|
| 05/11/2026 | S1 à S7 | Création | squelette | Phase 1 du plan : chemin de bout en bout minimal | Vert |

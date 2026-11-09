# Registre des coutures du squelette composite

Phase 7, 09/11/2026 — extension S4/S5/S6/S7 : le port réel `PermissionsFondamentales` remplace le
neutre implicite dans la composition Python. Celle-ci exige un port réel ou le scénario explicite
TECHNICAL_CONTROL_NEUTRAL ; ces choix sont exclusifs. Une source de paquets synthétiques, seule
frontière doublée, injecte les octets D-11/D-12 aux heures de réception déclarées. Ses échéances et
celles de C05 (heartbeat, expiration, annonce connue) rejoignent la minuterie du coordinateur sans
créer de cotation ni bougie. Les réceptions précèdent le suivi du même instant ; les faits natifs
restent traités avant les décisions du coordinateur. Le journal conserve les permissions et versions
réellement connues et les alertes de réception/heartbeat/expiration. La CLI conserve son choix neutre
explicite ; la lecture physique des fichiers C05 reste en phase 11. Vérification : scénarios de couture
`tests/robot/squelette/test_fondamental.py`, dont L-14 au vrai moteur London.

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
| S3 Stratégie | `xpbots.london.c2_moteur` (`MoteurLondon`, `StrategieLondon`, `fabriquer_strategie(ConfigurationFigee, tailles_tick)`) | Contrat structurel : `identifiant`, `sur_bougie(BougieEnrichie) → ResultatTechnique \| None`, `sur_issue(Issue) → None` ; un résultat par nouvelle M15, rien pour H1 ou issue, aucune réévaluation d’une M15 ancienne ; tailles de tick `Decimal` explicites par symbole | Remplacé : S02 complet, état indépendant par symbole, range exact, gel H1 causal immuable, stop local, quotas au premier fill non nul ; [contrat](../moteur-london/contrats/couche-2.md) | `moteur-london` | 4 | Remplacé |
| S4 Coordinateur | `xpbots.execution.c6_coordinateur` (`CoordinateurCompte`) ; couture pure `xpbots.orchestration.squelette` | Signaux, cotations et réponses C08 → `LotCoordinateur` ; `SortieMoteur` porte journal, commandes et lot ; coordinateur réel et profils injectés dans la fabrique ; port C05 réel, source externe scénarisée et minuteries heartbeat/expiration/annonce ; `traiter_ticks` groupe un même instant, `traiter_evenement` traite les minuteries, `confirmer_persistance` autorise l'entrée | Remplacé : réponses natives et issues avant bougies, sorties avant admissions, arbitrage de toutes les intentions simultanées ; préparation distincte de l'envoi après preuve de persistance et revalidation ; une seule clé par intention, ses mises à jour C09 et les traces C08 ; aucun import de moteur dans l'orchestration (D-18) | Coordinateur commun construit ; orchestration complète future | 6, 9 | Coordinateur remplacé ; enchaînement minimal |
| S5 Exécution papier | `xpbots.rejeu.squelette` (`ExecutionPapierMinimale`, `ContratPapier`, `StockageMemoirePapier`, `rejouer`, `PaquetFondamental`, `SourceFondamentaleScenario`) | Vraies `CommandeExecution` → `ReponseCourtier` ou `ObservationNative` ; port `CalculCourtier` synthétique USD ; compte et historique complets ; observation SL/TP actuels | Contrat et grille de volume explicitement fournis ; point=tick, IOC, frais et swaps nuls connus, marge à levier constant ; ACK sans quota, fill au prochain tick (Ask achat/Bid vente), SL/TP natifs avant clôture en attente ; échéances C05 et C08 simulées sans nouvelle cotation ; arrivées D-11/D-12 à la réception déclarée ; preuve de transaction mémoire, panne de stockage interdit l'entrée mais laisse les sorties ; aucune durabilité physique ni simulation C10 | `journal-rejeu` (simulateur C10) | 10 | Minimal adapté à C08 |
| S6 Journal | Format : `xpbots.noyau.c2_journal` (`serialiser`, schéma `xp-journal-v1`, enveloppe du document 08, §7) ; écriture : `xpbots.infra.squelette` (`ecrire_journal`) | `Enregistrement` du noyau → ligne JSON canonique (clés triées, sans espace, UTF-8, aucun nombre non fini, décimaux en texte) → `<sortie>/decisions.jsonl` écrit par fichier temporaire puis remplacement | Un enregistrement `CLOTURE` par M15 close (bougie, validité et motif d'invalidité, indicateurs `tr`, `atr`, `a`, `rang` si elle est valide), des mises à jour `INTENTION` par clé persistante et des traces ORDRE, REPONSE, EXECUTION, PROTECTION, RESERVATION, RAPPROCHEMENT et CLOTURE_POSITION, permissions et versions réellement connues ; alertes C05 de réception, heartbeat et expiration ; un `ALERTE` par changement d'état de trou (`DATA_GAP`, `DEBUT` ou `FIN`) ou anomalie de données ; motifs et détails contrôlés par le noyau (P-07) | Format : `noyau` (fait, phase 2) ; écriture : `infrastructure` (journaux quotidiens) | 2, 11 | Format remplacé ; écriture minimale |
| S7 Point d'entrée | `xpbots.app.rejeu_squelette` (`main`, `composer_rejeu_papier`) | `--ticks`, `--sortie`, `--racine-depot` ; `--tick-size SYMBOLE=DECIMAL` et `--contrat-papier SYMBOLE=TAILLE,MIN,MAX,PAS` exactement par symbole ; `--scenario TECHNICAL_CONTROL_NEUTRAL` obligatoire ; résumé JSON et journal canonique ; codes 0/1/2 conservés | Composition du vrai moteur London, flux et coordinateur via la fabrique d'orchestration ; profils et compte synthétiques déclarés, stockage mémoire ; résumé compte fills, clôtures et positions ouvertes ; aucune qualification de compte réel | `points-entree` | 11 | Minimal adapté |

Types partagés des coutures : ceux du noyau figé (phase 2) — `Tick` et `Bougie` (`c1a_marche`), `HorairesCotation` et
`Intervalle` (`c1b_instrument`), `SignalTechnique`,
`AbsenceDeSignal`, `Motif`, `Sens`, `CleIntention`, `Issue` (`c1c_domaine`), `ConfigurationFigee` (`c0c_configuration`),
`Enregistrement` et `Enveloppe` (`c2_journal`). Ils ont remplacé les types minimaux de `xpbots.noyau.squelette`,
supprimé ; depuis la phase 3, `BougieEnrichie`, `UniteTemps`, `ChangementTrou` et `AnomalieDonnees` de
`london-donnees-temps` (`xpbots.donnees.c0a_types`), importables par `moteur-london` et `orchestration` seulement (carte
composite). `common.timeframe_seconds`, `common.h1_seconds`, `common.atr_period` et `london.strategy_id` sont lus
dans la configuration figée, jamais recopiés.

## 2. Test de bout en bout et commande de démonstration

- Test : `tests/robot/squelette/test_bout_en_bout.py`. Journées EURUSD d'été et d'hiver avec
  préchargement complet, vrais signaux S02, ordres protégés, premier fill et clôture native ; OHLC exacts,
  journal canonique et numéros continus. Un second essai présente GBPUSD avant EURUSD au même instant
  et vérifie la priorité EURUSD des demandes, indépendante de l'ordre d'arrivée.
- Démonstration PowerShell : `$env:PYTHONPATH = "src"`, puis
  `python -m xpbots.app.rejeu_squelette --ticks <fichier.csv> --sortie <dossier> --tick-size EURUSD=0.00001 --contrat-papier EURUSD=1000,0.1,1,0.1 --scenario TECHNICAL_CONTROL_NEUTRAL`.
  Les paramètres de cette commande sont des hypothèses de fixture. Le marché est réputé couvert sur
  l'étendue H1 du fichier ; la validité du relevé d'horaires dépasse cette étendue d'une H1 afin de
  connaître la fermeture de séance. Aucun coût de stress ni permission historique n'est simulé.

## 3. Journal des changements de couture

| Date | Segment | Nature | Artefact | Justification | Bout en bout |
|---|---|---|---|---|---|
| 05/11/2026 | S1 à S7 | Création | squelette | Phase 1 du plan : chemin de bout en bout minimal | Vert |
| 05/11/2026 | S1, S6 ; S3, S4, S7 par conséquence | Extension (types du noyau) | noyau | Phase 2 : types minimaux remplacés par ceux du noyau figé ; journal au schéma `xp-journal-v1` avec enveloppe et empreintes des règles ; signal refusé tracé par un enregistrement `INTENTION` ; S7 charge la configuration par le chargeur de production (option `--racine-depot` à la place de `--configuration`) | Vert |
| 06/11/2026 | S2 ; S1, S3, S4, S6, S7 par conséquence | Remplacement (S2) ; extension (S1, S3, S4, S6, S7) | london-donnees-temps | Phase 3 : `xpbots.donnees.squelette` supprimé, le moteur minimal passe par `FluxBougies` (un flux par symbole) ; contrat de stratégie `sur_bougie(BougieEnrichie)` (M15 et H1) au lieu de `sur_cloture(Bougie)` ; hypothèse de marché du squelette (horaires et couverture sur l'étendue du fichier, alignée sur H1) fournie par S1 et composée par S7 ; indicateurs dans `CLOTURE` ; trous et anomalies journalisés en `ALERTE` | Vert |
| 06/11/2026 | S3 ; S4 et S7 par conséquence | Remplacement (S3) ; extension (S4, S7) | moteur-london | Phase 4 : segment London minimal supprimé ; vraie fabrique S02 injectée ; protocole étendu par `sur_issue`, appelée après chaque refus ; taille de tick explicite par symbole sur S7, hypothèse remplacée ultérieurement par le profil C04 ; bout en bout sur ticks avec préchargement et au moins une vraie cassure refusée, aucun quota consommé | Vert |
| 07/11/2026 | Aucun | Calculs purs seulement | london-execution-coordinateur | Phase 5 : onze couches communes figées ; S4 reste `CoordinateurMinimal`, les vraies cassures S3 sont toujours refusées sans ordre ; couture prévue en phase 6 | Vert, 35 tests du squelette |
| 08/11/2026 | S4 ; S1, S5, S6, S7 par conséquence | Remplacement S4 et modification de couture | london-execution-coordinateur | Phase 6 : segment `xpbots.execution.squelette` supprimé, coordinateur C08 réel, profils et contrat papier explicites, preuve mémoire avant envoi ; minuteries causales, réponses avant décisions et groupes simultanés ; 37 tests du squelette | Vert |
| 09/11/2026 | S4, S5, S6, S7 | Extension C05 | london-controles-fondamentaux | Port réel obligatoire hors neutre explicitement choisi ; paquets D-11/D-12 à leur réception, calendrier et permissions causaux dans C09, heartbeat et expiration sans tick ; FLATTEN, annonce tardive, revalidation avant envoi et L-14 réel été/hiver | Vert, 49 tests du squelette |
| 09/11/2026 | S4 | Correction de reprise | london-controles-fondamentaux | Le temps initial du moteur est celui du coordinateur, même avec un contrôle C05 restauré plus ancien ; ses alertes échues sont observées au démarrage sans recul du papier ; état C05 futur refusé | Test de reprise et mutation dédiée |

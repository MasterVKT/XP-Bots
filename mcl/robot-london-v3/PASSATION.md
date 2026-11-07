# Rapport de passation — robot London (`LONDON_V3`), reprise à la phase 6

> Mis à jour le 07/11/2026 à la fin de la phase 5, à l'intention de l'agent qui reprend l'exécution du plan dans une
> autre session, éventuellement avec un autre modèle ou un autre outil. Son but : que la suite soit construite
> exactement selon la logique, la rigueur et les conventions des phases 0 à 5. Ce rapport est un **contexte de
> reprise**, pas une source normative : en cas d'écart avec les spécifications, les exports figés, le plan ou le
> code réel, ce sont eux qui prévalent, et l'écart se signale (plan directeur, §0).

## 0. Fiche de passation

| Élément | Valeur |
|---|---|
| Dépôt | `MasterVKT/XP-Bots` |
| Branche de travail | `master`, après intégration en coexistence structurée (`5e5e288`) ; les commits `9c39d23` et `70c60d9` sont présents ; phase 4 `85069c0` ; le commit de phase 5 porte cette mise à jour |
| Plan suivi | [Plan directeur 1.4.6](../../docs/architecture/robot_london_v3/README.md), documents 01 à 08 du même dossier |
| Phases terminées | 0, 1, 2, 3, 4 et 5 ; état et publication vérifiables dans le journal Git |
| Prochaine action | **Phase 6 — cycle d’ordre, sorties, reprise, couches 4 à 6**, seulement sur demande explicite ; poursuivre le dossier actif `london-execution-coordinateur`, arbitrage R4/R5 déjà consigné |
| Suite du robot | 613 tests verts des deux lignées ; 80 propres au coordinateur (71 catégorie 1, 9 catégorie 2), 79 au moteur London, 35 au squelette |
| Contrôles | Régression intégrale, ressources métier, plan London, gouvernance et cartes strictes : preuves de phase 5 dans [le bilan](../london-execution-coordinateur/PLAN-MCL.md) et le journal MCL |
| Environnement vérifié | Python 3.13 ; `numpy` 2.4.1, `pandas` 3.0.0, `tzdata` 2025.3 (`requirements-dev.txt`, tests seulement) ; aucun accès réseau requis |

## 1. Résumé exécutif

Le robot 2 (London Breakout M15, `LONDON_V3`) se construit en Python, dans le paquet unique `src/xpbots/`, selon
la méthode **MCL** (couches construites de l'intérieur vers l'extérieur, chacune contractualisée, testée, passée
au gate de régression intégrale puis figée). Le plan compte 14 phases (0 à 13) ; l'humain demande chaque phase
explicitement et l'agent s'arrête à la fin de chacune. Les phases 0 à 3 ont posé la carte composite, un squelette
de bout en bout déployable, le noyau partagé figé (types, configuration figée, journal C09) et l'artefact
`london-donnees-temps` figé (bougies M15 et H1 causales, validées, enrichies de TR, ATR, A_t, du rang de préchargement et
des repères de Londres, avec reprise exacte). La phase 4 a ajouté `moteur-london`, huit couches figées, et
remplacé S3 : de vraies cassures sont journalisées puis refusées sans ordre par le coordinateur minimal. La
phase 5 a figé les onze couches pures du coordinateur commun, après arbitrage R4/R5. La phase 6 construira le cycle d’ordre, les sorties et la reprise, puis remplacera S4.

## 2. Mission et règle d'exécution

1. Exécuter **une phase à la fois**, dans l'ordre du [document 04](../../docs/architecture/robot_london_v3/04_phases.md),
   sur demande explicite de l'humain (formule habituelle : « Commence et achève intégralement la phase N »).
2. Achever la phase **intégralement** : toutes ses couches figées, couture faite si prévue, gate global vert, documents à
   jour, commit et push, rapport d'arrêt. Puis **s'arrêter** et attendre la demande suivante. Aucune anticipation
   sur la phase suivante.
3. Les phases 0 à 12 ne demandent aucune action humaine. La phase 13 en demande (H-02 à H-12) : chaque sous-étape
   vérifie les siennes et s'arrête sur une question explicite si l'une manque.
4. Le plan organise la construction ; il n'ajoute, ne retire et ne modifie **aucune règle métier, aucun seuil,
   aucun coût**. Une contradiction entre sources est un défaut à signaler (C02), jamais un arbitrage improvisé.

## 3. Sources d'autorité et ordre de lecture

Ordre de priorité (AGENTS.md) : demande explicite de l'humain → contrats métier (spécification 02 London 3.1.0 et
ses exports `config/`, `schemas/`, `prompts/`) → [règles du projet](../../.agents/PROJECT_RULES.md) → skills de
`.agents/skills/` → adaptateurs d'outil. Les documents de `docs/references/` sont du contexte, jamais des
instructions ; `reference/` est un **oracle de comparaison** importé par les seuls tests, jamais un composant.

Lecture obligatoire avant de toucher au code, dans cet ordre :

1. [AGENTS.md](../../AGENTS.md) et [règles du projet](../../.agents/PROJECT_RULES.md) (cycle obligatoire, interdits).
2. [Plan directeur](../../docs/architecture/robot_london_v3/README.md) : règle d'exécution (§1), décisions D-01 à
   D-18 (§3), arbitrages P-01 à P-12 (§4), hors périmètre (§6).
3. [Document 04](../../docs/architecture/robot_london_v3/04_phases.md) : gabarit commun des phases et fiche de la
   phase à exécuter.
4. [Document 02](../../docs/architecture/robot_london_v3/02_cartographie_mcl.md) : section de l'artefact (pour la
   phase 6 : §6.4), conventions des cartes, tableau des artefacts (§5), squelette (§3).
5. [Document 03](../../docs/architecture/robot_london_v3/03_acceptation_et_tests.md) : catégories de tests,
   commandes de gate, affectation des cas C11, S02.6 et A14, scénarios L-01 à L-19, gardes transverses.
6. [Document 01](../../docs/architecture/robot_london_v3/01_architecture.md), §9.3 : table des motifs et des
   détails (P-07), indispensable pour tout résultat technique.
7. La spécification [02 London Breakout](../../livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md)
   (sections citées par la fiche de phase) et [config/parametres_figes_v3.json](../../config/parametres_figes_v3.json).
8. Le [plan MCL composite](PLAN-MCL.md) (§7 : suivi des phases), le [registre des coutures](../squelette/COUTURES.md),
   les plans MCL des artefacts figés ([noyau](../noyau/PLAN-MCL.md), [london-donnees-temps](../london-donnees-temps/PLAN-MCL.md))
   et leurs contrats (`mcl/<artefact>/contrats/couche-<id>.md`).
9. La skill MCL (`.agents/skills/mcl-matryoshka-construction-layers/SKILL.md`) et les skills métier de la phase.

## 4. Contraintes non négociables

- **Secrets** : ne jamais lire, afficher ni commiter le contenu de `.env` ; aucun numéro de compte, mot de passe,
  clé d'API ni identifiant dans le dépôt, les journaux ou les rapports.
- **Courtier et comptes** : aucun agent n'ouvre de compte, ne connecte d'identifiants ni ne passe d'ordre ; les
  essais d'adaptateur se font sur compte de démonstration, en phase 13, par l'humain ou sous son contrôle.
- **Valeurs figées** : ne jamais modifier `config/`, les sections normatives des spécifications, `schemas/`,
  `prompts/`, les preuves de `docs/validation/`, les empreintes de conservation ni l'archive ZIP de MCL. Les
  seuils se lisent dans la configuration chargée ; ils ne sont jamais recopiés dans le code.
- **Dépendances** : bibliothèque standard seulement dans `src/xpbots/` ; `MetaTrader5` est la seule dépendance
  d'exécution autorisée (D-05, phase 11, roues Windows, remplacée par un faux module dans le conteneur) ;
  `numpy`, `pandas`, `tzdata` restent réservés aux tests et oracles. Aucune nouvelle dépendance, aucun framework,
  aucun `pytest` (D-04).
- **Refus arrêtés** : intégration continue distante refusée (D-10) ; appels réels aux API LLM refusés (D-17,
  autorisation redemandée seulement au début de 13.6).
- **Données** : aucune donnée réelle de prix commitée ; fixtures synthétiques générées par du code de test ;
  tout fichier téléchargé est non fiable (dossier isolé, Python lancé avec `-I`).
- **Tests** : déterministes (aucune horloge, aucun réseau, aucun hasard non semé) ; écriture uniquement dans des
  dossiers temporaires du système, jamais dans l'arbre suivi (l'empreinte d'arbre du gate MCL en dépend).
- **Contrats figés** : un fichier listé dans le champ `contrats` d'une couche figée ne change que par
  `mcl.py defiger` (nature `correction`, `extension` ou `modification`), suivi d'un nouveau gate et d'un nouveau gel.
- **Skills** : ne s'éditent que dans `.agents/skills/` ; les copies `.claude/skills/` se régénèrent par
  `python .agents/hooks/skill_mirrors.py --write` ; une nouvelle skill passe par
  `.agents/skills/xp-bots-skill-gap-detector/scripts/create_skill.py`.
- **Git** : travailler sur la branche que désigne la session (à défaut celle de la fiche §0), sans
  réécriture d'historique ; `git push -u origin <branche>`, avec nouvelles tentatives à 2, 4, 8 et 16 s en cas
  d'erreur réseau seulement ; **aucune pull request** sans demande explicite ; aucun identifiant de modèle dans
  les commits, le code ou les documents ; lignes d'attribution des commits : celles que fixe l'environnement de
  la session.
- **Rentabilité** : réussir des contrôles hors ligne ne prouve rien sur la rentabilité ; ne jamais présenter le
  code de référence comme opérationnel ni un composant comme existant sans l'avoir vu dans le code.

## 5. Préférences de l'humain

- Répondre **en français**, sans jargon inutile, en commençant par le résultat.
- Économiser les jetons de sortie sans altérer la qualité : réponses denses, pas de récapitulatifs redondants.
- Dans toute documentation : prose descriptive et explicative, complète et sans ambiguïté ; du code seulement là
  où il est réellement indispensable (une commande, une signature).
- Ne poser une question de clarification que si elle est réellement nécessaire ; sinon prendre la décision la
  plus conforme au plan, la consigner et avancer.
- Le rapport d'arrêt de chaque phase suit la forme décrite au §8.8 et se termine par l'invitation explicite à
  demander la phase suivante.

## 6. État exact du dépôt

### 6.1 Phases

| Phase | Commit | Contenu |
|---|---|---|
| 0 | `21854b1` | Dossier MCL composite `mcl/robot-london-v3/` (carte au grain des paquets, divergence stricte) ; guide et règles alignés sur D-01, D-02 |
| 1 | `6821747` | Squelette composite S1 à S7, lanceur `tools/run_london_tests.py`, fabrique de ticks, test de bout en bout, gardes de pureté et de carte |
| 2 | `7d22b6f` | Artefact `noyau` figé (7 couches) ; couture S1, S6 ; défigeages `correction` de la couche 2 |
| 3 | `70c60d9` | Artefact `london-donnees-temps` figé (8 couches) ; couture S2 ; défigeage `extension` de 1a et `correction` de 2b ; 24 mutations détectées |
| 4 | `85069c0` | Artefact `moteur-london` figé (8 couches), checkpoint après le niveau 1 et couture S3 ; protocole `sur_issue` et taille de tick explicite ; mutations et défigeages éventuels au bilan de l’artefact |
| 5 | Commit portant ce rapport | Onze couches pures communes figées, checkpoints 1 et 3 ; adaptation EMA, gardes, risque, arbitrage et dimensionnement ; aucune couture S4 ; bilan et mutations dans le dossier actif |

### 6.2 Carte composite (`mcl/robot-london-v3/carte.json`, divergence stricte)

Couches au grain des paquets : 0 `noyau` (`xpbots.noyau`) ; 1 `london-donnees-temps` (`xpbots.donnees`) ;
2a `moteur-london` (`xpbots.london`) ∥ 2b `execution-coordinateur` (`xpbots.execution`) ; 3a
`controles-fondamentaux` ∥ 3b `contexte-ia` ∥ 3c `infrastructure` ; 4a `orchestration` ∥ 4b `service-ia` ; 5
`journal-rejeu` ; 6 `points-entree`. Dépendances autorisées : `moteur-london` → noyau, london-donnees-temps ;
`execution-coordinateur` → noyau, london-donnees-temps ; `orchestration` → noyau, london-donnees-temps, execution,
fondamental, contexte_ia (**jamais** `xpbots.london`, D-18) ; `journal-rejeu` → noyau, execution, orchestration,
london ; `points-entree` → noyau, orchestration, journal-rejeu, infrastructure, london. Seule l'orchestration
peut importer `xpbots.donnees` parmi les couches supérieures à 2 ; `journal-rejeu` et `points-entree` ne le
peuvent pas. Frontières : `MetaTrader5` → 3c ; `sqlite3`, fichiers, horloge, fils → 3c et 4b ; réseau → 4b ;
hasard → 5 ; processus et `reference` → aucune couche. Le test transverse `test_carte_composite.py` vérifie la
carte composite et **toutes** les cartes `mcl/*/carte.json` sans avertissement : une nouvelle carte est donc
contrôlée automatiquement.

### 6.3 Interfaces publiques disponibles (figées)

Noyau (`xpbots.noyau.*`) :

- `c0a_temps` : instants UTC en millisecondes entières (`aligner`, conversions ISO et `datetime`, `verifier_instant`,
  `CleEvenement`, `ErreurInstant`).
- `c0b_nombres` : décimaux et arrondis sur grille (`decimal_depuis`, `arrondir_sur_grille`, `est_sur_grille`,
  `Arrondi`, `EPSILON_GRILLE`, `ErreurNombre`).
- `c0c_configuration` : `charger_configuration_figee(octets_technique, octets_ia, octets_preuve)` → `ConfigurationFigee(technique, ia)` ;
  `ExportTechnique(commun, london, ema, empreinte_octets, empreinte_canonique)` ; `ParametresCommuns` (73 clés typées
  de `common`) ; `london` reste un `Mapping` brut, typé par `charger_parametres_london` en phase 4 ; `ErreurConfiguration`.
- `c1a_marche` : `Tick(symbole, symbole_courtier, instant_fournisseur_ms, instant_reception_ms, numero, bid, ask, drapeaux=0)`,
  `Cotation`, `cotation_depuis_tick`, `Bougie(symbole, debut_ms, duree_ms, ouverture, haut, bas, cloture,
  nombre_evenements, valide, motif_invalidite, instant_disponibilite_ms)` avec `fin_ms`.
- `c1b_instrument` : `Intervalle`, `HorairesCotation(seances, fermetures, debut_validite_ms, fin_validite_ms)`,
  `ProfilInstrument` (dont `tick_size: Decimal`), `ProfilCompte`, `construire_profil_*` (liste
  `ENVIRONMENT_NOT_READY` si un champ manque).
- `c1c_domaine` : `Motif` (22 codes de C09 et P-07), `DETAILS_ENUMERES` (détails admis par motif, `VERSION_DETAILS`),
  `Sens`, `SignalTechnique(strategie, symbole, cloture_ms, sens, cloture_prix, atr_reference, stop_technique,
  multiple_objectif, contexte)`, `AbsenceDeSignal(strategie, symbole, cloture_ms, motif, detail, contexte)`,
  `ResultatTechnique`, `CleIntention`, `Issue(cle, nature, instant_ms, motif, detail, cause)`, `NatureIssue`,
  `CauseCloture`, décisions fondamentale et IA, `verifier_motif`.
- `c2_journal` : schéma `xp-journal-v1`, `Enveloppe`, `Enregistrement`, `TypeEnregistrement` (dont `CLOTURE`,
  `INTENTION`, `ALERTE`), `enregistrement_cloture`, `enregistrement_intention`, `enregistrement`, `serialiser`
  (JSON canonique), `empreintes_regles`.

Données (`xpbots.donnees.*`) :

- `c0a_types` : `BougieEnrichie(bougie, unite, indicateurs, jour_londres, ouverture_locale, cloture_locale, jour_utc)`,
  `UniteTemps` (M15, H1), `IndicateursBougie(tr, atr, a, rang)`, `IdentitePrechargement`, `ChangementTrou`,
  `NatureTrou`, `AnomalieDonnees`, `StatutCouverture`, `ErreurDonneesTemps`.
- `c0b_sessions` : `CalendrierLondres.depuis_parametres(commun)` avec `jour_local`, `datetime_local`, `jour_actif`,
  `instant_local`, `ouvertures(jour, debut, fin_exclue, duree_ms)` (ouvertures du range), `decision_dans_fenetre`
  (sémantique exacte de `local_decision_in_window`), `jour_utc`, `dans_blackout`, `prochain_debut_blackout`.
- `c1a` à `c2b` : constructeur, indicateurs, couverture, validation et chaîne (utilisés par la couche 3).
- `c3_flux` : `FluxBougies(symbole, technique, horaires, couverture)` avec `sur_tick(tick)` → bougies enrichies M15
  et H1, `ChangementTrou`, `AnomalieDonnees` ; H1 émise avant la M15 de même fin ; `exporter_etat()` et
  `FluxBougies.reprendre(...)` ; `en_trou`, `identite(unite)`, `calendrier`.

### 6.4 Squelette actuel (registre des coutures à jour)

- S1 : `xpbots.rejeu.squelette.analyser_lignes_ticks` et `hypotheses_marche_squelette` (marché réputé coté et
  couvert sur l'étendue du fichier, alignée sur H1) ; lecture par `xpbots.infra.squelette`.
- S2 : **remplacé** par `FluxBougies` (un flux par symbole dans le moteur minimal).
- S3 : **remplacé** par `xpbots.london.c2_moteur` (`MoteurLondon`, `StrategieLondon`,
  `fabriquer_strategie(configuration, tailles_tick)`) ; un moteur par symbole, taille `Decimal` explicite,
  vrai signal S02 ou motif à chaque nouvelle M15 ; rien pour H1 ou issue ; aucune réévaluation d’une M15 ancienne.
- S4 : `xpbots.orchestration.squelette.MoteurMinimal` et `fabriquer_moteur_minimal(strategie, configuration, mode,
  deploiement='squelette', *, horaires, periodes_couvertes)` ; protocole structurel `Strategie` (attribut
  `identifiant`, méthodes `sur_bougie` et `sur_issue`, contrôlées structurellement) ; `CoordinateurMinimal` refuse tout signal (`ENVIRONMENT_NOT_READY`,
  `SEGMENT_MINIMAL_S4`, issue transmise à la stratégie) ; `CLOTURE` par M15 avec indicateurs, `INTENTION` par signal, `ALERTE` par trou ou anomalie.
- S5 : exécution papier minimale ; S6 : journal canonique écrit par `ecrire_journal` ; S7 :
  `python -m xpbots.app.rejeu_squelette --ticks <csv> --sortie <dossier> --tick-size EURUSD=0.00001 [--racine-depot .]` ; répéter `--tick-size` pour chaque symbole synthétique présent.

### 6.5 Interfaces London disponibles (figées)

`xpbots.london.c0a_parametres` expose `ParametresLondon` et `charger_parametres_london` ; `c0b_types`
porte les valeurs immuables et `ErreurLondon`. Les unités de niveau 1 exposent `construire_range`,
`construire_gel`, `evaluer_cassure`, `calculer_stop` et `QuotasLondon`. L'enveloppe `c2_moteur` expose
`MoteurLondon`, `StrategieLondon` et `fabriquer_strategie(configuration, tailles_tick)`.
Les signatures, refus et garanties exacts sont dans les [contrats de moteur-london](../moteur-london/PLAN-MCL.md).
Une issue `REMPLIE` suppose un premier volume effectivement non nul ; aucun volume n'existe dans `Issue`.
La propriété d'une position persiste au changement de jour jusqu'à sa clôture explicite.

### 6.6 Coordinateur commun : interfaces de phase 5 disponibles

Les onze paquets `xpbots.execution.c0a_types` à `c3_dimensionnement` sont suivis dans
[le dossier actif](../london-execution-coordinateur/PLAN-MCL.md), avec leurs contrats figés.
`CalculCourtier` sépare profit, frais aller-retour, frais de sortie, marge isolée, contrôle natif total,
spécifications et état du compte. `GardesCompte` exporte ses arrêts et références de flux ; la reprise
P-12 exige une preuve du livre complet et d’absence de position à minuit. `RegistreReservations`
préserve le risque initial, déduplique les positions par clé et bloque l’externe. Il est sérialisé par
un propriétaire de compte ; le stockage transactionnel physique n’est pas encore implémenté.

`dimensionner` reçoit explicitement la configuration commune et produit un `PlanDimensionnement`
versionné, sans réserver ni envoyer. Après remplissage, fournir le plan initial, le volume confirmé,
le prix réel et les frais d’entrée réels ; budget et fonds propres de référence restent gelés,
SL inchangé, TP recalculé, seule réserve de sortie. Une impossibilité de réduction doit conduire
à la clôture dans la phase 6. Aucun accès privé entre couches : utiliser les interfaces publiques.
Les adaptateurs EMA sont limités à 0a ; le coordinateur ne doit importer aucun moteur de stratégie.

## 7. Méthode MCL telle qu'appliquée

### 7.1 Vocabulaire

- **Artefact** : un paquet (`xpbots.<paquet>`), son dossier `mcl/<artefact>/` (`carte.json`, `PLAN-MCL.md`,
  `journal.jsonl`, `contrats/`), ses tests `tests/robot/<artefact_avec_soulignés>/`.
- **Couche** : un sous-paquet `src/xpbots/<paquet>/c<id>_<nom>/` composé de `__init__.py` (interface publique figée :
  docstring « Couche X de <artefact> — `<unité>` : … Interface publique figée ; contrat : mcl/… », réexportations et
  `__all__`) et de `_impl.py` (docstring « Implémentation de la couche X (<unité>). Révisable à comportement constant
  sous harnais complet. »). Identifiants : `0a`, `0b`, `1a`… ; même chiffre = même profondeur = couches parallèles.
- **Contrat** : `mcl/<artefact>/contrats/couche-<id>.md` au gabarit (en-tête Statut, Consommateurs cartographiés,
  Dépend de ; sept lignes Unité, Responsabilité, Signature, Entrée, Sortie, Effets de bord, Erreurs ; « Spécification
  exécutable » qui nomme les fichiers de tests ; « Comportements documentés (loi de Hyrum) »). Le champ `contrats`
  de la carte liste pour chaque couche : la fiche `.md`, le `__init__.py` et ses fichiers de tests ; tous sont figés.
- **Catégorie 1** : contrat propre de la couche, couches internes réelles et figées, frontières externes doublées.
  **Catégorie 2** : jonction sur le bloc réel `{0 → k}` de l'artefact, chemins représentatifs, comparaison aux
  oracles. Une couche de profondeur 0 n'a pas de catégorie 2.

### 7.2 Carte d'artefact (modèle : `mcl/london-donnees-temps/carte.json`)

`artefact` (nom, échelle `composant`, mode `pur`, description), `langage` `python`, `sources` `["src"]`, `couches`
(id, profondeur, nom, `chemins`, `imports`, `contrats`), `unites` (id, responsabilité, `depend_de`, couche),
`externes` (chaque interdit avec `couches_autorisees` vide : horloge, fichiers, réseau, sqlite3, fils, processus,
hasard, `importlib`, `MetaTrader5`, `reference`, et `paquets_aval` : tous les paquets en aval ou parallèles et le
segment du squelette remplacé), `regles` toutes `strict` (dont `divergence`), `checkpoint_tous_les` 2. Les imports
du noyau ou d'un artefact amont ne se déclarent pas : ils sont hors de la carte de l'artefact et contrôlés par la
carte composite. **Chaque dépendance directe réelle entre couches se déclare**, y compris vers la couche de types
0a (leçon de la phase 2).

### 7.3 Outil

`M="python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/<artefact>"`, puis :
`init --nom <artefact> --langage python --echelle composant --mode pur --sources src` ; `analyser` (DAG, divergence ;
`--ecrire` pour amorcer) ; `statut` (couches constructibles, checkpoint dû) ; `gate` ; `figer` ; `defiger` ;
`checkpoint` ; `verifier` ; `rayon` ; `rapport`. Le gate journalise une empreinte de l'arbre : **rien ne doit
changer dans l'arbre entre un gate vert et le gel** (les rapports de `.local/` sont ignorés par Git).

## 8. Procédure détaillée d'une phase (celle suivie en phases 2 et 3)

### 8.1 Entrée

1. Appliquer le cycle d'AGENTS.md : orchestrateur de skills d'abord (sélection du hook, ou
   `python .agents/skills/xp-bots-request-skill-orchestrator/scripts/select_skills.py --explain "<requête>"`),
   annonce de la couverture tâche → skill, chargement des seules skills utiles.
2. Vérifier que les artefacts amont sont figés : `mcl.py --dossier mcl/<amont> statut` (« Toutes les couches sont
   figées »).
3. Relever l'état initial : `git status --short`, `python tools/run_london_tests.py`, `python tools/verify_project.py`.
   Tout échec préexistant est prouvé et documenté avant le moindre changement.

### 8.2 Initialisation de l'artefact

`init`, puis carte complète (§7.2), `PLAN-MCL.md` (sections : 0 périmètre ; 1 applicabilité ; 2 étape 1 : finalité,
entrées et sorties, contraintes, point d'insertion, arbitrages intégrés ; 3 carte en tableau avec dépendances réelles
déclarées et groupes parallèles ; 4 contrats, gate, checkpoints ; 5 bilan rempli en fin de phase), `analyser`
jusqu'à zéro divergence, puis esquisse de tous les contrats (une fiche par couche).

### 8.3 Boucle de chaque couche (ordre donné par `statut`)

1. **Finaliser le contrat** avant toute ligne de code : signatures exactes, entrées, sorties, erreurs, choix de
   conception tranchés et écrits (ils deviennent des garanties figées).
2. **Implémenter** `_impl.py` et `__init__.py` ; validation stricte des entrées (types, `bool` refusé là où un
   entier est attendu, nombres finis), une exception propre à l'artefact (sous-classe de `ValueError`), objets
   immuables (`dataclass(frozen=True)`) pour les valeurs, aucune entrée-sortie.
3. **Tests de catégorie 1** puis **de catégorie 2** dans `tests/robot/<artefact>/test_cat<1|2>_c<id>_<thème>.py`,
   avec docstring de module (« Catégorie N, couche X (<unité>) : … »), cas nominaux, bornes exactes, refus
   (sous-tests), et comparaison aux oracles de `reference/` en catégorie 2.
4. Sélection rapide : `python tools/run_london_tests.py --artefact <artefact> --couche <id> [--categorie 1|2]`.
5. **Gate** puis **gel** (commande au §12) ; couches parallèles possibles dans la même passe, chacune avec son gate
   et son gel. `verifier` doit rester VERT (divergence stricte).
6. **Checkpoint** quand `statut` le signale (tous les deux niveaux figés) : `checkpoint --par agent --notes "<revue :
   duplications, code mort, révisions à contrat constant>"`.

### 8.4 Gate rouge et défigeage

Catégorie 1 rouge : correction locale. Catégorie 1 verte mais intégration ou régression rouge : remonter les
couches jusqu'à la source, puis `defiger --couche <id> --nature correction|extension|modification --motif "<cause>"
--par agent`, ajouter le test qui capture le cas, corriger à la source, porter la mention dans le « Statut » de la
fiche (« corrigé le … (défigeage `correction` : …) » ou « étendu le … »), nouveau gate, nouveau gel, puis gate des
consommateurs si leur régression l'exige. Une extension est additive (méthode ou paramètre optionnel à valeur
conservatrice) ; une modification de contrat est l'exception.

### 8.5 Couture sur le squelette

Remplacer le segment minimal par l'enveloppe de l'artefact ; supprimer le module minimal remplacé (`git rm`),
adapter les autres segments seulement autant que le nouveau contrat l'exige, adapter les tests du squelette (le
test de bout en bout doit rester vert avec la vraie chair) ; mettre à jour `mcl/squelette/COUTURES.md` : lignes du
§1 concernées (module, contrat d'entrée-sortie, comportement minimal, statut « Remplacé » pour le segment
remplacé), types partagés, et une ligne datée au §3 (segments, nature, artefact, justification, « Vert »). Ajouter
l'ancien module aux `paquets_aval` interdits de la carte pour empêcher sa réintroduction.

### 8.6 Vérification adversariale par mutations

Sur une **copie jetable hors du dépôt** (dossier temporaire ou bloc-notes de la session), copier `src`, `tests`,
`tools`, `config`, `schemas`, `prompts`, `reference`, `docs`, `mcl`, `livrables` et `.agents` ; pour chaque mutation
(au moins une par couche, plus les segments de squelette touchés) remplacer un motif présent **exactement une fois**,
lancer `python tools/run_london_tests.py` dans la copie et exiger un code de sortie non nul. Vérifier qu'une mutation
change réellement le comportement (une mutation sans effet est une erreur du harnais, pas un trou des tests). Toute
mutation survivante réelle révèle une lacune de la spécification exécutable : défigeage `correction`, test exact,
nouveau gel, puis nouvelle passe de mutations jusqu'à détection totale. Phase 2 : 13 + 9 mutations ; phase 3 : 24.

### 8.7 Sortie de phase

1. Gate global : `$M gate --global --regression "python tools/run_london_tests.py" --regression "python tools/verify_project.py"`,
   puis checkpoint si dû, puis `mcl.py --dossier mcl/robot-london-v3 verifier` (et `verifier` des cartes de chaque
   artefact).
2. Documents : `mcl/<artefact>/PLAN-MCL.md` §5 (bilan : couches, défigeages et leurs motifs, choix de conception
   arrêtés, contrôles dérivés des sources, mutations, couture) ; ligne de la phase dans
   `mcl/robot-london-v3/PLAN-MCL.md` §7 ; plan directeur : version d'un cran (phase 6 → **1.4.7**), date, phrase
   d'état de l'en-tête, ligne du journal des révisions (§7) ; [guide](../../docs/architecture/GUIDE_IMPLEMENTATION.md) :
   phrase « État du dépôt au … » et numéro de version du plan ; document 02 seulement si une dépendance ou une
   sortie réelle diffère de l'esquisse ; ce rapport de passation : §0 et §6.1 (état), §9 (briefing de la phase
   suivante) si une nouvelle passation est probable.
3. Contrôles : `python tools/run_london_tests.py`, `python tools/verify_project.py`,
   `python tools/verifier_plan_london.py`, suite de gouvernance si un fichier de gouvernance a changé,
   `git diff --check`, `python .agents/hooks/agent_lifecycle.py --run-gates`.
4. Commit en français, titre « Exécute la phase N du robot London : <résumé> », corps en prose (couches et leur
   rôle, checkpoints, défigeages, couture, effectif des tests, mutations), lignes d'attribution de la session ; push.
5. Audit de fin (skill `xp-bots-completion-audit`) puis rapport d'arrêt (§8.8).

### 8.8 Rapport d'arrêt (forme attendue par l'humain)

En français, résultat d'abord en une phrase, puis : « Ce qui a été construit » (couches, choix fixés dans les
contrats, défigeages, couture), « Vérifications » (oracles, bornes, rangs, mutations), « Limites » (ce qui reste
hors de la phase ou à faire plus tard), et l'invitation « passe à la phase N+1 ». Il se termine par le pied d'audit
exact puis le marqueur :

Pied d'audit XP-Bots
- completion: exigences prouvées / total, écarts éventuels
- impact: méthode de recherche, régressions trouvées ou « aucune »
- verifications: commandes exécutées et résultats
- couverture_skills: couvert / étendre / créer / consigner
[XP-BOTS-AUDIT:OK]

Le marqueur `[XP-BOTS-AUDIT:BLOQUE]` ne sert qu'à un blocage prouvé et expliqué (dont l'attente d'une réponse de
l'humain). Les sous-agents n'émettent jamais de marqueur. Sous Claude Code, le hook de fin refuse une réponse sans
pied complet ; ailleurs, la règle s'applique sans hook.

## 9. Briefing de la phase 6 — cycle d’ordre, sorties et reprise

### 9.1 Préparation et coexistence

La phase 5 est terminée. Lire le document 04, phase 6, le document 02 §6.4, le document 01
§4 et §7, C06–C09 et les cas C11.11 à C11.13. Utiliser MCL, risque/exécution et les skills
fondamentales ou de déploiement si leurs contrats de contrôle et d’arrêt sont travaillés.
Aucune connexion réelle, aucun réseau ni terminal n’est nécessaire.

Le choix R4/R5 est déjà tranché : un seul coordinateur pour les deux méthodes, code commun sous
`xpbots.execution.c*`, domaine canonique du noyau London et adaptation typée EMA en 0a.
Poursuivre **`mcl/london-execution-coordinateur/`** ; ne pas initialiser une seconde carte
à partir de l’esquisse historique `mcl/execution-coordinateur/`.

### 9.2 Carte et ordre

Les onze couches 0a à 3 sont figées. La même carte contient quatre contrats seulement esquissés :
4 `cycle_ordre`, 5a `sorties_obligatoires`, 5b `reprise_rapprochement`, 6 `coordinateur`.
Finaliser leurs signatures avant leur code et déclarer toutes les dépendances directes réelles.
La couche 4 est cyclique : construire les transitions successivement, chacune avec gate catégorie 1,
puis gate intégral et gel de la couche. Construire 5a et 5b, puis 6 ; checkpoint après le niveau 6.
Ne défiger un contrat de phase 5 que pour une cause exacte et tracée, avec test et nouveau gel.

### 9.3 Garanties à construire

Appliquer C08 dans l’ordre : réponses et rapprochements, sorties prioritaires, maintenance des protections,
puis nouvelles intentions. Identifier propriétaire et intention par magic/commentaire (D-08).
Un accusé inconnu verrouille le symbole et déclenche les rapprochements aux cadences configurées,
puis l’alerte ; aucune retransmission aveugle. Un remplissage partiel annule le reliquat sans complément
automatique ; le premier volume confirmé non nul consomme seul le quota, de façon idempotente.
Un accusé ou volume nul ne doit jamais produire une issue `REMPLIE`.

Vérifier les protections : SL absent → clôture d’urgence immédiate ; TP recalculé depuis le prix moyen
réel avec SL fixe, réessais bornés par les délais et l’échéance ; TP déjà dépassé → clôture au prix
disponible. Recalculer le risque avec les frais d’entrée réels et la seule réserve de sortie, budget
et fonds propres de référence gelés ; réduire au plus grand volume admissible, sinon clôturer.
Les réservations ne se libèrent ni par un profit flottant ni par une réponse ambiguë.

Sans cotation ou en marché fermé, les sorties restent prioritaires et se réessaient ; aucune entrée
rétroactive. Arrêts quotidien et global survivent au redémarrage ; seul le quotidien se réarme au
jour UTC suivant, le global exige une décision tracée. Consommer les preuves P-12 et les flux
identifiés sans neutraliser deux fois le même mouvement. La persistance physique sera construite
dans l’infrastructure ; définir ici le port et les états purs de reprise, sans simuler un disque interne.

Recontrôler juste avant l’envoi la permission fondamentale et la copie mémoire IA. Le contrôle neutre
est un scénario **explicitement** `TECHNICAL_CONTROL_NEUTRAL`, jamais une permission implicite en production.
Le complément absent vaut `NEUTRAL` et ne crée aucune permission fondamentale. Journal C09 et issues
des stratégies doivent refléter chaque transition. P-08 : causes intermédiaires conservées et motif final
`SIGNAL_EXPIRED` avec dernière cause bloquante. Cas C11.11–13, L-12–14 et L-17–19 sur les vrais composants.

### 9.4 Sortie attendue

Couture S4 avec de vrais ordres synthétiques exécutés par S5 ; conserver les vrais signaux et les tests
de bout en bout causaux. Ne pas anticiper l’orchestration complète de phase 9. Gate global des deux
lignées, cartes strictes, mutations sur copies extérieures, bilan, suivi composite, registre des coutures,
plan directeur 1.4.7, guide et passation à jour, commit et push. Rapport d’arrêt invitant à la phase 7.

## 10. Leçons et pièges des phases 0 à 5

1. **Divergence stricte** : une dépendance réelle oubliée dans la carte fait échouer le gate ; déclarer aussi les
   dépendances vers les couches de types.
2. **Mutations** : elles ont révélé deux lacunes réelles (champs obligatoires du journal vérifiés par simple
   inclusion en phase 2 ; empreinte chaînée du préchargement non calculée exactement en phase 3). Tester
   l'égalité exacte d'une formule contractuelle, pas seulement une propriété (« différent si… »).
3. **Reprise exacte** : exporter un état complet (bougie ouverte comprise) plutôt qu'un état aux seules frontières ;
   contrôler la cohérence interne d'un état importé (compteurs, ATR présent ou non, premières valeurs nulles
   ensemble).
4. **Ne jamais lire les clés privées** d'un export d'une autre couche : passer par ses propriétés publiques.
5. **Ordre à fin égale** : H1 avant M15 ; une mutation qui l'inverse doit être détectée.
6. **Temps** : `zoneinfo` seulement ; `datetime.combine` n'accepte pas `fold` (utiliser `replace(tzinfo=…, fold=…)`) ;
   les changements d'heure britanniques tombent le dimanche à 01:00 UTC ; ne jamais supposer un décalage constant.
7. **Flottants** : comparaisons aux oracles avec tolérance relative explicite (1e-12) ; égalités aux seuils avec
   des valeurs dyadiques et l'arithmétique du robot.
8. **Gate puis gel** : ne rien modifier entre les deux ; un fichier de contrat oublié dans `contrats` n'est pas figé.
9. **Squelette** : il n'est jamais figé ; il doit rester vert ; ses hypothèses (marché couvert sur l'étendue du
   fichier, taille de tick) sont documentées dans le module et dans le registre des coutures.
10. **Tests du squelette** : chaque changement de couture casse des tests du squelette ; c'est attendu, ils se
    mettent à jour dans le même lot que la couture.
11. **Rapports** : `tools/run_london_tests.py` écrit `.local/reports/robot_tests.json` (ignoré par Git) ; le
    résumé JSON final donne `tests`, `echecs`, `erreurs`, `statut`.
12. **Portabilité des gels** : les fichiers contractuels doivent avoir les mêmes octets que leurs blobs Git ;
    écrire en UTF-8 et LF avant le gel. En phase 4, huit défigeages `correction` ont rendu cette conservation
    explicite ; celui de 1a a aussi ajouté le test exact des extrêmes hétérogènes révélé par mutation.
13. **Liens Markdown** : la porte `markdown-links` vérifie les liens relatifs des fichiers modifiés.

## 11. Aperçu des phases 6 à 13 (points d'attention)

- **6** (`execution-coordinateur` 4 à 6) : couche 4 cyclique construite par transitions successives, un gate de
  catégorie 1 par transition ; D-08 ; P-08 ; couture S4 avec de vrais ordres exécutés par S5.
- **7** (`controles-fondamentaux`) : fixtures au format exact du dossier d'échange (D-11) et de l'export MQL5 (D-12,
  document 01, §2.1 et §2.2) ; aucune lecture de fichier réel avant la phase 11.
- **8** (`contexte-ia`) : égalité avec `overlay_decision` ; persistance du cache par export et import.
- **9** (`orchestration`) : moteur unique, bras A/B indépendants, stratégies injectées (D-18), aucune importation
  de `xpbots.london` ; rejouabilité C11.14 ; couture en `PAPER_AB` sur fixtures.
- **10** (`journal-rejeu`) : simulateur C10 (P-11), bootstrap semé, métriques calculées à la main ; aucune donnée
  réelle.
- **11** (`infrastructure`, `points-entree`, source MQL5) : faux module `MetaTrader5` conforme au document 08 ;
  `requirements-windows.txt` ; tests de contrat écrits mais ignorés hors du poste ; répétition générale `PAPER` dans
  le conteneur ; aucun appel au vrai terminal.
- **12** (`service-ia`) : hors ligne, ouvreur HTTP factice ; aucun appel réseau ; route payante désactivée.
- **13** : seule phase avec actions humaines (H-02 à H-12, document 07) ; chaque sous-étape s'arrête sur question
  si ses prérequis manquent (marqueur de blocage), et l'autorisation des API est redemandée au début de 13.6.

## 12. Aide-mémoire des commandes (depuis la racine du dépôt)

- Suite complète : `python tools/run_london_tests.py` ; sélection :
  `python tools/run_london_tests.py --artefact london-execution-coordinateur --couche 3 --categorie 1`.
- Contrôles : `python tools/verify_project.py` ; `python tools/verifier_plan_london.py` ;
  `python .agents/skills/xp-bots-maintain-agent-skills/scripts/run_governance_suite.py` ;
  `python .agents/hooks/agent_lifecycle.py --run-gates` ; `git diff --check`.
- Gate d'une couche (une seule ligne) : `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/london-execution-coordinateur gate --couche <id> --unitaire "python tools/run_london_tests.py --artefact london-execution-coordinateur --couche <id> --categorie 1" --integration "python tools/run_london_tests.py --artefact london-execution-coordinateur --couche <id> --categorie 2" --regression "python tools/run_london_tests.py" --regression "python tools/verify_project.py"`
  (sans `--integration` en profondeur 0), puis `... figer --couche <id> --par agent`.
- Gate global : `... gate --global --regression "python tools/run_london_tests.py" --regression "python tools/verify_project.py"`.
- Vérification des cartes : `... --dossier mcl/robot-london-v3 verifier`, idem pour chaque artefact ; `statut`.
- Démonstration du squelette : `PYTHONPATH=src python -m xpbots.app.rejeu_squelette --ticks <fichier.csv> --sortie <dossier> --tick-size EURUSD=0.00001` (répéter pour chaque symbole synthétique).

## 13. Contrôle de reprise (à faire avant tout changement)

1. La branche contient `9c39d23`, l’intégration `5e5e288`, ce rapport et le moteur `c2_moteur` ; vérifier
   le commit de phase 5 dans `git log` (après `85069c0`) et le récupérer depuis la branche publiée si nécessaire. Ne pas repartir
   de la seule ancienne branche de phase 3, qui ne contient ni coexistence ni moteur S02.
2. `mcl.py statut` indique « Toutes les couches sont figées » pour `mcl/noyau`,
   `mcl/london-donnees-temps` et `mcl/moteur-london`. Dans `mcl/london-execution-coordinateur`, seules les onze couches 0a à 3 sont figées ; 4, 5a, 5b et 6 sont à construire.
3. `python tools/run_london_tests.py` donne au moins 613 tests verts des deux lignées ; `python tools/verify_project.py` PASS ;
   `mcl.py --dossier mcl/robot-london-v3 verifier` VERT ; `git status --short` comparé à la fin de phase 5 : deux modifications préexistantes de
   `.gitattributes` et `tests/robot/fixtures/squelette_ticks.csv` ont été préservées hors des commits des phases 4 et 5 ;
   tout autre écart doit être identifié et expliqué.
4. Sous Windows, conserver les octets LF de la fixture CSV lors d'un export pour les tests : employer
   `git -c core.autocrlf=false archive` pour obtenir les blobs exacts. Le réglage `core.autocrlf=true` avec
   l'ancienne règle CSV absente de la version commitée peut convertir cette fixture en CRLF ; ce cas a été
   reproduit sur le commit initial et ne vient pas du moteur London. La règle CSV ajoutée initialement dans
   le répertoire de travail reste une modification non commitée de l'utilisateur.
5. Tout écart est signalé dans la réponse avant de commencer, avec sa preuve ; il n'est jamais masqué.

## 14. Glossaire minimal

- **A_t** : ATR de la bougie t − 1 (référence de la décision sur t). **A_H1** : ATR H1 figé à 07:00 Londres.
- **Range** : les 20 M15 de `[02:00, 07:00)` Londres ; W = H − L.
- **Bougie enrichie** : bougie du noyau + TR, ATR, A, rang + jour et heures de Londres + jour UTC.
- **Couture** : point où un artefact remplace un segment minimal du squelette.
- **Défigeage** : levée tracée du gel d'une couche (`correction`, `extension`, `modification`).
- **Oracle** : fonction de `reference/` utilisée uniquement pour comparer dans les tests.

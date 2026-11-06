# Rapport de passation — robot London (`LONDON_V3`), reprise à la phase 4

> Rédigé le 06/11/2026 à la fin de la phase 3, à l'intention de l'agent qui reprend l'exécution du plan dans une
> autre session, éventuellement avec un autre modèle ou un autre outil. Son but : que la suite soit construite
> exactement selon la logique, la rigueur et les conventions des phases 0 à 3. Ce rapport est un **contexte de
> reprise**, pas une source normative : en cas d'écart avec les spécifications, les exports figés, le plan ou le
> code réel, ce sont eux qui prévalent, et l'écart se signale (plan directeur, §0).

## 0. Fiche de passation

| Élément | Valeur |
|---|---|
| Dépôt | `MasterVKT/XP-Bots` |
| Branche de travail | `claude/stoic-brown-l3qbv3` (dernier commit de code : `70c60d9`, « Exécute la phase 3 du robot London : artefact donnees-temps figé ») |
| Plan suivi | [Plan directeur 1.4.4](../../docs/architecture/robot_london_v3/README.md), documents 01 à 08 du même dossier |
| Phases terminées | 0, 1, 2, 3 (toutes commitées et poussées) |
| Prochaine action | **Phase 4 — artefact `moteur-london`**, à lancer seulement sur demande explicite de l'humain |
| Suite du robot | 197 tests verts (noyau 77, donnees-temps 71, squelette 33, gardes transverses 11, outils 5) |
| Contrôles | `tools/verify_project.py` PASS ; suite de gouvernance verte ; `tools/verifier_plan_london.py` sans problème ; `mcl.py verifier` VERT sur les trois cartes |
| Environnement vérifié | Python 3.13 ; `numpy` 2.4.1, `pandas` 3.0.0, `tzdata` 2025.3 (`requirements-dev.txt`, tests seulement) ; aucun accès réseau requis |

## 1. Résumé exécutif

Le robot 2 (London Breakout M15, `LONDON_V3`) se construit en Python, dans le paquet unique `src/xpbots/`, selon
la méthode **MCL** (couches construites de l'intérieur vers l'extérieur, chacune contractualisée, testée, passée
au gate de régression intégrale puis figée). Le plan compte 14 phases (0 à 13) ; l'humain demande chaque phase
explicitement et l'agent s'arrête à la fin de chacune. Les phases 0 à 3 ont posé la carte composite, un squelette
de bout en bout déployable, le noyau partagé figé (types, configuration figée, journal C09) et l'artefact
`donnees-temps` figé (bougies M15 et H1 causales, validées, enrichies de TR, ATR, A_t, du rang de préchargement et
des repères de Londres, avec reprise exacte). La prochaine phase construit la méthode S02 elle-même
(`moteur-london`), pure, puis la branche sur le squelette à la place de la stratégie minimale.

## 2. Mission et règle d'exécution

1. Exécuter **une phase à la fois**, dans l'ordre du [document 04](../../docs/architecture/robot_london_v3/04_phases.md),
   sur demande explicite de l'humain (formule habituelle : « Commence et achève intégralement la phase N »).
2. Achever la phase **intégralement** : toutes ses couches figées, couture faite, gate global vert, documents à
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
   phase 4 : §6.3), conventions des cartes, tableau des artefacts (§5), squelette (§3).
5. [Document 03](../../docs/architecture/robot_london_v3/03_acceptation_et_tests.md) : catégories de tests,
   commandes de gate, affectation des cas C11, S02.6 et A14, scénarios L-01 à L-19, gardes transverses.
6. [Document 01](../../docs/architecture/robot_london_v3/01_architecture.md), §9.3 : table des motifs et des
   détails (P-07), indispensable pour tout résultat technique.
7. La spécification [02 London Breakout](../../livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md)
   (sections citées par la fiche de phase) et [config/parametres_figes_v3.json](../../config/parametres_figes_v3.json).
8. Le [plan MCL composite](PLAN-MCL.md) (§7 : suivi des phases), le [registre des coutures](../squelette/COUTURES.md),
   les plans MCL des artefacts figés ([noyau](../noyau/PLAN-MCL.md), [donnees-temps](../donnees-temps/PLAN-MCL.md))
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
- **Git** : travailler sur la branche que désigne la session (à défaut `claude/stoic-brown-l3qbv3`), sans
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
- Le rapport d'arrêt de chaque phase suit la forme décrite au §8.13 et se termine par l'invitation explicite à
  demander la phase suivante.

## 6. État exact du dépôt

### 6.1 Phases

| Phase | Commit | Contenu |
|---|---|---|
| 0 | `21854b1` | Dossier MCL composite `mcl/robot-london-v3/` (carte au grain des paquets, divergence stricte) ; guide et règles alignés sur D-01, D-02 |
| 1 | `6821747` | Squelette composite S1 à S7, lanceur `tools/run_robot_tests.py`, fabrique de ticks, test de bout en bout, gardes de pureté et de carte |
| 2 | `7d22b6f` | Artefact `noyau` figé (7 couches) ; couture S1, S6 ; défigeages `correction` de la couche 2 |
| 3 | `70c60d9` | Artefact `donnees-temps` figé (8 couches) ; couture S2 ; défigeage `extension` de 1a et `correction` de 2b ; 24 mutations détectées |

### 6.2 Carte composite (`mcl/robot-london-v3/carte.json`, divergence stricte)

Couches au grain des paquets : 0 `noyau` (`xpbots.noyau`) ; 1 `donnees-temps` (`xpbots.donnees`) ;
2a `moteur-london` (`xpbots.london`) ∥ 2b `execution-coordinateur` (`xpbots.execution`) ; 3a
`controles-fondamentaux` ∥ 3b `contexte-ia` ∥ 3c `infrastructure` ; 4a `orchestration` ∥ 4b `service-ia` ; 5
`journal-rejeu` ; 6 `points-entree`. Dépendances autorisées : `moteur-london` → noyau, donnees-temps ;
`execution-coordinateur` → noyau, donnees-temps ; `orchestration` → noyau, donnees-temps, execution,
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
  de `common`) ; `london` reste un `Mapping` brut à typer par la phase 4 ; `ErreurConfiguration`.
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
- S3 : `xpbots.london.squelette.StrategieMinimale` : `sur_bougie(BougieEnrichie)` rend `NO_SETUP` /
  `SEGMENT_MINIMAL_S3` pour chaque M15, rien pour une H1 ; `fabriquer_strategie(configuration)`.
- S4 : `xpbots.orchestration.squelette.MoteurMinimal` et `fabriquer_moteur_minimal(strategie, configuration, mode,
  deploiement='squelette', *, horaires, periodes_couvertes)` ; protocole structurel `Strategie` (attribut
  `identifiant`, méthode `sur_bougie`) ; `CoordinateurMinimal` refuse tout signal (`ENVIRONMENT_NOT_READY`,
  `SEGMENT_MINIMAL_S4`) ; `CLOTURE` par M15 avec indicateurs, `INTENTION` par signal, `ALERTE` par trou ou anomalie.
- S5 : exécution papier minimale ; S6 : journal canonique écrit par `ecrire_journal` ; S7 :
  `python -m xpbots.app.rejeu_squelette --ticks <csv> --sortie <dossier> [--racine-depot .]`.

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

### 7.2 Carte d'artefact (modèle : `mcl/donnees-temps/carte.json`)

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
3. Relever l'état initial : `git status --short`, `python tools/run_robot_tests.py`, `python tools/verify_project.py`.
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
4. Sélection rapide : `python tools/run_robot_tests.py --artefact <artefact> --couche <id> [--categorie 1|2]`.
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
lancer `python tools/run_robot_tests.py` dans la copie et exiger un code de sortie non nul. Vérifier qu'une mutation
change réellement le comportement (une mutation sans effet est une erreur du harnais, pas un trou des tests). Toute
mutation survivante réelle révèle une lacune de la spécification exécutable : défigeage `correction`, test exact,
nouveau gel, puis nouvelle passe de mutations jusqu'à détection totale. Phase 2 : 13 + 9 mutations ; phase 3 : 24.

### 8.7 Sortie de phase

1. Gate global : `$M gate --global --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"`,
   puis checkpoint si dû, puis `mcl.py --dossier mcl/robot-london-v3 verifier` (et `verifier` des cartes de chaque
   artefact).
2. Documents : `mcl/<artefact>/PLAN-MCL.md` §5 (bilan : couches, défigeages et leurs motifs, choix de conception
   arrêtés, contrôles dérivés des sources, mutations, couture) ; ligne de la phase dans
   `mcl/robot-london-v3/PLAN-MCL.md` §7 ; plan directeur : version d'un cran (phase 4 → **1.4.5**), date, phrase
   d'état de l'en-tête, ligne du journal des révisions (§7) ; [guide](../../docs/architecture/GUIDE_IMPLEMENTATION.md) :
   phrase « État du dépôt au … » et numéro de version du plan ; document 02 seulement si une dépendance ou une
   sortie réelle diffère de l'esquisse ; ce rapport de passation : §0 et §6.1 (état), §9 (briefing de la phase
   suivante) si une nouvelle passation est probable.
3. Contrôles : `python tools/run_robot_tests.py`, `python tools/verify_project.py`,
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

## 9. Briefing de la phase 4 — artefact `moteur-london` (paquet `xpbots.london`)

### 9.1 Objet et sources

Appliquer S02 aux bougies enrichies d'un symbole et rendre, à chaque clôture M15, un signal technique ou un motif ;
appliquer les issues reçues. Pur : ni coordinateur, ni courtier, ni horloge. Sources : document 02, §6.3 (unités,
carte, esquisses de contrat, ordre d'évaluation de l'enveloppe) ; document 04, phase 4 ; document 03 (S02.6-1 à 8,
L-01 à L-13 au niveau du moteur, C11.1, C11.2, C11.4) ; document 01, §9.3 (motifs et détails) ; spécification
S02.1 à S02.6 ; `reference/technical.py` (`london_signal`, `london_setups`, `LONDON_CFG`). Skills :
`xp-bots-london-breakout`, MCL, et `anthropic-skills:expert-scalper-m15` pour une lecture critique des cas sans
changer de règle (si cette skill n'existe pas dans l'outil, s'appuyer sur la lecture d'expert du document 05 et le
déclarer dans `couverture_skills`). Arbitrages : P-09 (couche 1b), P-03 et P-10 (déjà portés par donnees-temps,
consommés ici), P-07 (motifs).

### 9.2 Carte prévue

0a `parametres_london` ∥ 0b `types_london` ; 1a `range_londres` ∥ 1b `gel_atr_h1` ∥ 1c `bougie_cassure` ∥ 1d
`stop_local` ∥ 1e `quotas_london` ; 2 `moteur_london` (enveloppe). Sous-paquets suggérés, sur le modèle des phases
précédentes : `c0a_parametres`, `c0b_types`, `c1a_range`, `c1b_gel_atr_h1`, `c1c_cassure`, `c1d_stop`, `c1e_quotas`,
`c2_moteur`. Tests : `tests/robot/moteur_london/` (le lanceur convertit `moteur-london` en `moteur_london`).
Checkpoint après le niveau 1, puis gate global. Interdits de la carte : ceux de `donnees-temps` plus
`xpbots.execution` (couche composite parallèle), `xpbots.london.squelette` (segment remplacé) et tous les
paquets en aval. Déclarer chaque dépendance réelle : les couches de niveau 1 dépendent de 0a et 0b ; l'enveloppe de
toutes celles qu'elle importe.

### 9.3 Points de conception à trancher dans les contrats (recommandations)

1. **Paramètres** (0a) : typer le bloc `london` (le `Mapping` brut de `ExportTechnique.london`) et lire dans
   `ParametresCommuns` les clés communes utilisées par S02 (`maximum_signal_true_range_atr`, `structural_buffer_atr`,
   `minimum_chart_stop_atr`, `maximum_chart_stop_atr`, `warmup_closed_m15_bars`, `warmup_closed_h1_bars`,
   `timeframe_seconds`, `h1_seconds`, fuseau, jours actifs). Refuser au démarrage `fresh_close_cross_required`,
   `h1_directional_filter_enabled` et `exit_on_close_back_inside_range_enabled` s'ils ne sont pas faux ; contrôler
   `expected_range_m15_bars` = durée du range / `timeframe_seconds` et l'ordre début de séance < fin d'entrée ≤
   sortie forcée. Aucun seuil écrit en dur.
2. **Taille de tick** : elle n'est pas dans `config/` ; elle vient du profil d'instrument C04
   (`ProfilInstrument.tick_size`, `Decimal`). Recommandation : un contrat étroit qui reçoit, par symbole, une taille
   de tick décimale (et la convertit une fois en flottant pour les comparaisons, comme la référence), plutôt que tout
   le profil. Le squelette n'ayant pas de profil, prévoir pour S7 une **option explicite** de la ligne de commande
   (par exemple une taille de tick par symbole, obligatoire pour chaque symbole du fichier, code 1 si elle manque),
   tracée au registre des coutures comme hypothèse du squelette remplacée plus tard par le vrai profil ; éviter de
   la déduire du nombre de décimales des prix.
3. **Contrat de stratégie (D-18)** : le protocole structurel déclaré par `xpbots.orchestration.squelette` est
   `identifiant` et `sur_bougie(BougieEnrichie) -> ResultatTechnique | None` (un résultat pour chaque M15 close,
   valide ou non ; rien pour une H1, reçue avant la M15 de même fin). « Appliquer les issues » exige une extension
   additive du protocole, par exemple `sur_issue(issue: Issue) -> None`, appelée par le moteur minimal après chaque
   issue (le coordinateur minimal ne rend que des refus : aucun quota consommé). Le moteur London ne doit importer ni
   `xpbots.orchestration` ni `xpbots.execution` ; un test vérifie sa conformité structurelle au protocole.
4. **Instances** : un état par symbole (et par bras, plus tard, par l'orchestration) ; la stratégie injectée peut
   contenir un moteur par symbole créé à la première bougie, à partir des paramètres et de la taille de tick du
   symbole.
5. **Ordre d'évaluation et motifs** (document 02, §6.3) : trou actif → hors fenêtre ou jour inactif → préchargement
   et A → validité du range → disponibilité du gel → admissibilité → position London possédée sur le symbole →
   cassure → quota du sens → stop ; sinon signal avec son contexte (H, L, W, A_H1, W/A_H1, disponibilité du gel,
   mesures de la bougie). Chaque refus prend un `Motif` et un détail de `DETAILS_ENUMERES` conformes à la table du
   document 01, §9.3 (par exemple `NO_SETUP`/`RANGE_HORS_BORNES`, `DATA_GAP`/`RANGE_INCOMPLET`,
   `WARMUP`/`ATR_H1_INDISPONIBLE`, `OUTSIDE_SESSION`/`HORS_FENETRE`, `SYMBOL_BUSY`/`POSITION_METHODE`,
   `DAILY_ENTRY_CAP`/`SENS_DEJA_REMPLI`, `STOP_TOO_WIDE`). Le préchargement se lit sur `IndicateursBougie.rang`
   (P-10 : rang ≥ `warmup_closed_m15_bars` − 1) ; la fenêtre par `CalendrierLondres.decision_dans_fenetre` ; le jour
   par `BougieEnrichie.jour_londres` ; l'état de trou par les bougies invalides et les motifs `TROU_DONNEES`
   (P-03 : range effacé au début du trou, recalculé après récupération si ses 20 bougies sont valides).
6. **Gel de A_H1** (P-09) : instant de gel 07:00 Londres ; dernière H1 **valide** close au plus tard à 07:00 et
   datant d'au plus 3 600 s ; ATR > 0 ; au moins `warmup_closed_h1_bars` H1 valides jusqu'à elle (rang) ;
   disponibilité = instant de disponibilité de sa bougie ; première version figée, aucune mise à jour ensuite ;
   décision antérieure à la disponibilité refusée.
7. **Quotas** : enregistrement au premier remplissage non nul, idempotent par clé d'intention ; remise à zéro au
   seul changement de jour Londres ; un refus sans remplissage ne consomme rien ; jamais deux signaux pour une même
   bougie ni de rattrapage.

### 9.4 Tests clés et données

- Catégorie 1 par couche, bornes exactes avec des valeurs dyadiques (exactement représentables en binaire) et
  cas de la spécification cités tels quels (L-01, exemple S02.5).
- Égalité de `bougie_cassure` et `stop_local` avec `london_signal` sur des cas synthétiques ; égalité des signaux de
  l'enveloppe avec `london_setups` (cadres pandas construits comme en phase 3 avec `add_indicators` pour les M15 et
  les H1) quand aucun remplissage n'est rapporté ; causalité par préfixe (C11.1) ; réinitialisation au changement
  de jour Londres ; non-recopie des seuils (paramètres modifiés par `robot.outils.configuration.octets_technique_modifies`
  qui changent le comportement) ; S02.6-1 à 8 et L-01 à L-13 au niveau du moteur.
- **Fabrique de journées London à écrire** dans `tests/robot/outils/` (document 03, §4) : ticks (et non bougies)
  produisant un historique d'au moins 1 000 M15 et 300 H1 valides de TR constant (clôture précédente dans `[L, H]`,
  donc TR = H − L) pour obtenir exactement l'A et l'A_H1 voulus, puis une journée avec un range voulu et une bougie
  de cassure voulue ; elle sert aussi au test de bout en bout de la couture (au moins treize jours de ticks avant la
  journée de décision : 1 000 M15 ≈ 10,4 jours et 300 H1 = 12,5 jours).

### 9.5 Couture S3 et critères de sortie

Remplacer `xpbots.london.squelette` par la fabrique du vrai moteur ; le squelette journalise alors de vrais signaux
London, refusés explicitement par le coordinateur minimal (`INTENTION` refusée) ; adapter S4 (appel des issues),
S7 (taille de tick, fabrique London) et le test de bout en bout (préchargement suffisant et au moins un vrai
signal). Sortie : huit unités figées, gate global vert, bout en bout vert, cartes vertes, mutations toutes détectées,
documents et plan 1.4.5, commit, push, rapport d'arrêt.

## 10. Leçons et pièges des phases 0 à 3

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
11. **Rapports** : `tools/run_robot_tests.py` écrit `.local/reports/robot_tests.json` (ignoré par Git) ; le
    résumé JSON final donne `tests`, `echecs`, `erreurs`, `statut`.
12. **Liens Markdown** : la porte `markdown-links` vérifie les liens relatifs des fichiers modifiés.

## 11. Aperçu des phases 5 à 13 (points d'attention)

- **5** (`execution-coordinateur` 0 à 3) : calculs purs C06–C07 ; P-04, P-05 (0c), P-12 (1b), P-06 (3) ;
  comparaison à `rounded_levels` ; aucune couture.
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

- Suite complète : `python tools/run_robot_tests.py` ; sélection :
  `python tools/run_robot_tests.py --artefact moteur-london --couche 1a --categorie 1`.
- Contrôles : `python tools/verify_project.py` ; `python tools/verifier_plan_london.py` ;
  `python .agents/skills/xp-bots-maintain-agent-skills/scripts/run_governance_suite.py` ;
  `python .agents/hooks/agent_lifecycle.py --run-gates` ; `git diff --check`.
- Gate d'une couche (une seule ligne) : `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/moteur-london gate --couche <id> --unitaire "python tools/run_robot_tests.py --artefact moteur-london --couche <id> --categorie 1" --integration "python tools/run_robot_tests.py --artefact moteur-london --couche <id> --categorie 2" --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"`
  (sans `--integration` en profondeur 0), puis `... figer --couche <id> --par agent`.
- Gate global : `... gate --global --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"`.
- Vérification des cartes : `... --dossier mcl/robot-london-v3 verifier`, idem pour chaque artefact ; `statut`.
- Démonstration du squelette : `PYTHONPATH=src python -m xpbots.app.rejeu_squelette --ticks <fichier.csv> --sortie <dossier>`.

## 13. Contrôle de reprise (à faire avant tout changement)

1. La branche contient le commit `70c60d9` et ce fichier ; sinon récupérer `origin/claude/stoic-brown-l3qbv3`
   (et, si la session impose une autre branche, la faire partir de ce commit) avant toute autre action.
2. `mcl.py statut` indique « Toutes les couches sont figées » pour `mcl/noyau` et `mcl/donnees-temps`.
3. `python tools/run_robot_tests.py` donne au moins 197 tests verts ; `python tools/verify_project.py` PASS ;
   `mcl.py --dossier mcl/robot-london-v3 verifier` VERT ; `git status --short` vide.
4. Tout écart est signalé dans la réponse avant de commencer, avec sa preuve ; il n'est jamais masqué.

## 14. Glossaire minimal

- **A_t** : ATR de la bougie t − 1 (référence de la décision sur t). **A_H1** : ATR H1 figé à 07:00 Londres.
- **Range** : les 20 M15 de `[02:00, 07:00)` Londres ; W = H − L.
- **Bougie enrichie** : bougie du noyau + TR, ATR, A, rang + jour et heures de Londres + jour UTC.
- **Couture** : point où un artefact remplace un segment minimal du squelette.
- **Défigeage** : levée tracée du gel d'une couche (`correction`, `extension`, `modification`).
- **Oracle** : fonction de `reference/` utilisée uniquement pour comparer dans les tests.

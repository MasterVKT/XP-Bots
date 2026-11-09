# Rapport de passation — robot London (`LONDON_V3`), reprise à la phase 9

> Mis à jour le 09/11/2026 à la fin de la phase 8, à l'intention de l'agent qui reprend l'exécution du plan dans une
> autre session, éventuellement avec un autre modèle ou un autre outil. Son but : que la suite soit construite
> exactement selon la logique, la rigueur et les conventions des phases 0 à 8. Ce rapport est un **contexte de
> reprise**, pas une source normative : en cas d'écart avec les spécifications, les exports figés, le plan ou le
> code réel, ce sont eux qui prévalent, et l'écart se signale (plan directeur, §0).

## 0. Fiche de passation

| Élément | Valeur |
|---|---|
| Dépôt | `MasterVKT/XP-Bots` |
| Branche de travail | `master`, après intégration en coexistence structurée (`5e5e288`) ; les commits `9c39d23` et `70c60d9` sont présents ; phase 4 `85069c0` ; phase 5 `4213a07` ; phase 6 `5b017cc` ; phase 7 `27284c2` ; le commit de phase 8 porte cette mise à jour |
| Plan suivi | [Plan directeur 1.4.9](../../docs/architecture/robot_london_v3/README.md), documents 01 à 08 du même dossier |
| Phases terminées | 0, 1, 2, 3, 4, 5, 6, 7 et 8 ; état et publication vérifiables dans le journal Git |
| Prochaine action | **Phase 9 — orchestration**, seulement sur demande explicite ; C05 et le lecteur IA commun sont figés et branchés au rejeu London |
| Suite du robot | 851 tests verts des deux lignées ; 58 propres au lecteur IA (47 catégorie 1, 11 catégorie 2), 62 à C05, 170 au coordinateur, 79 au moteur London, 60 au squelette |
| Contrôles | Régression intégrale, ressources métier, plan London, gouvernance et cartes strictes : preuves de phase 8 dans [le bilan](../london-contexte-ia/PLAN-MCL.md) et le journal MCL |
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
phase 5 a figé les onze couches pures du coordinateur commun, après arbitrage R4/R5. La phase 6 a figé le cycle C08, les sorties, la reprise et le coordinateur, puis remplacé S4. Les journées synthétiques passent avec ordres, remplissages et sorties. La phase 7 a figé les cinq couches C05 communes, après arbitrage R4/R5, et branché le vrai port au rejeu ; les permissions et calendriers sont reçus à leurs instants scénarisés. Le neutre reste explicite. La phase 8 a figé le lecteur IA partagé, son cache causal et sa reprise pure ; le vrai port est injecté au bras IA du rejeu. La référence conserve ComplementAbsent. L’orchestration A/B complète reste à construire en phase 9.

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
   phase 8 : §6.6), conventions des cartes, tableau des artefacts (§5), squelette (§3).
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
| 5 | `4213a07` | Onze couches pures communes figées, checkpoints 1 et 3 ; adaptation EMA, gardes, risque, arbitrage et dimensionnement ; aucune couture S4 ; bilan et mutations dans le dossier actif |

| 6 | `5b017cc` | Quatre couches C08 figées dans le coordinateur unique, checkpoint 6 ; extensions et corrections tracées ; couture S4, profils papier explicites et vrais ordres ; bilan et mutations dans le dossier actif |

| 7 | `27284c2` | Cinq couches C05 communes figées dans london-controles-fondamentaux ; CP2 ; schémas stricts, registre causal, heartbeat, calendrier, port réel et couture avec L-14 été/hiver ; bilan et mutations dans le dossier actif |

| 8 | Commit portant ce rapport | Quatre couches du lecteur IA commun figées dans london-contexte-ia ; CP2 ; snapshot strict, cache causal, preuves de reprise, politique financière et port réel ; couture C09 et L-15 été/hiver ; 10 mutations sur 10 détectées |

### 6.2 Carte composite (`mcl/robot-london-v3/carte.json`, divergence stricte)

Couches au grain des paquets : 0 `noyau` (`xpbots.noyau`) ; 1 `london-donnees-temps` (`xpbots.donnees`) ;
2a `moteur-london` (`xpbots.london`) ∥ 2b `execution-coordinateur` (`xpbots.execution`) ; 3a
`controles-fondamentaux` ∥ 3b `contexte-ia` ∥ 3c `infrastructure` ; 4a `orchestration` ∥ 4b `service-ia` ; 5
`journal-rejeu` ; 6 `points-entree`. Dépendances autorisées : `moteur-london` → noyau, london-donnees-temps ;
`execution-coordinateur` → noyau, london-donnees-temps ; `orchestration` → noyau, london-donnees-temps, execution,
fondamental, contexte_ia (**jamais** `xpbots.london`, D-18) ; `journal-rejeu` → noyau, execution, orchestration,
london, fondamental, contexte_ia ; `points-entree` → noyau, orchestration, journal-rejeu, infrastructure, london. Seule l'orchestration
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

- S1 : lecteur CSV canonique et hypothèse de couverture H1 ; validité du relevé d'horaires prolongée
  d'une H1 pour connaître la fermeture. Cette hypothèse ne représente aucun horaire réel.
- S2 et S3 remplacés : vrais `FluxBougies` et `MoteurLondon`, tailles de tick explicites, H1 avant M15,
  aucun signal rétroactif et quotas au seul premier volume non nul confirmé.
- S4 remplacé par `CoordinateurCompte` ; `MoteurMinimal` injecte le coordinateur et les profils.
  `traiter_ticks` groupe un même instant : réponses natives et issues, sorties, bougies puis admission
  simultanée. `traiter_evenement` traite les minuteries sans nouvelle cotation ; `confirmer_persistance`
  autorise la transmission après revalidation. Aucun moteur importé par l'orchestration (D-18).
- S5 adapté aux vraies commandes C08 : ACK, fill au prochain tick, SL/TP natifs, clôture et réduction,
  historique et observation native avec SL/TP actuels. Compte et calculs synthétiques USD, contrats et
  grille fournis, point=tick, frais et swaps nuls connus. `StockageMemoirePapier` prouve une transaction
  mémoire ; aucune durabilité physique ni simulation C10. Une panne de stockage interdit les entrées.
- S6 : journal canonique du noyau ; une clé persistante par intention et ses mises à jour, traces C08,
  profils et compte, issues seulement lorsqu'un fait les justifie. L'écriture reste minimale.
- S7 : `python -m xpbots.app.rejeu_squelette --ticks <csv> --sortie <dossier> --tick-size EURUSD=0.00001 --contrat-papier EURUSD=1000,0.1,1,0.1 --scenario TECHNICAL_CONTROL_NEUTRAL`.
  Répéter les deux paramètres d'instrument exactement par symbole. Les valeurs ci-dessus décrivent la
  fixture synthétique ; elles ne qualifient aucun courtier. Le résumé donne fills, clôtures et positions.

### 6.5 Interfaces London disponibles (figées)

`xpbots.london.c0a_parametres` expose `ParametresLondon` et `charger_parametres_london` ; `c0b_types`
porte les valeurs immuables et `ErreurLondon`. Les unités de niveau 1 exposent `construire_range`,
`construire_gel`, `evaluer_cassure`, `calculer_stop` et `QuotasLondon`. L'enveloppe `c2_moteur` expose
`MoteurLondon`, `StrategieLondon` et `fabriquer_strategie(configuration, tailles_tick)`.
Les signatures, refus et garanties exacts sont dans les [contrats de moteur-london](../moteur-london/PLAN-MCL.md).
Une issue `REMPLIE` suppose un premier volume effectivement non nul ; aucun volume n'existe dans `Issue`.
La propriété d'une position persiste au changement de jour jusqu'à sa clôture explicite.

### 6.6 Calculs communs disponibles depuis la phase 5

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
SL inchangé, TP recalculé, seule réserve de sortie. Une impossibilité de réduction conduit
à la clôture par le cycle C08 construit en phase 6. Aucun accès privé entre couches : utiliser les interfaces publiques.
Les adaptateurs EMA sont limités à 0a ; le coordinateur ne doit importer aucun moteur de stratégie.

### 6.7 Cycle et coordinateur communs disponibles depuis la phase 6

Quinze couches figées dans `mcl/london-execution-coordinateur`. `CycleOrdre` émet des commandes,
issues et traces pures ; `evaluer_sorties` ordonne les sorties ; `restaurer` et `rapprocher` vérifient
les preuves natives ; `CoordinateurCompte` sérialise le compte et l'admission. Les contrats exacts
se lisent dans ce dossier. Seules les frontières externes sont doublées dans les tests MCL.

`LotCoordinateur` sépare les préparations des commandes autorisées. `PreuvePersistance` doit viser
la même révision et les références exactes ; avant envoi, le compte, les cotations, C05, l'IA et le
risque au volume initial sont recontrôlés. Aucune retransmission aveugle après panne ou ACK ambigu.
Les gardes, quotas et réservations sont exportables, mais leur persistance physique reste future.

`PositionNative(..., *, sl, tp)` exige les protections actuelles : `None` signifie absence constatée,
jamais une valeur devinée dans le journal. Un ordre natif porte sa nature ENTREE ou CLOTURE.
Une position externe n'est ni adoptée ni fermée ; le netting exige la preuve d'exclusivité. Un SL
absent bloque toute nouvelle entrée jusqu'à protection ou clôture confirmée. Les corrections tracées
de 4 incluent les accusés tardifs après clôture : ils ne réactivent aucune minuterie.

L'extension additive du noyau 1c ajoute deux causes de clôture, sans motif ou seuil nouveau.
Les extensions de registre et de dimensionnement sont tracées ; l'arbitrage R4/R5 reste applicable.
L'adaptateur EMA de 0a demeure l'unique frontière des deux domaines ; aucun second coordinateur.

### 6.8 Contrôles C05 communs disponibles depuis la phase 7

Dossier actif `mcl/london-controles-fondamentaux/`, source `xpbots.fondamental`, tests
`tests/robot/london_fondamental/` : cinq couches figées, 62 tests propres. L'esquisse historique
`mcl/controles-fondamentaux/` est préservée ; aucune nouvelle phase EMA n'est déclarée terminée.

0 définit les messages et versions immuables, JSON strict, devises C05 et classification HIGH
externe versionnée ; 1a valide D-11 sans état ; 1b garde l'historique D-12 et les heures de connaissance ;
2 gère séquences, interruptions explicites, heartbeat et expiration ; 3 implémente le port canonique
`PermissionsFondamentales(commun, convertir_serveur, etat=None)`. Les signatures exactes et états
exportables sont dans les contrats publics. Le convertisseur serveur est une frontière injectée
qualifiée, jamais un décalage inféré du document. Le message garde la réception locale distincte
de known_at. Une relecture ne renouvelle rien ; un invalide ne détruit pas le dernier message valide.

Le port expose recevoir_permission, recevoir_calendrier, interrompre, avancer, prochaine_echeance_ms,
evaluer, clotures_obligatoires et etat. Les consultations historiques restent causales. FLATTEN valide
prime ; une HIGH connue ferme même si la permission est périmée. NO_NEW, direction incompatible,
absence et péremption bloquent sans liquidation ; un heartbeat manqué alerte sans invalider un
message encore valide. Une nouvelle séquence valide résout une interruption explicite.

La composition Python `composer_rejeu_papier` exige un contrôle réel, ou le scénario neutre explicite ;
ces choix sont exclusifs. `SourceFondamentaleScenario` livre les `PaquetFondamental` synthétiques
à leur réception exacte. Les échéances C05 rejoignent celles du coordinateur sans nouvelle cotation.
Le journal conserve les vrais messages, réceptions et versions, ainsi que les alertes de suivi. Le moteur démarre au temps du coordinateur : les échéances d’un C05 restauré avant le premier tick sont observées à cet instant sans recul de l’horloge papier ; un C05 futur au démarrage est refusé.
L-14 passe sur les vrais flux et moteur London en été et hiver : demande à N−900 s et fill au tick
suivant. Sans cotation fraîche, C08 conserve demande prioritaire et protections jusqu'au marché
négociable ; le test distingue cette attente d'un retard de contrôle. La CLI reste un contrôle
technique neutre explicite ; fichiers réels et transport physique sont réservés à la phase 11.

Un défigeage correction de 1b a retiré une ligne blanche finale de son test après contrôle de l’index ; aucune signature ou règle ne change. L’AST est identique, puis gate, gel, mutations et archive sont rejoués.

Le contrôle de gouvernance de phase 7 passe ses huit étapes sur l'arbre de travail. Le test natif
du lanceur PowerShell passe également sur une archive exacte du commit initial `5b017cc` : la
limite de phase 6 conservée au §13.1 n'est pas reproduite dans cette vérification. Aucun des hooks
ou tests de gouvernance modifiés avant la requête n'est inclus dans le commit de phase 7.

### 6.9 Lecteur de contexte IA commun disponible depuis la phase 8

Dossier actif `mcl/london-contexte-ia/`, sources `xpbots.contexte_ia`, tests
`tests/robot/london_contexte_ia/` : quatre couches figées et CP2, 58 tests propres. L'esquisse
historique `mcl/contexte-ia/` est conservée. L'arbitrage R4/R5 et les deux cartes composites
désignent un seul lecteur ; aucun contrat amont ni squelette EMA n'a été modifié.

0 définit paramètres chargés, types immuables, JSON canonique et preuves originales ; 1 valide
taille avant analyse, JSON strict, schéma complet, hash, configuration, séquence, génération,
âge et tous les événements ; 2 conserve la dernière réception, les identités scellées et le
cache actif ; 3 implémente le vrai port du coordinateur. Le cache conserve les vetos validés
malgré un heartbeat vide ou un snapshot invalide. Une nouvelle séquence ne prolonge aucune
identité ; même après expiration, une réécriture d'un ID connu est refusée. Les preuves de
reprise sont revalidées depuis leurs octets à leur réception d'origine, sans renouvellement.

`LecteurContexte(parametres, PolitiqueVeto(bras_ia, execution_reelle=False,
validation_financiere=False), etat=None)` expose recevoir, avancer, evaluer,
prochaine_echeance_ms, description et etat. Evaluer rend la DecisionContexteIA canonique,
BLOCK avec ID ou NEUTRAL. Le bras de référence reste neutre ; en exécution réelle, le veto reste
neutre lorsque la validation financière exigée n'est pas acquise. NEUTRAL n'autorise jamais C05. La source physique et le service IA
restent futurs ; aucun LLM n'est appelé, même dans les tests.

S4/S5/S7 reçoivent le lecteur réel et sa `SourceSnapshotScenario` de `PaquetSnapshot` synthétiques.
Réceptions et expirations sont observées sans créer de cotation ni de bougie. Les preuves C09
gardent politique, ID, item, fournisseur, hash, première réception et échéance propre. L-15 passe
au vrai moteur London en été et hiver : veto sur 08:15, aucun rattrapage à 08:22, nouvelle cassure
de 08:30 étudiée et remplie ; réception tardive à 08:23 sans réécriture de 08:15. Un veto après
fill ne ferme pas la position ; FLATTEN C05 reste prioritaire. Le moteur reprend au temps du
coordinateur ; un cache restauré plus ancien est accepté sans recul, un état futur est refusé.

La référence `overlay_decision` reste inchangée et constitue un oracle partiel : elle retourne
au premier veto actif avant de valider la fin de la liste. Une fixture mixte valide puis
malformée prouve cette différence. Le lecteur rejette le snapshot entier selon A10/A12. Ne pas
affaiblir cette validation pour revendiquer une égalité universelle avec l'oracle. Les matrices
valides, corrompues, futures, périmées et en recul ainsi que le cache sont comparées réellement.

Les 851 tests, 30 contrôles projet, 288 contrôles de référence et 16 cartes strictes constituent
les preuves hors ligne. Les 15 modifications préexistantes sont préservées et hors publication.
Le bilan de phase 8 contient les commandes, l'inventaire, les mutations et les limites ; ses
rapports de travail sous `.local/reports/` ne remplacent pas le journal MCL versionné.

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
   `mcl/robot-london-v3/PLAN-MCL.md` §7 ; plan directeur : version d'un cran (phase 9 → **1.4.10**), date, phrase
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

## 9. Briefing de la phase 9 — orchestration

La phase 8 est achevée par le commit portant ce rapport. Attendre la demande explicite
« Commence et achève intégralement la phase 9 ». Lire le document 04 (phase 9), le document 02
§6.7, les règles C08/C09 et les contrats réels des données, du moteur, du coordinateur, de C05
et du lecteur IA. Appliquer orchestrateur, MCL, planification, London, risque, contrats IA,
causalité, cohérence et audit ; vérifier le code réel et ajuster la sélection.

Construire les trois couches 0, 1, 2 de l'artefact orchestration, contrats avant code et gels
inside-out. Le moteur de décision est unique et ne doit importer ni xpbots.london ni un moteur
de méthode : les fabriques de stratégies sont injectées (D-18). Réutiliser le coordinateur de
compte, les ports et décisions canoniques ; aucun deuxième C05 ou lecteur IA. Arbitrer toute
coexistence R4/R5 avant code et conserver les socles EMA/London distincts. Examiner l'esquisse
historique et les cartes avant de choisir le dossier actif et les tests.

L'ordre C08 traite les faits natifs puis sorties obligatoires avant admissions. Les bras
REFERENCE et IA possèdent chacun leur compte, positions, quotas et état ; mêmes données
causales, complément absent pour REFERENCE, LecteurContexte réel pour IA. Rejouer le journal
d'entrées synthétique sans réinférence et vérifier mêmes entrées → mêmes sorties. Tester
A14-9, A14-17 et C11.10, événements simultanés et indépendance des bras. La couture remplace
l'enchaînement minimal S4 et rejoue une journée en PAPER_AB sur fixtures, sans simulateur C10,
service distant ni source physique anticipés.

Sortie : trois unités gelées, bout en bout simple et PAPER_AB vert, gate intégral des deux
robots et ressources, mutations par couche et couture, documents, passation phase 10,
directeur 1.4.10, audit, commit français et push. Puis s'arrêter avec l'invitation
« passe à la phase 10 ». Ne lancer aucune API, aucun courtier ni qualification financière.

## 10. Leçons et pièges des phases 0 à 8

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

## 11. Aperçu des phases 9 à 13 (points d'attention)

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
- Démonstration du squelette : `PYTHONPATH=src python -m xpbots.app.rejeu_squelette --ticks <fichier.csv> --sortie <dossier> --tick-size EURUSD=0.00001 --contrat-papier EURUSD=1000,0.1,1,0.1 --scenario TECHNICAL_CONTROL_NEUTRAL` (répéter les paramètres d’instrument).

## 13. Contrôle de reprise (à faire avant tout changement)

1. La branche contient `9c39d23`, l’intégration `5e5e288`, ce rapport et le moteur `c2_moteur` ; vérifier
   le commit de phase 8 dans `git log` (après `27284c2`) et le récupérer depuis la branche publiée si nécessaire. Ne pas repartir
   de la seule ancienne branche de phase 3, qui ne contient ni coexistence ni moteur S02.
2. `mcl.py statut` indique « Toutes les couches sont figées » pour `mcl/noyau`,
   `mcl/london-donnees-temps` et `mcl/moteur-london`. Les quinze couches du coordinateur commun dans `mcl/london-execution-coordinateur`, les cinq couches C05 dans `mcl/london-controles-fondamentaux` et les quatre couches du lecteur IA dans `mcl/london-contexte-ia` sont aussi figées.
3. `python tools/run_london_tests.py` donne au moins 851 tests verts des deux lignées ; `python tools/verify_project.py` PASS ;
   `mcl.py --dossier mcl/robot-london-v3 verifier` VERT ; `git status --short` comparé à la fin de phase 8 : quinze modifications préexistantes de gouvernance,
   de hooks et de leurs tests, de `.gitattributes` et de `tests/robot/fixtures/squelette_ticks.csv` ont été préservées hors des commits des phases 7 et 8 ;
   tout autre écart doit être identifié et expliqué.
4. Sous Windows, conserver les octets LF de la fixture CSV lors d'un export pour les tests : employer
   `git -c core.autocrlf=false archive` pour obtenir les blobs exacts. Le réglage `core.autocrlf=true` avec
   l'ancienne règle CSV absente de la version commitée peut convertir cette fixture en CRLF ; ce cas a été
   reproduit sur le commit initial et ne vient pas du moteur London. La règle CSV ajoutée initialement dans
   le répertoire de travail reste une modification non commitée de l'utilisateur.
5. Tout écart est signalé dans la réponse avant de commencer, avec sa preuve ; il n'est jamais masqué.

### 13.1 Limite Windows historique observée lors de la clôture de phase 6

Lors de la clôture de phase 6, la gouvernance complète était à 7/8 : seul le test du lanceur PowerShell dépasse 120 s. L'échec
identique est reproduit sur le commit de départ `4213a07`, sans code de phase 6 ; les hooks et
leurs tests n'ont pas été modifiés. Les cinq portes applicables aux fichiers modifiés passent,
y compris le contrat de gouvernance. Les suites des robots et du projet passent sur les blobs
publiés. Voir le bilan du coordinateur §6.11 pour les preuves de travail. Ne pas annoncer 8/8,
ne pas retirer ce test et ne pas étendre ce constat à la qualification de plateforme de phase 13.
La phase 7 a rejoué le test avec succès, y compris sur le commit initial : ne pas présenter ce délai historique comme un échec courant. Les nouvelles preuves de gouvernance de phase 8 figurent dans son bilan.

## 14. Glossaire minimal

- **A_t** : ATR de la bougie t − 1 (référence de la décision sur t). **A_H1** : ATR H1 figé à 07:00 Londres.
- **Range** : les 20 M15 de `[02:00, 07:00)` Londres ; W = H − L.
- **Bougie enrichie** : bougie du noyau + TR, ATR, A, rang + jour et heures de Londres + jour UTC.
- **Couture** : point où un artefact remplace un segment minimal du squelette.
- **Défigeage** : levée tracée du gel d'une couche (`correction`, `extension`, `modification`).
- **Oracle** : fonction de `reference/` utilisée uniquement pour comparer dans les tests.

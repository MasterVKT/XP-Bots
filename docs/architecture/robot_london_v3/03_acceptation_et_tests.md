# 03 — Acceptation et stratégie de tests du robot London

Retour au [plan directeur](README.md). Cas d'acceptation : C11 (14 cas communs), S02.6 (8 cas London) et A14
(18 cas IA) de la [spécification 02](../../../livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md).
Les contrôles existants (`tests/check_technical.py`, `tests/check_llm.py`, `tools/verify_project.py`) ne sont
pas l'exécution de ces cas sur un robot : ils restent verts et inchangés.

## 1. Principes

1. **Deux catégories exactement** (MCL) : la catégorie 1 teste le contrat propre de la couche, frontières
   externes doublées, couches internes réelles et figées ; la catégorie 2 teste la jonction de la couche sur le
   bloc réel `{0 → k}` de l'artefact, sans doublure interne, par chemins représentatifs. Aucune
   sur-isolation.
2. **Régression intégrale à chaque gate** : toute la suite du robot (squelette compris), puis
   `python tools/verify_project.py`. La sélection de tests accélère le travail, elle ne remplace jamais le gate.
3. **Oracles** : `reference/technical.py` et `reference/llm_contracts.py` sont importés par les seuls tests.
   Valeurs flottantes comparées avec une tolérance explicite ; décisions comparées sur des fixtures éloignées des
   seuils ; cas d'égalité aux seuils testés avec l'arithmétique du robot.
4. **Valeurs** : les tests lisent les seuils dans la configuration chargée et en dérivent leurs cas limites ;
   seuls les exemples chiffrés de la spécification (S02.5, A07) sont repris tels quels, comme citations.
   Pour qu'une égalité au seuil soit réelle en flottant 64 bits, les fixtures utilisent des valeurs exactement
   représentables en binaire (fractions dyadiques).
5. **Données synthétiques seulement** : générées par du code de test ; aucun prix réel commité ; chaque fichier
   de fixture reste sous 1 Mio (contrôle de `tools/verify_project.py`).
6. **Déterminisme** : aucune horloge, aucun réseau, aucun hasard non semé ; les tests n'écrivent que dans des
   dossiers temporaires du système, jamais dans l'arbre suivi (l'empreinte d'arbre du gate MCL resterait sinon
   instable).
7. **Frontières réelles** : tests de contrat séparés, désactivés par défaut, activés explicitement sur le poste
   Windows (MT5 démo) ou pour des appels d'API approuvés ; leurs preuves vont dans le rapport de qualification.
8. **Rejouabilité** : rejouer un journal d'entrées dans le cœur doit rendre des sorties identiques (C11.14).

## 2. Conventions

- Fichiers : `tests/robot/<artefact>/test_cat1_c<couche>_<theme>.py` et
  `tests/robot/<artefact>/test_cat2_c<couche>_<theme>.py` ; squelette : `tests/robot/squelette/` ; outils de
  test (doublures des seules frontières externes) : `tests/robot/outils/`.
- Tests de contrat des frontières réelles : `test_contrat_<frontiere>_<theme>.py`, ignorés sauf si
  `XPBOTS_CONTRATS_MT5=1` (Windows, terminal connecté au compte démo Deriv) ou `XPBOTS_CONTRATS_API=1` (appels
  d'API réels : non autorisés au 05/11/2026, D-17, redemandés en phase 12).
- Lanceur `tools/run_robot_tests.py` (bibliothèque standard) : ajoute `src` au chemin d'import ; découvre les
  tests ; options `--artefact`, `--couche`, `--categorie 1|2` ; code de sortie non nul au moindre échec ; résumé
  écrit dans `.local/reports/robot_tests.json` (ignoré par Git).
- Chaque couche liste ses fichiers de tests dans le champ `contrats` de sa carte : ils sont figés avec elle.

## 3. Commandes de gate

Commandes à lancer depuis la racine du dépôt, sur une seule ligne chacune (présentées ici sur plusieurs lignes
pour la lecture) :

```text
python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/<artefact> gate --couche <id>
  --unitaire "python tools/run_robot_tests.py --artefact <artefact> --couche <id> --categorie 1"
  --integration "python tools/run_robot_tests.py --artefact <artefact> --couche <id> --categorie 2"
  --regression "python tools/run_robot_tests.py"
  --regression "python tools/verify_project.py"

python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/<artefact> figer --couche <id> --par agent
```

- Une couche de profondeur 0 n'a pas de catégorie 2 (rien en dessous) : l'option `--integration` est omise.
- Le gate exécute aussi la vérification d'architecture de la carte (imports interdits, invariant, parallèles,
  contrats figés). Rien ne change dans l'arbre entre un gate vert et le gel.
- Fin de phase : `mcl.py --dossier mcl/<artefact> gate --global --regression "python tools/run_robot_tests.py" --regression "python tools/verify_project.py"`,
  puis `mcl.py ... checkpoint` lorsque `statut` signale un checkpoint dû (tous les deux niveaux figés).
- Gate rouge : aiguillage mécanique de MCL (catégorie 1 rouge → correction locale ; catégorie 1 verte et
  intégration ou régression rouge → remontée de couches puis défigeage formel `correction` à la source).

## 4. Fabriques et doublures de test

| Outil | Rôle | Points de contrôle |
|---|---|---|
| Fabrique de ticks | À partir d'une liste de bougies voulues (symbole, ouverture, OHLC, spread), produire des ticks à des décalages fixes, l'événement de frontière, des intervalles vides, des trous, des ticks de même milliseconde ordonnés, des jours de changement d'heure | Reproductible, sans hasard |
| Fabrique de journées London | Construire une journée complète avec un range voulu, un historique H1 d'au moins 300 bougies de TR constant pour obtenir exactement l'A_H1 voulu, et un historique M15 de TR constant pour obtenir l'A voulu | Bougies dont la clôture précédente reste dans `[L, H]`, donc TR = H − L |
| Courtier scénarisé | Répondre aux commandes selon un scénario : accusé, remplissage total ou partiel, refus, absence de réponse puis rapprochement, protections présentes ou absentes | Doublure de la frontière « exécution du courtier » |
| Calculateur paramétré | Implémenter le port de calcul (profit, marge, contrôle, spécifications, compte) avec des formules et des frais paramétrés, frais minimaux non linéaires compris | Doublure de la frontière « calculs du courtier » |
| Faux module `MetaTrader5` | Exposer les fonctions et constantes utilisées par l'infrastructure, avec retours scénarisés | Catégorie 1 de `infrastructure` |
| Messages et calendriers | Produire des messages `fundamental-permission-v1` et des versions de calendrier avec heures de connaissance | Cas tardifs, futurs, expirés |
| Snapshots | Produire des snapshots valides ou altérés ; empreinte comparée à `make_snapshot` de la référence | Corruption, futur, recul, âge |
| Ouvreur HTTP factice | Simuler Groq, Gemini, OpenAI et les flux RSS (codes 200, 401, 403, 429, 5xx, délais) | Catégorie 1 de `service-ia` |

## 5. Affectation des cas d'acceptation

### 5.1 C11 — cas communs

| Cas | Énoncé | Artefact et couche | Cat. | Scénario |
|---|---|---|---|---|
| C11.1 | Modifier une bougie future ne change aucune décision passée ; H1 partielle invisible | `donnees-temps` 3 ; `moteur-london` 2 ; `orchestration` 2 | 2 | Coupe à plusieurs instants, modification des bougies postérieures, décisions identiques avant la coupe ; égalité avec `london_setups` restreint aux décisions antérieures (comme `tests/check_technical.py`) |
| C11.2 | Spread au plafond admis ; TTL exactement atteint expiré ; clôture à la fin de fenêtre interdite ; égalité d'EMA | `execution-coordinateur` 0c ; `donnees-temps` 0b ; `moteur-london` 2 | 1 | Spread égal au plafond du symbole ; instant égal à clôture + TTL ; bougie close à 11:00 ; le cas EMA relève du robot 1 |
| C11.3 | Tick de frontière hors de l'OHLC précédent ; première cotation reçue après clôture seule exécutable | `donnees-temps` 1a ; `execution-coordinateur` 6 ; `journal-rejeu` 1b | 1, 2 | Tick exactement à T+900 s, extrême du tick hors de l'ancienne bougie, entrée sur ce tick |
| C11.4 | Été et hiver Londres ; jours UTC et Londres distincts ; aucune entrée le dimanche | `donnees-temps` 0b ; `moteur-london` 2 ; `execution-coordinateur` 1b | 1, 2 | Scénarios L-02 à L-05 ; base quotidienne UTC distincte du jour Londres |
| C11.5 | Achat à l'Ask et sortie au Bid, vente au Bid et sortie à l'Ask, spread compté une fois | `execution-coordinateur` 0d, 2a ; `journal-rejeu` 1b | 1 | Comparaison à `rounded_levels` ; distance de risque égale à D + 2g, jamais D + S + 2g |
| C11.6 | Position minimale au-delà de 0,50 USD de risque à 100 USD refusée, sans arrondi à la hausse | `execution-coordinateur` 3 | 1 | Scénario L-01 : 1 000 unités → 0,80 USD, refus ; 100 unités → 0,08 USD, admis si la grille le permet |
| C11.7 | Frais minimaux et non linéaires, réserve de glissement, marge cumulée, positions externes, contrats micro | `execution-coordinateur` 2a, 3 ; `infrastructure` 2c | 1, 2, contrat | Commission minimale par ordre qui rend le risque non linéaire ; deuxième position qui dépasse la marge ; position externe présente → blocage |
| C11.8 | Permissions expirées, futures ou incompatibles bloquées ; message neutre explicitement valide admis ; `FLATTEN` prioritaire | `controles-fondamentaux` 1a, 2, 3 ; `execution-coordinateur` 5a, 6 ; `orchestration` 2 | 1, 2 | Messages à la borne d'expiration, futurs d'une milliseconde, sens incompatible ; `FLATTEN` pendant une position |
| C11.9 | Annonce à N : début inclus, fin exclue ; calendrier révisé tardivement sans réécriture du passé | `controles-fondamentaux` 1b ; `journal-rejeu` 2 | 1, 2 | Entrée à N − 900 s refusée et à N + 900 s admise ; version tardive appliquée seulement après sa connaissance |
| C11.10 | Signaux simultanés de deux robots : réservations atomiques, priorité, symbole unique, pas de fusion | `execution-coordinateur` 2b, 6 ; `orchestration` 2 | 1, 2 | Signaux `LONDON_V3` et `EMA_V3` construits à la main comme données (le robot EMA n'existe pas encore) |
| C11.11 | Remplissage partiel, accusé ambigu, redémarrage après envoi, position préexistante inconnue, échec de protection : aucun doublon | `execution-coordinateur` 4, 5b, 6 ; `infrastructure` 2d | 1, 2, contrat | Chaque scénario du courtier scénarisé, puis sur compte démo en sous-étape 13.2 |
| C11.12 | Gap au stop, SL et TP à la même milliseconde avec séquence connue, flux absent à l'heure de sortie : résultat causal | `journal-rejeu` 1b ; `execution-coordinateur` 5a | 1, 2 | Exécution au premier prix disponible après le gap ; aucune exécution reconstruite à un prix disparu |
| C11.13 | Arrêts quotidien et global et durée maximale sur fonds propres, frais et flottant compris ; un redémarrage ne réinitialise pas l'arrêt | `execution-coordinateur` 1b, 5a, 5b ; `points-entree` 1a | 1, 2 | Seuils exactement atteints ; arrêt persistant après redémarrage |
| C11.14 | Égalité des décisions entre moteur de référence et robot de plateforme | `orchestration` 2 ; `points-entree` ; phase 13.2 | 2, contrat | Rejeu du journal d'entrées d'une séance PAPER ou DEMO : commandes et enregistrements identiques |

### 5.2 S02.6 — cas London

| Cas | Énoncé | Artefact et couche | Cat. | Scénario |
|---|---|---|---|---|
| S02.6-1 | Exactement 20 bougies pour `[02, 07)` en été et en hiver ; les bougies de 07:00 et suivantes n'affectent jamais le range | `donnees-temps` 0b ; `moteur-london` 1a, 2 | 1, 2 | L-02, L-03, L-09 |
| S02.6-2 | W/A_H1 exactement 0,5 ou 4 admis ; H1 partielle ou close après 07:00 exclue du gel ; réception tardive jamais disponible pour une décision antérieure | `moteur-london` 1b, 2 | 1, 2 | L-06, L-07 |
| S02.6-3 | Signal dès 08:15 et jusqu'à 10:45 ; aucune entrée sur clôture 11:00 | `moteur-london` 2 | 1 | L-02, L-03 |
| S02.6-4 | Prix déjà hors du range avant 08:00 admis sur une nouvelle bougie valide ; pas de croisement récent exigé | `moteur-london` 1c, 2 | 1 | L-09 |
| S02.6-5 | Doji, corps < 40 %, clôture insuffisamment proche de l'extrême ou TR > 2,5 A refusés | `moteur-london` 1c | 1 | L-10 |
| S02.6-6 | Stop local à trois composantes, conversion short en Ask et objectif 2D | `moteur-london` 1d ; `execution-coordinateur` 0d | 1 | L-01, L-11 ; comparaison à `london_signal` et `rounded_levels` |
| S02.6-7 | Remplissage partiel compte le sens ; ordre refusé sans remplissage ne le compte pas ; deuxième entrée du même sens interdite | `moteur-london` 1e, 2 ; `execution-coordinateur` 4 | 1, 2 | L-12 |
| S02.6-8 | Après un stop long, nouvelle vente seulement sur nouveau signal clos ; aucune inversion instantanée | `moteur-london` 2 ; `execution-coordinateur` 6 | 2 | L-12 ; aucun ordre au moment du stop |

### 5.3 A14 — cas IA

| Cas | Énoncé abrégé | Artefact et couche | Cat. |
|---|---|---|---|
| A14-1 | Un appel API de 20 s ne bloque ni le TTL, ni les protections, ni les sorties | Cœur sans réseau (cartes) ; `orchestration` 2 ; `points-entree` 1a (service lent simulé) | 2 |
| A14-2 | Une réponse arrivée après une bougie ne change pas la décision prise avant | `contexte-ia` 3 ; `orchestration` 2 | 1, 2 |
| A14-3 | Une décision conditionnelle ou historique n'est pas une décision actuelle | `service-ia` 1b | 1 |
| A14-4 | Citation inventée, `item_id` étranger, clés en trop, doublons JSON, mauvais enums, sortie tronquée : aucun veto | `service-ia` 0c (oracle `parse_model_output`) | 1 |
| A14-5 | Un discours non programmé ne suffit pas ; acteur égal à la source ; décision monétaire annoncée | `service-ia` 1b (oracle `build_policy_event`) | 1 |
| A14-6 | Une décision programmée au calendrier n'ajoute pas de veto ; un calendrier invalide reste bloquant pour le socle | `service-ia` 1b ; `controles-fondamentaux` 1b | 1 |
| A14-7 | À publication + 900 s exactement, veto expiré ; un heartbeat neuf ne le prolonge pas | `contexte-ia` 2, 3 | 1 |
| A14-8 | Une panne API est neutre pour le complément ; une panne de C05 reste bloquante | `contexte-ia` 3 ; `execution-coordinateur` 6 ; `orchestration` 2 | 1, 2 |
| A14-9 | Risque, SL/TP, volumes minimaux, sorties horaires et priorités identiques avec ou sans IA | `orchestration` 2 (bras A/B sur entrées identiques) | 2 |
| A14-10 | Un veto refuse le signal selon A07, sans rattrapage après le TTL | `moteur-london` 2 ; `execution-coordinateur` 6 ; scénario L-15 | 2 |
| A14-11 | Les deux robots consomment un même événement sans second appel ni seconde facturation | `service-ia` 3 ; `journal-rejeu` 3 (allocation des coûts) | 2 |
| A14-12 | Deux requêtes simultanées ne dépassent pas le budget réservé | `service-ia` 1c (deux connexions concurrentes) | 1 |
| A14-13 | Une requête de coût inconnu conserve sa réserve ; un projet Gemini payant n'est pas appelé comme gratuit | `service-ia` 1c, 2b | 1 |
| A14-14 | Plafonds de tentatives, de tokens, d'API payante et global testés aux bornes | `service-ia` 1c, 2b (valeurs lues dans la configuration IA) | 1 |
| A14-15 | Aucun modèle local, appel d'outil, ordre, changement de taille ou appel facturé hors liste autorisée | `service-ia` 1d ; cartes (imports interdits) | 1 |
| A14-16 | Snapshot incomplet, corrompu, futur ou en recul refusé ; reprise sans réinférence | `contexte-ia` 1, 2 ; `service-ia` 2c ; `points-entree` 1a | 1, 2 |
| A14-17 | Les comptes A/B évoluent séparément à 100 USD ; performances et coûts rapprochés | `orchestration` 2 ; `journal-rejeu` 2, 3 | 2 |
| A14-18 | Une précision JSON de 100 % n'est jamais présentée comme un taux de réussite de trades | `journal-rejeu` 3 | 1 |

## 6. Scénarios London détaillés

| Id | Scénario | Attendu |
|---|---|---|
| L-01 | Exemple S02.5 : range H = 1,10000, L = 1,09800 ; A_H1 = 0,00080 ; bougie O = 1,09995, H = 1,10055, L = 1,09990, C = 1,10050 ; A = 0,00050 ; `tick_size` 0,00001 ; cotation d'entrée 1,10050 / 1,10060 | Achat ; B_SL = 1,09985 ; E = 1,10060 ; SL = 1,09985 ; D = 0,00075 ; TP = 1,10210 ; g = 0,000025 ; distance de risque 0,00080 ; 1 000 unités → 0,80 USD → `MIN_VOLUME_OR_RISK_REJECT` ; 100 unités → 0,08 USD |
| L-02 | Hiver, lundi 12/01/2026 | Range 02:00–07:00 UTC ; première décision 08:15 UTC ; dernière 10:45 UTC ; clôture 11:00 refusée ; sortie forcée 12:00 UTC |
| L-03 | Été, mercredi 01/07/2026 | Range 01:00–06:00 UTC ; première décision 07:15 UTC ; dernière 09:45 UTC ; sortie forcée 11:00 UTC |
| L-04 | Lundis 30/03/2026 et 26/10/2026, lendemains de changement d'heure | 20 bougies de range ; correspondances UTC correctes |
| L-05 | Samedi et dimanche 05/07/2026, ticks du dimanche soir après l'ouverture | Aucun range, aucune entrée ; motif `OUTSIDE_SESSION` |
| L-06 | W = 0,5 × A_H1 et W = 4,0 × A_H1 exactement (valeurs dyadiques), puis juste en dehors | Admis aux bornes, refusé au-delà (`RANGE_HORS_BORNES`) |
| L-07 | Gel H1 : H1 partielle à 06:59, H1 close à 08:00, H1 de 06:00–07:00 reçue à 08:20, seulement 299 H1, ATR nul, H1 de 07:00 invalide | Partielle et tardive jamais utilisées ; décision de 08:15 refusée, celle de 08:30 admise ; préchargement insuffisant ; refus ; repli sur la H1 valide close à 06:00 (P-09) |
| L-08 | Une bougie de range manquante, ou intervalle couvert sans tick | Aucune entrée ce jour sur ce symbole (P-02, P-03) |
| L-09 | Bougie de 07:00 avec un extrême hors range ; prix hors range avant 08:00 ; bougie de 08:15 valide | Range inchangé ; signal à 08:15 sans croisement récent |
| L-10 | Doji ; corps juste sous et exactement à `signal_body_fraction_min` ; clôture exactement à `signal_close_location_min` ; TR exactement à `maximum_signal_true_range_atr` × A et juste au-dessus ; clôture exactement à H_range + b | Refus, refus puis admis, admis, admis puis refus, refus (égalité ≠ cassure) |
| L-11 | Chacune des trois composantes du stop rendue contraignante ; distance exactement au maximum, puis au-delà ; miroir vendeur | B_SL correct pour chaque cas ; maximum admis ; `STOP_TOO_WIDE` au-delà ; symétrie |
| L-12 | Achat rempli partiellement ; ordre refusé ; deuxième achat ; vente sur nouveau signal après stop de l'achat ; troisième entrée | Quota achat consommé au premier volume ; refus sans consommation ; `DAILY_ENTRY_CAP` ; vente admise ; aucune troisième entrée |
| L-13 | Position London ouverte sur EURUSD pendant de nouvelles cassures EURUSD ; GBPUSD indépendant | `SYMBOL_BUSY` sur EURUSD ; GBPUSD évalué normalement |
| L-14 | Remplissage à 08:15 ; à 10:45 ; GBPUSD rempli à 10:00 avec annonce HIGH GBP à 12:00 Londres | Sortie à 10:15 (durée maximale) ; sortie à 12:00 Londres ; clôture à 11:45 (N − 900 s) |
| L-15 | Exemple A07 : décision BCE imprévue publiée à 08:07, classification reçue à 08:08, fin de veto à 08:22 ; réponse tardive reçue à 08:23 dans une variante | Cassure EURUSD de 08:15 refusée (`AI_CONTEXT_VETO`) ; bougie valide de 08:30 étudiée ; la variante ne bloque pas 08:15 |
| L-16 | Trou de flux de 09:00 à 09:20 pendant la fenêtre | Entrées bloquées (`DATA_GAP`) ; comportement après récupération selon l'arbitrage P-03 |
| L-17 | Cassures EURUSD et GBPUSD à la même clôture de 08:15 | EURUSD admis d'abord ; GBPUSD réévalué après réservation ; plafonds de réserve et de positions respectés |
| L-18 | Spread égal au plafond ; spread au-dessus puis amélioré avant le TTL ; instant exactement égal à clôture + TTL | Admis ; entrée sur la cotation améliorée ; `SIGNAL_EXPIRED` |
| L-19 | Écart d'entrée exactement à `max_entry_bid_gap_atr` × A, puis au-delà | Admis ; attente puis expiration si aucune cotation conforme |

## 7. Tests de contrat des frontières réelles

- **Convertisseurs d'exports de ticks** : en catégorie 1, fixtures reproduisant le format relevé par les sondes
  S-09 (export du terminal, heure du serveur) et S-10 (source tierce) ; attendus : fichiers canoniques
  identiques à une référence calculée à la main, ordre natif conservé, heure UTC exacte de part et d'autre
  d'un changement d'heure du serveur, tick sans Bid ni Ask connu écarté et journalisé ; en contrat, conversion
  d'un mois réel sur le poste.
- **MT5 (poste Windows, compte démo, `XPBOTS_CONTRATS_MT5=1`)** : confirmation des sondes S-01 à S-10 ; lecture
  complète du profil C04 ; entrée protégée de volume minimal sur compte démo ; ajustement du TP ; clôture ;
  rapprochement après déconnexion provoquée ; détection d'une position externe ouverte à la main sur le compte
  démo ; chemin du dossier commun. Jamais sur un compte réel.
- **Fichiers et SQLite** : arrêt brutal pendant une transaction, puis reprise ; écriture et lecture concurrentes
  du snapshot et du dossier d'échange des permissions sous Windows (refus de partage, nouvelles tentatives,
  jamais de contenu tronqué accepté).
- **Service MQL5 d'export** : compilation sans avertissement ; un export réel comparé à la vue calendrier du
  terminal et à la fiche de séances du symbole ; format validé par les mêmes tests Python que les fixtures.
- **API LLM (`XPBOTS_CONTRATS_API=1`)** : une requête de conformité par route gratuite configurée, selon les
  gabarits A08, seulement après l'autorisation explicite que D-17 exige (non accordée au 05/11/2026) ; aucune
  route payante sans décision.
- **RSS** : lecture réelle des flux Fed et BCE si la politique réseau le permet ; refus BoE consigné.

## 8. Gardes transverses

- **Pureté du cœur** : test qui parcourt les paquets du cœur et refuse tout appel à l'horloge système,
  `datetime.now`, `datetime.utcnow`, `date.today`, ainsi que toute ouverture de fichier.
- **Architecture** : `mcl.py verifier` de chaque carte, exécuté par chaque gate et par l'intégration continue.
- **Configuration figée** : le robot refuse de démarrer sur une copie modifiée de l'un des deux exports, et sur
  une configuration où une option désactivée serait activée.
- **Non-recopie des valeurs** : en test seulement, des paramètres construits avec d'autres valeurs doivent
  changer le comportement attendu (preuve qu'aucun seuil n'est codé en dur) ; le chargeur de production, lui,
  refuse toute valeur différente des exports figés.
- **Secrets** : aucun motif de clé dans les journaux et rapports produits par les tests ; le contrôle de
  `tools/verify_project.py` couvre déjà `tests/`.

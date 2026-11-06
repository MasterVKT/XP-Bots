# Plan MCL — london-donnees-temps

> Document de travail MCL de l'artefact `london-donnees-temps` (paquet `xpbots.donnees`, phase 3 du
> [plan](../../docs/architecture/robot_london_v3/04_phases.md)). Cartographie de référence :
> [document 02, §6.2](../../docs/architecture/robot_london_v3/02_cartographie_mcl.md). Carte : `carte.json` ;
> contrats : `contrats/couche-<id>.md` ; traces : `journal.jsonl`.

## 0. Périmètre

- **Artefact** : ticks Bid/Ask → bougies M15 et H1 Bid causales, validées, enrichies de TR, ATR14, A_t, du rang
  de préchargement et des repères de Londres ; suivi des trous ; export et reprise des états (C03).
- **Échelle** : composant. **Mode** : pur, chair du composite (couche 1 de la carte composite), au-dessus du
  noyau figé. Hors périmètre : EMA et RSI (robot EMA, non construit), logique S02 (`moteur-london`), lecture des
  fichiers et du flux MT5 (`infrastructure`).

## 1. Applicabilité

Structure connaissable (C03, P-01, P-02, P-03, P-10, fonctions `wilder`, `add_indicators` et
`local_decision_in_window`) ; contrats stabilisables (règles figées) ; rien à construire pour comprendre.
Verdict : applicable. Signaux surveillés : divergence, défigeage en chaîne.

## 2. Étape 1

1. **Finalité** : ne jamais exposer une donnée avant sa disponibilité réelle ; bougies identiques à C03.2 ;
   indicateurs identiques aux récurrences de C03.10 et C03.11 ; trous signalés, jamais comblés.
2. **Entrées** : ticks du noyau (heures fournisseur et réception, numéro, Bid, Ask), états de connexion,
   horaires de cotation du noyau, registre de couverture historique, configuration figée. **Sorties** : bougies
   enrichies M15 et H1, changements d'état de trou, anomalies de données, état exportable.
3. **Contraintes** : bibliothèque standard ; `zoneinfo` pour `Europe/London` ; flottants 64 bits dans l'ordre
   des récurrences ; aucune horloge, aucun fichier.
4. **Point d'insertion** : segment S2 du squelette (`xpbots.donnees.squelette`), remplacé en fin de phase.

Arbitrages intégrés : P-01 (1c), P-02 (2a), P-03 et P-10 (2b, et 3 pour la reprise).

## 3. Carte

| Couche | Unité | Sous-paquet | Dépend de (réel, déclaré) |
|---|---|---|---|
| 0a | `types_donnees` | `c0a_types` | — |
| 0b | `sessions_londres` | `c0b_sessions` | — |
| 1a | `constructeur_bougies` | `c1a_constructeur` | 0a |
| 1b | `indicateurs` | `c1b_indicateurs` | 0a |
| 1c | `couverture_flux` | `c1c_couverture` | 0a |
| 2a | `validation_bougies` | `c2a_validation` | 0a, 1a, 1c |
| 2b | `etat_indicateurs` | `c2b_etat_indicateurs` | 0a, 1b |
| 3 | `flux_bougies` | `c3_flux` | 0a, 0b, 1a, 1c, 2a, 2b |

Groupes parallèles : 0a ∥ 0b ; 1a ∥ 1b ∥ 1c ; 2a ∥ 2b. Toutes les règles de `mcl.py` en mode strict, divergence
comprise (leçon de la phase 2 : chaque dépendance directe réelle est déclarée, y compris vers les types de 0a).
Interdits déclarés (document 02, §8) : horloge, fichiers, réseau, SQLite, fils, processus, hasard, chargement
dynamique, `MetaTrader5`, `reference`, paquets en aval ou parallèles et le segment du squelette.

## 4. Contrats, gate, checkpoints

Fiches : `contrats/couche-<id>.md`. Tests : `tests/robot/london_donnees_temps/test_cat<1|2>_c<id>_<theme>.py`. Gate :
document 03, §3, avec `--artefact london-donnees-temps`. Checkpoints après les niveaux 1 et 3. Gardien de la carte :
l'utilisateur ; défigeages par `mcl.py defiger`.

## 5. Bilan (06/11/2026)

- **Couches** : 0a, 0b, 1a, 1b, 1c, 2a, 2b et 3 construites dans l'ordre de `mcl.py statut`, chacune avec son
  contrat finalisé, ses tests de catégorie 1 (et de catégorie 2 au-dessus de la profondeur 0), un gate vert avec
  régression intégrale (suite du robot et `tools/verify_project.py`), puis figée. Checkpoints après les niveaux 1
  et 3 ; gate global vert ; `verifier` vert, divergence stricte comprise ; 71 tests propres à l'artefact.
- **Défigeages** : deux, tracés au journal. (1) 1a, `extension` : export et import de l'état complet du
  constructeur, bougie ouverte comprise, exigés par la reprise exacte de la couche 3 (C03.7 : reprendre le même
  état et ne traiter que les bougies nouvelles) ; aucune signature existante modifiée. (2) 2b, `correction` : une
  mutation retirant la clôture de l'empreinte chaînée restait verte ; la spécification exécutable calcule
  désormais `h_n` exactement selon la formule du contrat et vérifie la sensibilité à chacun des quatre prix.
- **Choix de conception arrêtés dans les contrats** : la H1 close à t précède la M15 close à t ; l'état de trou du
  symbole est celui de la M15 (les changements du validateur H1 ne sont pas émis) ; un tick antérieur à
  l'ouverture M15 courante n'est agrégé dans aucune unité ; `jour_londres` et `jour_utc` sont ceux de l'ouverture
  de la bougie ; l'état exporté est signé par l'empreinte canonique de l'export technique et ne contient ni
  horaires ni couverture (une coupure non couverte reste un trou à la reprise).
- **Contrôles dérivés des sources** : égalité avec `local_decision_in_window` sur plus de 20 000 instants de 2019
  à 2027 et sur chaque M15 de semaines d'hiver, d'été et de changement d'heure ; 18 changements d'heure, tous le
  dimanche à 01:00 UTC ; exactement `expected_range_m15_bars` ouvertures de range par jour, en été comme en
  hiver ; TR, ATR et A égaux à `add_indicators` (tolérance relative 1e-12) en M15 et en H1 ; H1 égales à
  l'agrégation des M15 ; rangs P-10 (999 à la 1 000e M15 valide, 299 à la 300e H1) ; invariance par préfixe
  (C11.1) ; reprise identique à un traitement continu à toute coupure.
- **Vérification adversariale** (copie jetable hors du dépôt) : vingt-quatre mutations (une ou plusieurs par
  couche, plus les segments S3, S4 et S5 du squelette), toutes détectées par la suite après la correction de 2b.
- **Couture** : segment S2 remplacé (`xpbots.donnees.squelette` supprimé) ; le moteur minimal construit un
  `FluxBougies` par symbole ; contrat de stratégie `sur_bougie(BougieEnrichie)` ; hypothèse de marché du
  squelette en rejeu ; trous et anomalies journalisés en `ALERTE` ([registre des coutures](../squelette/COUTURES.md)).

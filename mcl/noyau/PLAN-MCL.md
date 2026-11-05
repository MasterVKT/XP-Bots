# Plan MCL — noyau

> Document de travail MCL de l'artefact `noyau` (paquet `xpbots.noyau`, phase 2 du
> [plan](../../docs/architecture/robot_london_v3/04_phases.md)). Cartographie de référence :
> [document 02, §6.1](../../docs/architecture/robot_london_v3/02_cartographie_mcl.md). Carte : `carte.json` ;
> contrats : `contrats/couche-<id>.md` ; traces : `journal.jsonl`.

## 0. Périmètre de l'artefact

- **Artefact** : types et règles partagés, purs, sans entrée-sortie, réutilisables par le futur robot EMA ;
  lecture stricte des deux exports figés à partir d'octets fournis par la coquille.
- **Échelle** : composant. **Mode** : pur, chair du composite `mcl/robot-london-v3/` (couche 0 de la carte
  composite).
- **Règle de périmètre** : ordre de livraison fixé par le plan (document 04) ; MCL ne gouverne que l'ordre des
  couches de cet artefact. Hors périmètre : toute logique de méthode, de risque ou d'exécution (artefacts
  `donnees-temps`, `moteur-london`, `execution-coordinateur`).

## 1. Test d'applicabilité

| Question | Réponse | Justification |
|---|---|---|
| 1. Structure connaissable ? | Oui | Types fixés par C03, C04, C05, C06, C08, C09 et A07 ; exports figés ; table des motifs du document 01, §9.3 |
| 2. Contrats stabilisables tôt ? | Oui | Valeurs figées (C01, C02) ; arbitrage P-07 arrêté |
| 3. Construire pour comprendre ? | Non | Aucune inconnue technique : bibliothèque standard seulement |

Verdict : applicable. Signaux à surveiller : divergence entre carte et code ; défigeage en chaîne.

## 2. Étape 1 — Comprendre la cible

1. **Finalité** : fournir aux autres artefacts des types validés et une configuration figée typée, pour que
   toute valeur vienne des exports et que tout enregistrement C09 soit canonique.
2. **Entrées** : octets des deux exports et de `docs/validation/conservation_ressources.json` ; champs lus du
   courtier ; textes et instants. **Sorties** : objets immuables validés, empreintes, lignes JSON canoniques.
3. **Contraintes** : Python 3.13, bibliothèque standard, aucune horloge, aucun fichier, aucun réseau, aucun
   hasard ; flottants 64 bits pour les grandeurs de signal, décimaux sur la grille pour les prix exécutables et
   les montants (document 01, §6).
4. **Nature** : projet neuf. **Point d'insertion** : types minimaux du squelette S1 et S6
   (`xpbots.noyau.squelette`), remplacés en fin de phase par extension tracée
   ([registre des coutures](../squelette/COUTURES.md)).

Arbitrage intégré : P-07 (motifs fermés et détails énumérés, couches 1c et 2).

## 3. Étapes 2 à 4 — Unités et carte

Unités, responsabilités, entrées et sorties, dépendances : document 02, §6.1. Question-test posée unité par
unité : `instant`, `nombres` et `configuration` se construisent seules (feuilles) ; `marche` a besoin des
instants et des décimaux ; `instrument` des instants, des décimaux et de la configuration (compte attendu) ;
`domaine` des instants ; `journal` de tous les types qu'il sérialise.

| Couche | Unité | Sous-paquet | Dépend de |
|---|---|---|---|
| 0a | `instant` | `xpbots.noyau.c0a_temps` | — |
| 0b | `nombres` | `xpbots.noyau.c0b_nombres` | — |
| 0c | `configuration` | `xpbots.noyau.c0c_configuration` | — |
| 1a | `marche` | `xpbots.noyau.c1a_marche` | 0a, 0b |
| 1b | `instrument` | `xpbots.noyau.c1b_instrument` | 0a, 0b, 0c |
| 1c | `domaine` | `xpbots.noyau.c1c_domaine` | 0a |
| 2 | `journal` | `xpbots.noyau.c2_journal` | 0a, 0c, 1a, 1b, 1c |

Groupes parallèles : 0a ∥ 0b ∥ 0c ; 1a ∥ 1b ∥ 1c. `mcl.py analyser` (05/11/2026) : profondeurs identiques au
document 02, aucune divergence, aucun cycle.

## 4. Encodage de la carte

`mcl.py verifier`, toutes les règles en mode strict, divergence comprise (depuis le défigeage du 05/11/2026). Interdits déclarés
en frontières sans couche autorisée (document 02, §8) : horloge, fichiers, réseau, SQLite, fils d'exécution,
processus, hasard, chargement dynamique, `MetaTrader5`, `reference`, tous les paquets `xpbots` en aval ou
parallèles et le module du squelette `xpbots.noyau.squelette`. Chaque couche est un sous-paquet :
`__init__.py` (interface publique, figée) et `_impl.py` (implémentation, révisable à comportement constant).

## 5. Contrats et frontières

Esquisses puis fiches finalisées : `contrats/couche-<id>.md`. Aucune frontière externe réelle : le noyau
reçoit des octets et des champs ; aucune doublure n'est nécessaire.

## 6. Plan de construction et de gate

| Couche | Catégorie 1 | Catégorie 2 | Statut |
|---|---|---|---|
| 0a, 0b, 0c | `tests/robot/noyau/test_cat1_c0<x>_*.py` | — (profondeur 0) | voir `mcl.py statut` |
| 1a, 1b, 1c | `tests/robot/noyau/test_cat1_c1<x>_*.py` | `tests/robot/noyau/test_cat2_c1<x>_*.py` | voir `mcl.py statut` |
| 2 | `tests/robot/noyau/test_cat1_c2_journal.py` | `tests/robot/noyau/test_cat2_c2_journal.py` | voir `mcl.py statut` |

Commandes de gate et de gel : [document 03, §3](../../docs/architecture/robot_london_v3/03_acceptation_et_tests.md),
avec `--artefact noyau`. Régression intégrale : `python tools/run_robot_tests.py` et
`python tools/verify_project.py`.

## 7. Checkpoints et gouvernance

Checkpoint après le niveau 1 (deux niveaux figés). Profil solo ; gardien de la carte : l'utilisateur ; tout
changement de contrat figé passe par `mcl.py defiger` avec nature et motif.

## 8. Bilan (05/11/2026)

- **Couches** : 0a, 0b, 0c, 1a, 1b, 1c et 2 construites dans l'ordre de `mcl.py statut`, chacune avec son contrat
  finalisé, ses tests de catégorie 1 (et de catégorie 2 au-dessus de la profondeur 0), un gate vert avec
  régression intégrale (suite du robot et `tools/verify_project.py`), puis figée.
- **Défigeages** : deux, de nature « correction », sur la couche 2, contrat d'interface inchangé.
  (1) La carte et la fiche omettaient la dépendance réelle de `journal` vers `instant` (0a), signalée en
  avertissement par `mcl.py verifier` après le gel : carte et fiche corrigées, test transverse ajouté (toute carte
  MCL vérifiée sans avertissement), divergence passée en mode strict. (2) Une mutation retirant un champ
  obligatoire de `CLOTURE` restait verte : la spécification exécutable exige désormais l'ensemble exact des champs
  obligatoires et le refus de chacun quand il manque. Après chacun : gate vert, nouveau gel.
- **Vérification adversariale** (copie jetable hors du dépôt) : treize mutations du noyau (une ou plusieurs par
  couche, plus la carte) et neuf du squelette, toutes détectées par la suite.
- **Checkpoint** après le niveau 1 : aucune révision nécessaire ; duplication assumée de petits validateurs
  entre couches parallèles (0c et 1c), faute de couche commune plus interne.
- **Contrôles dérivés des sources** : empreintes égales à la preuve de conservation et au `design_sha256` ; 73
  clés de `common` typées ; motifs égaux à la liste de C09 plus les deux codes de P-07 ; détails égaux, dans les
  deux sens, au tableau du document 01, §9.3 (une ambiguïté de ce tableau a été corrigée : une ligne du
  squelette attribuait ses deux détails aux deux motifs) ; types d'enregistrement égaux au document 08, §7 ;
  arrondis égaux à la sémantique de `rounded_levels`.
- **Couture** : les types minimaux du squelette (`xpbots.noyau.squelette`) sont remplacés par ceux du noyau
  (extension tracée de S1 et S6 dans le [registre des coutures](../squelette/COUTURES.md)) ; le squelette charge
  désormais la configuration par le chargeur de production, empreintes contrôlées.
- **Garantie** : le bloc {0 → 2} du noyau est testé, intégré et stable. Garantie non donnée : l'usage correct de
  ces types par les artefacts suivants, vérifié par leurs propres gates.

# Plan MCL — robot-ema-v3 (composite)

> Niveau application du robot 1 `EMA_V3`. Le détail complet (décisions, cartes, cas d'acceptation, phases) est
> dans le plan maître `docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md` ; ce fichier n'en garde que ce qui
> pilote le composite. Coutures : `COUTURES.md`. Points à valider : `INTERPRETATIONS.md`.

Au 06/11/2026, les couches pures du coordinateur de compte sont construites une seule fois dans
[london-execution-coordinateur](../london-execution-coordinateur/PLAN-MCL.md). La carte composite pointe
vers ses contrats ; les adaptateurs 0a conservent les types EMA existants. Cette disponibilité commune
ne déclare aucune nouvelle phase EMA achevée. L’esquisse historique `execution-coordinateur` ne doit
pas être implémentée en parallèle.

## 0. Périmètre

- **Artefact** : système du robot 1 (squelette `noyau` + `app`, et huit artefacts de chair).
- **Échelle** : application ; **mode** : composite (squelette outside-in, chair au protocole MCL intégral).
- **Règle de périmètre** : l'ordre de livraison est celui des phases du plan maître (dérivé du guide
  `docs/architecture/GUIDE_IMPLEMENTATION.md`), jamais celui de MCL.

## 1. Applicabilité

Applicable au niveau de chaque artefact (structure connaissable, contrats stabilisables, rien à construire pour
comprendre). Bénéfice dégradé assumé : frontières externes dominantes, couvertes par une même suite de contrats
contre doublures et contre le réel.

## 2. Étape 1 — Cible

1. Finalité : appliquer S01 et C03–C09 avec A07/A10/A12, journaliser selon C09, rejouer causalement (C10) et se
   qualifier sur un compte MT5 démo (C04), avec un service IA partagé (A04–A11).
2. Entrées : ticks Bid/Ask, caractéristiques du courtier, permissions fondamentales, calendrier, snapshot IA.
   Sorties : ordres protégés ou refus motivés, journal C09, rapports de rejeu et de qualification.
3. Contraintes : Python 3.13 ; `MetaTrader5` (Windows) seulement en infrastructure ; bibliothèque standard
   ailleurs ; `config/` figé ; aucune inférence locale ; `PAPER` puis `DEMO` ; jamais de compte réel.
4. Projet neuf.

## 3–5. Carte des artefacts (vérifiée par `mcl.py analyser`, zéro divergence le 2026-11-05)

| Couche | Artefact (paquet) | Dossier MCL | Phase |
|---|---|---|---|
| 0 | noyau (squelette) | — (CI du squelette) | 1 |
| 1a | donnees_temps | `mcl/donnees-temps/` | 2 |
| 1b (profondeur 3) | contexte_ia | `mcl/london-contexte-ia/` (commun) | 7 |
| 2a | moteur_ema | `mcl/moteur-ema/` | 3 |
| 2b | execution | `mcl/execution-coordinateur/` | 4–5 |
| 2c | fondamental | `mcl/london-controles-fondamentaux/` (commun) | 6 |
| 2d | service_ia | `mcl/service-ia/` | 10 |
| 3 | journal_rejeu | `mcl/journal-rejeu/` | 8 |
| 4 | infrastructure | `mcl/infrastructure/` | 9–10 (segments minimaux dès la phase 1) |
| 5 | app (squelette) | — (CI du squelette) | 1, enrichi à chaque phase |

## 6. Encodage

`mcl.py --dossier mcl/robot-ema-v3 verifier --mode strict` (dépendances entre artefacts) et
`mcl.py --dossier mcl/<artefact> verifier --mode strict` (dépendances entre couches), en CI dès la phase 1.
`MetaTrader5`, `sqlite3`, `urllib`/`http`/`ssl`/`socket` : couche 4 seulement ; `time` : couches 4 et 5.

## 7–8. Contrats et frontières

Coutures et ports : `COUTURES.md`. Contrats de couche : `mcl/<artefact>/contrats/couche-<id>.md` (esquisses).
Frontières externes, doublures et tests de contrat : plan maître, section 5.

## 9. Construction

Phases 0 à 11 du plan maître, arrêt obligatoire à la fin de chacune. Gate d'une couche :
`mcl.py --dossier mcl/<artefact> gate --couche <id> --unitaire "<cat. 1>" --integration "<cat. 2>" --regression
"python tools/run_robot_tests.py" --regression "python tools/verify_project.py"`, puis `figer`.

## 10–12. Checkpoints, gouvernance, bilan

Checkpoint tous les deux niveaux figés par artefact. Gardien des cartes et décideur des défigeages :
l'utilisateur. Bilan par `mcl.py rapport` à la clôture de chaque artefact.

## Journal des phases

| Phase | Date | Résultat |
|---|---|---|
| 0 — Cadrage | 2026-11-05 | Neuf cartes sans divergence, 60 esquisses de contrat de couche, coutures, registre R1–R17 soumis |
| 1 — Squelette | 2026-11-05 | Noyau (types, ports, motifs, journal C09, configuration), segments minimaux, rejeu `xpbots.app.rejeu`, lanceur `tools/run_robot_tests.py`, CI ; coutures finalisées ; gate global tracé |
| 2 — Données et temps | 2026-11-05 | Artefact `donnees-temps` construit et figé (couches 0, 1a, 1b, 1c, 2, 3 ; 6 gates verts, 2 checkpoints, aucun défigeage) ; branché à la place de l'agrégateur minimal ; coutures étendues (section 5 de `COUTURES.md`) ; R4–R6 appliqués |
| 3 — Moteur EMA | 2026-11-05 | Décisions R1–R18 prises par délégation (registre) ; R6′ : défigeage tracé de `donnees-temps` 3 (recalcul sur les bougies valides), re-figé ; artefact `moteur-ema` construit et figé (couches 0, 1a, 1b, 1c, 1d, 2, 3 ; 7 gates verts, 2 checkpoints) ; signaux identiques à `reference.technical.ema_setups` ; `MoteurEMA` branché à la place de la stratégie neutre (manifeste v3 avec `tick_size`, stockage mémoire) ; rejeu de bout en bout de 2 600 bougies : signaux refusés (`FUNDAMENTAL_INVALID` ou `ENVIRONMENT_NOT_READY`), `STOP_TOO_WIDE`, cooldown, point d'entrée en ligne de commande ; coutures étendues (section 5 de `COUTURES.md`) |

### Disponibilité commune après la phase 6 London

Le dossier actif `london-execution-coordinateur` contient désormais quinze couches figées, incluant
cycle C08, sorties et reprise. Le robot EMA doit consommer ces mêmes interfaces via 0a ; aucune
nouvelle phase EMA n'est déclarée réalisée et son squelette historique n'est pas modifié.

### Disponibilité commune après la phase 7 London

Les cinq couches C05 sous `xpbots.fondamental` sont figées dans le dossier actif commun
`london-controles-fondamentaux`, après arbitrage R4/R5. Les types et le port sont ceux du noyau
London et du coordinateur unique ; l'adaptateur EMA existant reste la frontière des domaines.
Le squelette EMA n'est pas recâblé et aucune phase EMA supplémentaire n'est déclarée terminée.

### Disponibilité commune après la phase 8 London

Les quatre couches du lecteur IA sont figées sous `xpbots.contexte_ia`, dossier actif
`london-contexte-ia`. Le port est celui du coordinateur commun ; les types temporels, de
configuration et de décision viennent du noyau canonique. La carte recalcule les profondeurs
des futurs consommateurs, sans renommer leurs identifiants. Le squelette EMA n'est pas recâblé
et aucune phase EMA supplémentaire n'est déclarée terminée. L'esquisse `mcl/contexte-ia/`
reste historique et ne doit pas être implémentée comme un second lecteur.

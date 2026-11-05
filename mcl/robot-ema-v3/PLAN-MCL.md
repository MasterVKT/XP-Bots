# Plan MCL — robot-ema-v3 (composite)

> Niveau application du robot 1 `EMA_V3`. Le détail complet (décisions, cartes, cas d'acceptation, phases) est
> dans le plan maître `docs/architecture/PLAN_IMPLEMENTATION_ROBOT_EMA_V3.md` ; ce fichier n'en garde que ce qui
> pilote le composite. Coutures : `COUTURES.md`. Points à valider : `INTERPRETATIONS.md`.

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
| 1b | contexte_ia | `mcl/contexte-ia/` | 7 |
| 2a | moteur_ema | `mcl/moteur-ema/` | 3 |
| 2b | execution | `mcl/execution-coordinateur/` | 4–5 |
| 2c | fondamental | `mcl/controles-fondamentaux/` | 6 |
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

# 13 — Référence de l'outil `scripts/mcl.py`

Outil en bibliothèque standard Python (≥ 3.8), sans dépendance, qui rend mécaniques les contrôles que la
méthode prescrit. Il ne remplace pas les outils d'architecture natifs (ArchUnit, import-linter…) : il les
**configure** (`exporter`) et ajoute ce qu'ils ne font pas (divergence, contrats figés, baseline protégée,
journal du gate, gel/défigeage, statut, rapport).

Invocation : `python3 <chemin-du-skill>/scripts/mcl.py [--racine .] [--dossier mcl] <commande> [options]`.
Codes de sortie : **0** succès ; **1** échec de contrôle (violation stricte, gate rouge, gel refusé,
divergence à l'analyse) ; **2** erreur d'usage ou de configuration. Une `carte.json` mal formée (racine non
objet, `id` manquant ou non textuel, profondeur non entière, liste écrite comme un texte…) est refusée avec un
message explicite (code 2), jamais interprétée silencieusement.

## Sommaire
1. Fichiers d'état
2. Schéma de carte.json
3. Commandes
4. Journal (format des entrées)
5. Séquences types
6. Intégration continue
7. Limites connues

---

## 1. Fichiers d'état (dossier `mcl/`, versionné avec le code)

| Fichier | Rôle |
|---|---|
| `carte.json` | Carte des couches (artefact de référence) : couches, unités, frontières externes, règles |
| `journal.jsonl` | Traces append-only : gates, gels, défigeages, checkpoints, baseline (auto-instrumentation) |
| `baseline.json` | Dette tolérée au jour J (cliquet), protégée par empreinte journalisée |
| `contrats/couche-<id>.md` | Contrats de couche (gabarit sept lignes) |
| `PLAN-MCL.md` | Plan de travail (étapes 0 à 8) |

Ne jamais éditer `journal.jsonl` ni `baseline.json` à la main : passer par les commandes.

## 2. Schéma de `carte.json`

| Champ | Type | Sens |
|---|---|---|
| `artefact` | objet | `nom`, `echelle` (tache, tranche, composant, application), `mode` (pur, composite), `description` |
| `langage` | texte ou liste | python, javascript, typescript, go, java, kotlin, csharp, php, dart, rust ; absent = toutes les extensions connues |
| `sources` | liste | répertoires de code analysés (relatifs à la racine) |
| `exclure` | liste | motifs glob de fichiers ignorés |
| `couches[]` | liste | une entrée par couche ou subdivision parallèle |
| `couches[].id` | texte | « 0 », « 1a », « 2 »… (unique) |
| `couches[].profondeur` | entier ≥ 0 | profondeur de dépendance ; même profondeur = couches parallèles |
| `couches[].chemins` | liste | répertoires (ou fichiers) qui appartiennent à la couche ; correspondance par préfixe de composants |
| `couches[].imports` | liste | préfixes de modules sous lesquels la couche est importée (paquet Python/Java, namespace .NET/PHP, chemin de module Go, `package:app/c0` Dart, `crate::c0` Rust, alias TS `@app/c0`) ; en Python, déduit des chemins si absent (en retirant la source) |
| `couches[].contrats` | liste | fichiers du contrat gelé (motifs glob) : fiche de contrat, interface publique, tests de la couche |
| `unites[]` | liste | unités fonctionnelles : `id`, `couche` (id déclaré), `responsabilite` (une phrase), `depend_de` (ids d'unités ou de frontières externes) |
| `externes[]` | liste | frontières externes : `id`, `imports` (bibliothèques ou modules de l'implémentation réelle), `couches_autorisees` (couche d'infrastructure) |
| `regles` | objet | mode par règle : `strict`, `warn` ou `off` pour `invariant`, `paralleles`, `externes`, `cycles`, `divergence` (warn par défaut), `contrats_figes` |
| `checkpoint_tous_les` | entier | nombre de niveaux figés déclenchant « checkpoint dû » (défaut 2 ; la méthode dit 2 à 3) |

Graphe des couches utilisé par `gate`, `figer`, `statut`, `rayon` : déduit des dépendances des unités ; pour
une couche sans unité, repli prudent sur toutes les couches de profondeur inférieure.

## 3. Commandes

| Commande | Rôle | Options principales |
|---|---|---|
| `init` | Crée `mcl/` (carte vide, journal, contrats/, PLAN-MCL.md, gabarit de contrat) | `--nom`, `--langage`, `--echelle`, `--mode`, `--sources`, `--force` |
| `analyser` | Étapes 3-4 : tri topologique, cycles (Tarjan), profondeurs, subdivisions parallèles, divergences carte/graphe, unités isolées ou sans responsabilité, racines multiples, frontières externes et consommateurs | `--json`, `--ecrire` (écrit des couches proposées si `couches` est vide) |
| `exporter` | Configuration d'outil d'architecture | `--outil importlinter|depcruise|archunit|deptrac|netarchtest`, `--sortie`, `--paquet-racine`, `--ancre` |
| `verifier` | Code réel contre carte : invariant, parallèles, frontières externes, cycles entre couches, divergence, contrats figés modifiés, baseline altérée | `--mode warn|strict` (force toutes les règles), `--json` |
| `rayon` | Consommateurs directs et transitifs (gouvernance) | `--couche ID` ou `--unite ID` |
| `gate` | Regression gate journalisé : refuse si une dépendance n'est pas figée ; vérifie l'architecture ; exécute catégorie 1, catégorie 2, suite intégrale ; aiguillage mécanique ; empreinte de l'arbre | `--couche ID` ou `--global`, `--unitaire CMD`, `--integration CMD`, `--regression CMD` (obligatoire, répétable) |
| `figer` | Gèle le contrat : exige dépendances figées, dernier gate vert **sur l'arbre courant** (même empreinte), au moins un fichier de contrat ; enregistre leurs empreintes | `--couche ID`, `--par NOM` |
| `defiger` | Levée formelle du gel, rayon calculé, circuit de gouvernance rappelé | `--couche`, `--nature extension|modification|correction`, `--motif` (obligatoire), `--par` |
| `checkpoint` | Journalise l'étape 8 | `--notes`, `--par` |
| `baseline` | Cliquet : créer (clé du gardien), resserrer (toujours permis), réinitialiser (clé du gardien) | `--creer|--resserrer|--reinitialiser`, `--par`, `--motif` |
| `statut` | Tableau des couches : statut, dépendances, dernier gate, **constructible maintenant** ; cascades à re-vérifier ; checkpoint dû ; défigeages ouverts | — |
| `rapport` | Traces → métriques (gates par couche et profondeur, aiguillages, coût cumulé de régression, défigeages par nature, corrections par couche, baseline, checkpoints) | — |

## 4. Journal

Une ligne JSON par événement, champ `date` (UTC) et `type` :
- `gate` : `couche` (ou null si global), `portee`, `profondeur`, `etapes[]` (`categorie`, `commande`, `code`,
  `duree_s`), `architecture` (`vert`, `violations_strictes`, `avertissements`), `resultat` (vert/rouge),
  `aiguillage` (regression_locale, interaction_ou_amont, indetermine), `motif_refus`, `empreinte` ;
- `figer` : `couche`, `profondeur`, `contrats` {fichier: sha256}, `par`, `empreinte` ;
- `defiger` : `couche`, `nature`, `motif`, `par`, `rayon` {directs, transitifs} ;
- `checkpoint` : `profondeur_max_figee`, `notes`, `par` ;
- `baseline` : `action` (creation, resserrement, reinitialisation), `nb`, `par`, `motif`, `sha256`.

## 5. Séquences types

Démarrage :
```
mcl.py init --nom <artefact> --langage <lg> --sources src
(remplir PLAN-MCL.md étapes 0 à 2 ; unites et externes dans carte.json)
mcl.py analyser --ecrire        # puis ajuster couches : chemins, imports, contrats
mcl.py analyser                 # jusqu'à zéro divergence
mcl.py exporter --outil <outil> --sortie <fichier>   # si un outil natif existe
```
Par couche (dans l'ordre que donne `statut`) :
```
(finaliser mcl/contrats/couche-<id>.md, implémenter, écrire tests cat.1 et cat.2)
mcl.py gate --couche <id> --unitaire "<cat.1>" --integration "<cat.2>" --regression "<suite intégrale>"
mcl.py figer --couche <id>
mcl.py statut
```
Ne rien modifier entre le gate vert et le gel (l'empreinte doit être identique ; sinon relancer le gate).

## 6. Intégration continue

Câbler en check bloquant de la branche d'intégration : `mcl.py verifier` (ou l'outil natif exporté) **et** la
suite de tests intégrale ; ou directement `mcl.py gate --global --regression "<suite intégrale>"`, qui unifie
architecture et régression fonctionnelle et journalise le résultat. Le journal étant versionné, préférer en CI
`verifier` + suite de tests (sans écriture) et réserver `gate`/`figer` au poste qui construit la couche. Mettre
les tests instables en quarantaine avant de rendre le check bloquant.

## 7. Limites connues

- Extraction d'imports statique : Python par arbre syntaxique (`ast`) ; autres langages par expressions
  régulières après retrait des commentaires. Non détectés : références pleinement qualifiées sans import (Java,
  C#), imports dynamiques calculés, réflexion, injection par configuration. Compléter par la revue de code.
- Imports JS/TS non relatifs : reconnus seulement s'ils correspondent à un préfixe `imports` déclaré (alias).
- L'outil vérifie la **structure** des dépendances, pas le respect sémantique des contrats (couvert par les
  tests).
- L'empreinte de l'arbre exclut les caches usuels (`__pycache__`, `node_modules`, `.pytest_cache`, `build`,
  `dist`, `target`…) et le journal ; un test qui écrit des fichiers dans le projet change l'empreinte (relancer
  le gate, ou écrire dans un répertoire ignoré).

# 04 — Encoder la carte : l'invariant devenu règle de build

Source : I.8 (A4), II.2, II.4, III.3, III.8. À faire juste après l'étape 4, avant la couche 0.

## Sommaire
1. Principe
2. La règle exacte à encoder
3. Les quatre conditions de l'encodage
4. Convention de modules par écosystème
5. Outillage par écosystème et génération avec mcl.py
6. Forme minimale sans outillage
7. Warn puis strict, règle par règle

---

## 1. Principe

Consigner la carte des couches dans la configuration d'un **outil de test d'architecture**, versionnée avec
le code. L'invariant devient une règle de build : toute unité d'une couche `k` qui référence une couche plus
externe fait **échouer le build**. La carte ne peut plus dériver du code réel. Trois contrôles deviennent
automatiques :
1. la **violation de l'invariant** ;
2. la **détection de cycles** (même outillage) ;
3. le **contrôle de divergence** (l'outil confronte le graphe qu'il calcule à la carte déclarée).

Dans la taxonomie de l'architecture évolutive (Ford, Parsons & Kua, 2017), c'est une **fonction de fitness
statique et atomique** : une mesure (références entre couches), une évidence (dépendance interdite), une
contrainte (l'invariant). MCL ne l'invente pas ; elle la **prescrit** et produit son entrée : une carte
justifiée par la dépendance. Un schéma au tableau ne fait échouer aucun build ; une carte issue de l'étape 4,
si.

## 2. La règle exacte à encoder

- Dépendances autorisées vers **n'importe quelle couche plus interne, à profondeur quelconque**.
- **Piège** : le réglage par défaut de certains outils propose « couche adjacente seulement ». Plus strict que
  l'invariant, il rejette du code parfaitement conforme. Ne jamais l'utiliser.
- Couches parallèles (même profondeur) : aucune dépendance mutuelle. Leur indépendance peut être encodée si on
  veut la garantir (recommandé : `mcl.py` et ses exports l'encodent par défaut).
- Frontières externes : l'implémentation réelle n'est importée que dans la couche d'infrastructure (règle
  dérivée de l'étape 6, encodable comme « module interdit » dans la plupart des outils).

## 3. Les quatre conditions de l'encodage

1. **Précondition de traçabilité.** Une couche correspond à une unité adressable par l'outil : package,
   module, namespace, répertoire. La convention **« une couche = un module nommé »** se fixe ici ; elle resservira
   en gouvernance (fichier de propriétaires déclaré sur les mêmes modules).
2. **Couches parallèles.** Les unités de même profondeur forment un même groupe de couche pour l'outil ; leur
   indépendance mutuelle peut être encodée.
3. **Portée du contrôle.** L'outil vérifie la **structure** des dépendances, pas le respect sémantique des
   contrats. L'enforcement couvre la moitié structurelle de l'invariant ; le protocole de test couvre l'autre.
4. **Outillage disponible.** Voir section 5. Dans tous les cas, la **carte déclarée reste l'artefact de
   référence**.

## 4. Convention de modules (recommandation d'outillage)

Nommer les modules de couche de façon à rendre la profondeur lisible, par exemple `c0_noyau`, `c1a_parser`,
`c1b_taxes`, `c2_enveloppe` (Python, Dart, Rust, Go), `com.acme.app.c0` (Java/Kotlin), `App.C0` (.NET),
`App\C0` (PHP), `src/c0/` (JS/TS). Placer les tests de chaque couche dans un emplacement adressable par couche
(`tests/c0/`, `tests/c1a/`…), pour pouvoir lancer séparément la catégorie 1 d'une couche, et déclarer ces tests
dans les fichiers de contrat de la couche (la suite de tests fait partie du contrat gelé). Cette convention est
une recommandation de mise en œuvre, non un texte du document de référence.

## 5. Outillage par écosystème

| Écosystème | Outil (cité par le document) | Génération `mcl.py exporter --outil …` | Points d'attention |
|---|---|---|---|
| Java | ArchUnit | `archunit` → classe JUnit 5 `MclCouchesTest.java` : `layeredArchitecture().consideringOnlyDependenciesInLayers().withOptionalLayers(true)` (couches externes encore absentes tolérées), une couche ArchUnit par couche MCL, `whereLayer(X).mayOnlyAccessLayers(couches plus internes)`, `mayNotAccessAnyLayer()` pour la profondeur 0, règle `slices().beFreeOfCycles()`, règles `noClasses()` pour les frontières externes (`allowEmptyShould(true)`) | Champ `imports` = paquet Java de chaque couche ; ArchUnit 1.x ; dépendances de test `archunit-junit5` + `junit-jupiter` |
| Kotlin | Konsist, detekt | (non généré) | Écrire l'équivalent : chaque couche ne dépend que de couches plus internes ; vérifier la sémantique exacte des assertions de l'outil dans sa documentation ; à défaut `mcl.py verifier` (Kotlin pris en charge) |
| PHP | Deptrac | `deptrac` → `deptrac.yaml` (collecteurs `directory`, `ruleset` listant pour chaque couche toutes les couches plus internes ; `~` pour la profondeur 0) | Champ `chemins` obligatoire |
| .NET | NetArchTest | `netarchtest` → classe xUnit, un test par couche : `ResideInNamespace(couche).ShouldNot().HaveDependencyOnAny(couches plus externes et parallèles)` | Remplacer `TypeAncre` par un type public de l'assembly (`--ancre`) |
| JS / TS | dependency-cruiser | `depcruise` → `.dependency-cruiser.cjs` : règles `forbidden` par couche (invariant, parallèles), frontières externes vers `node_modules/<paquet>/`, règle `circular` | En TypeScript : installer `typescript` dans le projet et, si des alias de chemins existent, ajouter `options.tsConfig.fileName` (sinon aucun module n'est analysé) |
| Python | import-linter | `importlinter` → `.importlinter` : contrat `layers` listé de l'enveloppe au noyau, chaque couche entre parenthèses (optionnelle : tolérée tant qu'elle n'existe pas), couches parallèles sur une même ligne séparées par `|` (indépendantes) ; contrats `forbidden` par frontière externe : source = paquet racine, `ignore_imports` pour la seule couche autorisée, `unmatched_ignore_imports_alerting = none`, `include_external_packages = True` | import-linter ≥ 2.0 ; déclarer les `imports` externes par leur nom de paquet de premier niveau ; lancer `lint-imports` depuis un répertoire où le paquet racine est importable (souvent `src/`) |
| Go, Rust, Dart/Flutter, mobile natif | aucun outil mûr dédié | — | Convention de modules + **lint personnalisé** + revue de code : utiliser `mcl.py verifier` en CI (Go, Rust et Dart pris en charge) |

Les exports produits par `mcl.py` pour import-linter (2.15), dependency-cruiser (16.10), ArchUnit (1.3.0)
et Deptrac (2.0.7) ont été vérifiés contre les outils réels, dans les trois phases que traverse une
construction MCL : couche 0 seule (couches externes absentes : aucune erreur), projet complet conforme
(contrats tenus), projet fautif (violations d'invariant, de parallèles, de frontière externe et de cycles
signalées). L'export NetArchTest suit la syntaxe documentée de l'outil sans avoir été exécuté : le compiler et
l'exécuter une première fois sur un cas fautif volontaire pour confirmer qu'il casse.

`mcl.py verifier` reste utile **même avec un outil natif** : il vérifie aussi la **divergence** (dépendance
réelle entre couches non justifiée par la carte des unités), les **contrats figés** (empreintes) et la
**baseline** — ce que les outils d'architecture ne font pas.

## 6. Forme minimale sans outillage

Carte versionnée (`mcl/carte.json` ou tableau dans le plan) + vérification des imports en revue de code.
L'encodage outillé devient le **standard dès qu'une intégration continue existe**.

## 7. Warn puis strict

Sur une base existante, déployer d'abord en **warn** (signaler sans bloquer) pour apprendre les signaux, puis
passer en **strict, règle par règle** (`regles` dans `carte.json` : `invariant`, `paralleles`, `externes`,
`cycles`, `divergence`, `contrats_figes`). Le mur de violations initial se franchit par la **baseline à
cliquet** (`08-gate-gouvernance-parallelisme.md`). N'exiger en strict que ce que le build vérifie.

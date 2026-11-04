---
name: mcl-matryoshka-construction-layers
description: "Ce skill doit être utilisé pour concevoir, programmer, développer, refactorer ou planifier rigoureusement tout logiciel (fonction, module, composant, service, algorithme, API, application web, mobile, CLI, robot, pipeline, code legacy), dans n'importe quel langage, selon la méthode MCL (Matryoshka Construction Layers, ex-« méthode Matryoshka », d'Eric Vekout) : construction inside-out par couches de profondeur de dépendance, chaque couche testée, validée et gelée avant la suivante, contrats avant le code, doublures aux seules frontières externes, regression gate intégral, carte des couches encodée au build, gel et défigeage tracés, checkpoints, mode composite pour une application entière. Déclencheurs : MCL, Matryoshka, poupées russes, couche par couche, inside-out, ordre de dépendance, carte des couches, regression gate, figer ou défiger un contrat, applicabilité, diagnostic par remontée de couches, adoption ou évaluation de MCL ; en anglais : build bottom-up by dependency layers."
---

# MCL — Matryoshka Construction Layers

## Objet

Appliquer intégralement et fidèlement la méthode MCL, telle que définie par son document de référence
(E. Vekout, août 2026), pour construire le code d'un artefact donné : partir de l'unité fonctionnelle la plus
fondamentale, puis ajouter des couches de complexité croissante, **chacune entièrement validée et gelée avant
que la suivante ne soit construite**, dans l'**ordre du graphe des dépendances, jamais dans l'ordre d'exécution
du flux**.

Le skill fournit : un flux de travail opérationnel (ci-dessous), treize références détaillées
(`references/`), des gabarits (`assets/gabarits/`) et un outil sans dépendance, `scripts/mcl.py`, qui rend
mécaniques les contrôles prescrits (carte, invariant au build, gate journalisé, gel, défigeage, baseline,
traces).

## Quand l'utiliser

- Construire un artefact dont la structure est **connaissable** : tâche ou tranche fonctionnelle, composant
  autonome (bibliothèque, service, moteur, algorithme), application entière (en mode composite), refactoring
  de code legacy (cas le plus naturel).
- Planifier l'ordre de construction, diagnostiquer un échec au gate, gouverner un changement de contrat,
  introduire MCL dans une équipe, expliquer ou évaluer la méthode.

Ne pas l'appliquer tel quel à un artefact **exploratoire** (structure non connaissable, contrats non
stabilisables, besoin de construire pour comprendre : recherche algorithmique, modèle d'apprentissage dont
l'architecture émerge, sensation de jeu, interaction inédite). Chemin : sonder d'abord (spike, prototype,
tranche-sonde jetables), puis reconstruire au protocole. Infrastructure pure (déploiement, configuration) :
approche plate ou outside-in.

## L'invariant et les règles non négociables

> **Une couche n'est jamais construite tant que toutes les couches dont elle dépend ne sont pas testées,
> validées et stables.**

1. **Ordre de dépendance, jamais de flux.** Pour chaque unité, poser la question-test : « Cette unité
   pourrait-elle être construite et testée même si toutes les autres n'existaient pas encore ? » Oui → feuille
   (couche 0 ou proche). Non → au-dessus de ce dont elle dépend. Les heuristiques (début de pipeline, fonction
   la plus profondément appelée) orientent, ne tranchent jamais ; « inverser le flux » est une autre règle
   fausse.
2. **Contrat avant code.** Esquisse pour toutes les unités pendant la cartographie ; finalisation par couche,
   juste avant de la construire, un niveau d'avance sur le premier consommateur, jamais plus. Exception :
   frontières externes finalisées tôt. Contrat minimal : besoin cartographié seulement (pas de paramètre
   spéculatif, pas de généricité « pour plus tard », pas d'indirection sans deuxième cas réel).
3. **Doublures uniquement aux frontières externes** (base de données, API tierce, paiement, système de
   fichiers…). Implémentation réelle uniquement dans la couche d'infrastructure, la plus externe.
4. **Exactement deux catégories de tests**, définies par leur cible : catégorie 1 = contrat propre de la couche
   (externe doublé ; couches internes réelles et figées par défaut, doublure interne seulement en option
   justifiée) ; catégorie 2 = jonction de la couche sur le bloc réel `{0 → k}`, sans doublure interne, par
   chemins représentatifs. Jamais de sur-isolation (`{k+1}`, puis `{k+1 + k}`…).
5. **Regression gate intégral à chaque couche** : la totalité de la suite existante repasse au vert avant le
   gel. La sélection de tests accélère la boucle interne, ne remplace jamais le gate.
6. **Le gel porte sur le contrat** (interface, comportements documentés, suite de tests de la couche), pas sur
   l'implémentation interne, révisable à comportement constant sous harnais complet. Tout changement de contrat
   ou correction de défaut passe par un **défigeage formel tracé**.
7. **Corriger à la source, jamais au symptôme.**
8. **Ne jamais présenter MCL comme statistiquement supérieure** à une autre approche. Typer les affirmations
   (établi / analyse mécaniste / hypothèse) ; dire ce qu'on achète et ce qu'on paie.

Garantie donnée : à tout instant, le bloc `{0 → k}` est testé, intégré, stable. Garantie **non** donnée : le
chemin de bout en bout avant l'enveloppe (retour produit tardif par construction ; d'où le mode composite à
l'échelle application).

## Flux de travail

Chemin de l'outil : `M="python3 <répertoire du skill>/scripts/mcl.py"` (exécuté depuis la racine du projet
cible). Consigner chaque sortie dans `mcl/PLAN-MCL.md` (gabarit copié par `init`).

### Phase 0 — Périmètre, échelle, applicabilité
1. Désigner l'**artefact** et son **échelle** (tâche/tranche, composant, application). Ne pas décider *quoi*
   livrer ni *dans quel ordre* : c'est le niveau produit (règle de périmètre).
2. Passer le **test en trois questions** au niveau de l'artefact (jamais du produit). Exploratoire → chemin
   spike puis reconstruction. Signaler les conditions de bénéfice dégradé (frontières externes dominantes,
   application sans composite).
3. Application entière → **mode composite** : squelette outside-in déployable dès le départ, puis chaque
   remplissage de chair = un artefact MCL distinct (cinq règles de couture).
Lire : `references/02-applicabilite.md` ; composite : `references/09-stacks-composite-positionnement.md`.

### Phase 1 — Cartographier (étapes 1 à 4)
1. **Étape 1** (seul moment outside-in) : quatre réponses — finalité au plus haut niveau ; entrées/sorties de
   l'enveloppe ; contraintes (langage, framework, performance, déploiement) ; greenfield ou refactoring. Ne pas
   prolonger au-delà. Demander à l'utilisateur ce qui ne se déduit pas du contexte.
2. **Étape 2** : 2.1 entrées/sorties du cadre ; 2.2 workflow détaillé et **objets intermédiaires** ; 2.3 liste à
   plat des unités (responsabilité en une phrase, entrée → transformation → sortie, au moins une relation) ;
   2.4 question-test unité par unité. Systèmes non-flux (2.5) : machine à états → composantes fortement
   connexes ; domaine événementiel → événements au passé + agrégats ; grand domaine → contextes bornés, une
   décomposition par contexte. Appliquer récursivement aux modules et unités non triviaux.
3. **Étape 3** : DAG explicite ; **contrôle de divergence** contre l'intuition de 2.4 ; frontières externes à
   part ; cycles brisés par interface (préférable) ou condensés en une couche.
4. **Étape 4** : carte des couches (0 = noyau … N = enveloppe), couches parallèles subdivisées (1a, 1b…) et
   **signalées** comme constructibles simultanément.
Outil : `$M init --nom … --langage … --sources …`, renseigner `unites`/`externes` dans `mcl/carte.json`,
`$M analyser --ecrire`, compléter `chemins`/`imports`/`contrats`, puis `$M analyser` jusqu'à **zéro divergence**.
Lire : `references/03-cartographie.md` (illustrations, heuristiques bornées, cycles, systèmes non-flux).

### Phase 2 — Encoder la carte (invariant devenu règle de build)
Créer un module par couche (« une couche = un module nommé »). Encoder la règle **« dépendances autorisées vers
n'importe quelle couche plus interne, à profondeur quelconque »** (jamais « adjacente seulement ») dans l'outil
de l'écosystème : `$M exporter --outil importlinter|depcruise|archunit|deptrac|netarchtest --sortie …` ;
Go, Rust, Dart, Kotlin ou absence d'outil : `$M verifier` en CI. Sur l'existant : mode warn, baseline à cliquet,
strict règle par règle.
Lire : `references/04-encodage-carte.md`.

### Phase 3 — Contrats et frontières externes (étapes 5 et 6)
Esquisser tous les contrats (`mcl/contrats/couche-<id>.md`, gabarit sept lignes). Pour chaque frontière
externe : contrat attendu (port), doublure minimale, usage dans toutes les couches internes, implémentation
réelle seulement en couche d'infrastructure, tests de contrat contre la dérive de fidélité. Déclarer dans
`contrats` de chaque couche : fiche de contrat, interface publique, tests de la couche.
Lire : `references/05-contrats-frontieres.md`.

### Phase 4 — Construire couche par couche (étape 7)
Pour chaque couche, dans l'ordre que donne `$M statut` (colonne « constructible maintenant ») :
1. finaliser le contrat ; 2. IMPLÉMENTER ; 3. TESTER (catégorie 1) ; 4. VALIDER (tous verts, sinon corriger
d'abord) ; 5. INTÉGRER sur le bloc réel ; 6. TESTER L'INTÉGRATION (catégorie 2, chemins représentatifs) ;
7. RÉGRESSER (suite intégrale) ; 8. FIGER.
Outil : `$M gate --couche <id> --unitaire "<cat. 1>" --integration "<cat. 2>" --regression "<suite intégrale>"`
puis, sans rien modifier entre-temps, `$M figer --couche <id>`.
**Exécuter réellement les tests** ; ne jamais annoncer un gate vert non exécuté. Un seul delta par gate. Les
couches parallèles peuvent s'écrire dans la même passe, chacune avec son gate et son gel.
Lire : `references/06-boucle-construction.md`.

### Phase 5 — Quand le gate est rouge
Aiguillage mécanique : catégorie 1 de la couche courante rouge → **régression locale**, corriger la couche
courante. Catégorie 1 verte mais intégration/régression rouge → **interaction ou défaut amont** : remontée de
couches (séquentielle ≤ N sondes, ou dichotomie ~log N) avec doublures de coupe jetables, supprimées sitôt le
niveau localisé. Protocole correctif : `$M defiger --couche k --nature correction --motif …`, test capturant le
cas, correction à la source ; contrat inchangé → re-gel, la propagation s'arrête ; contrat modifié → nature
`modification`, cascade dans l'ordre des couches.
Lire : `references/07-diagnostic-correction.md`.

### Phase 6 — Checkpoints, gouvernance, parallélisme (étape 8)
Tous les 2 à 3 niveaux (`$M statut` signale « checkpoint dû ») : révisions d'implémentation en lot à contrat
constant ; changements de contrat anticipés par défigeage formel ; une seule régression intégrale
(`$M gate --global --regression …`) ; `$M checkpoint --notes …`. Gouvernance : le circuit suit le rayon d'impact
(`$M rayon --couche …`) ; modification de contrat → arbitrage tracé (gabarit `assets/gabarits/defigeage-adr.md`) ;
baseline → clé du gardien. Ne jamais organiser les équipes par couches.
Lire : `references/08-gate-gouvernance-parallelisme.md`.

### Phase 7 — Clôture
Enveloppe figée, gate global vert, `$M rapport` (traces auto-instrumentées : gates, aiguillages, coût cumulé,
défigeages par nature). Rapporter à l'utilisateur ce qui est garanti et ce qui ne l'est pas.

## Proportionnalité

| Échelle | Cérémonie |
|---|---|
| Tâche / tranche | Cartographie de quelques minutes (liste de vingt lignes dans le plan ou dans la réponse) ; question-test et contrôle de divergence à la main ; outil facultatif ; gate = suite intégrale locale à chaque couche |
| Composant | Protocole complet : `mcl/` versionné, carte encodée, contrats soignés, gate et gel outillés |
| Application | Mode composite : squelette déployable + un dossier d'état par artefact de chair (`$M --dossier mcl/<artefact> …`) |

Même en version proportionnée, ne jamais sauter : la question-test, l'ordre de dépendance, le contrat avant
l'implémentation, la régression intégrale avant de passer à la couche suivante.

## Communication avec l'utilisateur

- Présenter, avant d'écrire la couche 0 : verdict d'applicabilité, carte des couches (avec groupes
  parallèles), frontières externes et leurs doublures. À l'échelle composant ou application, laisser
  l'utilisateur la corriger si des choix de conception restent ouverts.
- Rapporter couche par couche : unités, contrat finalisé, tests catégorie 1 et 2, résultat de la régression
  intégrale, statut (figée).
- Annoncer les coûts : retour produit tardif hors composite, coût du gate croissant (~N²/2), sérialisation entre
  couches dépendantes, risque de contrat spéculatif.
- Signaler les deux signaux de mauvais domaine (divergences répétées, défigeages en chaîne) dès qu'ils
  apparaissent : suspendre, sonder, re-cartographier.
- Distinguer ce qui vient du document de référence de ce qui est dérivé (stacks dérivées, conventions
  d'outillage). Les Parties IV à VI et les annexes du document sont absentes de la source : ne pas les inventer.

## Anti-patterns à refuser

- Écrire toutes les couches puis tester (big bang) ; commencer une couche dont une dépendance n'est pas figée.
- Ordonner les couches selon le flux d'exécution (ou son inverse mécanique).
- Doubler des couches internes qui existent déjà sans justification ; laisser survivre une doublure interne
  temporaire ; sur-isoler en tranches partielles.
- Passer à la couche suivante avec un test rouge ; remplacer le gate par une sélection de tests.
- Modifier un contrat ou les tests d'une couche figée sans défigeage ; contourner un défaut amont dans une couche
  supérieure.
- Contrat spéculatif (paramètres « au cas où », généricité fictive) ; finaliser un contrat plus d'un niveau en
  avance.
- Règle « couche adjacente seulement » dans l'outil d'architecture ; équipes organisées par couches.
- Promouvoir un prototype exploratoire en couche 0 ; appliquer le protocole pur à une application entière sans
  raison (réécriture à comportement constant ou spécification figée exceptées).

## Références (charger selon le besoin)

| Fichier | Contenu | Charger quand |
|---|---|---|
| `references/01-socle-commun.md` | Identité, concept, invariant, vocabulaire normatif, notations, échelles, six axes, statut épistémique | Toujours au premier usage ; doute sur un terme |
| `references/02-applicabilite.md` | Périmètre, test en trois questions, exemples, chemin exploratoire, signaux, frontières | Phase 0 |
| `references/03-cartographie.md` | Étapes 1 à 4 détaillées, illustrations, heuristiques, systèmes non-flux, cycles | Phase 1 |
| `references/04-encodage-carte.md` | Règle de build, conditions, outils par écosystème, warn/strict | Phase 2 |
| `references/05-contrats-frontieres.md` | Contrat en deux temps, gabarit, YAGNI de contrat, extension additive, frontières externes | Phase 3 et avant chaque couche |
| `references/06-boucle-construction.md` | Boucle en sept sous-étapes, deux catégories de tests, gel, loi de Hyrum, règles opératoires | Phase 4 |
| `references/07-diagnostic-correction.md` | Aiguillage, remontée de couches, protocole correctif | Gate rouge |
| `references/08-gate-gouvernance-parallelisme.md` | Gate à l'échelle, cliquet, deux vitesses, gouvernance, checkpoints, parallélisme | Équipe, CI, checkpoint, changement de contrat |
| `references/09-stacks-composite-positionnement.md` | Stacks du document et dérivées, mode composite, couture, Agile/TDD/BDD/Clean | Choix d'une carte type, application entière |
| `references/10-adoption-benefices-conditions.md` | Plan d'adoption, objections, bénéfices, conditions | Introduction en équipe, décision d'engagement |
| `references/11-fondements-scientifiques.md` | Revendications typées, fondements formels, état de l'art, comparaison par axe, mécanismes, huit hypothèses | « Pourquoi », comparaison, évaluation, rédaction scientifique |
| `references/12-exemples-travailles.md` | Facturation de bout en bout, chaîne d'appels, machine à états, legacy | Besoin d'un modèle concret |
| `references/13-outil-mcl-py.md` | Schéma de `carte.json`, commandes, journal, séquences, CI, limites | Usage de l'outil |

Gabarits (`assets/gabarits/`) : `PLAN-MCL.md` (plan étapes 0 à 8), `contrat-couche.md` (contrat sept lignes),
`defigeage-adr.md` (trace de gouvernance), `carte.exemple.json` (carte complète de l'exemple facturation).

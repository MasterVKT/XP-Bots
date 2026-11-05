# 03 — Cartographier : étapes 1 à 4

Source : I.6, III.2. C'est la phase où se joue la qualité de tout le reste : une carte fausse produit un
protocole parfaitement exécuté sur une structure erronée. Le protocole ne rattrape pas une carte fausse ; il
la **détecte**, après coup. Produire les sorties de chaque étape dans `mcl/PLAN-MCL.md` et `mcl/carte.json`.

## Sommaire
1. Étape 1 — Comprendre la cible
2. Étape 2 — Décomposer en unités fonctionnelles (2.1 à 2.4)
3. 2.5 — Les systèmes qui ne sont pas des flux (a, b, c, cycles)
4. Étape 3 — Construire le graphe de dépendances
5. Étape 4 — Assigner les couches
6. Traduction dans carte.json et contrôle outillé

---

## 1. Étape 1 — Comprendre la cible

Regarder le système depuis l'extérieur. Quatre questions suffisent :

1. Que doit faire le système à son niveau le plus haut ?
2. Quelles sont les entrées et sorties attendues de l'enveloppe finale ?
3. Quelles contraintes s'imposent : langage, framework, performance, environnement de déploiement ?
4. Projet neuf (greenfield) ou refactoring de code existant ?

**En pratique.** C'est **le seul moment de réflexion outside-in** de tout le protocole. Indispensable : sans
lui, risque de bâtir des fondations qui ne correspondent pas aux besoins réels. **Ne pas le prolonger
au-delà de ces quatre réponses** : la conception détaillée des couches internes vient de l'analyse de
dépendance, pas de l'intuition descendante. En mode composite, cette étape lit le **point d'insertion** dans
le squelette (contrat d'entrée et de sortie du segment à remplacer).

Pour l'agent : si une de ces quatre réponses manque et ne peut pas se déduire du contexte (code existant,
spécification fournie), poser la question à l'utilisateur avant de cartographier.

## 2. Étape 2 — Décomposer en unités fonctionnelles

Quatre temps, appliqués au problème entier, **puis récursivement à chaque module et à chaque unité non
triviale**.

### 2.1 — Identifier les entrées et les sorties
Délimiter le cadre traité (problème entier, module ou unité). Les **entrées** déterminent les objets qui
reçoivent et représentent les données fournies ; les **sorties** déterminent les objets qui produisent et
représentent les résultats. Ces frontières fixent le contrat externe du cadre avant toute exploration de
son intérieur.

### 2.2 — Élaborer le workflow de résolution
Modéliser, avec le maximum de détail possible, le flux qui mène des entrées aux sorties ; le représenter
explicitement (suite d'étapes ou graphe de flux). Double bénéfice, dont le second est le plus négligé : le
flux rend visibles les étapes, et il fait **émerger les variables et objets intermédiaires** (ni entrées ni
sorties, mais nécessaires au passage des unes aux autres). Ces intermédiaires sont souvent des unités à part
entière qu'on aurait manquées.

### 2.3 — Extraire les unités du flux
Chaque étape du flux et chaque objet intermédiaire révélé devient un **candidat-unité**. Une unité valide se
reconnaît à trois traits :
1. une **responsabilité unique** énonçable en une phrase ;
2. une spécification **entrée → transformation → sortie** (ou changement d'état) ;
3. **au moins une relation de dépendance** avec une autre unité.

Produire une **liste à plat**. À ce stade, **privilégier l'exhaustivité sur la précision**.

### 2.4 — Ordonner par dépendance, non par position dans le flux
**Point de bascule de toute la méthode et source d'erreur la plus fréquente.** Le flux montre dans quel ordre
les étapes s'exécutent ; il ne dit pas quelle unité dépend de quelle autre. **Seule la dépendance détermine
la profondeur d'une couche.** Pour chaque candidat-unité, poser la question de dépendance (et non de
position) :

> **« Cette unité pourrait-elle être construite et testée même si toutes les autres n'existaient pas
> encore ? »**

- **Oui** → c'est une **feuille** : couche 0 ou proche. Typiquement : fonction de calcul pur, entité de
  données sans logique, structure d'entrée, transformation autonome.
- **Non**, elle a besoin de telle autre unité → sa couche se situe **au-dessus** de celles dont elle dépend.

Le flux sert à *voir* les unités et leurs liens ; l'orientation des dépendances se lit **par-dessus** le flux,
elle ne s'en déduit pas.

**Première illustration (chaîne d'appels).** Flux `lire_fichier → calculer_moyenne → afficher_résultat`.
L'ordre d'exécution suggère à tort que la fin (`afficher_résultat`) serait la fondation. Les dépendances
disent : `afficher_résultat` dépend de `calculer_moyenne`, qui dépend de la structure de données produite par
`lire_fichier`. La fondation réelle est au **début** du flux ; `afficher_résultat` est la couche la plus
externe. (Ici chaque étape est conçue pour invoquer la précédente : ce sont de vraies dépendances.)

**Seconde illustration (cas général, orchestration).** Artefact de facturation, flux
`parser_lignes → calculer_taxes → appliquer_remise → générer_facture`. La modélisation fait apparaître des
objets intermédiaires qui ne sont des étapes nulle part : `LigneCommande`, `Facture`, `règles_tarifaires`.
- `LigneCommande`, `Facture`, `règles_tarifaires` sont constructibles et testables seules → **couche 0**. Les
  unités les plus profondes **n'apparaissent pas dans le flux comme étapes** : le flux montre des traitements,
  pas toutes les unités ; les intermédiaires émergés en 2.2 sont les candidats naturels à la couche 0.
- Les quatre étapes consomment et produisent des structures de la couche 0, et aucune n'a besoin qu'une autre
  étape **existe** pour être construite et testée (on alimente `calculer_taxes` avec des `LigneCommande`
  fabriquées à la main, sans parser) → **couches parallèles 1a à 1d**, côte à côte.
- L'orchestrateur `facturer`, qui appelle les quatre dans l'ordre du flux, dépend de toutes → **couche 2**,
  l'enveloppe.

L'ordre de dépendance n'est ici **ni l'ordre du flux, ni son inverse**. La différence avec la première
illustration tient à un **choix de conception** (étapes qui s'invoquent contre étapes orchestrées qui ne se
connaissent pas) : c'est la **conception effective** que la question-test interroge.

**Heuristiques bornées.** Dans un pipeline de données séquentiel, la feuille est souvent au début du flux ;
dans un arbre d'appels, c'est la fonction la plus profondément appelée. Ces heuristiques **orientent, elles ne
tranchent jamais**. Remplacer « suivre le flux » par « inverser le flux » substituerait une règle mécanique
fausse à une autre. **Seule la question-test tranche, unité par unité.**

*Ancrage* : Parnas (1972, système KWIC) — une décomposition calquée sur l'organigramme de traitement disperse
les décisions de conception ; la question-test outille ce principe au moment où l'erreur se commet.

**Unités de même profondeur.** Plusieurs unités à la même profondeur sans dépendance entre elles forment une
même couche **subdivisée par indice** (4a, 4b, 4c). Elles sont candidates à une construction parallèle ; cette
opportunité **doit être explicitement signalée** dans le plan de construction.

## 3. 2.5 — Les systèmes qui ne sont pas des flux

Pour toutes ces familles, **le critère de dépendance reste inchangé** : la couche 0 est toujours ce qui peut
être construit et testé sans que rien d'autre n'existe. Ce qui change, c'est l'objet qu'on cartographie avant
d'appliquer le critère.

### a) Machines à états et systèmes réactifs
Pas d'étape finale ; des états et transitions souvent mutuellement accessibles ; graphe cyclique par nature.
Tout graphe cyclique se décompose en **composantes fortement connexes** (clusters d'états mutuellement
accessibles) ; leur **condensation** est toujours un DAG. L'algorithme de **Tarjan** émet les composantes en
ordre topologique inverse : la première composante émise est la couche 0 (ordre de construction sans calcul
supplémentaire).

Orientation : la phrase « la première composante émise est la couche 0 » suppose des arcs orientés **comme des
dépendances** (un état dépend des états depuis lesquels on l'atteint), c'est-à-dire en sens inverse des flèches
de transition. Sur le graphe des transitions brut, Tarjan émet d'abord les composantes puits. Dans
`carte.json`, déclarer donc pour chaque état `depend_de` = ses prédécesseurs.

En pratique : tracer le diagramme d'états et de transitions → identifier les composantes fortement connexes →
les ordonner par condensation. La couche 0 est la composante source, le cluster le plus autonome,
typiquement l'état initial et le cycle dont il fait partie ; étendre ensuite vers les composantes qui
dépendent des précédentes.

**À l'intérieur d'une composante, préserver l'incrémental.** L'atomicité d'une composante est une atomicité
**d'ordonnancement externe** (elle occupe une seule couche du DAG). La construire d'un bloc recréerait un mini
big bang. Appliquer MCL **récursivement à l'intérieur** sur un critère différent : la **couverture
incrémentale des transitions**. Implémenter d'abord un **cycle minimal vivant** (l'état initial plus une
transition de retour), le tester, puis ajouter une à une les transitions et états restants, en validant après
chaque ajout.

### Le cas général des dépendances circulaires
Un cycle entre unités ordinaires se condense en une composante occupant une seule couche, puis la méthode
reprend sur le DAG des composantes. **Briser le cycle par une interface reste préférable** quand le cycle
trahit un défaut de conception. Sinon, construction interne en trois temps :

1. **Noyau minimal.** Implémenter *simultanément* les versions minimales des unités mutuellement dépendantes,
   juste assez pour fermer le cycle, et les tester **ensemble, comme un seul pas de construction**.
   Co-construction bornée : exception assumée et déclarée à la règle « une unité à la fois » (un cycle n'admet
   aucun ordre interne total).
2. **Croissance incrémentale.** Noyau vivant et vert, enrichir les unités une à une, méthode par méthode, cas
   par cas, en validant après chaque ajout.
3. **Doublure de sectionnement temporaire**, en repli si le noyau minimal reste trop gros : couper le cycle en
   un point par une doublure interne provisoire, construire le reste dans l'ordre, puis fermer le cycle en
   remplaçant la doublure par l'unité réelle. Choisir le point de coupe qui **minimise le nombre et la richesse
   des doublures** (objectif CITO). **Règle de temporalité** : toute doublure interne intra-composante est
   provisoire ; sa suppression est un critère de fermeture ; une doublure interne qui survit à la construction
   de la composante est un **défaut**.

Dans une composante cyclique, l'économie de doublures se **dégrade localement** : raison supplémentaire de
préférer la résolution architecturale.

### b) Systèmes événementiels ou pilotés par le domaine
Cartographie par *event storming* allégé :
1. lister les **événements du domaine, au passé** (« commande passée », « paiement validé ») ;
2. identifier les **agrégats** (entités cohérentes sur lesquelles opèrent ces événements : Commande, Paiement,
   Stock) ;
3. regrouper selon « ce qui change ensemble va ensemble ; minimiser les dépendances entre groupes ».

La couche 0 est l'**agrégat le plus autonome** (il maintient son cycle de vie sans dépendre d'un autre). Les
agrégats qui réagissent à des événements produits ailleurs forment les couches externes.

### c) Domaines complexes à frontières multiples
Délimiter d'abord les **frontières de sens**, les **contextes bornés** (« facturation » et « livraison » parlent
de choses différentes même s'ils partagent le mot « commande » ; signal fiable : **le vocabulaire change**).
Puis appliquer la décomposition **indépendamment à l'intérieur de chacun** : chaque contexte devient un
sous-problème MCL autonome, avec sa propre couche 0.

> Flux séquentiel : suivre les données. Machine à états : suivre les transitions. Domaine événementiel :
> suivre les événements et regrouper en agrégats. Une fois la carte établie, la même question de dépendance
> désigne la couche 0, et les étapes 3 à 8 s'appliquent à l'identique.

## 4. Étape 3 — Construire le graphe de dépendances

Formaliser l'ordonnancement amorcé en 2.4. Pour chaque unité : **de quoi dépend-elle ? qu'est-ce qui dépend
d'elle ?** Résultat : un graphe orienté acyclique (DAG).

```
Unité A → dépend de → Unité B, Unité C
Unité B → dépend de → Unité D
Unité C → dépend de → (rien — feuille)
Unité D → dépend de → (rien — feuille)
```

- **Feuilles** (aucune dépendance sortante) = couche 0, point de départ. **Racine** (rien n'en dépend) =
  couche N, point d'arrivée.
- **Contrôle de divergence** : confronter le graphe formalisé à l'ordonnancement intuitionné en 2.4. Toute
  divergence est un **signal, pas un échec** : dépendance mal comprise ou unité manquante détectée au coût le
  plus bas, avant qu'une seule couche ne soit construite. **Résoudre la divergence avant l'assignation des
  couches.**
- **Dépendances externes** (base de données, API tierce, paiement, système de fichiers) : les identifier
  **séparément**. Elles seront doublées dans les couches internes et connectées réellement dans la seule
  couche d'infrastructure finale.
- **Détection de cycles** (fréquente en legacy) : soit briser le cycle par une interface ou une abstraction
  (préférable si défaut de conception), soit le condenser en composante fortement connexe occupant une seule
  couche, construite de façon incrémentale en interne (2.5.a). Un cycle est un cas traité, plus un obstacle.

## 5. Étape 4 — Assigner les couches

| Couche | Contenu | Dépend de |
|---|---|---|
| 0 — Noyau | Unités feuilles, aucune dépendance | Rien |
| 1 | Unités dépendant uniquement de la couche 0 | Couche 0 |
| 2 | Unités dépendant des couches 0 et 1 | Couches 0-1 |
| … | … | … |
| N — Enveloppe | Point d'entrée, orchestrateur final | Toutes les couches internes |

Formellement : profondeur d'une unité = 0 si elle ne dépend d'aucune unité interne, sinon 1 + la profondeur
maximale de ses dépendances (tri topologique, Kahn 1962). Ce tableau est le **plan de construction** et un
**artefact exécutable** (voir `04-encodage-carte.md`).

## 6. Traduction dans carte.json et contrôle outillé

1. Renseigner `unites` (id, responsabilite, depend_de — unités et identifiants de frontières externes) et
   `externes` dans `mcl/carte.json` (schéma : `13-outil-mcl-py.md`).
2. Lancer `python3 <skill>/scripts/mcl.py analyser` : tri topologique, cycles (Tarjan), profondeurs, groupes
   parallèles, divergences, unités isolées ou sans responsabilité, racines multiples.
3. Si `couches` est vide : `analyser --ecrire` propose une subdivision ; l'ajuster (regroupements de même
   profondeur, noms), puis renseigner `chemins`/`imports` (convention « une couche = un module nommé »).
4. Relancer `analyser` jusqu'à **zéro divergence** (code de sortie 0) avant d'écrire la moindre ligne de
   la couche 0.

À l'échelle tâche/tranche, l'outil est facultatif : une liste de vingt lignes dans le plan suffit, à
condition d'y appliquer la question-test et le contrôle de divergence à la main.

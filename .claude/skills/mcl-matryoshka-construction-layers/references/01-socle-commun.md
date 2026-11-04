# 01 — Socle commun : identité, concept, invariant, vocabulaire, échelles

Source : document de référence MCL (E. Vekout, août 2026), Partie 0 et Partie I. Ce fichier fixe le sens
exact des mots ; tout le reste du skill s'appuie dessus. Presque tous les malentendus sur MCL viennent d'un
glissement sur *artefact* (qui fixe l'échelle) ou sur *couche* (mot déjà pris ailleurs dans un autre sens).

## Sommaire
1. Identité et nomenclature
2. Définition en une phrase
3. Le problème adressé et ses deux lignes de base
4. Le concept fondateur
5. L'invariant central : la garantie donnée et la garantie non donnée
6. Vocabulaire unifié (tableau normatif)
7. Notations
8. La règle de périmètre et les trois échelles
9. Les six axes de contribution (A1 à A6)
10. Statut épistémique et disciplines de discours
11. Conventions d'écriture (cinq encadrés)
12. Parties absentes de la source

---

## 1. Identité et nomenclature

- Nom : **Matryoshka Construction Layers**, abrégé **MCL**. Ancien nom : « Méthode Matryoshka ». Le changement
  est purement nominal ; tout travail antérieur parlant de « Méthode Matryoshka » désigne MCL.
- *Construction* : la méthode gouverne l'**acte de construire**, non l'organisation statique du code.
  *Layers* : l'unité d'avancement est la **couche de profondeur de dépendance**.
- Auteur : Eric Vekout (Douala, Cameroun). Maturation janvier–juin 2026, en boucle serrée avec des projets
  industriels ; chaque faille ou défaut induit repéré a produit une version suivante. Double origine :
  rendre la **localisation d'un défaut** « question à réponse courte » plutôt qu'« enquête », et donner à
  l'apprenant un chemin explicite de l'idée à l'implémentation, compris et non appliqué mécaniquement.

## 2. Définition en une phrase

MCL prescrit de bâtir le code d'une unité de travail donnée (fonction, module, composant, service,
algorithme, application) en partant de son **unité fonctionnelle la plus fondamentale**, puis en ajoutant des
**couches de complexité croissante**, chacune **entièrement validée et gelée** avant que la suivante ne soit
construite. L'ordre des couches suit le **graphe des dépendances, jamais l'ordre d'exécution du flux**.

Deux propriétés en découlent : la carte des couches devient une **déclaration vérifiable au build** ; tout
échec de régression s'analyse contre un **delta unique appliqué à une base entièrement verte**.

## 3. Le problème adressé et ses deux lignes de base

- Problème : écrire toutes les parties d'un système puis chercher pourquoi l'ensemble ne fonctionne pas. Nom
  informel depuis les années 1970 : *magic subroutine problem* (en codant de haut en bas, la complexité non
  résolue est repoussée de module en module jusqu'à s'accumuler dans un dernier composant impossible à
  implémenter dans les temps).
- Ce problème **motive** MCL ; il n'en est pas le **concurrent**. La pratique professionnelle l'a déjà traité
  (conception outside-in, tranches verticales de bout en bout, intégration continue). La comparaison utile se
  mène **contre ces pratiques modernes** (ligne de base professionnelle).
- Chez l'**apprenant**, la pratique observée reste l'intégration *big bang* (tout écrire, test final,
  débogage décourageant). C'est une **seconde ligne de base**. Ne jamais transposer une comparaison d'un
  terrain à l'autre : confondre les deux produit des affirmations fausses dans les deux sens.

## 4. Le concept fondateur

- Image 1, la matryoshka : la figurine la plus intérieure ne contient rien et ne dépend de rien ; chacune
  enveloppe les précédentes ; on ne peut pas fermer le jeu si une intermédiaire est défectueuse, et pour le
  savoir il faut l'avoir manipulée séparément, avant l'assemblage.
- Transposition : la couche la plus profonde est l'unité dont tout dépend et qui ne dépend de rien. On la
  construit, on la teste isolément, on la valide, on la gèle ; on ajoute la couche qui la contient ; on
  valide de nouveau ; ainsi jusqu'à l'enveloppe finale.
- Image 2, les boucles imbriquées : devant `for i { for j { for k { … } } }` qui donne un résultat faux, tout
  développeur isole d'abord `k`, puis remonte vers `j`, puis `i`. Ce réflexe, universel et réservé au
  débogage, MCL l'**élève au rang de méthode de construction**, appliquée dès le premier jour. C'est ce qui la
  rend transmissible en quelques heures.

## 5. L'invariant central

> **Une couche n'est jamais construite tant que toutes les couches dont elle dépend ne sont pas testées,
> validées et stables.**

Non négociable. Le lire avec exactitude dans ses deux sens :

- **Garantie donnée : la stabilité du bloc.** À tout instant, tout ce qui existe est testé, intégré et
  stable. Le bloc `{0 → k}` est un **sous-ensemble validé du système final**, ni prototype jetable ni chantier.
  « Fonctionne » s'entend au sens du code : chaque contrat tenu, chaque test vert. Tant que l'enveloppe
  n'existe pas, **la suite de tests est le seul moyen d'exécuter le bloc** (il n'a pas de point d'entrée).
- **Garantie non donnée : le chemin de bout en bout.** Aucune fonctionnalité n'est démontrable de l'entrée
  utilisateur à la sortie avant la construction des couches externes. Le retour produit arrive tard *par
  construction de l'ordre inside-out*. C'est l'axe où l'outside-in garde l'avantage ; MCL ne le conteste pas
  et prévoit la combinaison des deux quand un retour précoce a de la valeur : le **mode composite**.

Conséquence de communication : ne jamais promettre une démo de bout en bout avant l'enveloppe en mode pur ;
annoncer « bloc {0 → k} validé par N tests » à la place.

## 6. Vocabulaire unifié (normatif)

| Terme | Sens exact dans MCL |
|---|---|
| **Artefact** | L'unité de travail choisie, à quelque échelle que ce soit : une tâche, une tranche fonctionnelle, un composant autonome, une application entière. C'est *sur* un artefact que le protocole s'applique. |
| **Unité fonctionnelle** | Un élément à responsabilité unique énonçable en une phrase, spécifié entrée → transformation → sortie (ou changement d'état), et lié par au moins une relation de dépendance à une autre unité. |
| **Couche** | Une **profondeur de dépendance** à l'intérieur de l'artefact. Pas une strate technique au sens des architectures en tiers ; **jamais un découpage d'équipe**. La couche 0 regroupe les unités qui ne dépendent de rien. |
| **Couches parallèles** | Les unités de même profondeur sans dépendance mutuelle : couches 1a, 1b, 1c. Candidates à une construction simultanée. |
| **Bloc `{0 → k}`** | L'ensemble des couches construites, validées et gelées jusqu'à la profondeur `k`. Un système unique déjà intégré, pas un empilement à réassembler. |
| **Contrat** | L'interface publique d'une unité : responsabilité, signature, entrées et contraintes, sorties et garanties, effets de bord, conditions d'erreur. Rédigé avant l'implémentation. |
| **Gel (FIGER)** | L'opération qui rend le contrat d'une couche *read-only* une fois celle-ci validée. Le gel porte sur le contrat, pas sur l'implémentation interne, qui reste révisable sous harnais complet. |
| **Défigeage** | La levée formelle du gel, pour changer un contrat ou corriger un défaut. Tracée ; sa propagation est conditionnelle. |
| **Doublure** | Terme générique des substituts de test. Un *driver* appelle l'unité testée ; un *stub* ou un *mock* remplace une dépendance absente. L'économie de la méthode repose sur cette distinction. |
| **Frontière externe** | Une dépendance hors du système : base de données, API tierce, service de paiement, système de fichiers. **Le seul endroit où MCL impose des doublures.** |
| **Carte des couches** | La déclaration explicite de l'assignation des unités aux couches. Versionnée avec le code, elle devient une règle vérifiée au build. |
| ***Regression gate*** | Le point de passage obligé entre deux couches : **la totalité de la suite existante** doit repasser au vert avant que la couche courante ne soit gelée. |
| **Mode composite** | Squelette outside-in déployé dès le départ + chair construite au protocole MCL. Mode d'emploi de référence à l'échelle d'une application entière. |

## 7. Notations

- Couche notée par son indice de profondeur : couche 0, couche 1, couche `k`. Racine (enveloppe) : couche N.
- Bloc des couches déjà construites et gelées, de la plus interne jusqu'à `k` : `{0 → k}`.
- Unités de même profondeur sans dépendance mutuelle : lettre suffixée (1a, 1b, 1c ; 4a, 4b…).
- *Artefact* désigne partout l'unité de travail choisie, quelle que soit son échelle.

## 8. La règle de périmètre et les trois échelles

**Règle de périmètre.** MCL gouverne *comment construire le code* d'une unité de travail **déjà choisie**. Elle
ne décide jamais *quoi* livrer ni *dans quel ordre* le livrer : cela relève du niveau produit (tranches,
backlog, feuille de route), avec lequel la méthode s'articule sans le remplacer. La cadence de livraison ne
change pas ; ce qui change est la construction *à l'intérieur* de la tranche.

| Échelle | Nature | Lourdeur du protocole | Coût du retour produit tardif |
|---|---|---|---|
| 1. Tâche ou tranche | Code d'une fonctionnalité déjà choisie ; échelle **native** | Cartographie en quelques minutes (tableau blanc, fichier texte de vingt lignes) ; version proportionnée ; aucun outillage requis pour commencer | À peu près nul (la tranche livre dès qu'elle est finie) |
| 2. Composant autonome | Bibliothèque, service, moteur, algorithme ; échelle de **plein exercice** | Protocole pleinement exercé ; contrats écrits avec soin (d'autres coderont contre eux) | Retour technique rapide (consommateurs testant contre les contrats dès le gel) ; retour produit dépendant du système englobant |
| 3. Application entière | Possible, mais la garantie non donnée pèse le plus longtemps | **Mode composite** comme mode d'emploi de référence | Maximal en mode pur |

L'échelle est une question distincte du **domaine** (types de problèmes qui se prêtent à MCL) : voir
`02-applicabilite.md`.

## 9. Les six axes de contribution

- **A1 — Pont entre structure et processus.** Clean et Onion Architecture prescrivent une direction de
  dépendance (vers l'intérieur) sans ordre de construction. MCL relie les deux : si les dépendances pointent
  vers l'intérieur, on construit de l'intérieur vers l'extérieur, avec validation à chaque étape. Seule
  exception connue, tardive et partielle : l'évolution 2020-2024 d'Hexagonal Architecture.
- **A2 — Intégration opérationnelle.** Sept éléments : analyse du graphe de dépendances comme outil de
  planification ; contrats avant implémentation ; ordre strict des feuilles vers la racine ; *regression gate*
  systématique ; doublures confinées aux frontières externes ; checkpoints périodiques ; le tout sous un
  protocole nommé et reproductible. Ils s'alimentent mutuellement : la carte nourrit l'enforcement au build,
  le rayon des arbitrages et les groupes de parallélisation ; le gel nourrit la localisation, la révision sous
  harnais et l'extension additive ; le gate nourrit l'intégration continue et le plan d'adoption.
- **A3 — Externalisation d'un savoir tacite.** Le réflexe des développeurs expérimentés (analyser les
  dépendances avant de coder, tester petit avant d'intégrer) devient un protocole nommé, ordonné, vérifiable,
  apprenable sans dix ans de pratique (phase d'Externalisation du modèle SECI).
- **A4 — Invariant rendu exécutable.** La carte, consignée dans un outil de test d'architecture et versionnée,
  fait échouer le build dès qu'une unité de couche `k` référence une couche plus externe. Trois contrôles
  deviennent automatiques : violation de l'invariant, détection de cycles, écart carte déclarée / graphe réel.
  MCL **prescrit** ce mécanisme et fournit son entrée : une carte justifiée par la dépendance.
- **A5 — Auto-instrumentation et réfutabilité déclarée.** Huit hypothèses réfutables, dont deux défavorables ;
  six se lisent dans des traces produites par construction (historique des défigeages, journaux du gate,
  baseline, cartes versionnées).
- **A6 — Couverture étendue.** Systèmes non-flux (machines à états, domaines événementiels, grands domaines à
  frontières multiples), dépendances circulaires (condensées en composante occupant une seule couche),
  application entière (mode composite qui protocolise la boucle interne du Double-Loop TDD).

## 10. Statut épistémique et disciplines de discours

MCL est une **synthèse cohérente et une formalisation opérationnelle** de pratiques établies (construction
ascendante, contrats avant le code, doublures aux frontières externes, intégration incrémentale, vérification
mécanique des dépendances). Aucun élément n'est neuf ; ce qui est revendiqué est le pont, l'intégration et
l'externalisation. Trois disciplines s'imposent dans **tout discours** produit avec ce skill :

1. **Revendications typées** : établi et sourçable / analyse mécaniste (raisonnement sur le protocole, sans
   mesure) / hypothèse à démontrer. Jamais mélangés dans une même phrase.
2. **Résultat de vérification daté** : l'état de l'art est une absence constatée après recherche, pas une
   inexistence démontrée.
3. **Bénéfices réfutables** : ne **jamais** présenter MCL comme produisant statistiquement de meilleurs
   résultats qu'une autre approche. L'évidence ne le permet pas. Dire axe par axe ce qu'on achète et ce qu'on
   paie, et renvoyer au dispositif d'évaluation (voir `11-fondements-scientifiques.md`).

## 11. Conventions d'écriture (cinq encadrés)

Pour toute documentation rédigée « à la manière MCL » : **Ancrage** (rattache un mécanisme à son précédent
documenté), **Apport** (ce que MCL ajoute), **Renvoi** (lien précis vers une autre partie), **Condition** (ce
dont dépend un bénéfice, vérifiable sur le terrain), **En pratique** (le geste concret au niveau où il
s'exécute). Termes définis à leur première occurrence utile.

## 12. Parties absentes de la source

Le document cite des Parties IV (recherche en éducation), V (formation : progression en trois temps,
évaluation par frontière de couche), VI (questions ouvertes communes) et des annexes A à D (glossaire,
sources, citation). **Leur contenu n'est pas dans le fichier source.** Ne pas l'inventer : signaler
l'absence si une demande en dépend (onboarding pédagogique détaillé, grille de correction, citations exactes).
Seules les mentions explicites des Parties 0 à III sont exploitables (par exemple : pour les praticiens
confirmés, l'échafaudage cognitif n'apporte rien, la vérification mécanique et la coordination si ; l'effet
d'expertise inversée prédit un effet hétérogène novices / confirmés).

# 09 — Stacks de référence, mode composite, positionnement

Source : III.12, III.13, III.14. Les sections 1 et 3 à 5 sont fidèles au document. La section 2 est
**dérivée** (hors document de référence) : elle applique la question-test à des contextes que le document ne
liste pas, et doit être présentée comme telle.

## Sommaire
1. Les cinq stacks du document
2. Dériver une stack pour un autre contexte (méthode + trois exemples dérivés)
3. Le mode composite : squelette outside-in, chair MCL
4. Les cinq règles de couture
5. Positionnement avec Agile/Scrum, TDD, BDD, Clean/Onion/Hexagonal

---

## 1. Les cinq stacks du document

Elles décrivent l'échelle la plus exigeante (application entière), donc à lire **avec le mode composite**. Aux
échelles composant ou tâche, la carte se restreint au périmètre choisi. **Ce sont des points de départ : la
question-test, unité par unité, reste seule juge des profondeurs réelles.**

**API backend REST, générique**
```
0 : Modèles de données / entités (structures pures, sans logique)
1 : Validateurs / parseurs (validation et transformation des entrées)
2 : Repositories / DAO (interfaces d'accès aux données + doublures)
3 : Services de domaine / logique métier
4 : Services applicatifs (orchestration de cas d'usage)
5 : Contrôleurs / handlers de routes
6 : Middleware / authentification / gestion d'erreurs
7 : Point d'entrée (bootstrap serveur, injection de dépendances)
```

**Application Flutter**
```
0 : Entités du domaine (classes Dart pures)
1 : Value objects / enums / constantes
2 : Interfaces et implémentations de cas d'usage
3 : Interfaces de repository (+ implémentations doublées)
4 : Sources de données (locales : Hive/SQLite ; distantes : clients API)
5 : Implémentations de repository (câblage des sources de données)
6 : Gestion d'état (Bloc/Riverpod/Provider)
7 : Widgets (stateless → stateful → écrans)
8 : Entrée de l'application + routage + injection de dépendances
```

**Application Django**
```
0 : Modèles (champs, validation basique, sans logique métier)
1 : Méthodes de modèle / managers (helpers de requête)
2 : Couche de service / logique métier (Python pur, sans dépendance Django)
3 : Serializers (contrats d'entrée/sortie)
4 : Views / ViewSets
5 : Routage URL + middleware
6 : Settings / câblage de l'infrastructure
```

**Algorithme ou pipeline de données**
```
0 : Fonction de transformation centrale (calcul le plus imbriqué)
1 : Fonctions utilitaires / helpers
2 : Parseur / normaliseur d'entrée
3 : Formateur / sérialiseur de sortie
4 : Orchestrateur / exécuteur de pipeline
5 : Interface CLI / API
```

**Refactoring de code legacy**
```
0 : Identifier les unités les moins couplées (dépendances externes minimales)
    → les extraire, les tester, les traiter comme couche 0
1 : Unités ne dépendant que de la couche 0 → extraire, tester
… continuer vers l'extérieur jusqu'à ce que le point d'entrée legacy devienne la dernière couche
```
Le legacy est le cas où la méthode s'installe le plus naturellement : la structure ne se devine pas, elle se
lit dans le code existant. Les cycles y sont fréquents (étape 3 : briser ou condenser). Sur l'existant, adopter
le gate par baseline à cliquet.

## 2. Dériver une stack pour un autre contexte (hors document)

Méthode, applicable à tout langage et tout type d'application :
1. Lister les **familles d'unités** du contexte (types de domaine, calculs purs, ports de frontières externes,
   cas d'usage, état, présentation, adaptateurs réels, point d'entrée).
2. Pour chaque famille, poser la question-test : « constructible et testable si rien d'autre n'existait ? ».
3. Profondeur = 1 + profondeur maximale des familles dont elle dépend ; familles de même profondeur =
   couches parallèles.
4. Les **adaptateurs réels** des frontières externes vont dans la couche d'infrastructure, la plus externe
   (avec le point d'entrée ou juste sous lui) ; leurs **interfaces (ports)** se placent à la profondeur que
   leur donnent leurs propres dépendances (souvent juste au-dessus des types de domaine).
5. Considérer la stack obtenue comme une **hypothèse** : la carte réelle se fait unité par unité.

Exemples dérivés (à présenter comme dérivés, jamais comme issus du document) :

**Robot de trading / moteur de décision sur flux de marché** (cas des spécifications de ce dépôt)
```
0  : Types de domaine purs (bougie OHLC, tick, profil d'instrument, ordre, position, temps UTC, décimaux)
     + configuration validée (value objects)
1a : Indicateurs (EMA, RSI, ATR…) en fonctions pures sur séries de bougies clôturées
1b : Construction de bougies à partir de ticks (intervalles, clôture, trous)
1c : Règles de calendrier et de sessions
1d : Calcul de risque et de volume (arrondis sur la grille de l'instrument)
1e : Ports des frontières externes (flux de marché, exécution d'ordres, calendrier économique, horloge,
     journal persistant) + doublures
2  : Machine à états de la stratégie (2.5.a : composantes fortement connexes, cycle minimal vivant puis
     transitions une à une)
3  : Moteur de décision événementiel (orchestration : bougies → indicateurs → machine à états → intentions
     d'ordre, via les ports)
4  : Adaptateurs réels (plateforme/courtier, persistance) — couche d'infrastructure
5  : Points d'entrée (exécution réelle, backtest), câblage
```
Calibrage d'applicabilité : **implémenter une spécification déterministe** est applicable (structure
connaissable, contrats stabilisables) ; **chercher une stratégie rentable** (réglage, recherche d'avantage
statistique) est exploratoire : sonder d'abord, puis reconstruire au protocole la version retenue.

**Application front-end (SPA)**
```
0 : Types et modèles de domaine, constantes
1 : Fonctions pures (formatage, validation, sélecteurs) ; ports API (interfaces client) + doublures
2 : Cas d'usage côté client (logique d'application sans framework d'interface) ; composants de présentation
    sans état (s'ils ne dépendent que de 0-1 : couche parallèle)
3 : Gestion d'état (store)
4 : Composants conteneurs / écrans connectés à l'état
5 : Routage, client HTTP réel, bootstrap
```
Si l'inconnue principale porte sur l'interaction elle-même : outside-in d'abord (wireframe, BDD), puis MCL.

**Outil en ligne de commande**
```
0 : Structures de données du domaine
1 : Calculs et règles purs ; ports des frontières (système de fichiers, réseau, horloge) + doublures
2 : Services / cas d'usage
3 : Analyse des arguments et formatage de sortie (adaptateurs d'interface)
4 : Adaptateurs réels des frontières ; point d'entrée (main, câblage)
```

## 3. Le mode composite

À l'échelle de l'application entière, mode d'emploi de référence.

- **Le principe.** Construire d'abord le **squelette** : une implémentation minuscule de bout en bout qui relie
  les composants architecturaux principaux et **se déploie dès le départ**, intégration continue comprise. Du
  **code de qualité production destiné à durer**, jamais un prototype jetable. Puis la **chair** : chaque
  remplissage est un **artefact** (tranche fonctionnelle ou composant) construit de l'intérieur vers
  l'extérieur selon le **protocole intégral**, et branché sur le squelette.
- **La division des risques.** Le squelette couvre ce que MCL ne garantit pas : chemin de bout en bout dès la
  semaine zéro, risque d'intégration et de déploiement, retour produit continu. MCL couvre ce que le squelette
  seul ne fournit pas : construction validée de la logique (couches, contrats, gel, gate, localisation). Chaque
  approche opère là où elle est forte, aucune n'est dénaturée.
- **Ce que le composite ne change pas.** Il traite le risque de retour à l'échelle application ; il ne modifie
  pas le domaine d'applicabilité (un artefact de chair exploratoire reste exploratoire).
- *Apport* : le Double-Loop TDD nomme une boucle interne inside-out sans en régler l'exécution ; le composite
  MCL la règle (chaque artefact de chair a ses couches, ses contrats, son gel et son gate).

Organisation outillée suggérée : un dossier d'état MCL par artefact de chair (`mcl.py --dossier
mcl/<artefact> …`), chacun avec sa carte, son journal et son gate.

## 4. Les cinq règles de couture

1. **Identité.** Le squelette n'est pas une étape de la méthode : c'est l'autre approche, assumée comme telle.
   « L'étape 1 est le seul instant de réflexion outside-in » reste vrai *du protocole lui-même*.
2. **Statut.** Le squelette n'est pas figé au sens de FIGER. Il est le **contexte externe** des artefacts de
   chair ; sa discipline propre est de rester **déployable en continu**. **Sa CI est son gate.**
3. **Entrée.** L'étape 1 de chaque artefact de chair lit son **point d'insertion** dans le squelette : contrat
   d'entrée et de sortie du segment à remplacer.
4. **Sortie.** L'enveloppe finale de l'artefact se branche sur le squelette en **remplaçant le segment minimal
   correspondant**. Si la couture exige de modifier un contrat du squelette, c'est un **changement de contrat** :
   défigeage et propagation, avec la CI du squelette en garde-fou.
5. **Cadence.** Chaque remplissage est un **incrément démontrable sur le squelette**. La livraison reste
   verticale (niveau produit) ; la construction reste inside-out (niveau code).

## 5. Positionnement

MCL ne remplace aucune méthodologie ; elle s'y intègre comme **discipline de construction**.
- **Agile / Scrum** : MCL opère au niveau du code **à l'intérieur d'un sprint** ; Agile au niveau des
  fonctionnalités à livrer (règle de périmètre).
- **TDD** : compatible et renforçante. Le TDD inside-out de l'école Detroit partage la même direction ; MCL y
  ajoute l'analyse du graphe de dépendances et les contrats formels en amont. (Le cycle rouge-vert-refactor
  s'exerce naturellement à l'intérieur de IMPLÉMENTER/TESTER d'une couche.)
- **BDD** : complémentaire. Le BDD opère outside-in au niveau du comportement attendu ; MCL inside-out au niveau
  de la construction technique.
- **Clean, Onion, Hexagonal** : MCL se lit comme le **protocole de construction manquant** de ces architectures.
  Elles définissent où placer chaque chose ; MCL définit dans quel ordre les construire et comment valider
  chaque étape.

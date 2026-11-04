# 02 — Choisir l'artefact et tester l'applicabilité

Source : I.5, I.9, II.8, III.1, III.13 (combinaisons ponctuelles), III.17. À appliquer **avant** toute
cartographie.

## Sommaire
1. La première décision est une décision de périmètre
2. Proportionner le protocole à l'échelle
3. Le test en trois questions (au niveau de l'artefact)
4. Exemples de calibrage
5. Chemin exploratoire : sonder, stabiliser, reconstruire
6. Conditions de bénéfice dégradé (applicable, mais rapporte moins)
7. Le classement se vérifie en construisant (deux signaux)
8. Combinaisons ponctuelles
9. Les cinq frontières du résultat

---

## 1. La première décision est une décision de périmètre

Désigner l'**artefact** : tâche, tranche fonctionnelle, composant, application. Ce choix précède tout et
**n'appartient pas à MCL** : backlog, roadmap et découpage produit décident *quoi* construire et *dans quel
ordre le livrer* ; MCL décide seulement *comment construire le code* de ce qui a été choisi.

Conduite de l'agent : si l'utilisateur demande « construis l'application X », ne pas réordonner ses priorités
produit ; identifier l'artefact demandé, son échelle, et appliquer le protocole à cette échelle. Si une
application entière est demandée, l'artefact de premier niveau est l'application (mode composite) et chaque
remplissage de chair est un artefact distinct.

## 2. Proportionner le protocole à l'échelle

- **Tâche / tranche** : cartographie en quelques minutes (tableau blanc ou fichier texte de vingt lignes) ;
  protocole en version proportionnée ; aucun outillage particulier requis pour commencer.
- **Composant autonome** (bibliothèque, service, moteur de calcul) : protocole pleinement exercé ;
  frontières contractuelles nettes ; consommateurs identifiables ; contrats écrits avec soin.
- **Application entière** : **mode composite** (voir `09-stacks-composite-positionnement.md`). C'est le mode
  d'emploi de référence, pas une variante. L'application **pure** du protocole reste licite quand un retour
  produit précoce n'a aucune valeur : réécriture à comportement constant, projet à spécification figée
  contractuellement.

## 3. Le test en trois questions

La question se pose **au niveau de l'artefact, jamais au niveau du produit qui l'englobe**. Un produit en
pleine découverte (marché incertain, exigences mouvantes) contient des artefacts parfaitement décidés dont la
structure est connaissable. Exclure MCL au motif que l'entreprise cherche encore serait faux.

1. **La structure est-elle connaissable avant construction ?** Des praticiens compétents peuvent-ils
   cartographier unités et dépendances avec confiance, parce que des systèmes analogues existent ou parce que
   la structure se lit dans le code existant ?
2. **Les contrats internes sont-ils stabilisables tôt ?** Si les interfaces ne peuvent être arrêtées qu'après
   avoir vu le système tourner, le gel devient un générateur de défigeages en cascade.
3. **Faut-il construire pour comprendre ?** Recherche algorithmique, exploration d'un modèle d'apprentissage,
   sensation de jeu, interaction inédite, expérience utilisateur inédite : si la compréhension n'émerge qu'en
   sondant, la carte serait une fiction.

Verdict : **oui, oui, non** (structure connaissable, contrats stabilisables, pas besoin de construire pour
comprendre) → appliquer le protocole. **Une seule réponse défavorable** → l'artefact est **exploratoire**.

## 4. Exemples de calibrage (issus du document)

- La tranche « export CSV » d'un produit en pleine découverte est **applicable** : l'artefact décidé est banal,
  c'est le produit qui sonde, pas lui.
- Un moteur d'apprentissage dont l'architecture émerge des expériences est **exclu**, même si tout le reste du
  système se construit au protocole.
- Le refactoring de code legacy est le cas où la méthode s'installe le plus naturellement : la structure se lit
  dans l'existant, la question 1 reçoit un oui presque automatique.
- L'espèce la plus fréquente d'artefact exploratoire est l'**incertitude structurelle d'expérience
  utilisateur** : quand l'inconnue porte sur ce que doit être l'interaction plutôt que sur la logique,
  l'outside-in est premier.

## 5. Chemin exploratoire

Sonder d'abord (**spike**, **prototype**, **tranche-sonde**), puis **reconstruire au protocole** une fois la
structure stabilisée. **Le prototype se jette ; la reconstruction est le travail réel.** Pour l'agent : livrer
le spike comme jetable, explicitement étiqueté, puis proposer la reconstruction MCL ; ne pas « promouvoir » le
code du spike en couche 0.

## 6. Conditions de bénéfice dégradé

À distinguer des exclusions : la méthode s'applique mais rapporte moins. On peut s'y engager, en le sachant
et en le disant à l'utilisateur.

- **Système dominé par ses frontières externes** (service d'intégration fait surtout d'appels externes) :
  l'économie de doublures se dilue, les doublures externes (payées de toute façon) dominent le budget.
- **Application entière conduite sans mode composite** : le retour produit tardif se paie plein pot, et le
  gate devient prohibitif sur un monolithe en couches globales.

## 7. Le classement se vérifie en construisant

Le test vaut **hypothèse de départ**, que la construction met à l'épreuve. Se croire à tort en terrain
connaissable se détecte tôt, à deux signaux :

1. des **divergences répétées** entre la carte déclarée et le graphe réel (calculé par l'outillage) ;
2. des **défigeages en chaîne** dès les premières couches.

Ces signaux disent « **mauvais domaine** », pas « mauvaise exécution ». Réponse : **suspendre, sonder,
re-cartographier**, sans y voir un échec de discipline. Pour l'agent : surveiller ces signaux (via
`mcl.py verifier`, `mcl.py rapport`) et les signaler à l'utilisateur dès qu'ils apparaissent.

## 8. Combinaisons ponctuelles (indépendantes du mode composite)

| Situation | Approche recommandée |
|---|---|
| Incertitude sur l'expérience utilisateur | Outside-in d'abord (wireframe, BDD), puis MCL pour l'implémentation |
| Faisabilité technique inconnue | Spike ou prototype outside-in rapide → validation du concept → reconstruction inside-out |
| Dépendance circulaire dans le graphe | Briser le cycle par une abstraction, ou le condenser en composante (voir `03-cartographie.md`, 2.5.a) |
| Tâches d'infrastructure pure (déploiement, configuration) | Outside-in ou approche plate : aucun bénéfice à l'imbrication |

## 9. Les cinq frontières du résultat (II.8, par sévérité décroissante)

1. **Les artefacts exploratoires sont hors domaine.** Seule frontière qui *exclut* : la cartographie y produit
   une carte fictive payée en défigeages en chaîne. Contre-indiquée, pas « moins efficace ». Sortie
   constructive : sonder, stabiliser, reconstruire.
2. **La décomposition exige du jugement.** L'étape 2 guide, sans éliminer le jugement. Filet : l'invariant
   fournit un critère de validation *a posteriori* mécanique (toute unité de couche `k` qui référence une couche
   supérieure signale une décomposition erronée). On ne garantit pas une bonne décomposition ; on détecte
   mécaniquement une mauvaise.
3. **Le contrat spéculatif est un risque structurel.** Construire avant les consommateurs réels invite à
   généraliser ; la forme dangereuse est la **généricité fictive gelée** que des consommateurs épousent. Trois
   remparts : finalisation au moment responsable, discipline du besoin cartographié, extension additive ; le
   checkpoint détecte le résidu. Le risque reste plus élevé que dans une approche pilotée par le consommateur
   réel (la carte est un substitut des consommateurs, pas leur présence).
4. **Les dépendances circulaires sont atténuées, pas gratuites.** Dans une composante condensée, l'asymétrie
   des doublures se dégrade (co-construction bornée, doublures internes temporaires) : préférer la résolution
   architecturale quand elle est accessible.
5. **Aucune supériorité empirique généralisée n'est démontrée.** Le chemin pour la produire, dans les deux
   sens, est le protocole d'évaluation (`11-fondements-scientifiques.md`).

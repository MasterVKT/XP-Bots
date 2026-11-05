# 12 — Exemples travaillés

Les exemples A et B reprennent les illustrations du document (III.2). Les exemples C et D sont **dérivés**
(construits par application du protocole, hors document) et doivent être présentés comme tels.

## Sommaire
- A. Facturation, de bout en bout (composant, mode pur)
- B. Chaîne d'appels lire → calculer → afficher
- C. Machine à états (dérivé)
- D. Refactoring legacy avec baseline (dérivé)

---

## A. Facturation, de bout en bout

**Périmètre.** Artefact : composant « facturation » (échelle composant, mode pur). Le produit a déjà décidé de
le livrer ; MCL ne gouverne que sa construction.

**Applicabilité.** Structure connaissable (facturation = domaine connu) : oui. Contrats stabilisables tôt : oui.
Construire pour comprendre : non. → Applicable.

**Étape 1.** Haut niveau : transformer un texte de commande en facture. Entrée : texte (une ligne par produit :
produit ; quantité ; prix unitaire). Sortie : objet Facture. Contraintes : décimaux exacts. Greenfield.

**Étape 2.**
- 2.1 Entrée → structure représentant une ligne de commande ; sortie → structure Facture.
- 2.2 Flux : `parser_lignes → calculer_taxes → appliquer_remise → générer_facture` ; intermédiaires révélés :
  `LigneCommande`, `Facture`, `règles_tarifaires`.
- 2.3 Liste à plat : les quatre étapes, les trois intermédiaires, l'orchestrateur `facturer`.
- 2.4 Question-test : `LigneCommande`, `Facture`, `règles_tarifaires` → oui (feuilles) ; chaque étape → non,
  besoin des structures de la couche 0 seulement (pas d'une autre étape) ; `facturer` → non, besoin des quatre.

**Étape 3.** DAG : étapes → structures de 0 ; `facturer` → quatre étapes. `mcl.py analyser` : zéro cycle, zéro
divergence. Pas de frontière externe.

**Étape 4.** Carte : couche 0 = {LigneCommande, Facture, règles_tarifaires} ; couches parallèles 1a parser,
1b taxes, 1c remise, 1d génération ; couche 2 = `facturer` (enveloppe). Groupes parallèles signalés : 1a–1d.
Modules : `facturation.c0_noyau`, `facturation.c1a_parser`, …, `facturation.c2_enveloppe`. Fichier complet :
`assets/gabarits/carte.exemple.json`.

**Encodage.** `mcl.py exporter --outil importlinter --sortie .importlinter` : contrat `layers` listant
`c2_enveloppe`, puis `c1a_parser | c1b_taxes | c1c_remise | c1d_generation` (parallèles indépendantes), puis
`c0_noyau`. `lint-imports` en CI, ou `mcl.py verifier`.

**Étape 5.** Esquisse de toutes les unités dans `mcl/contrats/`. Finalisation de la couche 0 juste avant de la
construire : par exemple `LigneCommande` — responsabilité « représenter une ligne de commande » ; entrée :
produit (texte non vide), quantité (entier), prix unitaire (décimal) ; garanties : immuable ; erreurs : aucune.
Pas de champ « devise » tant qu'aucun consommateur cartographié ne l'exige (YAGNI de contrat).

**Étape 6.** Sans objet (aucune frontière externe). Si les règles tarifaires venaient d'une base de données :
port « source de barème » + doublure en mémoire dans les couches internes, implémentation réelle uniquement dans
la couche d'infrastructure, test de contrat commun aux deux.

**Étape 7.**
- Couche 0 : tests de catégorie 1 (construction des structures, valeurs du barème). Pas de catégorie 2. Gate :
  `mcl.py gate --couche 0 --unitaire "pytest tests/c0" --regression "pytest tests"` → vert ; `figer`.
- Couches 1a–1d (constructibles simultanément) : catégorie 1 de chacune sur les structures réelles de la couche 0
  (sociable par défaut : on fabrique des `LigneCommande` à la main, sans parser). Catégorie 2 : jonction avec le
  bloc réel {0}. Gate de chacune avec la suite intégrale, gel de chacune.
- Couche 2 : catégorie 1 de `facturer` ; catégorie 2 = scénarios traversant toute la profondeur (texte →
  facture), chemins représentatifs. Gate, gel. Enveloppe atteinte.

**Incident (aiguillage).** Un test d'intégration de la couche 2 exige le rejet d'une quantité négative ; il
échoue alors que la catégorie 1 de la couche 2 passe → aiguillage « interaction ou amont ». Remontée : la
tranche {1a + 0} accepte la quantité négative → niveau fautif 1a. Protocole correctif : `defiger --couche 1a
--nature correction`, test capturant le cas ajouté à la suite de 1a, correction **dans le parser** (à la source,
pas un contournement dans `facturer`). Contrat de 1a inchangé si le rejet était déjà spécifié (sinon : défigeage
`modification`, rayon = couche 2). Gate 1a, gel 1a, gate 2, gel 2. Pendant le défigeage de 1a, le gate de la
couche 2 est refusé.

**Étape 8.** Après deux niveaux figés, `statut` signale le checkpoint : révisions en lot (duplication du calcul
du montant entre 1b et 1c ?), un seul gate global, `checkpoint --notes`.

## B. Chaîne d'appels

Flux `lire_fichier → calculer_moyenne → afficher_résultat`, où chaque étape **invoque** la précédente. Question-
test : la structure de données lue (intermédiaire) est une feuille → couche 0 ; `lire_fichier` (dépend de la
structure, et du système de fichiers = frontière externe, doublée) → couche 1 ; `calculer_moyenne` → couche 2 ;
`afficher_résultat` → couche 3, enveloppe. Construire dans l'ordre du flux « en partant de la fin » tenterait de
bâtir l'affichage avant qu'il y ait quoi que ce soit à afficher ; l'inverser mécaniquement serait une autre
règle fausse : seule la question-test tranche.

## C. Machine à états (dérivé)

Cycle de vie d'une commande : Créée → Payée → Expédiée → Livrée ; Annulée depuis Créée ou Payée ; Payée →
Créée (échec de paiement, retour à la saisie). Graphe cyclique {Créée, Payée} ; condensation : composante
{Créée, Payée} (source, contient l'état initial) = couche 0 ; {Annulée} et {Expédiée} = couches parallèles 1a,
1b ; {Livrée} = couche 2. À l'intérieur de la composante {Créée, Payée} : **cycle minimal vivant** d'abord (état
initial Créée + transition Créée → Payée + transition de retour Payée → Créée), testé ; puis ajout des gardes et
cas une à une, en validant après chaque ajout. Pour `mcl.py analyser`, déclarer chaque état comme unité avec
`depend_de` = les états **depuis lesquels il est atteint** (orientation de dépendance, inverse du sens des
transitions) : l'outil signale alors la composante {Créée, Payée} en profondeur 0 et propose son traitement.

## D. Refactoring legacy (dérivé)

1. Applicabilité : structure lisible dans l'existant → oui presque automatique.
2. Cartographier le code tel qu'il est (unités, dépendances réelles) ; cycles fréquents → briser par interface
   si défaut de conception, sinon condenser.
3. Identifier les unités les moins couplées (dépendances externes minimales) → couche 0 : les extraire, les
   tester, les figer ; puis les unités ne dépendant que de 0 ; et ainsi vers l'extérieur jusqu'à ce que le point
   d'entrée legacy devienne la dernière couche.
4. Encoder la carte en **warn** ; `mcl.py baseline --creer --par <gardien> --motif "dette au jour J"` ; toute
   violation nouvelle bloque, toute violation résolue est retirée par `baseline --resserrer` et ne revient plus ;
   passage en **strict** règle par règle.

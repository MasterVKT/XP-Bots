# 11 — Fondements scientifiques : revendications, mécanismes, réfutabilité

Source : Partie II. À lire quand l'utilisateur demande *pourquoi* une règle existe, compare MCL à une autre
approche, veut instrumenter son équipe, ou rédige un texte de recherche. Sert aussi de garde-fou de discours :
ne rien affirmer au-delà de ce qui suit.

## Sommaire
1. Genre et trois familles de revendications
2. Le verdict d'innovation en quatre énoncés
3. Les fondements formels mobilisés
4. État de l'art : précédents, quatre méthodologies proches
5. Comparaison par axe avec le concurrent moderne (GOOS)
6. Statut de preuve des six contributions
7. Les quatre mécanismes analysables
8. Les huit hypothèses réfutables, les mesures, les designs
9. Discipline épistémique, frontières, agenda

---

## 1. Genre et revendications

MCL relève du **document de position et d'expérience** : proposition argumentée, issue d'une pratique de
terrain et d'un travail de formalisation, dont les bénéfices ont le statut d'**hypothèses testables**.
L'auteur-inventeur rapportant l'application de sa méthode ne produit pas une observation indépendante (coût
déclaré) ; vertu : aucune règle n'a été écrite avant d'avoir été exercée.

Trois familles, **jamais mélangées** :
- **documentaires** (ce que la littérature contient ou non) : vérifiables par les sources primaires,
  provisoires par nature (absence constatée ≠ inexistence démontrée) ;
- **analytiques** (fonctionnement du protocole : asymétrie driver/stub, localisation face à un delta unique,
  non-redondance des deux niveaux de test, croissance quadratique du coût de régression) : vérifiables par
  raisonnement, réfutables par contre-argument ;
- **empiriques** (effets mesurés) : **MCL n'en formule aucune**. Tout « la méthode réduit le temps de
  débogage » se reformule en hypothèse et se renvoie au protocole d'évaluation.

## 2. Verdict d'innovation (instruit en posture adversariale)

- *Innovation radicale : non.* Chaque composante a un précédent (années 1970, 1986, 2005, 2009…).
- *Innovation de synthèse : oui, avec mesure.* Aucune méthodologie nommée combinant les sept éléments trouvée ;
  Cleanroom (1987), GOOS (2009), RUP (1999/2003), Stratified Design (2021) en couvrent chacun trois à quatre.
- *Innovation de pont : oui, avec réserve historique.* Les architectures concentriques prescrivent une direction
  sans ordre de construction (confirmé sur sources primaires) ; exception : Hexagonal 2020-2024, absente du
  texte de 2005.
- *Formalisation du savoir tacite : oui, solidement établie* (parallèle TDD comme redécouverte selon Beck ;
  modèle SECI, Nonaka & Takeuchi 1995).

## 3. Fondements formels

| Mécanisme | Origine | Usage dans MCL |
|---|---|---|
| Tri topologique d'un graphe orienté | Kahn 1962 ; systèmes de build depuis les années 1970 | Ordre de construction des couches (étapes 3-4) |
| Critères de décomposition modulaire | Parnas, CACM 15(12), 1972 | Piège symétrique intercepté par la question-test de 2.4 |
| Composantes fortement connexes et condensation | Tarjan | Condensation d'un graphe cyclique en DAG ; ordre topologique inverse = ordre MCL |
| Ordre d'intégration et de test sous cycles (CITO) | Kung et al. 1995 ; Tai & Daniels 1999 ; Le Traon et al. 2000 ; Briand, Labiche & Wang 2002 | Objectif du point de coupe : minimiser nombre et richesse des doublures |
| Condensation + ordre topologique pour le build incrémental | Allen, Callahan & Kennedy 1989 ; Jørgensen 2001 ; Google 2015 | Repris tel quel |
| Design by Contract | Meyer 1986 (Eiffel) | Contrats avant implémentation (étape 5) |
| Last / Most Responsible Moment | Poppendieck 2003 ; Reinertsen 2009 | Finalisation un niveau d'avance sur le premier consommateur |
| Delta debugging | Zeller 1999 ; commandes `bisect` | Localisation du déclencheur face à un petit delta sur base verte |
| Fonctions de fitness statiques atomiques | Ford, Parsons & Kua 2017 ; ArchUnit, Deptrac… | Taxonomie de la carte encodée |
| Architecture Decision Records | Nygard 2011 | Forme des traces de défigeage |
| Loi de Conway ; Team Topologies | Conway 1968 ; Skelton & Pais 2019 | Interdiction des équipes par couches ; alignement sur les flux |
| Cynefin | Snowden & Boone 2007 | Domaine d'application : clair et compliqué |
| Programmation ascendante | Graham, *On Lisp*, 1993 | Antécédent direct de l'inside-out (retrouvé tardivement) |

Ce que MCL ajoute est toujours au même endroit : la **formulation opératoire au moment précis où le praticien se
trompe** (question-test, heuristiques bornées, contrôle de divergence ; précondition du delta debugging rendue
permanente ; carte justifiée par la dépendance fournie aux outils d'architecture).

## 4. État de l'art

Précédents par composante : construction ascendante (années 1970, contre le top-down de Mills et Wirth) ; test
d'intégration ascendant (1970-1980) ; TDD classiciste (Beck, C3, années 1990) ; Design by Contract (1986) ;
Clean Architecture (Martin, 2012) ; Onion (Palermo, 2008) ; Hexagonal (Cockburn, 2005) ; GOOS mock-first et
walking skeleton (Freeman & Pryce, 2009) ; Cleanroom (Mills, Dyer & Linger, 1987) ; RUP (1999-2003) ; Stratified
Design (Normand, 2021) ; walking skeleton, tracer bullet, Double-Loop TDD (1996-2009).

Les quatre plus proches : **Cleanroom** (certification incrémentale, spécifications avant code ; intégration
descendante, l'opposé de MCL ; pas de doublures) ; **GOOS** (rouge-vert-refactor, découverte d'interface par
doublures, direction outside-in : l'inverse de MCL et son **concurrent le plus sérieux**) ; **RUP** (intégration
progressive architecture-centrique, ni inside-out ni stratégie de doublure) ; **Stratified Design** (le plus
proche en substance, mais lentille de conception sans protocole). Toutes décrochent sur les deux mêmes points :
**direction de construction** et **confinement des doublures aux frontières externes**.

Légitimité de la synthèse : Clean Architecture est une synthèse explicite (Hexagonal, Onion, DCI, BCE) ; Palermo
a reconnu avoir rassemblé l'existant sous un nom nouveau.

## 5. Comparaison par axe (à échelle égale et domaine égal)

| Axe | MCL (artefact, domaine cadré) | Outside-in + tranches verticales (GOOS) | Verdict |
|---|---|---|---|
| Doublures à écrire | Les drivers *sont* les tests ; doublures aux frontières externes seulement | Doublures internes tant que l'intérieur n'existe pas | MCL, avantage qui se dilue avec le nombre de frontières externes |
| Localisation des régressions locales | Immédiate (delta unique sur base verte) | Dépend de la granularité du cycle | MCL |
| Défaut de contrat amont | Bissection bornée ; propagation nulle si contrat inchangé | Détecté plus tôt (bout en bout tôt) | Égalité, léger avantage concurrent |
| Retour produit de bout en bout | Tardif par construction | Dès le squelette | Concurrent (résolu par le composite à l'échelle application) |
| Sur-ingénierie interne | Risque élevé, borné par les checkpoints | Faible (le besoin externe pilote) | Concurrent |
| Pression de conception par les tests | Les tests vérifient des contrats déjà conçus | Les tests dessinent les interfaces | Concurrent (apport propre de GOOS) |
| Robustesse de la suite au refactoring interne | Tests sociables sur couches réelles | Tests d'interaction couplés aux collaborations | MCL |
| Artefacts exploratoires | Contre-indiquée | Le squelette explore | Concurrent |
| Domaine cadré ou algorithmique | Protocole guidé de bout en bout | Bon, moins guidé | MCL |
| Enseignabilité | Forte (étapes nommées) | GOOS subtil à enseigner | MCL |
| Enforcement de l'architecture | Prescrit (carte encodée) | Outillage disponible, non prescrit | Léger avantage MCL |

Mises en garde : **compter les lignes n'a aucun sens** (axes non commensurables, non équipondérés) ; **aucun
verdict n'est une mesure** (analyses mécanistes). Lecture légitime : les axes gagnés par MCL sont des propriétés
**structurelles** du protocole ; les axes concédés relèvent surtout du retour produit et de la conception pilotée
par le consommateur, que le composite réintroduit — sauf la pression de conception par les tests, acquis propre
de GOOS. En situation d'apprentissage, la ligne de base est le big bang : ce tableau ne s'y transpose pas.

## 6. Statut des six contributions

A1 revendication documentaire forte (réfutée par un texte antérieur reliant structure et ordre) ; A2 constat
documentaire **non probant** en soi (une conjonction de sept traits est presque toujours inédite ; l'apport est
l'imbrication ; la valeur de l'intégration reste une hypothèse) ; A3 solidement ancré (SECI ; TDD ; antécédent
NASA Mercury années 1960) ; A4 analyse mécaniste + prescription (règle exacte : toute couche plus interne, pas
« adjacente seulement ») ; A5 trait de conception observable ; A6 extension ancrée + dispositif non validé
(efficacité du composite sans validation contrôlée).

## 7. Les quatre mécanismes

1. **Asymétrie des doublures.** Avec une doublure par dépendance manquante, *n'importe quel* ordre satisfait
   techniquement « tester X sans Y ». En inside-out, la doublure nécessaire est un **driver**, qui est le test
   lui-même (coût déjà absorbé) ; ne restent que les doublures **externes**, dont le nombre dépend des frontières,
   pas de la profondeur. En ordre inverse, il faut des **stubs** de modules internes, en nombre croissant avec la
   largeur de l'arbre, au risque de fidélité. *Validité* : l'avantage porte sur le poste des stubs internes,
   entièrement évité sur un DAG ; dans une composante cyclique des doublures internes temporaires réapparaissent ;
   le delta ne s'inverse jamais mais se dilue quand les frontières externes dominent ; il ne couvre ni les tests
   d'intégration ni la régression, payés dans les deux ordres.
2. **Localisation face à un delta unique.** Déclencheur mécaniquement localisé ; régression locale (cause =
   déclencheur) contre défaut amont (recherche bornée : jusqu'à N sondes en séquentiel, ~log N en dichotomie).
   Limite : une couche gelée est validée, non prouvée.
3. **Économie du test à deux niveaux.** Refus de la sur-isolation : raison quantitative (k configurations à la
   couche k, total quadratique) et structurelle (sous-systèmes fictifs). Non-redondance auto-portée (gel +
   régression intégrale garantis par le protocole).
4. **Coûts déclarés.** Régression cumulée ~N²/2 (sélection en boucle interne, jamais au gate) ; sérialisation
   (Amdahl : la forme du graphe décide) ; retour produit tardif (composite à l'échelle application).

## 8. Réfutabilité

Objectif (GQM, Basili) : caractériser l'efficacité **comparée** de MCL sur localisation, coût des doublures,
retour et stabilité, du point de vue de l'équipe, dans le domaine d'application, contre la ligne de base de II.3.

Hypothèses :
1. **Localisation locale** bornée par la couche. *Réfutée si* le temps médian égale ou dépasse la ligne de base
   à tâches appariées.
2. **Défauts amont** : ~log N sondes ; propagation nulle à contrat inchangé. *Réfutée si* sondes nettement
   supérieures ou cascades fréquentes à contrat inchangé.
3. **Doublures** : volume et maintenance inférieurs, écart décroissant avec la part de frontières externes.
4. **Robustesse au refactoring** : moins de tests cassés par lot de révision que la ligne de base mockiste.
5. **Contrats** : extensions additives dominant les modifications ; généricité jamais consommée rare (lu dans
   l'historique des défigeages).
6. *(Défavorable)* **Retour** : premier retour de bout en bout plus tardif hors composite, comparable sous
   composite.
7. **Composite** : stabilité au moins égale à chaque approche seule, à retour comparable (design N2 ou N3).
8. *(Défavorable)* **Régression** : coût cumulé du gate quadratique ; si la courbe dément, corriger la
   déclaration.

Mesures : temps moyen de localisation, précision Top-N, localisation spectrale en CI ; Test Double Ratio, Useless
Stub Ratio, effort de maintenance par analyse statique ; délai de bout en bout et métriques DORA (pour piloter,
**jamais pour comparer des équipes**). Lecture : médianes et percentiles ; définitions opérationnelles avant
collecte ; lectures croisées (pipeline plus rapide + doublures inutiles en hausse = sous-test).

Auto-instrumentation : six hypothèses sur huit se lisent dans les traces que le protocole produit (historique
des défigeages, journaux du gate, baseline, cartes versionnées) — exactement ce que `mcl/journal.jsonl` et
`mcl.py rapport` fournissent (niveau N1).

Designs : **N1** auto-mesure (baseline de 2 à 4 semaines puis lecture longitudinale ; préliminaire, sans groupe
de contrôle) ; **N2** quasi-expérience intra-équipe, plan croisé AB/BA sur tâches appariées, même échelle, même
domaine ; **N3** multi-projets (au moins deux, ligne de base opérationnalisée, déploiement progressif).

Menaces : ordre et apprentissage (croisement AB/BA) ; hétérogénéité d'expertise (effet d'expertise inversée :
**stratifier** novices et confirmés au lieu de moyenner) ; validité de construit (aucune métrique unique, aucun
proxy non documenté) ; validité externe (pas de généralisation hors domaine) ; petits effectifs (transparence).
Engagement : résultats publiés positifs et négatifs.

## 9. Discipline épistémique, frontières, agenda

- Quatre campagnes documentaires adversariales (13 affirmations ; Google Scholar, ACM DL, IEEE Xplore, arXiv,
  Semantic Scholar, sources praticiennes, sources primaires de Martin, Palermo, Cockburn, Meyer, Beck) =
  **réplication corrélée**, pas quatre preuves indépendantes. Angle mort constaté et corrigé : *On Lisp* (1993).
  La confiance repose sur des sources nommées contrôlables une à une. Une seule des treize affirmations, A13
  (liée à l'évidence en éducation), a été démentie par les campagnes ; selon le document, c'est sans
  conséquence sur l'argument pédagogique réel. Son détail relève de la Partie IV, absente de la source.
- Frontières : voir `02-applicabilite.md`, section 9.
- Agenda (six questions) : valeur de l'intégration (le paquet fait-il mieux que ses éléments épars ? design N2
  avec bras partiels) ; efficacité propre du composite ; seuil de dilution des doublures ; forme réelle de la
  courbe de coût sous sélection de tests ; transfert hors domaine cadré ; versant éducatif.

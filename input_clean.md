**Matryoshka Construction Layers (MCL)**

Document de référence multi-perspective

*Concepts, méthodologie et application 

*recherche en génie logiciel, pratique professionnelle,*



**Par M. Ing., Eric Vekout, PMP, Prince 2, PSM 2**

Août 2026

## Document de référence multi-perspective



Août 2026

**Auteur** Eric Vekout Maître Ingénieur en Génie Logiciel · Maître
Ingénieur en Formation Enseignant d\'université (Douala, Cameroun) ·
Chercheur indépendant ORCID : 0009-0000-8333-5372 · Correspondance :
<vekout@yahoo.fr>



**Statut** Document de référence de la méthode. Il fait autorité pour
l\'usage de MCL dans les quatre postures qu\'il adresse.

## Résumé

Matryoshka Construction Layers (MCL) est une méthode de construction
logicielle qui prescrit de bâtir le code d\'une unité de travail donnée
(fonction, module, composant, service, algorithme, application) en
partant de son unité fonctionnelle la plus fondamentale, puis en
ajoutant des couches de complexité croissante, chacune entièrement
validée et gelée avant que la suivante ne soit construite. L\'ordre des
couches suit le graphe des dépendances, jamais l\'ordre d\'exécution du
flux. Un invariant unique gouverne l\'ensemble : aucune couche n\'est
construite tant que toutes celles dont elle dépend ne sont pas testées,
validées et stables.

Le protocole se déploie en huit étapes, de la cartographie du système
jusqu\'aux points de contrôle de refactoring, en passant par la
définition des contrats d\'interface avant tout code, le confinement des
doublures de test aux frontières externes, et un *regression gate* non
négociable à chaque couche. Deux propriétés en découlent directement :
la carte des couches devient une déclaration vérifiable au build, et
tout échec de régression s\'analyse contre un delta unique appliqué à
une base entièrement verte.

Ce document expose MCL selon quatre angles traités de façon quasi
autonome : la recherche en génie logiciel, la pratique professionnelle
du développement, la recherche en sciences de l\'éducation appliquée à
l\'apprentissage du développement, et la formation concrète. Chaque
partie peut se lire seule ; des renvois explicites relient celles qui
s\'éclairent mutuellement.

**Mots-clés** : construction logicielle incrémentale ; ordre de
dépendance ; graphe acyclique orienté ; contrats d\'interface ; tests de
régression ; architecture en couches ; charge cognitive ; formalisation
du savoir tacite ; pédagogie de la programmation.

##Note de version

La méthode a porté le nom de « Méthode Matryoshka » avant de recevoir sa
dénomination actuelle, **Matryoshka Construction Layers (MCL)**. Le
motif de ce choix et les conventions de citation figurent en 0.2 et à
l\'annexe D.

## Table des matières

Matryoshka Construction Layers (MCL)
[2]

Document de référence multi-perspective
[2]

Concepts, méthodologie et application
selon quatre postures : recherche en génie logiciel, pratique du génie
logiciel, recherche en éducation au développement logiciel, formation au
développement logiciel [2]

Résumé
[2]

Note de version
[3]

Table des matières
[3]

PARTIE 0 --- AVANT-PROPOS
[10]

0.1 Objet et périmètre du document
[10]

0.2 Note de nomenclature : de «
Matryoshka » à MCL [10]

0.3 Les quatre postures adressées
[11]

0.4 Parcours de lecture
[11]

0.5 Conventions du document
[12]

0.6 Genèse de la méthode
[13]

0.7 Statut épistémique
[14]

PARTIE I --- SOCLE COMMUN
[16]

I.1 Le problème adressé
[16]

I.2 Le concept fondateur
[16]

I.3 L\'invariant central
[17]

I.4 Vocabulaire unifié
[18]

I.5 Les trois échelles et la règle de
périmètre [19]

I.6 Le protocole en huit étapes
[20]

I.7 Les deux catégories de test et le
*regression gate* [21]

I.8 Les six axes de contribution de MCL
[22]

I.9 Le domaine d\'application
[24]

PARTIE II --- ASPECT SCIENTIFIQUE : GÉNIE
LOGICIEL [26]

II.0 Cadrage
[26]

II.1 MCL comme objet de recherche
[26]

Le genre
[26]

Trois familles de revendications, jamais
mélangées [26]

Le verdict d\'innovation, en quatre
énoncés [27]

II.2 Les fondements formels mobilisés
[28]

II.3 État de l\'art et analyse d\'écart
[29]

Les précédents par composante
[29]

Les quatre méthodologies les plus proches
[30]

La comparaison par axe avec le concurrent
moderne [31]

La légitimité de la synthèse comme forme
de contribution [32]

II.4 Les six contributions, caractérisées
[33]

II.5 Les mécanismes, énoncés en termes
analysables [34]

L\'asymétrie des doublures
[34]

La localisation face à un delta unique
[35]

L\'économie du test à deux niveaux
[36]

Les coûts déclarés
[36]

II.6 Réfutabilité : hypothèses, mesures,
designs [37]

L\'objectif
[37]

Les huit hypothèses réfutables
[37]

Les mesures
[38]

L\'auto-instrumentation
[38]

Trois niveaux de design
[39]

Menaces à la validité
[39]

L\'engagement
[39]

II.7 La discipline épistémique intégrée
[39]

II.8 Les frontières du résultat
[40]

II.9 Agenda de recherche
[42]

II.10 Renvois croisés
[42]

PARTIE III --- ASPECT PROFESSIONNEL :
GÉNIE LOGICIEL [44]

III.0 Cadrage
[44]

III.1 Choisir l\'artefact, puis vérifier
qu\'il s\'y prête [44]

La première décision est une décision de
périmètre [44]

Le test en trois questions
[45]

Le classement se vérifie en construisant
[45]

III.2 Cartographier : les étapes 1 à 4
[46]

Étape 1 --- Comprendre la cible
[46]

Étape 2 --- Décomposer en unités
fonctionnelles [46]

2.5 --- Les systèmes qui ne sont pas des
flux [49]

Étape 3 --- Construire le graphe de
dépendances [51]

Étape 4 --- Assigner les couches
[51]

III.3 Encoder la carte : l\'invariant
devenu règle de build [52]

III.4 Les contrats d\'interface : étape 5
[53]

La discipline du contrat minimal
[53]

III.5 Les frontières externes : étape 6
[54]

III.6 La boucle de construction : étape 7
[55]

Ce que « tester » veut dire exactement
[55]

Ce que la méthode ne fait pas
[56]

Ce que le gel gèle, ce qu\'il laisse
libre [56]

III.7 Quand ça casse : diagnostic et
correction [57]

L\'aiguillage, qui est mécanique
[57]

La remontée de couches
[58]

Le protocole correctif
[58]

III.8 Le *gate* à l\'échelle
[59]

III.9 Gouvernance : qui décide quoi
[60]

III.10 Les checkpoints de refactoring :
étape 8 [61]

III.11 Organiser le travail : ce qui se
parallélise [61]

III.12 Stacks de référence par contexte
technique [62]

III.13 Le mode composite : squelette
outside-in, chair MCL [64]

Combinaisons ponctuelles
[65]

III.14 Positionnement avec ce que vous
utilisez déjà [65]

III.15 Adopter MCL en équipe
[66]

III.16 Ce que MCL apporte au praticien
[67]

III.17 Ce qui conditionne le bénéfice
[68]

III.18 Renvois croisés
[68]

# PARTIE 0 --- AVANT-PROPOS

## 0.1 Objet et périmètre du document

Quatre publics se sont formés autour de MCL, et ils ne posent pas la
même question à la méthode. Le praticien veut savoir comment faire,
geste par geste. Le chercheur en génie logiciel veut des revendications
typées et un protocole d\'évaluation. Le chercheur en éducation veut des
constructs et des fondements théoriques. Le formateur veut un
dispositif, une progression, une grille de correction. Un exposé unique,
écrit pour l\'un d\'eux, oblige les trois autres à extraire eux-mêmes ce
qui les concerne d\'un texte qui ne les vise pas.

Ce document est écrit pour les quatre. Il expose la méthode entière,
sous quatre éclairages traités de façon quasi autonome. Un socle commun
bref (Partie I) porte ce qui ne peut pas être dit quatre fois : le
concept, l\'invariant, le vocabulaire, le protocole en vue d\'ensemble.
Les quatre parties qui suivent sont conçues pour être lues seules,
chacune dans son registre, chacune avec son propre appareil de
justification.

Une règle a gouverné la rédaction, et elle explique la forme du texte :
l\'autonomie sans redondance. Les renvois croisés remplacent la
répétition, et ils sont assez précis pour qu\'un lecteur les suive sans
se perdre. Un praticien qui n\'ouvre que la Partie III y trouve de quoi
construire de bout en bout ; s\'il veut savoir pourquoi le protocole
ordonne ce qu\'il ordonne, deux renvois le conduisent à l\'argument.

Le pari est qu\'un lecteur puisse entrer par sa porte, y trouver la
méthode dans sa forme utilisable, et n\'aller voir ailleurs que par
curiosité pour le raisonnement des autres.

## 0.2 Note de nomenclature : de « Matryoshka » à MCL

La méthode a longtemps porté le seul nom de « Matryoshka ». Le mot est
parlant : il dit d\'un coup l\'emboîtement, l\'ordre d\'assemblage,
l\'impossibilité de fermer le jeu si une figurine intermédiaire est
défectueuse. Il a un défaut : d\'autres travaux, dans des domaines sans
rapport avec le génie logiciel, l\'ont adopté pour désigner des
mécanismes eux aussi emboîtés. Un lecteur qui rencontre « méthode
Matryoshka » n\'a plus de garantie sur ce dont on lui parle.

D\'où le nom retenu ici : **Matryoshka Construction Layers**, abrégé
**MCL**. Il conserve l\'analogie fondatrice et ajoute ce qui lève
l\'ambiguïté. *Construction*, parce que la méthode gouverne l\'acte de
construire, non l\'organisation statique du code. *Layers*, parce que
l\'unité d\'avancement est la couche de profondeur de dépendance.

Le changement est purement nominal : la méthode n\'a pas bougé d\'une
virgule. Les travaux antérieurs qui parlent de « Méthode Matryoshka »
désignent MCL. Les conventions de citation et la façon de mentionner
l\'antériorité figurent à l\'annexe D.

## 0.3 Les quatre postures adressées

Quatre lecteurs, quatre questions différentes posées au même objet.

**Le chercheur en génie logiciel** demande : qu\'est-ce que MCL
revendique exactement, sur quoi ces revendications s\'appuient, en quoi
diffèrent-elles de ce que la littérature contient déjà, et comment les
mettre à l\'épreuve ? Sa partie est la II. Elle est construite comme un
dossier de revendications typées, adossé à un protocole d\'évaluation
que la méthode publie elle-même.

**Le praticien** (développeur, *tech lead*, architecte) demande :
comment je fais, concrètement, lundi matin, sur mon artefact ? Sa partie
est la III, la plus volumineuse du document, parce que c\'est la seule
dont chaque ligne est destinée à être exécutée.

**Le chercheur en sciences de l\'éducation** travaillant sur
l\'apprentissage de la programmation demande : quel effet
d\'apprentissage MCL prédit-il, sur quelle théorie, et qu\'est-ce qui,
dans la littérature existante, soutient ou contredit cette prédiction ?
Sa partie est la IV. Elle assume une position inhabituelle : elle
commence par ce que l\'évidence disponible ne soutient pas, parce que
c\'est de là que part l\'argument réel.

**Le formateur** (enseignant, concepteur pédagogique, mentor technique)
demande : comment j\'enseigne ça, dans quel ordre, avec quel matériel,
et comment j\'évalue ? Sa partie est la V.

Ces quatre lecteurs se croisent plus qu\'ils ne le pensent. Le praticien
qui intègre un nouveau membre d\'équipe entre dans la posture du
formateur ; le formateur qui veut savoir pourquoi sa progression
fonctionne entre dans celle du chercheur en éducation ; le chercheur en
génie logiciel qui conçoit une quasi-expérience a besoin du protocole
opérationnel exact. Les renvois croisés de chaque partie balisent ces
passages.

## 0.4 Parcours de lecture

  ---------------------------------------------------------------------------
  Vous êtes...     Lisez       Puis       Utile ensuite
                   d\'abord               
  ---------------- ----------- ---------- -----------------------------------
  Chercheur en     Partie 0,   **Partie   III.2 à III.8 pour
  génie logiciel   Partie I    II**       l\'opérationnalisation exacte de ce
                                          que II.6 propose de mesurer ;
                                          annexe C pour les sources

  Développeur,     0.4--0.5,   **Partie   II.6 si vous instrumentez votre
  *tech lead*,     Partie I    III**      équipe ; Partie V si vous formez ou
  architecte                              intégrez quelqu\'un

  Chercheur en     Partie 0,   **Partie   Partie V pour le dispositif
  sciences de      I.1 à I.6   IV**       réellement déployable ; II.6 dont
  l\'éducation                            IV.9 est l\'extension

  Formateur,       0.4--0.5,   **Partie   Partie IV pour les fondements
  enseignant,      Partie I    V**        théoriques du dispositif ; Partie
  mentor                                  III pour le contenu technique à
                                          transmettre

  Décideur,        0.1 à 0.3,  III.1,     II.8 et VI.3 pour ce que la méthode
  responsable      I.1 à I.5,  III.15 à   ne promet pas
  technique        I.8         III.17     
  ---------------------------------------------------------------------------

Le socle (Partie I) est court par construction. Le sauter est possible
pour qui pratique déjà la méthode ; le sauter sans la connaître rend les
quatre parties suivantes illisibles, car elles s\'appuient toutes sur le
vocabulaire fixé en I.4 et sur l\'invariant de I.3.

## 0.5 Conventions du document

Cinq types d\'encadrés reviennent d\'un bout à l\'autre. Ils portent
chacun une fonction distincte, et cette distinction compte : elle sépare
ce que MCL emprunte de ce qu\'elle apporte, et ce qu\'elle promet de ce
dont la promesse dépend.

> **Ancrage.** Rattache un mécanisme à son précédent documenté dans la
> littérature. Ils valent argument de fiabilité : un rouage éprouvé
> ailleurs entre ici avec son historique.
>
> **Apport.** Ce que MCL ajoute au précédent qui vient d\'être cité, ou
> ce qu\'elle rend possible et qui n\'existait pas sous cette forme.
>
> **Renvoi.** Lien vers une autre partie du document, avec l\'objet
> exact du lien.
>
> **Condition.** Ce dont dépend un bénéfice annoncé. Les conditions
> énoncées ici se vérifient sur le terrain.
>
> **En pratique.** Le geste concret, au niveau de détail où il
> s\'exécute.

Quelques notations reviennent également. Une **couche** est notée par
son indice de profondeur : couche 0, couche 1, couche `k`. Le **bloc**
des couches déjà construites et gelées, de la plus interne jusqu\'à `k`,
s\'écrit `{0 → k}`. Les unités situées à la même profondeur sans
dépendance mutuelle se distinguent par une lettre : couches 1a, 1b, 1c.
Le mot **artefact** désigne partout l\'unité de travail choisie, quelle
que soit son échelle. Sa définition exacte est en I.4. Elle mérite
l\'attention : presque tous les malentendus sur MCL viennent d\'une
confusion d\'échelle.

Les termes techniques sont définis à leur première occurrence utile dans
chaque partie, et repris à l\'annexe A. Un lecteur qui n\'ouvre qu\'une
seule partie n\'a donc pas à en chercher ailleurs le sens.

## 0.6 Genèse de la méthode

MCL n\'est pas née d\'une lecture. Elle est née de deux agacements,
l\'un professionnel, l\'autre pédagogique, qui se sont révélés être le
même.

Le premier : je cherchais une façon d\'implémenter des applications
d\'une complexité suffisante pour être un vivier d\'erreurs, sans que le
débogage devienne l\'essentiel du travail. Réduire le nombre de bugs par
la seule vertu ne fonctionne pas. Je cherchais plutôt à ce que la
localisation d\'un défaut devienne une question à réponse courte, au
lieu d\'une enquête.

Le second : depuis plusieurs années, dans plusieurs universités de
Douala et à plusieurs niveaux, je voyais mes étudiants buter au même
endroit. Pas sur la syntaxe, pas sur les concepts pris isolément. Sur le
passage de l\'idée à l\'implémentation. Ils savaient ce que
l\'application devait faire ; ils ne savaient pas par où l\'écrire. Je
cherchais une méthode assez précise pour être appliquée par quelqu\'un
en formation, et assez explicite pour qu\'il comprenne *pourquoi* elle
marche --- parce qu\'une méthode appliquée mécaniquement produit parfois
de bons résultats, mais elle ne produit jamais quelqu\'un capable de
l\'adapter à un contexte qu\'elle n\'avait pas prévu. C\'était
l\'objectif réel : que l\'apprenant se représente mentalement les
abstractions en jeu et le chemin qui les mène au code, pas qu\'il coche
des cases.

Cette double origine a laissé sa marque sur la méthode, et elle explique
une partie de ce qui suit. Née d\'un seul problème d\'ingénierie, elle
n\'aurait produit ni étapes nommées, ni progression d\'apprentissage, ni
critère de passage formulé pour être exigible d\'un débutant. Née d\'un
seul problème d\'enseignement, elle n\'aurait pas tenu à l\'échelle
d\'une application réelle, ni prévu sa gouvernance, ni compté ses coûts.
Les deux exigences ont travaillé l\'une contre l\'autre pendant six
mois. Ce qui a survécu à cette contrainte double est ce qui est écrit
ici.

Les deux problèmes ont convergé vers la même réponse, et c\'est en
réfléchissant à sa mise en œuvre concrète que le nom s\'est imposé : le
mécanisme que je décrivais était celui des poupées russes. Une figurine
intérieure autonome, chacune enveloppant les précédentes, et
l\'impossibilité de fermer le jeu si une intermédiaire est défectueuse.
Encore faut-il l\'avoir manipulée séparément pour le savoir.

La maturation s\'est faite entre janvier et juin 2026, en boucle serrée
avec la pratique. Les révisions successives ne correspondaient pas à des
jalons de calendrier, mais à des passes de correction : chaque fois que
je repérais une faille dans la méthode, chaque fois qu\'un projet mené
avec elle révélait un défaut induit par son application, chaque fois
qu\'un point manifestement améliorable apparaissait, une version
suivante l\'absorbait. Les projets industriels sur lesquels elle a été
éprouvée ne sont donc ni antérieurs ni postérieurs à la formalisation :
les deux se sont nourris l\'un l\'autre. Cette configuration a un coût
méthodologique que la Partie II ne dissimule pas ; elle a aussi une
vertu, celle d\'avoir soumis chaque règle à un usage réel avant de
l\'écrire.

Avant ce document et son article compagnon, MCL n\'avait fait l\'objet
d\'aucune diffusion publique.

## 0.7 Statut épistémique

Il faut dire tout de suite dans quel registre ce document parle, parce
que la suite en dépend.

MCL est une **synthèse cohérente et une formalisation opérationnelle**
de pratiques individuellement bien établies : construction ascendante,
contrats d\'interface avant le code, doublures confinées aux frontières
externes, test d\'intégration incrémental, vérification mécanique des
règles de dépendance. Aucun de ces éléments n\'est neuf, et le document
le dira chaque fois qu\'il en emploie un, à l\'endroit où il l\'emploie.
Cette transparence sert la méthode : un protocole assemblé de rouages
éprouvés depuis 1962, 1972, 1986 ou 1999 hérite de leur fiabilité.

Ce qui est revendiqué se situe ailleurs, et se situe précisément : le
pont explicite entre la règle de dépendance des architectures
concentriques et un protocole de construction ordonné et validé à chaque
étape ; l\'intégration opérationnelle d\'éléments qui, dans la
littérature, existent séparément ; l\'externalisation d\'un savoir que
les développeurs expérimentés appliquent par réflexe sans l\'avoir
jamais rendu transmissible. La grille complète de ces axes est déclarée
en I.8 et instanciée dans chacune des quatre parties, dans le registre
qui convient à chacune.

Trois disciplines de lecture s\'appliquent partout.

**Les revendications sont typées.** Ce qui est établi et sourçable est
présenté comme tel. Ce qui relève d\'une analyse mécaniste,
c\'est-à-dire d\'un raisonnement sur le fonctionnement du protocole sans
mesure à l\'appui, est présenté comme tel. Ce qui reste à démontrer est
présenté comme une hypothèse. Ces trois statuts ne sont jamais mélangés
dans une même phrase.

**Le résultat de vérification est daté.** L\'état de l\'art de la Partie
II provient de quatre campagnes de recherche documentaire menées en
posture adversariale, avec instruction explicite de chercher à réfuter
les affirmations d\'originalité plutôt qu\'à les confirmer. Quatre
exécutions du même type d\'instrument sur des corpus largement partagés
constituent une réplication corrélée, non quatre preuves indépendantes :
elles protègent contre l\'échec ponctuel d\'une recherche, pas contre un
angle mort partagé. Un tel angle mort a d\'ailleurs été constaté et
corrigé après coup. La confiance de ce document ne repose donc pas sur
le nombre de recherches convergentes, mais sur le fait que chaque
affirmation cite ses sources nommées et se contrôle une à une.

**Les bénéfices annoncés sont réfutables, et le protocole pour les
réfuter est publié.** MCL déclare huit hypothèses testables, dont deux
lui sont défavorables : le retour produit de bout en bout arrive plus
tard hors mode composite, et le coût cumulé de la régression croît de
façon quadratique avec le nombre de couches. Elles ont le même statut
que les six autres : des prédictions mesurables, dont la confirmation
compte comme un résultat à part entière. Une méthode qui annonce ce
qu\'elle coûte et fournit les instruments pour vérifier qu\'elle coûte
bien cela se met dans une position que peu de méthodes de construction
occupent. Six de ces huit hypothèses se lisent, du reste, dans des
traces que le protocole produit tout seul, sans instrumentation ajoutée
: historique des dégels de contrat, journaux du *gate*, baseline de
dette, cartes de couches versionnées. Le premier niveau d\'évaluation ne
coûte presque rien à une équipe qui applique la méthode.

Reste ce que rien ne permet encore d\'affirmer, et qui ne le sera pas
ici : MCL ne doit pas être présentée comme produisant statistiquement de
meilleurs résultats qu\'une autre approche. L\'évidence disponible ne le
permet pas. Ce qu\'elle permet, et qui n\'est pas rien pour une méthode
de cet âge : dire axe par axe ce qu\'on achète et ce qu\'on paie en
l\'adoptant, puis fournir le dispositif qui tranchera. Cette comparaison
par axe est en II.3 ; le dispositif est en II.6.

# PARTIE I --- SOCLE COMMUN

Cette partie porte ce qui ne peut pas être répété quatre fois. Elle est
délibérément courte, et elle est supposée acquise partout ailleurs dans
le document : le concept, l\'invariant, le vocabulaire, la vue
d\'ensemble du protocole, la grille des apports, le domaine où la
méthode a du sens. Un lecteur pressé peut la traiter comme une carte
routière et revenir chercher le détail dans sa propre partie.

## I.1 Le problème adressé

Écrire toutes les parties d\'un système puis chercher pourquoi
l\'ensemble ne fonctionne pas. Le problème est vieux, il porte un nom
informel chez les praticiens depuis les années 1970, le *magic
subroutine problem*, et il décrit ce qui arrive quand on code de haut en
bas : la complexité non résolue est repoussée de module en module
jusqu\'à s\'accumuler dans un dernier composant qu\'il devient
impossible d\'implémenter dans les temps.

Ce problème motive MCL. Il n\'en est pas le concurrent, et la
distinction commande tout le reste. La pratique professionnelle moderne
l\'a déjà largement traité par d\'autres voies : conception outside-in,
tranches verticales livrées de bout en bout, intégration continue.
Comparer MCL au chaos que ces pratiques ont remplacé n\'aurait aucun
intérêt. La comparaison utile se mène contre elles, et c\'est celle que
la Partie II conduit axe par axe.

Il existe cependant un second contexte, et sa ligne de base n\'est pas
la même. Chez l\'apprenant, la pratique effectivement observée reste
l\'intégration *big bang* : tout le code écrit, puis un test final, puis
un débogage qui décourage plus qu\'il n\'enseigne. La comparaison
professionnelle ne se transpose donc pas telle quelle au terrain
pédagogique. Les Parties IV et V travaillent contre cette seconde ligne
de base ; les Parties II et III contre la première. Confondre les deux
produit des affirmations fausses dans les deux sens.

## I.2 Le concept fondateur

Une *matryoshka* est un jeu de figurines en bois emboîtées. La plus
intérieure ne contient rien et ne dépend de rien. Chacune des suivantes
enveloppe toutes celles qui sont déjà à l\'intérieur. On ne peut pas
fermer le jeu si une figurine intermédiaire est défectueuse, et pour le
savoir il faut l\'avoir manipulée séparément, avant l\'assemblage.

Transposé au code : la couche la plus profonde d\'un système est
l\'unité dont tout le reste dépend et qui, elle, ne dépend de rien. On
la construit, on la teste isolément, on la valide, on la gèle. On lui
ajoute ensuite la couche qui la contient. On valide de nouveau. Ainsi
jusqu\'à l\'enveloppe finale.

Une seconde image dit la même chose autrement. Devant une structure
`for ``i`` ``{ for`` j ``{ for`` k ``{ …`` ``} ``}`` }` qui produit un
résultat faux, le réflexe de tout développeur est d\'isoler d\'abord la
boucle `k`, puis de remonter vers `j`, puis vers `i`. Ce réflexe est
universel, et il est réservé au débogage. MCL l\'élève au rang de
méthode de construction, appliquée dès le premier jour plutôt qu\'au
moment où tout est déjà écrit.

> **Apport.** Le geste que la méthode généralise est déjà dans les mains
> de tout le monde. Personne n\'a besoin d\'être convaincu qu\'on isole
> la boucle interne avant de remonter : c\'est ce que fait n\'importe
> quel développeur devant un résultat faux. MCL ne demande donc pas
> d\'adopter une intuition nouvelle, mais d\'appliquer avant la
> construction celle qu\'on applique déjà après l\'échec. C\'est ce qui
> la rend transmissible en quelques heures, là où une architecture
> demande des mois.

## I.3 L\'invariant central

> **Une couche n\'est jamais construite tant que toutes les couches dont
> elle dépend ne sont pas testées, validées et stables.**

Cet énoncé est non négociable, et il faut lire avec exactitude ce qu\'il
garantit comme ce qu\'il ne garantit pas. Les deux lectures sont
également importantes ; la seconde évite la plupart des déceptions
qu\'une lecture rapide provoque.

**La garantie donnée : la stabilité du bloc.** À tout instant de la
construction, l\'ensemble de ce qui existe est testé, intégré et stable.
Le bloc `{0 → k}` est un sous-ensemble validé du système final, pas un
prototype jetable ni un chantier en cours. « Fonctionne » s\'entend au
sens du code : chaque contrat tenu, chaque test vert. Tant que
l\'enveloppe n\'existe pas, la suite de tests est d\'ailleurs le seul
moyen d\'exécuter ce bloc, puisqu\'il n\'a pas encore de point
d\'entrée.

**La garantie non donnée : le chemin de bout en bout.** Aucune
fonctionnalité n\'est démontrable de l\'entrée utilisateur jusqu\'à la
sortie avant que les couches externes ne soient construites. Un
développeur peut exercer le bloc par ses tests ; un utilisateur n\'en
peut rien faire. Le retour produit arrive donc tard, et il arrive tard
*par construction de l\'ordre inside-out*. C\'est l\'axe sur lequel les
approches outside-in gardent l\'avantage, et MCL ne le conteste pas :
elle prévoit la combinaison des deux quand un retour précoce a de la
valeur (mode composite, I.5 et III.13).

## I.4 Vocabulaire unifié

Les mots qui suivent ont un sens précis dans tout le document. Presque
tous les malentendus sur MCL viennent d\'un glissement sur l\'un d\'eux,
et deux méritent une vigilance particulière : *artefact*, parce qu\'il
fixe l\'échelle, et *couche*, parce que le mot est déjà pris ailleurs
par une acception qui n\'est pas la nôtre.

  ----------------------------------------------------------------------------
  Terme             Sens dans MCL
  ----------------- ----------------------------------------------------------
  **Artefact**      L\'unité de travail choisie, à quelque échelle que ce soit
                    : une tâche, une tranche fonctionnelle, un composant
                    autonome, une application entière. C\'est *sur* un
                    artefact que le protocole s\'applique.

  **Unité           Un élément à responsabilité unique énonçable en une
  fonctionnelle**   phrase, spécifié entrée → transformation → sortie (ou
                    changement d\'état), et lié par au moins une relation de
                    dépendance à une autre unité.

  **Couche**        Une **profondeur de dépendance** à l\'intérieur de
                    l\'artefact. Ce n\'est pas une strate technique au sens
                    des architectures en tiers, et ce n\'est jamais un
                    découpage d\'équipe. La couche 0 regroupe les unités qui
                    ne dépendent de rien.

  **Couches         Les unités de même profondeur sans dépendance mutuelle :
  parallèles**      couches 1a, 1b, 1c. Elles sont candidates à une
                    construction simultanée.

  **Bloc**          L\'ensemble des couches construites, validées et gelées
  `{0 → k}`         jusqu\'à la profondeur `k`. Un système unique déjà
                    intégré, pas un empilement à réassembler.

  **Contrat**       L\'interface publique d\'une unité : responsabilité,
                    signature, entrées et contraintes, sorties et garanties,
                    effets de bord, conditions d\'erreur. Rédigé avant
                    l\'implémentation.

  **Gel (FIGER)**   L\'opération qui rend le contrat d\'une couche *read-only*
                    une fois celle-ci validée. Le gel porte sur le contrat,
                    pas sur l\'implémentation interne, qui reste révisable
                    sous harnais complet.

  **Défigeage**     La levée formelle du gel, pour changer un contrat ou
                    corriger un défaut. Elle est tracée et sa propagation est
                    conditionnelle.

  **Doublure**      Terme générique pour les substituts de test. Un *driver*
                    appelle l\'unité testée ; un *stub* ou un *mock* remplace
                    une dépendance absente. C\'est sur cette distinction que
                    repose l\'économie de la méthode (II.5).

  **Frontière       Une dépendance hors du système : base de données, API
  externe**         tierce, service de paiement, système de fichiers. C\'est
                    le seul endroit où MCL impose des doublures.

  **Carte des       La déclaration explicite de l\'assignation des unités aux
  couches**         couches. Versionnée avec le code, elle devient une règle
                    vérifiée au build.

  ***Regression     Le point de passage obligé entre deux couches : la
  gate***           totalité de la suite de tests existante doit repasser au
                    vert avant que la couche courante ne soit gelée.

  **Mode            La combinaison d\'un squelette outside-in déployé dès le
  composite**       départ et d\'une chair construite au protocole MCL. Mode
                    d\'emploi de référence à l\'échelle d\'une application
                    entière.
  ----------------------------------------------------------------------------

## I.5 Les trois échelles et la règle de périmètre

**La règle de périmètre.** MCL gouverne *comment construire le code*
d\'une unité de travail déjà choisie. Elle ne décide jamais *quoi*
livrer, ni *dans quel ordre* le livrer. Ces décisions relèvent du niveau
produit (tranches, backlog, feuille de route), avec lequel la méthode
s\'articule sans le remplacer. Cette règle est la réponse à l\'objection
la plus fréquente en équipe, celle du « encore une méthode » : la
cadence de livraison ne change pas ; ce qui change est la construction
*à l\'intérieur* de la tranche.

L\'artefact peut se situer à trois échelles.

**1. Une tâche ou une tranche.** Le code d\'une fonctionnalité déjà
choisie. C\'est l\'échelle native : l\'ordre inside-out y est courant et
raisonnable, les étapes de cartographie tiennent souvent en quelques
minutes, et le prix du retour tardif y est à peu près nul puisque la
tranche livre dès qu\'elle est finie.

**2. Un composant autonome.** Bibliothèque, service, moteur, algorithme.
L\'échelle de plein exercice : frontières contractuelles nettes,
consommateurs identifiés. Le retour technique est rapide, les
consommateurs testant contre les contrats dès le gel ; le retour
produit, lui, dépend du système englobant.

**3. Une application entière.** Possible, mais c\'est là que la garantie
non donnée de I.3 pèse le plus longtemps, puisqu\'aucun chemin de bout
en bout n\'existe pendant toute la construction des couches internes. À
cette échelle, le mode d\'emploi de référence devient le mode composite,
plutôt que l\'application pure du protocole.

Le coût du retour produit tardif croît donc avec l\'échelle, à peu près
nul au niveau 1, maximal au niveau 3. Toute lecture des exemples et des
stacks du document doit se faire avec ce gradient en tête. L\'échelle
reste une question distincte de celle du **domaine**, c\'est-à-dire des
types de problèmes qui se prêtent à MCL, traitée en I.9.

## I.6 Le protocole en huit étapes

  -------------------------------------------------------------------------
  Étape   Objet            Sortie attendue
  ------- ---------------- ------------------------------------------------
  **1**   Compréhension de Comportement externe attendu, entrées/sorties de
          la cible         l\'enveloppe, contraintes techniques, nature du
                           projet (greenfield ou refactoring). C\'est **le
                           seul moment de pensée outside-in** du protocole.

  **2**   Décomposition en En quatre temps : délimiter entrées et sorties
          unités           (2.1), modéliser le flux de résolution (2.2), en
          fonctionnelles   extraire les unités candidates (2.3), **les
                           ordonner par dépendance et non par position dans
                           le flux** (2.4). Les systèmes qui ne se laissent
                           pas décrire comme un flux relèvent de 2.5.

  **3**   Graphe de        Un DAG explicite. Feuilles = couche 0, racine =
          dépendances      couche N. Contrôle de divergence contre
                           l\'ordonnancement intuitionné en 2.4.
                           Dépendances externes identifiées à part ; cycles
                           détectés et traités.

  **4**   Assignation des  La carte des couches, avec ses groupes
          couches          parallèles, encodée dans l\'outillage de test
                           d\'architecture et versionnée avec le code.

  **5**   Contrats         Esquisse pour toutes les unités ; **finalisation
          d\'interface     par couche, juste avant de construire**, jamais
                           plus d\'un niveau d\'avance sur le premier
                           consommateur. Exception : les contrats des
                           frontières externes se finalisent tôt.

  **6**   Doublures des    Un contrat attendu et une doublure minimale par
          frontières       dépendance externe, utilisée dans toutes les
          externes         couches internes, remplacée par
                           l\'implémentation réelle dans la seule couche
                           d\'infrastructure.

  **7**   Build            Pour chaque couche de 0 à N : implémenter,
          incrémental avec tester, valider, intégrer, tester
          *regression      l\'intégration, **régresser sur la suite
          gate*            intégrale**, geler.

  **8**   Checkpoints de   Tous les deux ou trois niveaux, une pause en lot
          refactoring      : révisions d\'implémentation à contrat
                           constant, et instruction des changements de
                           contrat qui s\'anticipent au lieu de se subir.
  -------------------------------------------------------------------------

Le point de bascule de tout le protocole est en 2.4, et c\'est aussi la
source d\'erreur la plus fréquente. L\'ordre des couches suit l\'ordre
des dépendances, pas l\'ordre d\'exécution. Les deux ne coïncident pas
en général, et la question à poser unité par unité est toujours la même
:

> **« Cette unité pourrait-elle être construite et testée même si toutes
> les autres n\'existaient pas encore ? »**

Oui : c\'est une feuille, donc la couche 0 ou proche. Non, elle a besoin
de telle autre unité : sa couche se situe au-dessus de celles dont elle
dépend. Le flux sert à *voir* les unités et leurs liens ; l\'orientation
des dépendances se lit par-dessus le flux, elle ne s\'en déduit pas. Le
détail de ce raisonnement, avec ses deux illustrations et ses
heuristiques explicitement bornées, est en III.2.

> **Apport.** L\'ordonnancement par dépendance est un tri topologique,
> connu depuis 1962 et routinier dans les systèmes de build. Ce qui ne
> l\'était pas, c\'est sa formulation opératoire au moment exact où le
> développeur se trompe : une question posée unité par unité, des
> heuristiques dont les bornes sont écrites, et un contrôle de
> divergence qui rattrape l\'erreur avant qu\'une seule ligne ne soit
> écrite. Le protocole place l\'outil au point d\'usage.

## I.7 Les deux catégories de test et le *regression gate*

La boucle de l\'Étape 7 s\'exécute à l\'identique pour chaque couche.

  ------------------------------------------------------------------------
  N°   ETAPE               Sorties attendues
  ---- ------------------- -----------------------------------------------
  1    IMPLÉMENTER         Construire les unités de la couche

  2    TESTER              Tests unitaires de la couche (externe mocké,
                           dépendances internes réelles et figées par
                           défaut, mockées seulement en option justifiée)

  3    VALIDER             Tous verts ? → continuer. Échec → corriger
                           d\'abord.

  4    INTÉGRER            Brancher la couche sur le bloc réel {0 → k},
                           démocké

  5    TESTER              Tests de la jonction, sur le bloc réel
       L\'INTÉGRATION      

  6    RÉGRESSER           Relancer L\'INTÉGRALITÉ de la suite existante

  7    FIGER               Le contrat de la couche est gelé → couche
                           suivante
  ------------------------------------------------------------------------

Il existe **exactement deux catégories de tests**, pas un continuum de
combinaisons partielles. Ce qui les distingue est leur cible, non leur
outillage.

La **première** vise le contrat propre de la couche : entrées, sorties,
cas d\'erreur, de façon fine. Ses dépendances externes sont toujours
mockées. Pour ses dépendances internes, le régime par défaut est
d\'utiliser les couches réelles déjà gelées : construites, validées,
rapides puisque l\'externe est mocké, et gratuites en doublures.

La **seconde** vise la jonction : la couche `k+1` branchée sur
l\'ensemble réel `{0 → k}`, sans aucune doublure interne, puisque ces
couches existent et sont figées. Chaque test de cette catégorie traverse
donc toute la profondeur du bloc.

Ce que MCL ne fait pas, et c\'est ce qui la distingue d\'une lecture
naïve de son propre principe : elle ne teste pas successivement `{k+1}`,
puis `{k+1 + k}`, puis `{k+1 + k + k−1}` comme autant de sous-ensembles
isolés. Cette sur-isolation multiplierait les configurations et
testerait des sous-systèmes fictifs, puisqu\'il faudrait re-mocker une
couche interne pour recréer une frontière qui n\'existe pas dans le
système réel. Deux niveaux suffisent parce que `{0 → k}` forme un
système déjà intégré plutôt qu\'un empilement à recombiner : chaque
jonction y a été testée au moment de sa création, puis re-traversée par
chaque test d\'intégration ultérieur. La couverture des jonctions
s\'accumule au lieu d\'être un coup unique.

Le *gate* de l\'étape 6 est le point non négociable du protocole, et il
achète une propriété précise. Un échec constaté à cet endroit se produit
face à un **delta unique appliqué à une base entièrement verte**. Le
déclencheur est donc mécaniquement localisé : c\'est la couche qu\'on
vient d\'ajouter. Quand le défaut est dans cette couche, la cause
coïncide avec le déclencheur et la chasse au bug n\'a pas lieu. Quand il
s\'agit d\'un défaut latent d\'une couche plus basse, révélé par un
usage inédit, la cause est ailleurs : la chasse n\'est pas supprimée,
elle est **bornée par construction**. L\'aiguillage entre les deux cas
est lui-même mécanique (III.7).

## I.8 Les six axes de contribution de MCL

Ce que MCL apporte se répartit sur six axes. Ils sont déclarés une fois
ici, puis instanciés dans chacune des quatre parties, dans le registre
qui convient à chacune : ce qui compte pour un chercheur en génie
logiciel n\'est pas ce qui compte pour un formateur, alors même qu\'il
s\'agit du même mécanisme.

**A1 --- Le pont entre structure et processus.** Les architectures
concentriques répondent à la question « comment organiser le code ? » :
Clean Architecture et Onion Architecture prescrivent une direction de
dépendance, vers l\'intérieur, sans jamais prescrire d\'ordre de
construction. MCL relie explicitement les deux questions : si les
dépendances doivent pointer vers l\'intérieur, alors on construit de
l\'intérieur vers l\'extérieur, avec une validation à chaque étape. En
l\'état des recherches menées, c\'est le seul processus recensé qui
referme ce lien. La seule exception connue est tardive et partielle :
l\'évolution 2020-2024 d\'Hexagonal Architecture, absente de son texte
fondateur de 2005.

**A2 --- L\'intégration opérationnelle.** Sept éléments composent le
protocole : analyse du graphe de dépendances comme outil de
planification, contrats avant implémentation, ordre strict des feuilles
vers la racine, *regression gate* systématique, doublures confinées aux
frontières externes, checkpoints périodiques, le tout sous un protocole
nommé et reproductible. Leur propriété utile est de s\'alimenter
mutuellement. La carte des couches nourrit l\'enforcement au build, le
rayon des arbitrages de gouvernance et les groupes de parallélisation.
Le gel nourrit la localisation des défauts, la révision sous harnais et
l\'extension additive des contrats. Le *gate* nourrit l\'intégration
continue et le plan d\'adoption. Cette imbrication se vérifie sur pièce,
dans les renvois croisés du présent document.

**A3 --- L\'externalisation d\'un savoir tacite.** Les développeurs
expérimentés analysent les dépendances avant de coder et testent les
petites unités avant de les intégrer. Ils le font par réflexe, sans
l\'avoir formulé, donc sans pouvoir le transmettre autrement que par
compagnonnage long. MCL convertit ce réflexe en protocole nommé, ordonné
et vérifiable, qu\'un débutant peut apprendre sans disposer de dix ans
de pratique. C\'est la phase d\'Externalisation du modèle SECI, et
c\'est un type de contribution reconnu : le TDD lui-même a été décrit
par son auteur comme une redécouverte de pratiques tacites.

**A4 --- L\'invariant rendu exécutable.** La carte des couches sert de
plan de travail, et davantage : c\'est une déclaration exécutable.
Consignée dans la configuration d\'un outil de test d\'architecture et
versionnée avec le code, elle transforme l\'invariant en règle de build
: toute unité d\'une couche `k` qui référence une couche plus externe
fait échouer la compilation. Trois contrôles du protocole deviennent
alors automatiques : violation de l\'invariant, détection de cycles,
écart entre la carte déclarée et le graphe réel. MCL n\'invente pas ce
mécanisme, dont les outils disposent depuis les années 2010. Elle le
**prescrit**, là où les autres approches se contentent de le rendre
disponible, et surtout elle fournit ce que ces outils réclament en
entrée et qu\'aucune ne produit systématiquement : une carte des couches
justifiée par la dépendance.

**A5 --- L\'auto-instrumentation et la réfutabilité déclarée.** MCL
énonce huit hypothèses réfutables sur ses propres effets, dont deux lui
sont défavorables, et publie le protocole qui permettrait de la
démentir. Six de ces huit hypothèses se lisent dans des traces que le
protocole produit **par construction** : historique des défigeages,
journaux du *gate*, baseline, cartes encodées. L\'évaluation minimale
d\'une équipe adoptante ne coûte donc presque rien, et la méthode est
instrumentée avant même qu\'on décide de la mesurer.

**A6 --- La couverture étendue.** Trois situations font habituellement
décrocher les méthodes de construction par couches, et MCL les traite.
Les systèmes qui ne se laissent pas décrire comme un flux (machines à
états, domaines événementiels, grands domaines à frontières multiples)
relèvent d\'une cartographie adaptée, le critère de dépendance restant
inchangé. Les dépendances circulaires cessent d\'être bloquantes :
condensées en composante fortement connexe, elles occupent une seule
couche du DAG et se construisent de façon incrémentale en interne. Et à
l\'échelle d\'une application entière, le mode composite protocolise ce
que les approches voisines laissent informel : la boucle interne du
Double-Loop TDD reste une intention, ici elle a des couches, des
contrats, un gel et un *gate*.

## I.9 Le domaine d\'application

La question se pose au niveau de **l\'artefact**, jamais au niveau du
contexte produit qui l\'englobe. Un produit en pleine découverte, marché
incertain et exigences mouvantes, contient des artefacts parfaitement
décidés dont la structure est connaissable. Confondre les deux niveaux
conduirait à exclure MCL de la majorité du développement produit
moderne, et ce serait faux.

Trois questions, avant d\'appliquer la méthode à un artefact.

1.  **La structure est-elle connaissable avant construction ?** Des
    praticiens compétents peuvent-ils cartographier unités et
    dépendances avec confiance, parce que des systèmes analogues
    existent ou parce que la structure se lit dans l\'existant ?
2.  **Les contrats internes sont-ils stabilisables tôt ?** Si les
    interfaces ne peuvent être arrêtées qu\'après avoir vu le système
    tourner, le gel devient un générateur de défigeages en cascade.
3.  **Faut-il construire pour comprendre ?** Si la compréhension du
    problème n\'émerge qu\'en sondant (recherche algorithmique,
    exploration d\'un modèle d\'apprentissage, expérience utilisateur
    inédite), la carte serait une fiction.

Oui aux trois : l\'artefact est dans le domaine d\'application de la
méthode. Non à l\'une d\'elles : l\'artefact est exploratoire, et le
chemin devient alors sonder d\'abord, puis reconstruire au protocole une
fois la structure stabilisée. Deux exemples fixent le niveau du test :
la tranche « export CSV » d\'un produit en pleine découverte est
applicable, parce que l\'artefact décidé est banal et que c\'est le
produit qui sonde, pas lui ; un moteur d\'apprentissage dont
l\'architecture émerge des expériences est exclu, même si tout le reste
du système se construit au protocole.

À distinguer des exclusions, deux situations où la méthode s\'applique
mais rapporte moins : les systèmes dominés par leurs frontières
externes, où l\'avantage en doublures se dilue, et l\'échelle
application conduite sans mode composite, où le retour produit tardif se
paie plein pot. On s\'y engage en connaissance de cause.

Le classement se vérifie ensuite en construisant, ce qui évite d\'en
faire un jugement définitif pris à froid. Se croire à tort en terrain
connaissable se détecte à deux signaux : des divergences répétées entre
la carte déclarée et le graphe réel, et des défigeages en chaîne dès les
premières couches. Ces signaux ne disent pas « mauvaise exécution », ils
disent « mauvais domaine ». La réponse est alors de suspendre, sonder,
re-cartographier. Le test d\'applicabilité vaut comme hypothèse de
départ, que la construction met ensuite à l\'épreuve.

> **Apport.** Peu de méthodes de construction publient le domaine où
> elles sont contre-indiquées, et moins encore fournissent le moyen de
> vérifier le classement. MCL fait les deux : trois questions avant de
> s\'engager, deux signaux observables pendant la construction pour se
> corriger. Un praticien sait donc à l\'avance si son artefact relève de
> la méthode, et il l\'apprend tôt s\'il s\'est trompé. La délimitation
> vaut recommandation : ce qui tombe dans le périmètre y est traité de
> bout en bout.

# PARTIE II --- ASPECT SCIENTIFIQUE : GÉNIE LOGICIEL

## II.0 Cadrage

Cette partie s\'adresse au chercheur en génie logiciel, et
particulièrement à celui qui travaille en génie logiciel empirique. Elle
suppose la Partie I lue. Elle ne montre pas comment appliquer MCL, ce
qui est l\'objet de la Partie III ; elle expose ce que la méthode
revendique, avec quel statut de preuve, contre quel état de l\'art, et
par quel dispositif on pourrait la démentir.

L\'ordre de lecture y est délibéré. Le classement des revendications
vient avant l\'état de l\'art, parce qu\'un lecteur qui ne sait pas ce
qui est affirmé ne peut pas juger de ce qui est comparé. L\'analyse des
mécanismes vient avant le protocole d\'évaluation, parce que ce
protocole mesure précisément ce que ces mécanismes prédisent.

## II.1 MCL comme objet de recherche

### Le genre

MCL relève du **document de position et d\'expérience**. Une proposition
argumentée, issue d\'une pratique de terrain et d\'un travail de
formalisation, dont les bénéfices annoncés ont le statut d\'hypothèses
testables plutôt que de résultats établis. Cette qualification engage :
elle a pour contrepartie le protocole d\'évaluation de II.6, écrit pour
que les hypothèses puissent être infirmées autant que confirmées.

La genèse renforce ce classement plutôt qu\'elle ne l\'affaiblit.
Formalisation et application se sont nourries l\'une l\'autre, chaque
version absorbant ce qu\'un projet réel avait révélé. La configuration a
un nom en recherche empirique, et un coût : l\'auteur-inventeur qui
rapporte l\'application de sa propre méthode ne produit pas une
observation indépendante. Elle a aussi une vertu que les propositions
purement spéculatives n\'ont pas : aucune règle du protocole n\'a été
écrite avant d\'avoir été exercée.

### Trois familles de revendications, jamais mélangées

Une lecture rapide de MCL confondrait volontiers trois choses que le
document sépare partout.

Les **revendications documentaires** portent sur ce que la littérature
contient ou ne contient pas. « Clean Architecture et Onion Architecture
ne prescrivent aucun ordre de construction » en est une ; « aucune
méthodologie recensée ne combine les sept éléments du protocole » en est
une autre. Elles se vérifient par consultation des sources primaires, et
elles restent provisoires par nature : une absence constatée après
recherche n\'est pas une inexistence démontrée.

Les **revendications analytiques** portent sur le fonctionnement du
protocole lui-même. L\'asymétrie de coût entre driver et stub, la
localisation mécanique du déclencheur face à un delta unique, la
non-redondance des deux niveaux de test, la croissance quadratique du
coût cumulé de régression : ces énoncés se vérifient par raisonnement
sur la structure du protocole, sans mesure. Ils sont réfutables par
contre-argument, pas par expérimentation directe. Leur place dans un
article est celle d\'une analyse mécaniste, et la Partie II les traite
comme tels en II.5.

Les **revendications empiriques** portent sur des effets mesurés. MCL
n\'en formule aucune. Tout ce qui, dans une lecture pressée,
ressemblerait à un « la méthode réduit le temps de débogage » est
reformulé en hypothèse réfutable et renvoyé au protocole d\'évaluation.

Cette séparation a une conséquence pratique pour un relecteur de
conférence : chaque affirmation de ce document peut être contestée dans
son propre registre, sans que la contestation d\'une famille n\'entraîne
les deux autres.

### Le verdict d\'innovation, en quatre énoncés

Le statut d\'innovation de MCL a été instruit en posture adversariale
(II.7). Il se formule ainsi.

*Innovation radicale : non.* Chaque composante prise isolément a un
précédent documenté, certains remontant aux années 1970, d\'autres à
1986, 2005 ou 2009.

*Innovation de synthèse : oui, à formuler avec mesure.* Aucune
méthodologie nommée combinant les sept éléments n\'a été trouvée.
L\'espace conceptuel autour de cette combinaison est cependant plus
dense qu\'il n\'y paraît : Cleanroom (1987), GOOS (2009), RUP
(1999/2003) et Stratified Design (2021) couvrent chacun trois à quatre
des sept éléments.

*Innovation de pont : oui, avec une réserve historique précise.* Les
architectures concentriques prescrivent une direction de dépendance sans
prescrire d\'ordre de construction, ce que quatre recherches
indépendantes ont confirmé sur sources primaires. Hexagonal Architecture
fait exception, mais dans son évolution tardive de 2020-2024 seulement,
absente du texte fondateur de 2005.

*Innovation de formalisation du savoir tacite : oui, solidement
établie.* Le parallèle avec le TDD, que Kent Beck a lui-même décrit
comme une redécouverte, et l\'ancrage dans le modèle SECI de Nonaka et
Takeuchi (1995) placent ce type de contribution dans une tradition
reconnue en génie logiciel comme en gestion des connaissances.

## II.2 Les fondements formels mobilisés

MCL n\'a inventé aucun de ses rouages, et le document le déclare à
l\'endroit exact où chacun sert. Le tableau ci-dessous rassemble ces
ancrages ; le commentaire qui suit dit ce que la méthode en fait.

  -----------------------------------------------------------------------
  Mécanisme         Origine             Usage dans MCL
  ----------------- ------------------- ---------------------------------
  Tri topologique   Kahn, 1962 ;        L\'ordre de construction des
  d\'un graphe      systèmes de build   couches est un tri topologique du
  orienté           depuis les années   DAG des unités (Étapes 3 et 4)
                    1970                

  Critères de       Parnas, *CACM*      Documente le piège symétrique :
  décomposition     15(12), 1972        structurer un système d\'après
  modulaire                             les étapes de son traitement
                                        disperse les décisions de
                                        conception. C\'est l\'erreur que
                                        la question-test de l\'Étape 2.4
                                        intercepte

  Composantes       Tarjan              Un graphe cyclique se condense en
  fortement                             un DAG de composantes.
  connexes et                           L\'algorithme émet les
  condensation                          composantes en ordre topologique
                                        inverse, donc fournit l\'ordre de
                                        construction MCL sans calcul
                                        supplémentaire

  Ordre             Kung et al., 1995 ; Formalise l\'objectif du point de
  d\'intégration et Tai & Daniels, 1999 coupe dans une composante
  de test sous      ; Le Traon et al.,  cyclique : minimiser le nombre et
  cycles (CITO)     2000 ; Briand,      la richesse des doublures
                    Labiche & Wang,     
                    2002                

  Condensation +    Allen, Callahan &   Paradigme établi en compilation,
  ordre topologique Kennedy, 1989 ;     en build de modules et en
  pour le build     Jørgensen, 2001 ;   intégration continue, que le
  incrémental       Google, 2015        protocole reprend tel quel

  Design by         Meyer, 1986         Les contrats d\'interface rédigés
  Contract          (Eiffel)            avant toute implémentation (Étape
                                        5)

  Last / Most       Poppendieck, 2003 ; Cale le moment de finalisation
  Responsible       Reinertsen, 2009    des contrats : un niveau
  Moment                                d\'avance sur le premier
                                        consommateur, jamais plus

  Delta debugging   Zeller, 1999 ;      Fonde la localisation du
                    commandes `bisect`  déclencheur : un échec face à un
                    des gestionnaires   petit delta appliqué à une base
                    de versions         entièrement verte s\'isole
                                        mécaniquement

  Fonctions de      Ford, Parsons &     Donnent sa taxonomie à la carte
  fitness statiques Kua, 2017 ;         des couches encodée : une mesure,
  atomiques         ArchUnit, Deptrac   une évidence, une contrainte
                    et consorts         

  Architecture      Nygard, 2011        Forme des traces de défigeage
  Decision Records                      produites par la gouvernance
                                        (Étape 7)

  Loi de Conway ;   Conway, 1968 ;      Justifient l\'interdiction des
  Team Topologies   Skelton & Pais,     équipes organisées par couches et
                    2019                l\'alignement sur les flux

  Cadre Cynefin     Snowden & Boone,    Situe le domaine d\'application :
                    2007                les domaines clair et compliqué,
                                        où la relation cause-effet
                                        s\'analyse avant d\'agir

  Programmation     Graham, *On Lisp*,  Antécédent direct de la direction
  ascendante comme  1993                inside-out, retrouvé tardivement
  style de                              (voir II.7)
  conception                            
  -----------------------------------------------------------------------

Ce que MCL ajoute à chacun de ces mécanismes se situe au même endroit à
chaque fois : dans la formulation opératoire, au moment précis du
protocole où le praticien se trompe. Le tri topologique est connu depuis
1962 ; ce qui ne l\'est pas, c\'est la question-test qui distingue
l\'ordre de dépendance de l\'ordre du flux, les heuristiques
explicitement bornées qui l\'accompagnent, et le contrôle de divergence
qui confronte l\'ordonnancement intuitionné au graphe formalisé avant
qu\'une seule couche ne soit construite. Le *delta debugging* est publié
depuis 1999 ; ce que le *regression gate* apporte, c\'est de rendre sa
précondition --- petit delta, base verte --- permanente par construction
plutôt qu\'occasionnelle. Les outils de test d\'architecture existent
depuis les années 2010 ; ils réclament en entrée une carte des couches
que rien, dans les méthodes voisines, n\'oblige à produire ni ne
justifie par la dépendance.

## II.3 État de l\'art et analyse d\'écart

### Les précédents par composante

  --------------------------------------------------------------------------
  Composante                  Précédent                          Date
  --------------------------- ---------------------------------- -----------
  Construction ascendante     Bottom-up development, en          années 1970
                              opposition au top-down de Mills et 
                              Wirth                              

  Test des couches basses en  Bottom-up integration testing      1970-1980
  premier                                                        

  TDD démarrant par les       École Detroit / classiciste, Kent  années 1990
  petites unités              Beck, projet Chrysler C3           

  Contrats d\'interface avant Design by Contract, Meyer          1986
  le code                                                        

  Direction des dépendances   Clean Architecture, Martin         2012
  vers l\'intérieur                                              

  Couches concentriques       Onion Architecture, Palermo        2008
  centrées sur le domaine                                        

  Isolation de testabilité    Hexagonal Architecture, Cockburn   2005
  par ports et adaptateurs                                       

  Mock-first, walking         GOOS, Freeman & Pryce              2009
  skeleton                                                       

  Certification incrémentale, Cleanroom Software Engineering,    1987
  spécifications avant code   Mills, Dyer & Linger               

  Intégration progressive     RUP / Unified Process              1999-2003
  architecture-centrique                                         

  Couches spécifiques sur     Stratified Design, Normand         2021
  couches générales                                              

  Séquence squelette puis     Walking skeleton, tracer bullet,   1996-2009
  étoffement                  Double-Loop TDD                    
  --------------------------------------------------------------------------

### Les quatre méthodologies les plus proches

**Cleanroom Software Engineering (1987)** couvre la certification
incrémentale et les spécifications formelles avant codage. Son
intégration est explicitement descendante, soit l\'opposé exact de
l\'ordre MCL, et le concept de doublure y est absent.

**Growing Object-Oriented Software, Guided by Tests (2009)** couvre le
cycle rouge-vert-refactor avec ré-exécution complète, et la découverte
d\'interface pilotée par les doublures. La direction y est outside-in :
partir du squelette de bout en bout, puis affiner vers l\'intérieur.
C\'est l\'inverse de MCL, et c\'est aussi le concurrent le plus sérieux,
celui contre lequel la comparaison par axe est menée.

**RUP / Unified Process (1999-2003)** couvre l\'intégration progressive
architecture-centrique avec tests de régression par itération. Il ne
prescrit ni ordre inside-out, ni stratégie de doublure depuis
l\'intérieur.

**Stratified Design (2021)** est le plus proche en substance :
construire des couches spécifiques sur des couches plus générales, selon
les dépendances. Il reste une lentille de conception, sans protocole de
construction formalisé en étapes vérifiables.

Le motif est régulier. Chacune de ces quatre approches couvre trois à
quatre des sept éléments du protocole, et chacune décroche sur les deux
mêmes points : la direction de construction, et le confinement des
doublures aux frontières externes.

### La comparaison par axe avec le concurrent moderne

Une comparaison honnête exige deux conditions préalables, faute de quoi
elle ne mesure rien. **Échelle égale** : on compare sur le même type
d\'artefact. **Domaine égal** : on compare à l\'intérieur du domaine
d\'application de MCL (I.9). À l\'échelle de l\'application entière,
l\'objet pertinent cesse d\'être l\'opposition entre les deux colonnes
pour devenir le mode composite, qui les prend toutes les deux.

  ----------------------------------------------------------------------------
  Axe               MCL (artefact,        Outside-in +       Verdict
                    domaine cadré)        tranches           
                                          verticales (GOOS)  
  ----------------- --------------------- ------------------ -----------------
  Doublures de test Les drivers *sont*    Doublures internes **MCL**, avantage
  à écrire          les tests ; doublures tant que           qui se dilue avec
                    aux frontières        l\'intérieur       le nombre de
                    externes seulement    n\'existe pas      frontières
                                                             externes

  Localisation des  Immédiate : delta     Dépend de la       **MCL**
  régressions       unique sur base verte granularité du     
  locales                                 cycle              

  Défaut de contrat Bissection bornée ;   Détecté plus tôt : Égalité, léger
  amont             propagation nulle si  le chemin de bout  avantage au
                    le contrat est        en bout existe tôt concurrent
                    inchangé                                 

  Retour produit de Tardif par            Dès le squelette   **Concurrent**,
  bout en bout      construction                             résolu par le
                                                             composite à
                                                             l\'échelle
                                                             application

  Sur-ingénierie    Risque élevé          Faible : le besoin **Concurrent**
  interne           (contrats avant       externe pilote     
                    consommateurs), borné l\'intérieur       
                    par les checkpoints                      

  Pression de       Les tests vérifient   Les tests          **Concurrent**,
  conception        des contrats déjà     dessinent les      apport propre de
  exercée par les   conçus                interfaces         GOOS
  tests                                                      

  Robustesse de la  Tests sociables sur   Tests              **MCL**
  suite au          couches réelles :     d\'interaction     
  refactoring       survivent aux         couplés aux        
  interne           changements           collaborations :   
                    d\'implémentation     cassent au         
                                          refactoring        

  Artefacts         Contre-indiquée       Le squelette       **Concurrent**
  exploratoires                           explore            

  Domaine cadré ou  Protocole guidé de    Bon, moins guidé   **MCL**
  algorithmique     bout en bout                             

  Enseignabilité du Forte : étapes        GOOS est subtil à  **MCL**
  protocole         nommées, étiquettes   enseigner          
                    de sous-buts                             

  Enforcement de    Prescrit : carte      Outillage          Léger avantage
  l\'architecture   encodée               disponible, non    **MCL**, par
                                          prescrit           prescription
  ----------------------------------------------------------------------------

Deux mises en garde accompagnent ce tableau, et j\'insiste sur la
seconde parce qu\'elle est régulièrement ignorée. La première : compter
les lignes n\'a aucun sens, les axes n\'étant ni commensurables ni
équipondérés. Le poids du retour produit dépend du contexte produit ;
celui des doublures dépend du nombre de frontières externes. La seconde
: aucun de ces verdicts n\'est une mesure. Ce sont des analyses
mécanistes, au sens de II.1. Ce tableau dit au praticien ce qu\'il
achète et ce qu\'il paie ; il constitue surtout, pour le chercheur, la
grille exacte de ce qu\'un protocole d\'évaluation devrait mesurer.

Une lecture reste légitime, et elle porte sur la **nature** des axes
plutôt que sur leur nombre. Ceux que MCL emporte sont des propriétés
structurelles du protocole, acquises tant qu\'il est appliqué :
l\'économie de doublures découle de l\'ordre de construction, la
localisation découle du *gate*, la survie des suites au refactoring
découle du régime sociable. Ceux qu\'elle concède relèvent en majorité
du retour produit et de la conception pilotée par le consommateur réel,
c\'est-à-dire de ce que le mode composite réintroduit à l\'échelle où le
manque coûte quelque chose. La colonne concurrente garde un acquis
propre que le composite ne rapatrie pas : la pression de conception
exercée par les tests, apport spécifique de GOOS.

En situation d\'apprentissage, la ligne de base n\'est pas celle-ci mais
l\'intégration big bang, et la comparaison ci-dessus ne s\'y transpose
pas (Partie IV).

### La légitimité de la synthèse comme forme de contribution

Robert C. Martin décrit lui-même Clean Architecture comme une synthèse
explicite d\'Hexagonal Architecture, d\'Onion Architecture, de DCI et de
BCE. Jeffrey Palermo a reconnu publiquement avoir rassemblé des
techniques et des conventions existantes sous un nom nouveau. Deux des
architectures les plus respectées du génie logiciel moderne sont donc
nées de la démarche qui est ici la nôtre. La synthèse nommée n\'est pas
une contribution de second rang qu\'il faudrait excuser : c\'est une
forme de production de connaissance dont la discipline a l\'habitude, et
qu\'elle a validée par l\'usage.

## II.4 Les six contributions, caractérisées

Les axes déclarés en I.8 se reprennent ici avec leur statut de preuve et
ce qui les rend contestables.

**A1 --- Le pont entre structure et processus.** *Statut : revendication
documentaire forte.* Les quatre campagnes ont confirmé sur sources
primaires que Clean et Onion prescrivent une direction de dépendance
sans ordre de construction. En l\'état des recherches menées, MCL est le
seul processus recensé qui referme le lien : si les dépendances pointent
vers l\'intérieur, alors on construit de l\'intérieur vers l\'extérieur,
avec validation à chaque étape. *Réserve déclarée :* l\'évolution
2020-2024 d\'Hexagonal Architecture explicite une forme inside-out,
absente de 2005. *Ce qui la réfuterait :* l\'exhibition d\'un texte
antérieur reliant les deux questions.

**A2 --- L\'intégration opérationnelle.** *Statut : constat
documentaire, explicitement non probant.* Une conjonction de sept traits
est presque toujours inédite, et sept conditions suffisent à rendre à
peu près n\'importe quel assemblage « sans précédent ». Le document le
concède sans détour. L\'apport revendicable se déplace donc : les sept
éléments ne sont pas alignés côte à côte, ils se référencent et se
gouvernent ensemble. La carte des couches alimente l\'enforcement, le
rayon des arbitrages et les groupes de parallélisation. Le gel alimente
la localisation, la révision sous harnais, l\'extension additive. Le
*gate* alimente l\'intégration continue et le plan d\'adoption. Cette
imbrication se vérifie sur pièce, dans les renvois croisés du présent
document. *Ce qui reste ouvert :* la valeur de l\'intégration,
c\'est-à-dire la question de savoir si le paquet fait mieux que ses
éléments épars, est une hypothèse et non un acquis.

**A3 --- L\'externalisation d\'un savoir tacite.** *Statut : solidement
ancré.* Le modèle SECI (Nonaka & Takeuchi, 1995) nomme la phase
concernée. Le précédent le plus direct en génie logiciel est le TDD,
décrit par son propre auteur comme une redécouverte de pratiques
tacites, avec un antécédent documenté dans les programmes NASA Mercury
des années 1960. Un développeur confirmé analyse les dépendances avant
de coder et teste les petites unités avant de les intégrer ; il le fait
sans l\'avoir formulé, donc sans pouvoir le transmettre autrement que
par compagnonnage long. Convertir ce réflexe en protocole nommé, ordonné
et vérifiable produit un objet transmissible en semaines plutôt qu\'en
années.

**A4 --- L\'invariant rendu exécutable.** *Statut : analyse mécaniste,
plus une prescription.* Dans la taxonomie de l\'architecture évolutive,
la carte des couches encodée est une fonction de fitness statique et
atomique : une mesure (les références entre couches), une évidence (une
dépendance interdite), une contrainte (l\'invariant). L\'outillage est
commun à tout le monde et MCL ne l\'invente pas. Deux choses lui
appartiennent : la prescription, là où les approches voisines se
contentent de rendre le mécanisme disponible ; et l\'entrée que le
mécanisme réclame, à savoir une carte des couches justifiée par la
dépendance, que rien d\'autre n\'oblige à produire. La règle exacte à
encoder est celle de la méthode : dépendances autorisées vers n\'importe
quelle couche plus interne, à profondeur quelconque, et non la variante
« couche adjacente seulement » que certains outils proposent par défaut.

**A5 --- L\'auto-instrumentation et la réfutabilité déclarée.** *Statut
: trait de conception observable.* Huit hypothèses réfutables, dont deux
défavorables à la méthode, accompagnées de leurs conditions de
réfutation. Six d\'entre elles se lisent dans des traces que le
protocole produit par construction. Le niveau minimal d\'évaluation,
celui de l\'auto-mesure longitudinale, coûte donc presque rien à une
équipe adoptante, ce qui déplace le goulot d\'étranglement habituel de
la recherche empirique en génie logiciel : non plus l\'instrumentation,
mais le design et l\'interprétation. C\'est, à mon sens, la contribution
la moins visible du corpus et l\'une des plus utiles.

**A6 --- La couverture étendue.** *Statut : extension ancrée, plus un
dispositif non validé.* Les systèmes non-flux et les cycles sont traités
par des mécanismes établis (condensation, CITO), mis au service du
protocole. Le mode composite, lui, protocolise ce que la boucle interne
du Double-Loop TDD laisse informel. Sa séquence n\'est pas neuve : phase
Élaboration puis Construction du RUP, *walking skeleton* de Cockburn
(1996-2000), *tracer bullet* de Hunt et Thomas (1999), adage « design
outside-in, write inside-out ». L\'apport propre est le remplissage
réglé. *Ce qui reste ouvert :* l\'efficacité de ce composite précis n\'a
aucune validation contrôlée.

## II.5 Les mécanismes, énoncés en termes analysables

Quatre arguments portent l\'essentiel du raisonnement. Ils sont
contestables par contre-argument, et je donne pour chacun son domaine de
validité, parce qu\'un argument dont on ne connaît pas les bornes ne
vaut rien.

### L\'asymétrie des doublures

L\'invariant qui rend possible toute construction incrémentale est de
pouvoir tester X sans que Y existe. Avec une doublure pour chaque
dépendance manquante, **n\'importe quel** ordre de construction
satisfait techniquement cet invariant. L\'ordre de dépendance n\'est
donc pas le seul possible, et il faut dire précisément d\'où vient sa
supériorité.

En ordre inside-out, la doublure nécessaire pour exercer une couche est
un *driver*, un harnais qui l\'appelle. Or ce harnais est le test
unitaire lui-même : on l\'écrit de toute façon, son coût est déjà
absorbé. Les seuls artefacts supplémentaires sont les doublures des
dépendances **externes**, dont le nombre ne dépend pas de la profondeur
du graphe interne mais du nombre de frontières externes du système.

En ordre inverse, la doublure nécessaire est un *stub*, qui doit
reproduire le comportement d\'un module interne pas encore construit.
Leur nombre croît avec la largeur de l\'arbre, et leur fidélité
constitue un risque en soi : un stub trop simplifié masque des défauts
qui ne surgiront que tard.

*Domaine de validité.* Les doublures externes sont payées quel que soit
l\'ordre de construction ; l\'avantage propre de l\'ordre de dépendance
porte sur le poste des stubs internes, entièrement évité sur un graphe
acyclique. À l\'intérieur d\'une composante cyclique condensée, des
doublures internes temporaires peuvent réapparaître. Le delta ne
s\'inverse jamais, l\'inside-out ne coûtant jamais plus en doublures que
l\'ordre inverse, mais son poids relatif se dilue à mesure que les
frontières externes se multiplient : dans un système à logique interne
dominante, l\'asymétrie joue à plein ; dans un service distribué fait
surtout de frontières, les doublures externes dominent le budget et
l\'avantage différentiel devient marginal. L\'asymétrie porte enfin sur
les doublures seules : les tests d\'intégration par couche et la
régression sont un coût payé dans les deux ordres, que l\'argument du
driver déjà écrit ne couvre pas.

MCL ne supprime donc pas les doublures. Elle fait coïncider la doublure
nécessaire avec un harnais déjà écrit, et ramène les doublures restantes
aux seules frontières externes.

> **Apport.** L\'énoncé complet de cette asymétrie, avec son domaine de
> validité et son point de dilution, constitue en soi une contribution
> méthodologique. La littérature praticienne affirme volontiers qu\'une
> direction de construction « réduit les mocks », sans dire de combien,
> sous quelles conditions, ni à partir de quand l\'avantage s\'évanouit.
> Ici le poste concerné est nommé, sa borne est écrite, et l\'hypothèse
> 3 du protocole d\'évaluation en fait une quantité mesurable.

### La localisation face à un delta unique

Un échec au *gate* survient dans une configuration précise : un delta
unique appliqué à une base entièrement verte. Le déclencheur est alors
mécaniquement localisé, puisque le seul changement depuis le dernier
état vert est la couche qu\'on vient d\'ajouter.

Deux cas se distinguent, et l\'aiguillage entre eux est automatique.
Pour une **régression locale**, la cause coïncide avec le déclencheur :
localisation immédiate, sans recherche. Pour un **défaut amont**,
c\'est-à-dire un défaut latent d\'une couche gelée révélé par un usage
inédit, la cause se situe plus bas : la recherche n\'est pas supprimée,
elle est bornée par construction. Le signal d\'aiguillage est le test
unitaire de la couche courante. S\'il échoue, régression locale. S\'il
passe alors que la régression échoue, la cause est dans l\'interaction
ou plus bas, et le diagnostic par remontée de couches s\'ouvre, soit
séquentiellement (jusqu\'à N sondes), soit par dichotomie (de l\'ordre
de log N).

La limite épistémique du gel est celle du test lui-même : il montre la
présence de défauts, jamais leur absence. Une couche gelée est validée
par sa suite, non prouvée correcte. C\'est pourquoi les défauts amont
existent, et pourquoi leur coût de correction figure dans les hypothèses
réfutables plutôt que dans une note de bas de page.

### L\'économie du test à deux niveaux

MCL définit deux catégories de tests par leur **cible** : le contrat
propre de la couche, et la jonction avec le bloc réel. Elle refuse la
sur-isolation, c\'est-à-dire le découpage du système en tranches
testables par réintroduction de doublures sur des frontières internes.
Deux raisons, l\'une quantitative, l\'autre plus intéressante.

La raison quantitative : tester `{k+1}`, puis `{k+1 + k}`, puis
`{k+1 + k + k−1}` produirait `k` configurations à la couche `k`, soit
une croissance quadratique du nombre total de configurations sur
l\'ensemble de la construction.

La raison structurelle : isoler `{k+1 + k + k−1}` du reste exigerait de
re-mocker la couche `k−2`, donc de recréer une frontière qui n\'existe
pas dans le système réel. Ces tranches valideraient des sous-systèmes
fictifs.

L\'argument de non-redondance est auto-porté, et c\'est ce qui le rend
solide : le protocole garantit lui-même ses deux préconditions. Les
couches inférieures sont gelées, donc leur contrat ne bouge pas et rien
ne change sans re-passer l\'intégralité de la suite. La régression
intégrale est ré-exécutée à chaque couche. Sous ces deux conditions,
chaque jonction interne a été testée au moment de sa création, puis
re-traversée par chaque test d\'intégration ultérieur : la couverture
des jonctions s\'accumule au fil de la construction au lieu d\'être un
coup unique.

Définir les deux catégories par leur cible plutôt que par leur outillage
a un effet secondaire commode. Les définitions de « test unitaire » et
de « test d\'intégration » divergent notoirement dans la littérature
praticienne ; MCL n\'a pas besoin de trancher ce débat pour être
opérationnelle.

### Les coûts déclarés

Trois coûts sont annoncés par la méthode elle-même, chiffrés ou bornés
quand c\'est possible.

*Le coût cumulé de la régression.* Relancer à la couche `k` tout ce qui
a été écrit jusque-là produit, si la suite croît avec les couches, un
volume cumulé d\'exécutions de l\'ordre de N²/2 lancements pour N
couches. Le *gate* coûte donc de plus en plus cher à mesure qu\'on
monte. Deux familles d\'outils réduisent le volume en boucle interne, la
sélection par analyse d\'impact et la sélection prédictive, sous une
règle constitutive : la sélection accélère la boucle interne, elle ne
remplace jamais le *gate*. Gel de couche et fusion sur le tronc exigent
la suite intégrale, sans négociation, puisque la base entièrement verte
est la prémisse de toutes les garanties précédentes.

*La sérialisation.* Entre couches dépendantes, le protocole sérialise
structurellement : le gel de `k` précède la construction de `k+1`. Le
gain parallèle est donc borné par cette fraction sérialisée, au sens de
la loi d\'Amdahl, et la forme du graphe décide. Un graphe large
parallélise ; un graphe étroit et profond est un travail pour peu de
mains.

*Le retour produit tardif.* Il est tardif par construction de l\'ordre
inside-out, et le coût croît avec l\'échelle de l\'artefact. Le mode
composite est la réponse à ce coût à l\'échelle application, sans quoi
il se paie plein tarif.

Une méthode qui déclare ses coûts avec cette précision se rend
vérifiable sur ses coûts. Les hypothèses 6 et 8 de II.6 sont exactement
cela : la mise à l\'épreuve de deux prédictions défavorables.

## II.6 Réfutabilité : hypothèses, mesures, designs

### L\'objectif

Formulé selon le gabarit Goal-Question-Metric de Basili : analyser MCL
pour caractériser son efficacité **comparée** sur la localisation des
défauts, le coût des doublures, le retour et la stabilité, du point de
vue de l\'équipe, dans le domaine d\'application défini en I.9, contre
la ligne de base opérationnalisée de II.3.

### Les huit hypothèses réfutables

1.  **Localisation locale.** Le temps de localisation des régressions
    locales est borné par la couche, le delta étant unique. *Réfutée si*
    le temps médian de localisation égale ou dépasse la ligne de base, à
    tâches appariées.
2.  **Défauts amont.** La remontée exige de l\'ordre de log N sondes, et
    la propagation de la correction est nulle si le contrat reste
    inchangé. *Réfutée si* les sondes excèdent nettement log N, ou si
    les cascades sont fréquentes à contrat inchangé.
3.  **Doublures.** Volume et effort de maintenance inférieurs à la ligne
    de base, l\'écart décroissant avec la part de frontières externes.
4.  **Robustesse au refactoring.** Moins de tests cassés par lot de
    révision interne que la ligne de base mockiste, les suites étant
    sociables.
5.  **Contrats.** Les extensions additives dominent largement les
    modifications, et la généricité jamais consommée est rare. Les deux
    se lisent dans l\'historique des défigeages.
6.  ***(Défavorable)*** **Retour.** Le premier retour de bout en bout
    est plus tardif hors mode composite, et comparable sous composite.
    *La méthode aurait tort de s\'accuser si l\'écart hors composite
    n\'apparaissait pas.*
7.  **Composite.** Stabilité au moins égale à celle de chaque approche
    seule, à retour comparable. Exige un design de niveau 2 ou 3.
8.  ***(Défavorable)*** **Régression.** Le coût cumulé du *gate* suit la
    croissance quadratique déclarée. La courbe se lit dans les journaux
    ; si elle dément la déclaration, c\'est la déclaration qu\'il faut
    corriger.

### Les mesures

Pour la localisation : temps moyen de localisation, précision Top-N,
localisation spectrale en intégration continue par recoupement entre
commits de correction et anomalies. Pour les doublures : Test Double
Ratio, Useless Stub Ratio, effort de maintenance estimé par analyse
statique, modes stricts des frameworks et historique. Pour le retour et
la stabilité : délai de bout en bout et métriques DORA issues de la
télémétrie d\'intégration continue, employées pour piloter et jamais
pour comparer des équipes entre elles.

Trois disciplines de lecture s\'imposent. Médianes et percentiles plutôt
que moyennes. Définitions opérationnelles documentées avant collecte.
Lectures croisées, enfin : un pipeline plus rapide accompagné d\'un taux
de doublures inutiles qui monte signale un sous-test, pas un progrès.

### L\'auto-instrumentation

Six des huit hypothèses se lisent dans des traces que le protocole
produit sans instrumentation ajoutée : historique des défigeages,
journaux du *gate*, baseline de dette, cartes de couches versionnées.
Toute équipe qui applique MCL dispose donc du matériau du niveau 1 sans
effort supplémentaire, ce qui change la nature de l\'obstacle habituel
en recherche empirique de terrain.

> **Apport.** Le goulot d\'étranglement de la recherche empirique en
> génie logiciel tient rarement au manque d\'idées d\'étude. Il tient à
> l\'accès aux données de terrain et au coût d\'instrumentation d\'une
> équipe en production. MCL le déplace. Une équipe qui applique le
> protocole produit déjà l\'historique de ses défigeages, les journaux
> de son *gate* et ses cartes versionnées, parce que le protocole ne
> fonctionne pas sans eux. Le niveau 1 devient accessible à toute équipe
> adoptante, sans négociation d\'accès ni outillage ajouté.

### Trois niveaux de design

**N1, auto-mesure.** Accessible à toute équipe adoptante. Baseline de
deux à quatre semaines, puis lecture longitudinale des traces.
Préliminaire, sans groupe de contrôle.

**N2, quasi-expérience intra-équipe.** Plan croisé AB/BA sur tâches
appariées, le croisement contrôlant l\'ordre et l\'apprentissage, aux
conditions d\'égalité de II.3 : même échelle, même domaine.

**N3, multi-projets.** Au moins deux projets, ligne de base
opérationnalisée, designs de déploiement progressif en organisation.

### Menaces à la validité

Ordre et apprentissage, contrôlés par le croisement AB/BA. Hétérogénéité
d\'expertise : l\'effet d\'expertise inversée (Partie IV) prédit un
effet **hétérogène**, ce qui impose de stratifier novices et confirmés
au lieu de moyenner, sous peine de produire une moyenne qui ne décrit
personne. Validité de construit : aucune métrique unique, aucun proxy
non documenté. Validité externe : aucune généralisation hors du domaine
d\'application. Petits effectifs : transparence sur les nombres, pas de
sur-interprétation.

Le versant pédagogique appelle des mesures dédiées, qualité des cartes
produites en autonomie et charge perçue, qui relèvent d\'une extension
de ce protocole (IV.9).

### L\'engagement

Les résultats se publient positifs et négatifs. Le protocole lui-même
est une première version, destinée à s\'améliorer par son propre usage.

## II.7 La discipline épistémique intégrée

Le statut d\'innovation de MCL a été instruit par quatre campagnes de
recherche documentaire successives, chacune lancée avec instruction
explicite de poser une posture **adversariale** : chercher à réfuter les
affirmations d\'originalité plutôt qu\'à les confirmer. Treize
affirmations factuelles ont été soumises à ce traitement, couvrant les
précédents historiques, la nature de l\'innovation et la dimension
pédagogique. Les corpus consultés : Google Scholar, indexation ACM
Digital Library, indexation IEEE Xplore, arXiv, Semantic Scholar,
sources praticiennes, et vérification directe des sources primaires pour
les revendications architecturales (Martin, Palermo, Cockburn, Meyer,
Beck).

La portée de cette vérification demande d\'être énoncée sans
complaisance. Quatre exécutions du même type d\'instrument sur des
corpus largement partagés constituent une **réplication corrélée**, non
quatre preuves indépendantes. Leur convergence protège contre l\'échec
ponctuel d\'une recherche, une requête mal posée ou une base
indisponible. Elle ne protège pas contre les angles morts partagés par
l\'instrument et les corpus.

Ce risque a été constaté, et le constat figure ici plutôt que d\'avoir
été effacé. La tradition de programmation ascendante du monde Lisp,
documentée par Paul Graham dans *On Lisp* (1993), est un antécédent
direct de la direction inside-out. Elle était absente des quatre
rapports. Elle n\'a été retrouvée que par une analyse ultérieure, et
elle figure désormais dans les précédents recensés en II.3.

La conséquence est méthodologique. La confiance de ce document ne repose
pas sur le nombre de recherches convergentes, mais sur le fait que
chaque verdict cite ses sources nommées, contrôlables une à une. Un
lecteur qui doute d\'une affirmation n\'a pas à évaluer un dispositif de
recherche : il ouvre la source.

Le principe de prudence s\'applique partout. L\'absence de preuve n\'est
pas la preuve de l\'absence. Le résultat le mieux étayé de cette
instruction, « aucun contre-exemple trouvé après recherche adversariale
», reste par nature une conclusion provisoire : une méthodologie obscure
combinant les sept éléments pourrait exister sans avoir été indexée dans
les sources consultées.

Je note que peu de propositions méthodologiques en génie logiciel
publient la tentative de réfutation de leurs propres revendications, ni
l\'inventaire des angles morts de cette tentative. La pratique me paraît
transférable indépendamment de MCL, et je la recommanderais à quiconque
propose une méthode nommée.

## II.8 Les frontières du résultat

Cinq frontières délimitent ce que MCL peut revendiquer. Elles sont
ordonnées par sévérité, de ce qui exclut à ce qui reste à prouver, et
chacune est accompagnée de ce que le protocole fait à son sujet.

L\'existence même de cette section demande d\'être lue correctement. Une
méthode qui délimite son domaine de non-applicabilité, chiffre ses coûts
et publie les conditions de sa propre réfutation se rend attaquable sur
des points précis plutôt que sur son principe. C\'est le régime de
discussion qu\'on souhaite pour un objet destiné à durer.

**Les artefacts exploratoires sont hors domaine.** C\'est la seule
frontière de cette liste qui exclut au lieu de conditionner. Pour un
artefact dont la structure n\'est pas connaissable avant construction,
dont les contrats ne sont pas stabilisables tôt, ou dont la
compréhension exige de construire pour comprendre, les étapes de
cartographie produisent une carte fictive dont le coût se paie en
défigeages en chaîne. La méthode y est contre-indiquée, non « moins
efficace ». L\'espèce la plus fréquente est l\'incertitude structurelle
d\'expérience utilisateur : quand l\'inconnue principale porte sur ce
que doit être l\'interaction plutôt que sur la logique, l\'approche
outside-in est première. La sortie est constructive : sonder,
stabiliser, reconstruire au protocole.

**La décomposition exige du jugement.** L\'Étape 2 fournit un chemin
guidé, des frontières au workflow puis aux unités et aux dépendances.
Modéliser correctement un système complexe conserve une part
irréductible de jugement. MCL déplace la difficulté de « identifier des
unités dans le vide » vers « cartographier le système », plus guidée,
sans l\'éliminer. Ce jugement n\'est cependant pas laissé sans filet :
l\'invariant fournit un critère de validation *a posteriori* mécanique,
et toute unité de couche `k` qui référence une couche supérieure signale
une décomposition erronée. On ne peut pas garantir d\'avance une bonne
décomposition ; on peut détecter mécaniquement une mauvaise, ce qui
réduit le vide à sa part incompressible.

**Le contrat spéculatif est un risque structurel.** Construire une
couche avant ses consommateurs réels invite à généraliser tant qu\'à
figer, et la forme dangereuse n\'est pas le code mort, supprimable, mais
la généricité fictive gelée que des consommateurs épousent ensuite.
Trois remparts sont opposés à ce risque : finalisation des contrats au
moment responsable, discipline du besoin cartographié, extension
additive comme chemin prévu de la sous-construction. Le checkpoint reste
la détection résiduelle. Le risque demeure structurellement plus élevé
que dans une approche pilotée par le consommateur réel, la carte étant
un substitut des consommateurs et non leur présence. La comparaison par
axe le dit sans détour.

**Les dépendances circulaires sont atténuées, pas gratuites.** Un cycle
se brise par une abstraction ou se condense en composante occupant une
seule couche du DAG. À l\'intérieur d\'une composante condensée,
l\'asymétrie des doublures se dégrade localement, par co-construction
bornée ou doublures internes temporaires. Le coût de la condensation
n\'est pas nul, ce qui renforce la préférence pour la résolution
architecturale quand elle est accessible.

**Aucune supériorité empirique généralisée n\'est démontrée.** MCL ne
doit pas être présentée comme produisant statistiquement de meilleurs
résultats qu\'une autre approche : l\'évidence disponible ne le permet
pas. Le chemin pour produire cette évidence, dans les deux sens, est
spécifié en II.6.

À distinguer de ces frontières, deux conditions de bénéfice dégradé où
la méthode s\'applique mais rapporte moins : les systèmes à frontières
externes dominantes, et l\'échelle application conduite sans mode
composite.

## II.9 Agenda de recherche

Six questions restent ouvertes, et la première est la plus importante.

*La valeur de l\'intégration.* Le paquet fait-il mieux que ses éléments
épars ? Une équipe qui appliquerait séparément l\'ordre de dépendance,
les contrats préalables et le *gate*, sans le protocole qui les relie,
obtiendrait-elle les mêmes résultats ? Un design de niveau 2 avec bras
partiels y répondrait.

*L\'efficacité propre du composite.* La séquence squelette puis chair a
des preuves qualitatives convergentes ; ce composite précis, avec chair
réglée au protocole, n\'a aucune validation contrôlée.

*Le seuil de dilution.* À partir de quelle proportion de frontières
externes l\'avantage en doublures devient-il négligeable ? La question a
une réponse chiffrable, et la réponse conditionne le conseil qu\'on
donne à une équipe.

*La forme réelle de la courbe de coût.* La croissance quadratique
déclarée est un raisonnement, pas une mesure. Sous sélection de tests en
boucle interne, la courbe observée peut s\'écarter sensiblement de la
prédiction.

*Le transfert hors du domaine cadré.* La contre-indication aux artefacts
exploratoires est argumentée, pas mesurée. Un design comparant
l\'application de MCL à un artefact classé exploratoire, contre
l\'approche recommandée, serait informatif y compris s\'il donnait tort
à la contre-indication.

*Le versant éducatif*, dont les constructs et les mesures sont traités
en IV.9.

## II.10 Renvois croisés

Vers **III.2 à III.8** pour l\'opérationnalisation exacte des mécanismes
analysés en II.5 : un design de niveau 2 exige de savoir ce que
l\'équipe fait réellement, geste par geste.

Vers **III.9** pour les traces de gouvernance, qui constituent la
matière première de six des huit hypothèses.

Vers **IV.2 et IV.3** pour ce que l\'évidence en éducation soutient et
ne soutient pas, dont l\'affirmation A13 réfutée : la seule des treize à
avoir été démentie par les campagnes de vérification, et la Partie IV
explique pourquoi c\'est sans conséquence sur l\'argument pédagogique
réel.

Vers **IV.9** pour l\'extension pédagogique du protocole d\'évaluation.

Vers **VI.3** pour les questions ouvertes que les quatre postures
partagent.

# PARTIE III --- ASPECT PROFESSIONNEL : GÉNIE LOGICIEL

## III.0 Cadrage

Cette partie est écrite pour être exécutée. Développeur, *tech lead*,
architecte : à la fin de sa lecture, vous devez pouvoir prendre un
artefact réel, le cartographier, le construire couche par couche, et
savoir quoi faire quand un test casse. Elle suppose la Partie I lue, en
particulier le vocabulaire de I.4 et l\'invariant de I.3.

Elle ne discute pas les fondements. Quand une règle vous paraîtra
arbitraire, un renvoi vous conduira à l\'argument correspondant en
Partie II, et vous pourrez décider en connaissance de cause. En
attendant, elle se lit comme un mode d\'emploi.

## III.1 Choisir l\'artefact, puis vérifier qu\'il s\'y prête

### La première décision est une décision de périmètre

Avant tout, désignez l\'**artefact** : l\'unité de travail sur laquelle
le protocole va s\'appliquer. Une tâche, une tranche fonctionnelle, un
composant, une application. Ce choix précède tout le reste, et il
n\'appartient pas à MCL. Le backlog, la roadmap et le découpage produit
décident *quoi* construire et *dans quel ordre le livrer* ; la méthode
décide seulement *comment construire le code* de ce qui a été choisi.

Le geste a une conséquence directe sur la lourdeur du protocole.

Sur une **tâche ou une tranche**, les étapes de cartographie tiennent en
quelques minutes, souvent sur un tableau blanc ou dans un fichier texte
de vingt lignes. Le protocole s\'y exécute en version proportionnée.
Aucun outillage particulier n\'est requis pour commencer.

Sur un **composant autonome** (bibliothèque, service, moteur de calcul),
le protocole s\'exerce pleinement. Frontières contractuelles nettes,
consommateurs identifiables, contrats qui méritent d\'être écrits avec
soin puisque d\'autres équipes coderont contre eux.

Sur une **application entière**, appliquez le mode composite (III.13).
C\'est le mode d\'emploi de référence à cette échelle, pas une variante.
L\'application pure du protocole reste licite quand un retour produit
précoce n\'a aucune valeur, par exemple une réécriture à comportement
constant ou un projet à spécification figée contractuellement.

### Le test en trois questions

La question se pose **au niveau de l\'artefact**, jamais au niveau du
produit qui l\'englobe. Une startup en pleine découverte de son marché
contient des artefacts parfaitement décidés. Ne vous privez pas de la
méthode sous prétexte que l\'entreprise, elle, cherche encore.

1.  **La structure est-elle connaissable avant construction ?** Des gens
    compétents peuvent-ils cartographier unités et dépendances avec
    confiance, parce que des systèmes analogues existent ou parce que la
    structure se lit dans le code existant ?
2.  **Les contrats internes sont-ils stabilisables tôt ?** Si vous savez
    déjà que les interfaces ne pourront être arrêtées qu\'après avoir vu
    le système tourner, le gel deviendra une machine à produire des
    défigeages en cascade.
3.  **Faut-il construire pour comprendre ?** Recherche algorithmique,
    exploration d\'un modèle d\'apprentissage, sensation de jeu,
    interaction inédite : si la compréhension du problème n\'émerge
    qu\'en sondant, votre carte serait une fiction.

Trois oui : appliquez le protocole. Un non : l\'artefact est
exploratoire. Sondez d\'abord (spike, prototype, tranche-sonde), puis
reconstruisez au protocole une fois la structure stabilisée. Le
prototype se jette, la reconstruction est le travail réel.

Deux exemples calibrent le test. La tranche « export CSV » d\'un produit
en pleine découverte est **applicable** : l\'artefact décidé est banal,
c\'est le produit qui sonde et non lui. Un moteur d\'apprentissage dont
l\'architecture émerge des expériences est **exclu**, quand bien même
tout le reste du système se construit au protocole.

> **Condition.** Deux situations où la méthode s\'applique mais rapporte
> moins. Un système dominé par ses frontières externes, où l\'économie
> de doublures se dilue (II.5). Une application entière conduite sans
> mode composite, où le retour produit tardif se paie au prix fort. On
> peut s\'y engager ; il faut le faire en le sachant.

### Le classement se vérifie en construisant

Vous croire en terrain connaissable à tort se détecte à deux signaux, et
tous les deux apparaissent tôt. Des divergences répétées entre la carte
que vous avez déclarée et le graphe que l\'outillage calcule. Des
défigeages en chaîne dès les premières couches. Ces signaux disent «
mauvais domaine » plutôt que « mauvaise exécution ». La réponse est de
suspendre, sonder, re-cartographier, sans y voir un échec de discipline.

## III.2 Cartographier : les étapes 1 à 4

C\'est la phase où se joue la qualité de tout le reste. Une carte fausse
produit un protocole parfaitement exécuté sur une structure erronée, et
le protocole ne rattrape pas ça --- il le détecte, ce qui est déjà
beaucoup, mais après coup.

### Étape 1 --- Comprendre la cible

Avant toute construction, regardez le système depuis l\'extérieur.
Quatre questions suffisent.

Que doit faire le système à son niveau le plus haut ? Quelles sont les
entrées et sorties attendues de l\'enveloppe finale ? Quelles
contraintes s\'imposent, en langage, framework, performance,
environnement de déploiement ? S\'agit-il d\'un projet neuf ou d\'un
refactoring de code existant ?

> **En pratique.** C\'est le seul moment de réflexion outside-in de tout
> le protocole. Il est indispensable : sans lui, vous risquez de bâtir
> des fondations qui ne correspondent pas aux besoins réels du système
> final. Ne le prolongez pas non plus au-delà de ces quatre réponses ;
> la conception détaillée des couches internes viendra de l\'analyse de
> dépendance, pas de l\'intuition descendante.

### Étape 2 --- Décomposer en unités fonctionnelles

Quatre temps, appliqués au problème entier, puis récursivement à chaque
module et à chaque unité non triviale.

**2.1 --- Identifier les entrées et les sorties.** Délimitez le cadre
traité, qu\'il s\'agisse du problème entier, d\'un module ou d\'une
unité. Quelles sont les entrées ? Elles déterminent les objets qui
doivent recevoir et représenter les données fournies. Quelles sont les
sorties ? Elles déterminent les objets qui produisent et représentent
les résultats. Ces frontières fixent le contrat externe du cadre avant
toute exploration de son intérieur.

**2.2 --- Élaborer le workflow de résolution.** Modélisez, avec le
maximum de détail dont vous êtes capable, le flux qui mène des entrées
aux sorties. Représentez-le explicitement, comme une suite d\'étapes ou
un graphe de flux. Le bénéfice est double, et le second est celui qu\'on
néglige : le flux rend visibles les étapes de résolution, et il fait
**émerger les variables et objets intermédiaires**, ceux qui ne sont ni
des entrées ni des sorties mais qui sont nécessaires au passage des unes
aux autres. Ces intermédiaires sont souvent des unités fonctionnelles à
part entière, qu\'on aurait manquées sans modéliser le flux.

**2.3 --- Extraire les unités du flux.** Chaque étape du flux et chaque
objet intermédiaire qu\'il révèle devient un candidat-unité. Une unité
fonctionnelle valide se reconnaît à trois traits : une responsabilité
unique énonçable en une phrase, une spécification entrée →
transformation → sortie (ou changement d\'état), et au moins une
relation de dépendance avec une autre unité. Produisez une liste à plat.
À ce stade, privilégiez l\'exhaustivité sur la précision.

**2.4 --- Ordonner par dépendance, non par position dans le flux.**
Voici le point de bascule, et la source d\'erreur la plus fréquente de
toute la méthode.

Le flux de résolution montre dans quel ordre les étapes s\'exécutent. Il
ne dit pas quelle unité dépend de quelle autre. Or c\'est la dépendance,
et elle seule, qui détermine la profondeur d\'une couche. Pour chaque
candidat-unité, posez la question de dépendance et non la question de
position :

> **« Cette unité pourrait-elle être construite et testée même si toutes
> les autres n\'existaient pas encore ? »**

Oui : c\'est une **feuille**, donc la couche 0 ou proche. Fonction de
calcul pur, entité de données sans logique, structure d\'entrée,
transformation autonome. Non, elle a besoin de telle autre unité : sa
couche se situe au-dessus de celles dont elle dépend.

*Première illustration.* Soit le flux :

    lire_fichier → calculer_moyenne → afficher_résultat
    (début du flux)                    (fin du flux)

L\'ordre d\'exécution suggère à tort que `afficher``_résultat`, la fin,
serait la fondation. L\'ordre des dépendances dit autre chose :
`afficher_résultat` dépend de `calculer_moyenne`, qui dépend de la
structure de données produite par `lire_fichier`. La fondation réelle se
situe donc au **début** du flux. `afficher``_résultat`, qui dépend de
tout le reste, est la couche la plus externe. Construire dans l\'ordre
du flux placerait la fondation au mauvais bout et tenterait de bâtir
l\'affichage avant que rien ne soit là à afficher.

*Seconde illustration, le cas général.* Soit un artefact de facturation
dont le flux, modélisé en 2.2, est :

    parser_lignes → calculer_taxes → appliquer_remise → générer_facture

La modélisation du flux fait apparaître deux objets intermédiaires qui
ne sont des étapes nulle part : les structures de données
(`LigneCommande`, `Facture`) et le barème `règles_tarifaires`. La
question-test, posée unité par unité, donne :

-   `LigneCommande`, `Facture`, `règles_tarifaires` sont constructibles
    et testables seules, donc **couche 0**. Retenez ceci : les unités
    les plus profondes de cet artefact **n\'apparaissent pas dans le
    flux comme étapes**. Le flux montre des traitements, pas toutes les
    unités. Les objets intermédiaires émergés en 2.2 sont les candidats
    naturels à la couche 0.
-   `parser``_lignes`, `calculer_taxes`, `appliquer_remise` et
    `générer_facture` consomment et produisent chacune des structures de
    la couche 0, et aucune n\'a besoin qu\'une autre étape **existe**
    pour être construite et testée. On alimente `calculer_taxes` avec
    des `LigneCommande` fabriquées à la main, sans parser. Quatre étapes
    consécutives du flux atterrissent donc **côte à côte**, en couches
    parallèles 1a à 1d.
-   L\'orchestrateur `facturer`, qui appelle les quatre étapes dans
    l\'ordre du flux, dépend de toutes : **couche 2**, l\'enveloppe.

L\'ordre de dépendance n\'est ici **ni l\'ordre du flux, ni son
inverse**. La différence avec la première illustration tient à un choix
de conception et non au flux : là-bas, chaque étape était conçue pour
invoquer la précédente, ce qui en faisait de vraies dépendances ; ici,
les étapes sont orchestrées et ne se connaissent pas. C\'est la
conception effective que la question-test interroge.

> **Ancrage.** Le piège que cette étape désamorce est documenté depuis
> 1972. Parnas montrait, sur le système KWIC, qu\'une décomposition
> calquée sur l\'organigramme de traitement disperse les décisions de
> conception à travers tous les modules, là où une décomposition par
> responsabilités les localise. Le principe est établi de longue date.
> Il n\'avait jamais été outillé au moment où l\'erreur se commet.
>
> **Apport.** C\'est ce que fait la question-test. Elle transforme un
> principe de conception en geste de tri, applicable unité par unité,
> par quelqu\'un qui n\'a pas lu Parnas. Deux dispositifs la complètent
> : des heuristiques dont les bornes sont écrites, pour qu\'elles ne se
> durcissent pas en règle mécanique, et le contrôle de divergence de
> l\'étape 3, qui rattrape l\'erreur au coût le plus bas possible, avant
> qu\'une seule couche ne soit construite.
>
> **Condition.** Dans un pipeline de données séquentiel, la feuille est
> souvent au début du flux. Dans un arbre d\'appels, c\'est la fonction
> la plus profondément appelée. Ces heuristiques orientent, elles ne
> tranchent jamais. Remplacer « suivre le flux » par « inverser le flux
> » substituerait une règle mécanique fausse à une autre. Seule la
> question-test tranche, unité par unité.

**Unités de même profondeur.** Plusieurs unités situées à la même
profondeur sans dépendance entre elles forment une même couche
subdivisée par indice : 4a, 4b, 4c. Elles sont candidates à une
construction parallèle, et cette opportunité doit être explicitement
signalée dans le plan de construction.

### 2.5 --- Les systèmes qui ne sont pas des flux

L\'approche par workflow suppose que le problème se laisse représenter
comme un flux entrées → sorties. Trois familles y résistent. Pour
toutes, **le critère de dépendance reste inchangé** : la couche 0 est
toujours ce qui peut être construit et testé sans que rien d\'autre
n\'existe. Ce qui change, c\'est l\'objet qu\'on cartographie avant
d\'appliquer le critère.

**a) Machines à états et systèmes réactifs.** Il n\'y a pas d\'étape
finale dans une machine à états, mais des états et des transitions
souvent mutuellement accessibles. Le graphe est cyclique par nature, ce
qui semble interdire l\'assignation en couches. La théorie des graphes
résout exactement ce cas. Tout graphe cyclique se décompose en
**composantes fortement connexes**, des clusters d\'états mutuellement
accessibles ; le graphe formé par ces composantes, leur condensation,
est toujours un DAG. L\'algorithme de Tarjan produit les composantes
directement en ordre topologique inverse, ce qui vous donne l\'ordre de
construction sans calcul supplémentaire : la première composante émise
est la couche 0.

En pratique : tracez le diagramme d\'états et de transitions, identifiez
les composantes fortement connexes, ordonnez-les par condensation. La
couche 0 est la composante source, le cluster le plus autonome,
typiquement l\'état initial et le cycle dont il fait partie. On étend
ensuite vers les composantes qui dépendent des précédentes.

> **À l\'intérieur d\'une composante, préservez l\'incrémental.**
> Traiter une composante comme atomique est une atomicité
> **d\'ordonnancement externe** : elle occupe une seule couche du DAG.
> Mais elle peut contenir de nombreux états mutuellement dépendants, et
> les construire d\'un bloc recréerait un mini big bang. Appliquez donc
> MCL récursivement à l\'intérieur, sur un critère différent : non plus
> la dépendance acyclique, impossible par définition dans un cycle, mais
> la **couverture incrémentale des transitions**. Implémentez d\'abord
> un cycle minimal vivant (l\'état initial plus une transition de
> retour), testez-le, puis ajoutez une à une les transitions et les
> états restants, en validant après chaque ajout.

**Le cas général des dépendances circulaires.** Ce traitement ne
concerne pas que les machines à états : il résout aussi les cycles
ordinaires. Un cycle dans un graphe d\'unités se condense en une
composante occupant une seule couche du DAG, après quoi la méthode
reprend son cours sur le DAG des composantes. La résolution
architecturale, briser le cycle par une interface, reste préférable
quand le cycle trahit un défaut de conception. Pour des unités
ordinaires, la construction interne se transpose en trois temps :

1.  **Noyau minimal.** Implémentez *simultanément* les versions
    minimales des unités mutuellement dépendantes, juste assez pour
    fermer le cycle, et testez-les **ensemble, comme un seul pas de
    construction**. C\'est une co-construction bornée : l\'exception
    assumée et déclarée à la règle « une unité à la fois ». Un cycle
    n\'admet, par définition, aucun ordre interne total.
2.  **Croissance incrémentale.** Le noyau vivant et vert, enrichissez
    les unités une à une, méthode par méthode, cas par cas, en validant
    après chaque ajout. Le régime incrémental normal reprend.
3.  **Doublure de sectionnement temporaire**, en repli si le noyau
    minimal reste trop gros. Coupez le cycle en un point par une
    doublure interne provisoire, construisez le reste de la composante
    dans l\'ordre, puis fermez le cycle en remplaçant la doublure par
    l\'unité réelle. Choisissez le point de coupe qui minimise le nombre
    et la richesse des doublures. **Règle de temporalité :** toute
    doublure interne intra-composante est provisoire, et sa suppression
    est un critère de fermeture. Une doublure interne qui survit à la
    construction de la composante est un défaut.

À l\'intérieur d\'une composante cyclique, l\'économie de doublures de
2.4 se **dégrade localement**. Co-construction et doublures temporaires
sont précisément ce que l\'ordre de dépendance évite partout ailleurs,
ce qui donne une raison supplémentaire de préférer la résolution
architecturale quand elle est accessible.

**b) Systèmes événementiels ou pilotés par le domaine.** Quand le
système est dirigé par des événements métier plutôt que par un flux de
calcul, la cartographie devient un *event storming* allégé. Listez les
événements du domaine, au passé : « commande passée », « paiement validé
». Identifiez les **agrégats**, les entités cohérentes sur lesquelles
ces événements opèrent : Commande, Paiement, Stock. Regroupez selon la
règle « ce qui change ensemble va ensemble ; on minimise les dépendances
entre groupes ». La couche 0 est l\'**agrégat le plus autonome**, celui
qui maintient son cycle de vie sans dépendre d\'un autre. Les agrégats
qui réagissent à des événements produits ailleurs forment les couches
externes.

**c) Domaines complexes à frontières multiples.** Pour un grand système
métier, délimitez d\'abord les **frontières de sens**, les contextes
bornés : « facturation » et « livraison » parlent de choses différentes
même s\'ils partagent le mot « commande ». Un signal fiable de frontière
: le vocabulaire change. Ces frontières posées, appliquez la
décomposition **indépendamment à l\'intérieur de chacune** ; chaque
contexte devient un sous-problème MCL autonome, avec sa propre couche 0.

> Flux séquentiel : suivez les données. Machine à états : suivez les
> transitions. Domaine événementiel : suivez les événements et regroupez
> en agrégats. Dans les trois cas, une fois la carte établie, la même
> question de dépendance désigne la couche 0, et les étapes 3 à 8
> s\'appliquent à l\'identique.

### Étape 3 --- Construire le graphe de dépendances

Formalisez sous forme de graphe l\'ordonnancement amorcé en 2.4. Pour
chaque unité : de quoi dépend-elle ? Qu\'est-ce qui dépend d\'elle ? Le
résultat est un graphe orienté acyclique.

    Unité A → dépend de → Unité B, Unité C
    Unité B → dépend de → Unité D
    Unité C → dépend de → (rien — feuille)
    Unité D → dépend de → (rien — feuille)

Les **feuilles**, sans dépendance sortante, forment la couche 0 et le
point de départ. La **racine**, dont rien ne dépend, est la couche N et
le point d\'arrivée.

**Contrôle de divergence.** Confrontez le graphe formalisé à
l\'ordonnancement que vous aviez intuitionné en 2.4. Toute divergence
est un signal plutôt qu\'un échec : une dépendance mal comprise ou une
unité manquante vient d\'être détectée, au coût le plus bas possible,
avant qu\'une seule couche ne soit construite. Résolvez la divergence
avant l\'assignation des couches.

**Dépendances externes.** Base de données, API tierce, service de
paiement, système de fichiers : identifiez-les séparément. Elles seront
doublées dans les couches internes et connectées réellement dans la
seule couche d\'infrastructure finale.

**Détection de cycles.** Si le graphe contient un cycle, fréquent en
code legacy, deux options. Briser le cycle par l\'introduction d\'une
interface ou d\'une abstraction, préférable quand le cycle trahit un
défaut de conception. Ou le condenser en composante fortement connexe
occupant une seule couche, construite de façon incrémentale en interne
(2.5.a). Un cycle est donc un cas traité, plus un obstacle bloquant.

### Étape 4 --- Assigner les couches

  ------------------------------------------------------------------------
  Couche        Contenu                             Dépend de
  ------------- ----------------------------------- ----------------------
  0 --- Noyau   Unités feuilles, aucune dépendance  Rien

  1             Unités dépendant uniquement de la   Couche 0
                couche 0                            

  2             Unités dépendant des couches 0 et 1 Couches 0-1

  ...           ...                                 ...

  N ---         Point d\'entrée, orchestrateur      Toutes les couches
  Enveloppe     final                               internes
  ------------------------------------------------------------------------

Le tableau produit ici est votre plan de construction. Il est aussi, et
c\'est le sujet de la section suivante, un artefact exécutable.

## III.3 Encoder la carte : l\'invariant devenu règle de build

Consignez la carte des couches dans la configuration d\'un outil de test
d\'architecture, et versionnez-la avec le code. L\'invariant central
devient alors une règle de build : toute unité d\'une couche `k` qui
référence une couche plus externe fait **échouer la compilation**. La
carte ne peut plus dériver du code réel, puisque toute dérive casse le
build.

Trois contrôles du protocole deviennent automatiques. La **violation de
l\'invariant**. La **détection de cycles**, fournie par le même
outillage. Le **contrôle de divergence**, l\'outil confrontant le graphe
qu\'il calcule à la carte que vous avez déclarée.

> **En pratique.** La règle à encoder est celle de la méthode :
> dépendances autorisées vers **n\'importe quelle couche plus interne, à
> profondeur quelconque**. Attention au réglage par défaut de certains
> outils, qui proposent la variante « couche adjacente seulement ». Elle
> est plus stricte que l\'invariant et vous fera rejeter du code
> parfaitement conforme.

Quatre conditions encadrent l\'encodage.

**Précondition de traçabilité.** Une couche doit correspondre à une
unité adressable par l\'outil : package, module, namespace, répertoire.
La convention « une couche = un module nommé » se fixe à cette étape, et
elle resservira en gouvernance (III.9).

**Couches parallèles.** Les unités de même profondeur forment un même
groupe de couche pour l\'outil. Leur indépendance mutuelle peut
elle-même être encodée si vous voulez la garantir.

**Portée du contrôle.** L\'outil vérifie la **structure** des
dépendances, pas le respect sémantique des contrats. L\'enforcement
couvre la moitié structurelle de l\'invariant ; le protocole de test
couvre l\'autre.

**Outillage disponible.** ArchUnit en Java, Konsist et detekt en Kotlin,
Deptrac en PHP, NetArchTest en .NET, dependency-cruiser en JS et
TypeScript, import-linter en Python. Les écosystèmes sans outil mûr
dédié (Go, Rust, mobile natif dont Dart et Flutter) se rabattent sur la
convention de modules, un lint personnalisé et la revue de code. Dans
tous les cas, la carte déclarée reste l\'artefact de référence.

Sans outillage du tout, la forme minimale reste utilisable : carte
versionnée, vérification des imports en revue. L\'encodage outillé
devient le standard dès qu\'une intégration continue existe.

> **Apport.** L\'outillage de test d\'architecture existe depuis les
> années 2010 et il est commun à toutes les approches. Deux choses ne le
> sont pas. MCL **prescrit** son usage au lieu de le mentionner comme
> une option, et elle produit ce que ces outils réclament en entrée :
> une carte des couches justifiée par la dépendance, que rien d\'autre
> n\'oblige à établir. Un schéma d\'architecture dessiné au tableau ne
> fait échouer aucun build. Une carte issue de l\'étape 4, si.

## III.4 Les contrats d\'interface : étape 5

Le contrat de chaque unité se rédige **en deux temps**, et le calage de
ces deux temps est ce qui distingue la méthode d\'une simple discipline
d\'interface.

**L\'esquisse**, à cette étape, pour toutes les unités de la carte :
responsabilité, signature approximative. Les étapes 3 et 4 en ont
besoin, ainsi que l\'encodage de la carte.

**La finalisation**, par couche, **au moment de construire l\'unité**,
avant d\'en écrire la moindre ligne d\'implémentation. Un niveau
d\'avance sur son premier consommateur, jamais plus. Chaque report
jusqu\'à cet instant accumule de l\'information réelle : les couches
inférieures existent, leurs contrats sont exercés. Le report est borné
des deux côtés, l\'esquisse étant due maintenant et la finalisation au
début de la couche.

Une exception : les contrats des **frontières externes** se finalisent
tôt, puisque les doublures de l\'étape 6 en dépendent. C\'est le cas où
l\'anticipation se défend, avec les tests de contrat en garde-fou.

Le gabarit tient en sept lignes.

    Unité : [nom]
    Responsabilité : [une phrase]
    Signature : [interface de fonction, méthode ou classe]
    Entrée : [type, contraintes, exemples]
    Sortie : [type, garanties, exemples]
    Effets de bord : [aucun / liste]
    Erreurs, exceptions : [conditions de déclenchement]

**Pourquoi cette étape est décisive.** Un contrat rédigé avant
l\'implémentation empêche les couches internes d\'être optimisées pour
elles-mêmes plutôt que pour ce qui va effectivement les consommer.
C\'est le point de négociation entre la couche interne et la couche
externe qui l\'utilisera.

### La discipline du contrat minimal

Le contrat couvre le besoin **cartographié**, c\'est-à-dire ce que les
consommateurs présents sur la carte requièrent, et rien de plus. Pas de
paramètre spéculatif. Pas d\'axe de généricité « pour plus tard ». Pas
d\'interface d\'indirection sans deuxième cas réel.

La distinction qui compte est celle-ci : le YAGNI d\'*implémentation*
produit du code mort, facile à supprimer ; le **YAGNI de contrat** fige
de la généricité fictive dans ce que le protocole a précisément pour
vocation de geler. C\'est celui-là qu\'on s\'interdit. La frontière
d\'une unité cache une décision ; elle n\'expose pas des possibles.

Sous-construire n\'est pas un échec : c\'est le chemin prévu. Ajouter à
un contrat, une méthode ou un paramètre optionnel à valeur par défaut
conservatrice, reste compatible pour tous les appelants existants. Le
défigeage formel s\'applique, mais sa propagation est alors quasi nulle.
**Étroit d\'abord, étendre sur demande réelle** : l\'extension coûte une
révision, tandis que la généricité morte coûte sa construction, sa
maintenance, et la mauvaise abstraction qui s\'incruste.

> **Apport.** Le double temps du contrat résout une tension que la
> plupart des approches tranchent d\'un côté ou de l\'autre. Spécifier
> avant de coder protège les couches internes d\'être conçues pour
> elles-mêmes ; décider trop tôt fige de l\'ignorance. MCL découpe la
> décision en deux moments : l\'esquisse, due quand la carte en a
> besoin, et la finalisation, repoussée jusqu\'au point où
> l\'information est maximale, à la veille de la consommation. Le report
> est borné des deux côtés, ce qui en fait une règle exécutable plutôt
> qu\'un conseil de prudence.

## III.5 Les frontières externes : étape 6

Pour chaque dépendance externe identifiée à l\'étape 3, quatre gestes.

Rédigez le contrat d\'interface attendu de cette dépendance. Créez une
doublure minimale respectant ce contrat. Utilisez-la dans toutes les
couches internes concernées. Remplacez-la par l\'implémentation réelle
uniquement dans la couche d\'infrastructure, la plus externe.

L\'objectif : garder toute la logique interne pure, rapide à tester, et
indépendante de la disponibilité ou de la lenteur d\'une infrastructure
réelle.

> **Condition.** Chaque doublure externe reproduit un contrat qui ne
> vous appartient pas. Sa fidélité (schémas, cas d\'erreur, formats
> réels) est un risque du même type que celui de tout stub, et elle se
> dégrade avec le temps. Vérifiez périodiquement vos doublures externes
> contre le contrat réel ; les tests de contrat sont la parade usuelle.
> Le point mérite d\'autant plus d\'attention que les frontières
> externes sont nombreuses : c\'est là que se concentre l\'intégralité
> de votre budget de doublures.

## III.6 La boucle de construction : étape 7

Pour chaque couche, dans l\'ordre strict de 0 à N, la boucle de I.7
s\'exécute. Cette section en donne le détail opérationnel.

### Ce que « tester » veut dire exactement

À chaque couche, il existe **deux catégories de tests**, définies par
leur cible et non par leur outillage.

**Catégorie 1, le test unitaire de la couche.** La nouvelle couche est
testée pour elle-même : respecte-t-elle **son propre contrat**, entrées,
sorties, cas d\'erreur, de façon fine ? Ses dépendances externes sont
toujours doublées. Pour ses dépendances internes, deux régimes.

*Par défaut, les couches réelles figées.* C\'est le test dit
**sociable**, la pratique de l\'école classiciste dont la méthode se
réclame. Ces couches sont déjà construites, validées et gelées ; les
utiliser ne coûte aucune doublure, ne pose aucun problème de fidélité,
et reste rapide puisqu\'elles sont pures, l\'externe étant doublé depuis
l\'étape 6. La construction par couches figées rend les collaborateurs
réels disponibles précisément au moment où on en a besoin.

*En option justifiée, la doublure interne.* Le test dit **solitaire**,
quand une couche réelle est devenue lente, quand vous voulez isoler un
diagnostic, ou quand vous voulez spécifier le comportement de la couche
courante face à des réponses internes difficiles à provoquer. Cette
doublure est un choix de commodité. Elle porte un risque de fidélité
réduit, puisque la couche cible existe et que la doublure peut être
dérivée d\'elle et vérifiée contre elle. Réduit, non nul : une doublure
interne qui dérive de la couche réelle ment exactement comme un stub
trop simplifié.

Dans les deux régimes, les seules doublures *structurellement
obligatoires* sur toute la construction restent celles des dépendances
**externes**.

**Catégorie 2, le test d\'intégration sur le bloc réel.** La couche est
branchée directement sur l\'ensemble réel déjà construit, sans doublure
interne. La **cible** est la **jonction** : l\'interaction entre la
nouvelle couche et le système existant fonctionne-t-elle comme prévu ?
Parce que le bloc est réel, chaque test de cette catégorie traverse
toute la profondeur du bloc. Choisissez donc des scénarios qui
parcourent des **chemins représentatifs** de cette profondeur, et pas
seulement l\'interface immédiate entre les deux couches du dessus. «
Représentatif » qualifie le choix des scénarios ; il n\'exige pas une
couverture exhaustive du bloc.

### Ce que la méthode ne fait pas

Elle ne teste pas successivement la couche seule, puis avec la couche du
dessous, puis avec les deux du dessous, comme autant de sous-ensembles
isolés. Cette **sur-isolation** multiplierait les configurations et,
surtout, testerait des sous-systèmes **fictifs** : isoler trois couches
du reste exigerait de re-doubler la quatrième, donc de recréer
artificiellement une frontière qui n\'existe pas dans le système réel.

Deux niveaux suffisent parce que les couches déjà construites forment un
seul système intégré et validé. Chaque jonction interne a **déjà été
testée au moment où elle a été créée**, et elle est **re-traversée par
chaque test de catégorie 2 ultérieur**, puisque ces tests s\'exécutent
sur le bloc réel. La couverture des jonctions s\'accumule au fil de la
construction.

> **Apport.** Le refus de la sur-isolation vaut mieux qu\'une économie
> de configurations, même si celle-ci est déjà substantielle. Il change
> la nature de ce qu\'on teste. Les tranches partielles valident des
> systèmes qui n\'existeront jamais ; les deux niveaux du protocole
> valident le système réel. Et l\'argument tient parce que le protocole
> garantit lui-même ses deux préconditions, le gel des couches
> inférieures et la régression intégrale à chaque couche. Peu
> d\'arguments de conception sont ainsi auto-portés.

    Couche 0   : test unitaire de 0                        → fige
    Couche 1   : test unitaire de 1 (isolation de 0)
                 intégration {1 + 0} (réel)                → fige
                 régression : tests de {0, 1}
    Couche 2   : test unitaire de 2 (isolation de {1→0})
                 intégration {2 + (1→0)} (réel)            → fige
                 régression : tests de {0, 1, 2}
       …
    Couche n+1 : test unitaire de n+1 (isolation de {n→0})
                 intégration {n+1 + (n→0)} (réel)          → fige
                 régression : TOUS les tests {0 → n+1}

À chaque niveau : un test unitaire ciblé, un test d\'intégration sur le
bloc réel, une régression globale. Jamais une cascade de tranches
partielles.

### Ce que le gel gèle, ce qu\'il laisse libre

FIGER gèle le **contrat public** de la couche : son interface, ses
comportements documentés, sa suite de tests comme spécification
exécutable. C\'est ce que les consommateurs ont le droit de tenir pour
acquis, et c\'est ce qui porte les garanties du protocole.

L\'**implémentation interne** reste révisable, à comportement constant
et sous harnais complet : rien ne change sans que la suite de la couche
et la régression intégrale repassent au vert immédiatement.

Trois opérations, trois régimes.

*Réviser l\'implémentation*, à contrat constant : libre sous harnais,
organisée de préférence aux checkpoints pour amortir le coût.

*Changer le contrat* : défigeage formel, avec propagation
conditionnelle. La propagation coûte des couches, donc elle s\'anticipe.

*Corriger un défaut* : défigeage formel également. La confiance dans la
couche est entamée, et un test capturant le cas s\'ajoute à sa suite.

> **Condition.** « Comportement constant » s\'entend au sens du contrat
> documenté et de la suite de tests. Des observables non documentés
> (ordres d\'itération, formats de messages) peuvent changer, et des
> consommateurs peuvent en dépendre par accident. Les praticiens
> appellent cela la loi de Hyrum. Deux règles en découlent : les
> consommateurs ne codent que contre le contrat documenté, et toute
> casse de ce type découverte tranche le comportement et enrichit la
> suite.

## III.7 Quand ça casse : diagnostic et correction

Le *regression gate* est non négociable, et procéder à la couche
suivante avec un test en échec est la source principale des bugs
d\'intégration difficiles à diagnostiquer.

### L\'aiguillage, qui est mécanique

Test unitaire de la couche courante en échec → **régression locale**.
Corrigez la couche courante. La cause coïncide avec le déclencheur.

Régression en échec alors que le test unitaire passe → la cause est dans
l\'interaction, ou plus bas. Ouvrez le diagnostic par remontée de
couches.

Une couche gelée est **validée par sa suite de tests, non prouvée
correcte**. Un usage nouveau peut exercer un chemin que la suite ne
couvrait pas. Les défauts amont existent, et le protocole les traite
plutôt que de prétendre les avoir supprimés.

> **Ancrage.** La localisation face à un delta unique appliqué à une
> base entièrement verte est le principe du *delta debugging*, publié
> par Zeller en 1999, dont les commandes `bisect` des gestionnaires de
> versions sont les héritières documentées.
>
> **Apport.** Ce principe suppose une précondition que la pratique
> courante ne réunit qu\'accidentellement : petit delta, base verte. Le
> *regression gate* la rend **permanente par construction**. Ce que le
> débogage classique doit reconstituer après coup, souvent au prix
> d\'une bissection sur l\'historique, le protocole vous le livre à
> chaque couche, sans effort supplémentaire, parce que vous ne pouviez
> pas avancer autrement.

### La remontée de couches

La granularité par tranches, écartée comme protocole systématique,
**redevient pertinente en mode diagnostic réactif**. Le diagnostic isole
le niveau fautif en testant des tranches munies d\'une **doublure de
coupe** temporaire.

*Remontée séquentielle* : descendez couche par couche jusqu\'à ce que la
tranche casse. Simple, jusqu\'à N sondes.

*Dichotomie* : coupez au milieu de la pile et resserrez par moitiés, à
la manière d\'un `bisect` appliqué aux couches. De l\'ordre de log N
sondes.

Ces sondes testent des sous-systèmes fictifs, et c\'est assumé : ce sont
des **instruments de diagnostic jetables**. Les doublures de coupe se
suppriment sitôt le niveau localisé. Vous ne payez ce coût que
lorsqu\'un échec l\'exige.

### Le protocole correctif

Localiser le niveau fautif, disons la couche `k`, n\'est que la moitié
du travail.

1.  **Défigez** la couche `k` et corrigez, en ajoutant à sa suite un
    test qui capture le cas révélé.
2.  Si la correction ne touche que l\'**implémentation interne**,
    contrat inchangé : revalidez `k`, re-figez, relancez la régression
    globale. **La propagation s\'arrête là.**
3.  Si la correction **modifie le contrat** de `k`, la vérification se
    propage. Chaque couche consommatrice est re-vérifiée contre le
    nouveau contrat, et défigée à son tour si elle doit s\'adapter. Ce
    coût de propagation est le vrai coût des défauts amont : la remontée
    ne coûte que des sondes, la propagation coûte des couches. Le
    contrat est l\'arbitre de la frontière entre les deux cas.
4.  Dans tous les cas, **corrigez à la source, jamais au symptôme**.
    Compenser le défaut de `k` par un contournement dans une couche
    supérieure masque le défaut, installe une divergence entre le
    contrat et le comportement réel, et lègue les deux à toutes les
    couches futures.

## III.8 Le *gate* à l\'échelle

**Le coût, compté d\'abord.** RÉGRESSER relance à la couche `k` tout ce
qui a été écrit jusque-là. Si la suite croît avec les couches, le volume
cumulé d\'exécutions sur une construction complète est **quadratique**,
de l\'ordre de N²/2 lancements pour N couches. Le *gate* coûte donc de
plus en plus cher à mesure que vous montez. C\'est le prix de la
garantie achetée : un delta unique validé sur une base entièrement
verte.

**Le gate unifié.** En équipe, l\'étape de régression se câble en
**check bloquant** de la branche d\'intégration, unifiant les deux
contrôles que le protocole rend mécaniques : l\'**architecture**, via la
carte encodée, et la **régression fonctionnelle**. Un gate bloquant a un
ennemi opérationnel, les tests instables. Quarantaine et taux sous
contrôle sont une précondition, pas un raffinement.

**Adopter le gate sur une base existante.** Le mur de violations se
franchit par le protocole du **cliquet**. Une *baseline* versionnée
capture la dette au jour J. Toute violation **nouvelle** bloque la
fusion. Toute violation **résolue** resserre la baseline, et ne pourra
plus jamais revenir. La baseline elle-même est protégée : toute
altération de son fichier fait échouer le build, sauf autorisation
explicite. Le déploiement passe de *warn*, signaler sans bloquer, à
*strict*, règle par règle.

**La maîtrise du coût : le régime à deux vitesses.** À l\'échelle, deux
familles d\'outils réduisent le volume. La **sélection par analyse
d\'impact**, déterministe, ne joue que les tests que le diff touche ;
ses gains sont maximaux sur code modulaire, au prix d\'une maintenance
des cartes de couverture, et elle se dégrade sur code fortement couplé.
La **sélection prédictive**, probabiliste, est apprise sur l\'historique
; elle résiste mieux et se passe de cartes.

> **La règle constitutive de leur emploi.** La sélection accélère la
> boucle interne, elle ne remplace jamais le gate. Pushes et itérations
> à l\'intérieur d\'une couche : suite sélectionnée. **Gate de couche et
> fusion sur le tronc : suite intégrale, non négociable.** Le gel ne
> s\'accorde que sur base entièrement verte, et c\'est la prémisse de
> toutes les garanties de cette étape. Une nightly intégrale sert de
> filet. Conséquence assumée : une régression manquée par la sélection
> refait surface au gate, avec un délai borné par la couche.

**La proportionnalité.** Aux échelles d\'une tâche ou d\'un composant,
ce dispositif se réduit à sa forme minimale : la suite tourne en local
et dans une CI simple, le régime à deux vitesses est inutile. À
l\'échelle d\'une application, le mode composite est aussi la réponse au
coût, chaque artefact de chair portant sa propre suite, qui retombe à
l\'échelle d\'un composant. La forme qui rend le gate prohibitif, le
monolithe construit en couches globales, est précisément celle que III.1
déconseille.

## III.9 Gouvernance : qui décide quoi

Le protocole crée des décisions. Voici qui les prend.

La règle générale : **le circuit suit le rayon d\'impact**. La nature de
l\'opération dit le type de circuit ; la carte encodée dit qui est
touché, ses dépendances inverses listant mécaniquement les consommateurs
directs et transitifs d\'une couche. Un arbitrage convoque les touchés,
pas l\'organigramme.

**Trois décisions, trois circuits.**

*Révision d\'implémentation ou extension additive* → revue standard. Le
harnais est l\'autorité réelle, avec la suite de la couche et la
régression intégrale au gate. La décision humaine se réduit à la revue
de code ordinaire.

*Modification de contrat* → arbitrage entre le demandeur, le
propriétaire de la couche, et les consommateurs que la carte liste.
Décision **tracée**, sous forme d\'un enregistrement court de type ADR :
quoi, pourquoi, rayon constaté. Cascade exécutée **dans l\'ordre des
couches**, puis re-gel. Le moment naturel de ces demandes est le
checkpoint.

*Modification de la baseline* → la clé du gardien, chaque usage de la
clé étant lui-même tracé.

Chaque défigeage laisse une trace d\'une à quelques lignes. C\'est la
mémoire de la gouvernance, et la matière première de toute évaluation
ultérieure : extensions contre modifications contre corrections.

**Trois rôles**, qui sont des rôles et non des postes. Le **gardien de
la carte** veille à l\'intégrité de la carte encodée et de la baseline ;
il détient la clé, il garde les artefacts de référence, il ne décide pas
des contrats. Le **propriétaire de couche** répond du contrat gelé et
instruit les demandes. Les **consommateurs** sont partie prenante de
tout arbitrage qui les touche.

**Trois profils.**

*Solo.* Une personne porte les trois rôles. Zéro cérémonie ajoutée,
seules les traces demeurent. La gouvernance solo, c\'est la discipline
de se répondre par écrit.

*Petite équipe, environ deux à huit personnes.* Gardien : l\'auteur de
la carte, ou un rôle tournant. Propriétaires : les auteurs des couches.
L\'arbitrage est une conversation avec les consommateurs listés, plus la
trace.

*Organisation, plusieurs équipes.* Gardien : un architecte référent. La
propriété se **matérialise** dans le fichier de propriétaires de la
forge, déclaré sur les mêmes modules que la carte ; la convention « une
couche = un module » sert ici une seconde fois. L\'arbitrage
inter-équipes prend la forme d\'un mini-RFC avec les équipes
consommatrices, et la cascade se coordonne dans l\'ordre des couches,
chaque équipe re-vérifiant à son tour.

> **Apport.** Une méthode de construction qui arrive avec son modèle de
> gouvernance est peu commune. Celui-ci tient en trois circuits, trois
> rôles et trois profils, et il possède une propriété que les processus
> de décision improvisés n\'ont pas : le rayon d\'un arbitrage se
> **calcule** au lieu de se négocier. Les dépendances inverses de la
> carte listent mécaniquement les consommateurs touchés, directs et
> transitifs. Vous convoquez les gens concernés, pas ceux dont le titre
> le suggère.

## III.10 Les checkpoints de refactoring : étape 8

Tous les deux à trois niveaux ajoutés, marquez une pause avant de
continuer. Le checkpoint est le **moment planifié** où s\'exercent les
deux libertés que le gel laisse ouvertes.

Une unité interne fait-elle plus d\'une chose ? Une unité est-elle
sur-ingénierée par rapport à son usage réel ? Des duplications entre
couches devraient-elles être extraites ? Ce sont des **révisions
d\'implémentation**, à contrat constant, traitées en lot.

Les interfaces des couches internes sont-elles toujours pertinentes,
compte tenu de ce qu\'on sait désormais du contexte extérieur ? Si une
interface doit évoluer, c\'est un **changement de contrat** : ouvrez un
défigeage formel avec sa propagation conditionnelle. Il s\'anticipe ici
au lieu de se subir plus tard.

Refactorez en lot, relancez l\'intégralité de la suite, poursuivez la
construction.

**Le coût, compté honnêtement.** Chaque lot de révisions paie **une
régression intégrale**. « Chaque jonction testée une seule fois » vaut
pour la construction nominale ; le refactoring re-paie, et c\'est
normal. Le checkpoint existe précisément pour **amortir** ce prix : un
lot de révisions égale une seule régression, au lieu d\'une par retouche
dispersée. Un changement de contrat coûte davantage, à cause de la
propagation, et c\'est pourquoi il passe par le protocole formel.

> **Justification.** Lors de la conception initiale des couches
> internes, l\'information sur leurs futurs consommateurs est
> nécessairement incomplète. Le checkpoint corrige les effets de cette
> incomplétude avec le contexte réel acquis entre-temps.

## III.11 Organiser le travail : ce qui se parallélise

Entre couches dépendantes, le protocole **sérialise**, structurellement
: le gel de `k` précède la construction de `k+1`. Le gain parallèle est
donc borné par cette fraction sérialisée, et la forme du graphe décide.
Un graphe large parallélise. Un graphe étroit et profond est un travail
pour peu de mains.

Le parallélisme réel vit à trois niveaux.

**Intra-couche.** Les unités de même profondeur sans interdépendance,
les groupes 1a, 1b et suivants, se construisent simultanément :
développeurs différents, sessions parallèles. Ces groupes **se lisent
dans la carte encodée** et leurs contrats se finalisent ensemble.
Signalez explicitement cette opportunité dans tout plan de construction
; c\'est de l\'organisation gratuite qui se perd si personne ne la
nomme.

**Le tuilage de préparation.** Pendant que la couche `k` se construit,
la finalisation des contrats de `k+1` **s\'instruit**, et **se fige à
l\'issue de** `k`, au moment responsable. On parallélise la préparation,
jamais l\'anticipation.

**Inter-artefacts.** C\'est le vrai parallélisme d\'équipe. À l\'échelle
d\'une application, il ne vient pas des couches mais des **artefacts** :
tranches ou composants, un par équipe ou par binôme, le squelette du
mode composite servant de cadre d\'intégration.

> **L\'anti-pattern : les équipes par couches.** La méthode ordonne la
> *construction* par couches ; elle n\'ordonne jamais les *équipes* par
> couches. Une « équipe couche données » et une « équipe couche services
> » recréeraient la spécialisation horizontale documentée contre elle
> (silos, files d\'attente, retour tardif) et, par la loi de Conway, un
> système qui épouse l\'organigramme. Les équipes s\'alignent sur les
> flux. Les couches sont un ordre de travail, pas un découpage social.
> La synchronisation entre parallèles est fournie par le protocole
> lui-même : une couche gelée est un point de rendez-vous.

## III.12 Stacks de référence par contexte technique

Les stacks ci-dessous décrivent l\'échelle la plus exigeante,
l\'application entière, parce que c\'est la plus complète à illustrer. À
cette échelle, lisez-les avec III.13. Les mêmes stacks se découpent aux
échelles d\'un composant ou d\'une tâche ; la carte se restreint alors
au périmètre choisi.

**API backend REST, générique**

    0 : Modèles de données / entités (structures pures, sans logique)
    1 : Validateurs / parseurs (validation et transformation des entrées)
    2 : Repositories / DAO (interfaces d'accès aux données + doublures)
    3 : Services de domaine / logique métier
    4 : Services applicatifs (orchestration de cas d'usage)
    5 : Contrôleurs / handlers de routes
    6 : Middleware / authentification / gestion d'erreurs
    7 : Point d'entrée (bootstrap serveur, injection de dépendances)

**Application Flutter**

    0 : Entités du domaine (classes Dart pures)
    1 : Value objects / enums / constantes
    2 : Interfaces et implémentations de cas d'usage
    3 : Interfaces de repository (+ implémentations doublées)
    4 : Sources de données (locales : Hive/SQLite ; distantes : clients API)
    5 : Implémentations de repository (câblage des sources de données)
    6 : Gestion d'état (Bloc/Riverpod/Provider)
    7 : Widgets (stateless → stateful → écrans)
    8 : Entrée de l'application + routage + injection de dépendances

**Application Django**

    0 : Modèles (champs, validation basique, sans logique métier)
    1 : Méthodes de modèle / managers (helpers de requête)
    2 : Couche de service / logique métier (Python pur, sans dépendance Django)
    3 : Serializers (contrats d'entrée/sortie)
    4 : Views / ViewSets
    5 : Routage URL + middleware
    6 : Settings / câblage de l'infrastructure

**Algorithme ou pipeline de données**

    0 : Fonction de transformation centrale (calcul le plus imbriqué)
    1 : Fonctions utilitaires / helpers
    2 : Parseur / normaliseur d'entrée
    3 : Formateur / sérialiseur de sortie
    4 : Orchestrateur / exécuteur de pipeline
    5 : Interface CLI / API

**Refactoring de code legacy**

    0 : Identifier les unités les moins couplées (dépendances externes
        minimales) → les extraire, les tester, les traiter comme couche 0
    1 : Unités ne dépendant que de la couche 0 → extraire, tester
    … continuer vers l'extérieur jusqu'à ce que le point d'entrée legacy
      devienne la dernière couche

Le cas legacy mérite une remarque. C\'est celui où la méthode
s\'installe le plus naturellement, parce que la structure ne se devine
pas : elle se lit dans le code existant. La première question du test
d\'applicabilité y reçoit un oui presque automatique.

## III.13 Le mode composite : squelette outside-in, chair MCL

À l\'échelle de l\'application entière, le mode d\'emploi de référence
combine deux approches.

**Le principe.** Construisez d\'abord le **squelette** : une
implémentation minuscule de bout en bout, qui relie les composants
architecturaux principaux et se **déploie dès le départ**, intégration
continue comprise. Du code de qualité production destiné à durer, jamais
un prototype jetable. Puis la **chair** : chaque remplissage est un
artefact, tranche fonctionnelle ou composant, construit de l\'intérieur
vers l\'extérieur selon le protocole intégral, et branché sur le
squelette.

**La division des risques** est nette. Le squelette couvre exactement ce
que MCL ne garantit pas : le chemin de bout en bout, disponible dès la
semaine zéro, le risque d\'intégration et de déploiement, le retour
produit continu. MCL couvre exactement ce que le squelette seul ne
fournit pas : la construction validée de la logique, avec couches,
contrats, gel, gate et localisation. Chaque approche opère là où elle
est forte, et aucune n\'est dénaturée.

**Les règles de couture**, au nombre de cinq.

1.  **Identité.** Le squelette n\'est pas une étape de la méthode :
    c\'est l\'autre approche, assumée comme telle. La note de l\'étape
    1, « le seul instant de réflexion outside-in », reste vraie *du
    protocole lui-même*.
2.  **Statut.** Le squelette n\'est pas figé au sens de FIGER. Il est le
    **contexte externe** des artefacts de chair, et sa discipline propre
    est de rester **déployable en continu**. Sa CI est son gate.
3.  **Entrée.** L\'étape 1 de chaque artefact de chair lit son **point
    d\'insertion** dans le squelette : contrat d\'entrée et de sortie du
    segment à remplacer. La pensée outside-in du protocole y gagne une
    source concrète.
4.  **Sortie.** L\'enveloppe finale de l\'artefact se branche sur le
    squelette en remplaçant le segment minimal correspondant. Si la
    couture exige de modifier un contrat du squelette, c\'est un
    changement de contrat : défigeage et propagation, avec la CI du
    squelette en garde-fou.
5.  **Cadence.** Chaque remplissage est un **incrément démontrable sur
    le squelette**. La livraison reste verticale, au niveau produit ; la
    construction reste inside-out, au niveau du code.

**Ce que le composite ne change pas.** Il traite le risque de retour à
l\'échelle application. Il ne modifie pas le domaine d\'applicabilité de
III.1.

> **Apport.** La séquence squelette puis étoffement a plusieurs auteurs
> et une longue histoire. Ce que les formulations existantes laissent
> informel, c\'est le remplissage : le Double-Loop TDD nomme une boucle
> interne inside-out sans en régler l\'exécution. Le composite MCL la
> règle. Chaque artefact de chair a ses couches, ses contrats, son gel
> et son *gate*, et vous obtenez les deux garanties simultanément, un
> chemin de bout en bout dès la semaine zéro et une logique construite
> sous validation.

### Combinaisons ponctuelles

Indépendamment du mode composite, certaines situations appellent une
combinaison locale.

  -----------------------------------------------------------------------
  Situation                     Approche recommandée
  ----------------------------- -----------------------------------------
  Incertitude sur l\'expérience Outside-in d\'abord (wireframe, BDD),
  utilisateur                   puis MCL pour l\'implémentation

  Faisabilité technique         Spike ou prototype outside-in rapide →
  inconnue                      validation du concept → reconstruction
                                inside-out

  Dépendance circulaire dans le Briser le cycle par une abstraction, ou
  graphe                        le condenser en composante (III.2, 2.5.a)

  Tâches d\'infrastructure pure Outside-in ou approche plate : aucun
  (déploiement, configuration)  bénéfice à l\'imbrication
  -----------------------------------------------------------------------

## III.14 Positionnement avec ce que vous utilisez déjà

MCL ne remplace aucune méthodologie existante. Elle s\'y intègre comme
discipline de construction.

**Avec Agile et Scrum.** Elle opère au niveau du code à l\'intérieur
d\'un sprint, là où Agile opère au niveau des fonctionnalités à livrer.
C\'est la règle de périmètre de III.1.

**Avec le TDD.** Compatible et renforçante. Le TDD inside-out de
l\'école Detroit partage la même direction fondamentale ; MCL y ajoute
l\'analyse du graphe de dépendances et les contrats formels en amont.

**Avec le BDD.** Complémentaire plutôt que concurrente. Le BDD opère
outside-in au niveau du comportement attendu, MCL inside-out au niveau
de la construction technique.

**Avec Clean, Onion ou Hexagonal Architecture.** MCL peut se lire comme
le protocole de construction manquant de ces architectures. Elles
définissent où placer chaque chose ; MCL définit dans quel ordre les
construire et comment valider chaque étape.

## III.15 Adopter MCL en équipe

Le déficit d\'adoption d\'une méthode n\'est presque jamais un déficit
de connaissance. C\'est un déficit de **désir**, pourquoi changer ce qui
livre déjà, et de **capacité**, comment tenir le protocole sous
pression. Le plan cible les deux.

**Désir.** Trois vérités à établir d\'emblée. Rien de votre **cadence de
livraison** ne change : tranches, sprint et démo restent en place, et ce
qui change est la construction *dans* la tranche. Les premiers bénéfices
sont **développeur** : un échec au gate est localisé au dernier delta,
ce qui met fin à la chasse chez soi du bug de quelqu\'un d\'autre ;
moins de doublures à écrire ; des suites qui survivent au refactoring.
L\'entrée se fait par un **pilote volontaire** à l\'échelle d\'une
tranche, où les étapes 1 à 4 tiennent en minutes. Jamais par mandat :
l\'adoption imposée fabrique du rejet durable.

**Connaissance.** Ce document, plus la progression en trois temps de la
Partie V pour les nouveaux venus. Pour les praticiens confirmés, le
discours change : l\'échafaudage cognitif ne leur apporte rien, la
vérification mécanique et la coordination si.

**Capacité.** Elle se porte par l\'outillage, dans cet ordre : la carte
encodée et le gate en mode **warn** d\'abord, pour apprendre les signaux
sans bloquer, puis le **strict**, règle par règle. Baseline et cliquet
sur l\'existant. Les checkpoints s\'adossent aux rituels que vous avez
déjà, rétrospective ou refinement. Les rôles de gouvernance
s\'introduisent au fil de l\'extension, le gardien étant d\'abord
l\'initiateur du pilote.

**Renforcement.** Les traces rendent le bénéfice visible : historique
des défigeages, métriques du gate. Et le réalisme d\'abord ---
l\'adhérence aux protocoles stricts **non outillés** s\'effondre en
pratique, les études de terrain le montrent. Ici, la discipline est
portée par l\'enforcement plutôt que par la volonté. N\'exigez en strict
que ce que le build vérifie.

**La séquence.** Pilote sur une tranche avec un binôme volontaire → warn
sur le périmètre pilote → extension par flux → strict progressif →
échelles supérieures, composant puis composite pour les systèmes neufs.
Jamais l\'inverse.

Trois profils d\'entrée. **En solo**, le pilote est vous-même : le warn
est inutile, les traces suffisent. **En équipe de quatre à dix**, pilote
en binôme puis extension par tranches. **En organisation**, pilote par
équipe-flux, gardien institutionnel, warn-then-strict par service,
baseline par dépôt.

**Quatre objections prévisibles**, et ce qu\'elles valent.

*« Le gel, c\'est rigide. »* Le gel porte sur le contrat ;
l\'implémentation reste révisable sous harnais.

*« Le gate, c\'est du flicage. »* Il protège l\'auteur : la localisation
au dernier delta travaille pour vous.

*« Encore une méthode. »* Votre cadence ne change pas. Ce qui change est
la construction dans la tranche.

*« Nos couches ne sont pas vos couches. »* Exact. Ici, une couche est
une profondeur de dépendance dans votre tranche, pas une strate
technique, et jamais un découpage d\'équipe.

## III.16 Ce que MCL apporte au praticien

Les six axes de I.8, traduits en bénéfices de poste de travail.

**Un ordre de construction, là où votre architecture n\'en donnait
pas.** Clean, Onion et Hexagonal vous disent où placer chaque chose.
Aucune ne vous dit par quoi commencer un lundi matin. MCL referme ce
lien : direction des dépendances vers l\'intérieur, donc construction de
l\'intérieur vers l\'extérieur, avec un critère de passage à chaque
couche.

**Un protocole dont les pièces se tiennent.** La carte que vous
produisez à l\'étape 4 sert quatre fois : plan de construction, règle de
build, liste des consommateurs pour tout arbitrage, et repérage des
groupes parallélisables. Le gel sert trois fois : localisation des
défauts, autorisation de réviser sous harnais, base de l\'extension
additive. Vous ne payez la cartographie qu\'une fois.

**Un savoir d\'expert devenu procédure.** Ce que fait un développeur
confirmé par réflexe, analyser les dépendances avant de coder et tester
petit avant d\'intégrer, devient une suite d\'étapes nommées.
Conséquence directe pour un *tech lead* : un junior peut suivre le
protocole dès la première semaine, et sa production est vérifiable étape
par étape plutôt qu\'à la livraison.

**Une architecture que le build défend.** La carte encodée transforme
votre règle de dépendance en check bloquant. Plus de dérive silencieuse
entre le schéma d\'architecture et le code réel, plus de discussion en
revue sur un import qui n\'aurait pas dû exister : le build tranche.

**Des traces qui répondent aux questions qu\'on vous posera.**
Historique des défigeages, journaux du gate, baseline : de quoi répondre
à « pourquoi ce contrat a-t-il changé », « où en est la dette », «
combien de fois avons-nous cassé la couche 2 » sans reconstituer quoi
que ce soit après coup. Le protocole produit sa propre documentation
d\'exploitation.

**Une couverture des cas qui font décrocher les autres.** Machines à
états, domaines événementiels, grands domaines à contextes multiples,
dépendances circulaires, applications entières : chacun a son traitement
défini. Le cycle en particulier cesse d\'être le point où l\'on
abandonne la méthode.

## III.17 Ce qui conditionne le bénéfice

Quatre conditions, à connaître avant de vous engager.

**L\'artefact doit passer le test de III.1.** Sur un artefact
exploratoire, le protocole produit une carte fictive et se paie en
défigeages en chaîne. Sondez d\'abord.

**L\'économie de doublures dépend de votre topologie.** Elle joue à
plein sur un système à logique interne dominante. Elle devient marginale
sur un service d\'intégration fait surtout de frontières externes, où
les doublures externes, payées de toute façon, dominent le budget.

**Le contrat spéculatif reste le risque propre de la méthode.**
Construire une couche avant ses consommateurs réels invite à généraliser
tant qu\'à figer. Trois remparts existent (finalisation au moment
responsable, besoin cartographié, extension additive) et le checkpoint
attrape le reste. Le risque demeure structurellement plus élevé que dans
une approche pilotée par le consommateur réel.

**Le gate a un prix qui croît.** Quadratique en nombre de couches, et le
régime à deux vitesses le contient sans le supprimer. Sur une
application entière construite en couches globales, il devient
prohibitif --- raison de plus pour passer au composite.

## III.18 Renvois croisés

Vers **II.5** quand une règle vous paraît arbitraire : l\'économie des
doublures, la localisation par delta unique et l\'argument de
non-redondance des deux niveaux de test y sont démontrés, avec leurs
domaines de validité.

Vers **II.6** si vous voulez instrumenter votre équipe : six des huit
hypothèses se lisent dans les traces que III.9 vous fait déjà produire.

Vers **II.8** pour la formulation exacte des frontières résumées en
III.17.

Vers **V.3 et V.6** dès que vous intégrez quelqu\'un : la progression en
trois temps et l\'évaluation par frontière de couche s\'appliquent
telles quelles à un onboarding technique. La conduite du changement de
III.15 vise des praticiens confirmés ; la Partie V vise ceux qui
apprennent, et les deux discours diffèrent.

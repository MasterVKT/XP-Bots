# 08 — Le gate à l'échelle, la gouvernance, les checkpoints, le parallélisme

Source : II.5 (coûts déclarés), III.8, III.9, III.10, III.11.

## Sommaire
1. Le gate à l'échelle : coût, gate unifié, tests instables
2. Adopter le gate sur une base existante : baseline à cliquet
3. Le régime à deux vitesses et sa règle constitutive
4. Proportionnalité
5. Gouvernance : trois décisions, trois circuits
6. Trois rôles, trois profils
7. Étape 8 — Les checkpoints de refactoring
8. Organiser le travail : ce qui se parallélise
9. L'anti-pattern des équipes par couches

---

## 1. Le gate à l'échelle

- **Le coût, compté d'abord.** RÉGRESSER relance à la couche `k` tout ce qui a été écrit jusque-là. Si la suite
  croît avec les couches, le volume cumulé d'exécutions est **quadratique**, de l'ordre de **N²/2 lancements
  pour N couches**. C'est le prix de la garantie : un delta unique validé sur une base entièrement verte
  (hypothèse défavorable H8, lisible dans les journaux du gate : `mcl.py rapport`).
- **Le gate unifié.** En équipe, la régression se câble en **check bloquant de la branche d'intégration**,
  unifiant les deux contrôles que le protocole rend mécaniques : **l'architecture** (carte encodée) et la
  **régression fonctionnelle**. `mcl.py gate` réalise cette unification (vérification d'architecture + commandes
  de test, un seul verdict).
- **Ennemi opérationnel : les tests instables.** Un gate bloquant exige **quarantaine** des tests instables et
  **taux sous contrôle** : précondition, pas raffinement.

## 2. Baseline à cliquet (adopter le gate sur l'existant)

Le mur de violations initial se franchit par le protocole du **cliquet** :
1. Une **baseline versionnée** capture la dette au jour J (`mcl.py baseline --creer --par <gardien> --motif …`).
2. Toute violation **nouvelle** bloque la fusion.
3. Toute violation **résolue** resserre la baseline et **ne pourra plus jamais revenir**
   (`mcl.py baseline --resserrer`, toujours permis).
4. La baseline est **protégée** : toute altération de son fichier fait échouer le build, sauf autorisation
   explicite (`mcl.py baseline --reinitialiser --par … --motif …` = clé du gardien, tracée à chaque usage).
5. Déploiement de **warn** (signaler sans bloquer) à **strict**, règle par règle.

## 3. Le régime à deux vitesses

À l'échelle, deux familles d'outils réduisent le volume :
- **sélection par analyse d'impact**, déterministe : ne joue que les tests que le diff touche ; gains maximaux
  sur code modulaire, au prix d'une maintenance des cartes de couverture ; se dégrade sur code fortement couplé ;
- **sélection prédictive**, probabiliste, apprise sur l'historique ; résiste mieux et se passe de cartes.

**Règle constitutive** : la sélection **accélère la boucle interne, elle ne remplace jamais le gate**.
- Pushes et itérations à l'intérieur d'une couche : suite sélectionnée.
- **Gate de couche et fusion sur le tronc : suite intégrale, non négociable.** Le gel ne s'accorde que sur base
  entièrement verte (prémisse de toutes les garanties).
- Une **nightly intégrale** sert de filet.
- Conséquence assumée : une régression manquée par la sélection refait surface au gate, avec un délai borné par
  la couche.

Pour l'agent : `--regression` de `mcl.py gate` doit toujours désigner la **suite intégrale** ; une commande
sélective ne peut servir qu'aux itérations internes, hors gate.

## 4. Proportionnalité

- Tâche ou composant : forme minimale (suite en local et dans une CI simple ; régime à deux vitesses inutile).
- Application : le mode composite est aussi la réponse au coût — chaque artefact de chair porte sa propre suite,
  qui retombe à l'échelle d'un composant. La forme qui rend le gate prohibitif (monolithe construit en couches
  globales) est précisément celle que III.1 déconseille.

## 5. Gouvernance : qui décide quoi

Règle générale : **le circuit suit le rayon d'impact**. La nature de l'opération dit le type de circuit ; la
carte encodée dit **qui est touché** (ses dépendances inverses listent mécaniquement les consommateurs directs
et transitifs : `mcl.py rayon --couche <id>`). Un arbitrage convoque **les touchés, pas l'organigramme**.

| Décision | Circuit |
|---|---|
| Révision d'implémentation ou extension additive | **Revue standard.** Le harnais est l'autorité réelle (suite de la couche + régression intégrale au gate) ; la décision humaine se réduit à la revue de code ordinaire |
| Modification de contrat | **Arbitrage** entre le demandeur, le propriétaire de la couche et les consommateurs que la carte liste. Décision **tracée** (enregistrement court de type ADR : quoi, pourquoi, rayon constaté — `assets/gabarits/defigeage-adr.md`). Cascade exécutée **dans l'ordre des couches**, puis re-gel. Moment naturel : le checkpoint |
| Modification de la baseline | **Clé du gardien**, chaque usage étant lui-même tracé |

Chaque défigeage laisse une trace d'une à quelques lignes (`mcl.py defiger` + fiche ADR) : mémoire de la
gouvernance et matière première de l'évaluation (extensions contre modifications contre corrections).

## 6. Trois rôles, trois profils

Rôles (des rôles, pas des postes) :
- **Gardien de la carte** : intégrité de la carte encodée et de la baseline ; détient la clé ; garde les
  artefacts de référence ; **ne décide pas des contrats**.
- **Propriétaire de couche** : répond du contrat gelé et instruit les demandes.
- **Consommateurs** : partie prenante de tout arbitrage qui les touche.

Profils :
- **Solo** : une personne porte les trois rôles. Zéro cérémonie ajoutée, seules les traces demeurent. « La
  gouvernance solo, c'est la discipline de se répondre par écrit. » (Cas de l'agent travaillant seul avec
  l'utilisateur : l'agent tient les traces ; l'utilisateur tient la clé du gardien.)
- **Petite équipe (environ 2 à 8)** : gardien = auteur de la carte ou rôle tournant ; propriétaires = auteurs des
  couches ; arbitrage = conversation avec les consommateurs listés + trace.
- **Organisation (plusieurs équipes)** : gardien = architecte référent ; propriété **matérialisée** dans le
  fichier de propriétaires de la forge (type CODEOWNERS) déclaré sur les mêmes modules que la carte (« une couche
  = un module » sert une seconde fois) ; arbitrage inter-équipes par mini-RFC avec les équipes consommatrices ;
  cascade coordonnée dans l'ordre des couches, chaque équipe re-vérifiant à son tour.

## 7. Étape 8 — Les checkpoints de refactoring

**Tous les deux à trois niveaux ajoutés**, marquer une pause : le **moment planifié** où s'exercent les deux
libertés que le gel laisse ouvertes (`mcl.py statut` signale « checkpoint dû » ; `checkpoint_tous_les` dans
`carte.json`).

1. **Révisions d'implémentation** (à contrat constant, traitées en lot) : une unité interne fait-elle plus
   d'une chose ? une unité est-elle sur-ingénierée par rapport à son usage réel ? des duplications entre couches
   devraient-elles être extraites ?
2. **Changements de contrat** : les interfaces des couches internes sont-elles toujours pertinentes, compte tenu
   de ce qu'on sait désormais du contexte extérieur ? Si une interface doit évoluer : défigeage formel
   (`--nature modification`) avec sa propagation conditionnelle. Il **s'anticipe ici au lieu de se subir**.

Puis : refactorer en lot, **relancer l'intégralité de la suite** (`mcl.py gate --global --regression …`),
poursuivre la construction. Journaliser : `mcl.py checkpoint --notes "…"`.

**Le coût, compté honnêtement.** Chaque lot de révisions paie **une régression intégrale** (« chaque jonction
testée une seule fois » vaut pour la construction nominale ; le refactoring re-paie, c'est normal). Le checkpoint
existe pour **amortir** ce prix : un lot = une seule régression, au lieu d'une par retouche dispersée. Un
changement de contrat coûte davantage (propagation), d'où le protocole formel. Justification : à la conception
initiale des couches internes, l'information sur leurs futurs consommateurs est nécessairement incomplète ; le
checkpoint corrige les effets de cette incomplétude avec le contexte réel acquis entre-temps.

## 8. Ce qui se parallélise

Entre couches dépendantes, le protocole **sérialise** structurellement (le gel de `k` précède la construction de
`k+1`). Gain parallèle borné par cette fraction sérialisée (loi d'Amdahl) : **la forme du graphe décide**. Un
graphe large parallélise ; un graphe étroit et profond est un travail pour peu de mains. Trois niveaux :

1. **Intra-couche** : les groupes 1a, 1b… sans interdépendance se construisent simultanément (développeurs,
   sessions ou sous-agents différents). Ils se lisent dans la carte encodée ; leurs contrats se finalisent
   ensemble. **Signaler explicitement cette opportunité** dans tout plan de construction : c'est de
   l'organisation gratuite qui se perd si personne ne la nomme.
2. **Tuilage de préparation** : pendant la construction de `k`, la finalisation des contrats de `k+1`
   s'instruit et se fige à l'issue de `k`. On parallélise la préparation, jamais l'anticipation.
3. **Inter-artefacts** : le vrai parallélisme d'équipe. À l'échelle d'une application, il vient des
   **artefacts** (tranches ou composants, un par équipe ou binôme), le squelette du mode composite servant de
   cadre d'intégration.

La synchronisation entre parallèles est fournie par le protocole : **une couche gelée est un point de
rendez-vous**.

## 9. L'anti-pattern : les équipes par couches

MCL ordonne la **construction** par couches ; elle n'ordonne **jamais les équipes** par couches. Une « équipe
couche données » et une « équipe couche services » recréeraient la spécialisation horizontale (silos, files
d'attente, retour tardif) et, par la loi de Conway, un système qui épouse l'organigramme. Les équipes
s'alignent sur les **flux** (Team Topologies). Les couches sont un **ordre de travail**, pas un découpage social.

---
name: xp-bots-mcl-robot-planning
description: "Planifier l'implémentation d'un robot XP-Bots (EMA_V3, LONDON_V3) ou d'un composant partagé (données et bougies, coordinateur et exécution, contrôles fondamentaux, lecteur de contexte IA, service IA, journal et rejeu) selon la méthode MCL : artefact et échelle, applicabilité, mode composite avec squelette, cartographie des unités tirées des spécifications, carte des couches, frontières externes et doublures, contrats, affectation des cas d'acceptation C11, S01.6, S02.6 et A14 aux couches, commandes de gate et dossier mcl/<artefact>/. Utiliser avant d'écrire le code d'un robot ou d'un composant. Déclencheurs : planifier l'implémentation, plan MCL, plan de construction, implémenter un robot, construire le robot, construire le moteur, architecture du robot, ordre de construction, découpage en couches."
---

# Planifier l'implémentation d'un robot XP-Bots selon MCL

Cette skill applique la méthode `mcl-matryoshka-construction-layers` au contexte XP-Bots. MCL fixe le
protocole ; cette skill fournit les artefacts, les unités candidates, les frontières et l'affectation des cas
d'acceptation propres au projet. La cartographie proposée est une **hypothèse** à confirmer unité par unité.

## Ressources

- Méthode : `.agents/skills/mcl-matryoshka-construction-layers/SKILL.md`, puis selon la phase
  `.agents/skills/mcl-matryoshka-construction-layers/references/02-applicabilite.md`,
  `.agents/skills/mcl-matryoshka-construction-layers/references/03-cartographie.md`,
  `.agents/skills/mcl-matryoshka-construction-layers/references/09-stacks-composite-positionnement.md` et
  `.agents/skills/mcl-matryoshka-construction-layers/references/13-outil-mcl-py.md`.
- Outil et gabarits : `.agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py`,
  `.agents/skills/mcl-matryoshka-construction-layers/assets/gabarits/PLAN-MCL.md`,
  `.agents/skills/mcl-matryoshka-construction-layers/assets/gabarits/carte.exemple.json`.
- Contexte XP-Bots : `references/cartographie-xp-bots.md` (artefacts, unités, frontières, cas d'acceptation).
- Ordre produit des composants : section « Ordre de construction et de qualification » de
  `docs/architecture/GUIDE_IMPLEMENTATION.md` ; contrats : les deux spécifications de `livrables/strategies_m15/`.

## Workflow

1. **Périmètre.** Nommer l'artefact demandé et son échelle. Le système complet (deux robots et services
   partagés) est une application : mode composite, squelette déployable puis un artefact MCL par composant. Un
   moteur seul est un composant. L'ordre de livraison vient du guide d'implémentation, jamais de MCL.
2. **Décisions ouvertes.** Le langage et la plateforme ne sont pas arrêtés : demander à l'humain la plateforme
   (par exemple MT5/MQL5 ou un autre runtime), le langage et le répertoire des sources avant toute écriture de
   `carte.json` ; consigner la réponse dans la section 2 du plan.
3. **Applicabilité.** Passer le test en trois questions au niveau de l'artefact : implémenter une spécification
   déterministe figée est applicable ; chercher une variante plus rentable est exploratoire et hors de ce plan.
4. **Initialiser** (mode écriture seulement) :
   `python .agents/skills/mcl-matryoshka-construction-layers/scripts/mcl.py --dossier mcl/<artefact> init --nom <artefact> --langage <langage> --echelle composant --mode pur --sources <répertoire>`
   (`--echelle application --mode composite` pour le système complet). En planification ou lecture seule,
   rendre le plan dans la réponse sans rien écrire.
5. **Cartographier.** Reprendre les unités candidates de l'artefact dans `references/cartographie-xp-bots.md`,
   les recouper avec les sections de spécification citées, poser la question-test unité par unité, puis
   renseigner `unites` et `externes` et lancer `mcl.py --dossier mcl/<artefact> analyser --ecrire`, puis
   `analyser` jusqu'à zéro divergence.
6. **Frontières et contrats.** Pour chaque frontière externe listée : port, doublure minimale, couche
   d'infrastructure réelle, test de contrat. Esquisser tous les contrats de couche
   (`mcl/<artefact>/contrats/couche-<id>.md`) ; finaliser seulement juste avant de construire chaque couche.
7. **Affecter les cas d'acceptation** de la spécification aux couches et aux catégories de tests
   (tableau de la référence) ; aucun cas ne reste sans couche.
8. **Plan de gate.** Pour chaque couche : commande catégorie 1, catégorie 2 et régression intégrale = suite
   complète du robot plus `python tools/verify_project.py`.
9. **Présenter** à l'humain, avant la couche 0 : verdict d'applicabilité, carte avec groupes parallèles,
   frontières et doublures, décisions encore ouvertes, coûts annoncés par MCL.

## Garde-fous

- Les paramètres se chargent depuis `config/` : jamais de valeur recopiée en dur ni d'intervalle à optimiser.
- Le code de `reference/` est un oracle de comparaison, pas une couche du robot ni un composant opérationnel.
- Ordre de dépendance, jamais ordre du flux : le flux de ticks n'est pas la couche 0 parce qu'il arrive en
  premier ; ses types le sont, son adaptateur réel est dans la couche d'infrastructure.
- Doublures seulement aux frontières externes (courtier, flux, calendrier, fournisseur fondamental, API LLM,
  fichiers d'IPC, horloge, stockage) ; le même moteur de décision sert au rejeu et à la plateforme (C11 point 14).
- `mcl.py` n'analyse pas les imports MQL5 : sur MT5, encoder la carte par convention de modules, revue de code
  et `mcl.py verifier` sur les langages supportés seulement ; le signaler dans le plan.
- Les deux méthodes restent deux artefacts distincts ; seul le coordinateur de compte est partagé.

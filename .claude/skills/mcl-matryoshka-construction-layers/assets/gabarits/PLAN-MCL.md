# Plan MCL — [nom de l'artefact]

> Document de travail de la méthode MCL (Matryoshka Construction Layers). Versionné avec le code,
> à côté de `carte.json` (carte des couches) et `journal.jsonl` (traces : gates, gels, défigeages,
> checkpoints, baseline). Remplir les sections dans l'ordre ; ne rien construire avant la section 7.

## 0. Périmètre de l'artefact

- **Artefact** (l'unité de travail sur laquelle le protocole s'applique) : …
- **Échelle** : tâche / tranche · composant autonome · application entière
- **Mode** : pur · composite (obligatoire comme mode de référence à l'échelle application, sauf réécriture
  à comportement constant ou spécification figée contractuellement)
- **Règle de périmètre** : ce qui doit être livré et dans quel ordre est décidé par le niveau produit
  (backlog, roadmap) : … MCL ne gouverne que la construction du code de cet artefact.

## 1. Test d'applicabilité (au niveau de l'artefact, jamais du produit)

| Question | Réponse | Justification |
|---|---|---|
| 1. La structure est-elle connaissable avant construction ? | oui / non | systèmes analogues, code existant… |
| 2. Les contrats internes sont-ils stabilisables tôt ? | oui / non | … |
| 3. Faut-il construire pour comprendre ? | non / oui | … |

- **Verdict** : applicable (3 réponses favorables) · exploratoire (au moins une défavorable → sonder d'abord :
  spike / prototype / tranche-sonde, puis reconstruire au protocole ; le prototype se jette).
- **Conditions de bénéfice dégradé** (on s'y engage en le sachant) : frontières externes dominantes ? échelle
  application sans composite ?
- **Signaux de mauvais domaine à surveiller** pendant la construction : divergences répétées entre carte
  déclarée et graphe réel ; défigeages en chaîne dès les premières couches → suspendre, sonder, re-cartographier.

## 2. Étape 1 — Comprendre la cible (seul moment outside-in du protocole)

1. Que doit faire le système à son niveau le plus haut ? …
2. Entrées et sorties attendues de l'enveloppe finale ? …
3. Contraintes (langage, framework, performance, environnement de déploiement) ? …
4. Projet neuf (greenfield) ou refactoring de code existant ? …

(Composite : point d'insertion dans le squelette = contrat d'entrée/sortie du segment à remplacer : ….)

## 3. Étape 2 — Décomposer en unités fonctionnelles

### 2.1 Entrées et sorties du cadre traité
- Entrées → objets qui reçoivent et représentent les données fournies : …
- Sorties → objets qui produisent et représentent les résultats : …

### 2.2 Workflow de résolution (le plus détaillé possible)
```
étape_a → étape_b → … → étape_n
```
- Objets et variables **intermédiaires** révélés par le flux (ni entrées ni sorties) : …

(Système non-flux, voir 2.5 : machine à états → diagramme d'états/transitions ; domaine événementiel →
événements au passé + agrégats ; grand domaine → contextes bornés, une décomposition par contexte.)

### 2.3 Liste à plat des unités candidates (exhaustivité avant précision)

| Unité | Responsabilité (une phrase) | Entrée → transformation → sortie (ou changement d'état) | Relation(s) de dépendance |
|---|---|---|---|
| … | … | … | … |

### 2.4 Ordonnancement par dépendance (jamais par position dans le flux)

Question-test posée unité par unité : **« Cette unité pourrait-elle être construite et testée même si toutes
les autres n'existaient pas encore ? »**

| Unité | Réponse | Si non : a besoin de… | Profondeur intuitionnée |
|---|---|---|---|
| … | oui (feuille) / non | … | … |

## 4. Étape 3 — Graphe de dépendances (DAG)

```
Unité A → dépend de → Unité B, Unité C
Unité C → dépend de → (rien — feuille)
```
- **Contrôle de divergence** (graphe formalisé contre ordonnancement de 2.4) : résultat de
  `mcl.py analyser` ; divergences résolues : …
- **Dépendances externes** (base de données, API tierce, paiement, système de fichiers…) : …
- **Cycles** : aucun · brisé par interface/abstraction (défaut de conception) · condensé en composante
  (noyau minimal co-construit → croissance incrémentale → doublure de sectionnement temporaire en repli).

## 5. Étape 4 — Carte des couches

| Couche | Contenu (unités) | Dépend de | Module (une couche = un module nommé) |
|---|---|---|---|
| 0 — Noyau | … | rien | … |
| 1a / 1b … | … | 0 | … |
| N — Enveloppe | point d'entrée, orchestrateur final | toutes les couches internes | … |

- **Groupes parallèles signalés** (construction simultanée possible, contrats finalisés ensemble) : …

## 6. Encodage de la carte (invariant devenu règle de build)

- Outil : ArchUnit · Konsist/detekt · Deptrac · NetArchTest · dependency-cruiser · import-linter ·
  à défaut convention de modules + `mcl.py verifier` en CI + revue de code.
- Règle : dépendances autorisées vers **n'importe quelle couche plus interne, à profondeur quelconque**
  (jamais « couche adjacente seulement »).
- Fichier de configuration : … ; mode : warn → strict, règle par règle.

## 7. Étape 5 — Contrats d'interface

- **Esquisse** (maintenant, toutes les unités : responsabilité + signature approximative) : …
- **Finalisation** : par couche, au moment de la construire, avant la moindre ligne d'implémentation ;
  un niveau d'avance sur le premier consommateur, jamais plus. Fichiers : `contrats/couche-<id>.md`.
- Exception : contrats des **frontières externes** finalisés tôt (avec tests de contrat).
- Discipline du contrat minimal : besoin cartographié seulement ; aucun paramètre spéculatif ; aucun axe de
  généricité « pour plus tard » ; aucune interface d'indirection sans deuxième cas réel.

## 8. Étape 6 — Frontières externes

| Dépendance externe | Contrat attendu | Doublure minimale | Couches qui l'utilisent (doublée) | Couche d'infrastructure (réelle) | Test de contrat |
|---|---|---|---|---|---|
| … | … | … | … | … | … |

## 9. Étape 7 — Plan de construction (une ligne par couche, ordre strict de 0 à N)

| Couche | Unités | Tests cat. 1 (contrat propre) | Tests cat. 2 (jonction, chemins représentatifs du bloc) | Commande de gate | Statut |
|---|---|---|---|---|---|
| 0 | … | … | — (rien en dessous) | … | à construire / figée |

Boucle par couche : IMPLÉMENTER → TESTER → VALIDER → INTÉGRER → TESTER L'INTÉGRATION → RÉGRESSER (suite
intégrale) → FIGER.

## 10. Étape 8 — Checkpoints de refactoring

- Prévus tous les 2 à 3 niveaux : après les couches … et …
- Questions : une unité fait-elle plus d'une chose ? sur-ingénierie ? duplications entre couches ? interfaces
  internes toujours pertinentes vu le contexte extérieur ? → révisions en lot, une régression intégrale.

## 11. Gouvernance

- Profil : solo · petite équipe (2 à 8) · organisation
- Gardien de la carte : … ; propriétaires de couche : … ; consommateurs : listés par `mcl.py rayon`.
- Circuits : révision/extension → revue standard ; modification de contrat → arbitrage tracé (ADR) +
  cascade dans l'ordre des couches ; baseline → clé du gardien, tracée.

## 12. Bilan

- Enveloppe construite : oui / non ; dernier gate global : … ; `mcl.py rapport` joint.
- Garantie donnée : le bloc {0 → N} est testé, intégré et stable. Garantie non donnée avant l'enveloppe :
  le chemin de bout en bout.

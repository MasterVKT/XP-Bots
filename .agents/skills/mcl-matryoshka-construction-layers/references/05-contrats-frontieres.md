# 05 — Contrats d'interface (étape 5) et frontières externes (étape 6)

Source : I.4, I.6, II.2 (Meyer 1986 ; Poppendieck 2003, Reinertsen 2009), II.8, III.4, III.5, III.17.

## Sommaire
1. Le contrat en deux temps : esquisse, puis finalisation
2. L'exception des frontières externes
3. Le gabarit en sept lignes
4. Pourquoi l'étape est décisive
5. La discipline du contrat minimal (YAGNI de contrat)
6. L'extension additive : sous-construire est le chemin prévu
7. Étape 6 — les quatre gestes par frontière externe
8. Fidélité des doublures externes

---

## 1. Le contrat en deux temps

Le calage de ces deux temps distingue MCL d'une simple discipline d'interface.

- **Esquisse** — à l'étape 5, **pour toutes les unités** de la carte : responsabilité + signature
  approximative. Les étapes 3 et 4 et l'encodage de la carte en ont besoin.
- **Finalisation** — **par couche, au moment de construire l'unité, avant d'en écrire la moindre ligne
  d'implémentation**. **Un niveau d'avance sur son premier consommateur, jamais plus.** Chaque report jusqu'à
  cet instant accumule de l'information réelle (les couches inférieures existent, leurs contrats sont
  exercés). Le report est **borné des deux côtés** : l'esquisse est due maintenant, la finalisation au début
  de la couche. (Ancrage : *Last / Most Responsible Moment*.)
- Tuilage autorisé : pendant la construction de la couche `k`, la finalisation des contrats de `k+1`
  **s'instruit**, et **se fige à l'issue de `k`**. On parallélise la préparation, jamais l'anticipation.

## 2. L'exception des frontières externes

Les contrats des **frontières externes se finalisent tôt**, puisque les doublures de l'étape 6 en dépendent.
C'est le cas où l'anticipation se défend, avec les **tests de contrat** en garde-fou.

## 3. Le gabarit en sept lignes

```
Unité : [nom]
Responsabilité : [une phrase]
Signature : [interface de fonction, méthode ou classe]
Entrée : [type, contraintes, exemples]
Sortie : [type, garanties, exemples]
Effets de bord : [aucun / liste]
Erreurs, exceptions : [conditions de déclenchement]
```

Fichier de travail : `assets/gabarits/contrat-couche.md` (copié dans `mcl/contrats/` par `mcl.py init`). Un
fichier par couche (`mcl/contrats/couche-<id>.md`) regroupant les gabarits de ses unités. Traduire aussi le
contrat dans le langage cible : types, signatures, interfaces/protocoles/traits, docstrings, assertions de
préconditions et postconditions quand le langage le permet (Design by Contract).

Le contrat **gelé** comprend : l'interface, les comportements documentés, et la **suite de tests de la couche
comme spécification exécutable**. Déclarer ces fichiers dans le champ `contrats` de la couche (`carte.json`),
motifs glob acceptés, pour que `mcl.py figer` en prenne l'empreinte et que `mcl.py verifier` détecte toute
modification sans défigeage.

## 4. Pourquoi l'étape est décisive

Un contrat rédigé avant l'implémentation empêche les couches internes d'être optimisées **pour elles-mêmes**
plutôt que pour ce qui va effectivement les consommer. C'est le **point de négociation** entre la couche
interne et la couche externe qui l'utilisera.

## 5. La discipline du contrat minimal

Le contrat couvre le **besoin cartographié** — ce que les consommateurs présents sur la carte requièrent — et
rien de plus :
- **pas de paramètre spéculatif** ;
- **pas d'axe de généricité « pour plus tard »** ;
- **pas d'interface d'indirection sans deuxième cas réel**.

Distinction qui compte : le YAGNI d'*implémentation* produit du code mort, facile à supprimer ; le **YAGNI de
contrat** fige de la généricité fictive dans ce que le protocole a précisément pour vocation de geler. C'est
celui-là qu'on s'interdit. La frontière d'une unité **cache une décision** ; elle n'expose pas des possibles.

Pour l'agent : avant de finaliser un contrat, vérifier chaque élément de signature contre un consommateur réel
de la carte ; supprimer tout ce qu'aucun consommateur listé n'utilise.

## 6. L'extension additive

Sous-construire n'est pas un échec : c'est le **chemin prévu**. Ajouter à un contrat une méthode, ou un
paramètre optionnel à **valeur par défaut conservatrice**, reste compatible pour tous les appelants. Le
défigeage formel s'applique (`mcl.py defiger --nature extension`), mais sa propagation est quasi nulle.
**Étroit d'abord, étendre sur demande réelle** : l'extension coûte une révision ; la généricité morte coûte sa
construction, sa maintenance, et la mauvaise abstraction qui s'incruste. Hypothèse H5 : les extensions
additives doivent dominer largement les modifications dans l'historique des défigeages.

## 7. Étape 6 — Les frontières externes

Pour chaque dépendance externe identifiée à l'étape 3, quatre gestes :
1. Rédiger le **contrat d'interface attendu** de cette dépendance (côté système : un port, une interface).
2. Créer une **doublure minimale** respectant ce contrat.
3. L'utiliser dans **toutes les couches internes** concernées.
4. La remplacer par l'implémentation réelle **uniquement dans la couche d'infrastructure, la plus externe**.

Objectif : garder toute la logique interne **pure, rapide à tester, indépendante** de la disponibilité ou de la
lenteur d'une infrastructure réelle. Encoder la règle : déclarer la frontière dans `externes` de `carte.json`
(`imports` = bibliothèques ou modules de l'implémentation réelle, `couches_autorisees` = couche
d'infrastructure) pour que `mcl.py verifier` et les exports bloquent toute importation ailleurs.

## 8. Fidélité des doublures externes

**Condition.** Chaque doublure externe reproduit un contrat **qui ne vous appartient pas**. Sa fidélité
(schémas, cas d'erreur, formats réels) est un risque du même type que celui de tout stub, et elle **se dégrade
avec le temps**. Vérifier périodiquement les doublures externes contre le contrat réel ; les **tests de
contrat** sont la parade usuelle (par exemple une même suite exécutée contre la doublure et, en couche
d'infrastructure ou en nightly, contre l'implémentation réelle). Plus les frontières sont nombreuses, plus ce
point compte : c'est là que se concentre **l'intégralité du budget de doublures**.

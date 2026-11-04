# 06 — La boucle de construction (étape 7)

Source : I.7, II.5, III.6. Pour chaque couche, **dans l'ordre strict de 0 à N**, la même boucle.

## Sommaire
1. La boucle en sept sous-étapes
2. Exactement deux catégories de tests
3. Catégorie 1 : sociable par défaut, solitaire en option justifiée
4. Catégorie 2 : la jonction sur le bloc réel
5. Ce que la méthode ne fait pas : la sur-isolation
6. Le calendrier des tests couche par couche
7. Ce que le gel gèle, ce qu'il laisse libre
8. Loi de Hyrum
9. Exécution par l'agent : règles opératoires

---

## 1. La boucle en sept sous-étapes

| N° | Sous-étape | Sortie attendue |
|---|---|---|
| 1 | **IMPLÉMENTER** | Construire les unités de la couche (contrat finalisé au préalable) |
| 2 | **TESTER** | Tests unitaires de la couche (externe doublé ; dépendances internes réelles et figées par défaut, doublées seulement en option justifiée) |
| 3 | **VALIDER** | Tous verts ? → continuer. Échec → corriger d'abord |
| 4 | **INTÉGRER** | Brancher la couche sur le bloc réel `{0 → k}`, sans doublure interne |
| 5 | **TESTER L'INTÉGRATION** | Tests de la jonction, sur le bloc réel |
| 6 | **RÉGRESSER** | Relancer **l'intégralité** de la suite existante (*regression gate*, non négociable) |
| 7 | **FIGER** | Le contrat de la couche est gelé → couche suivante |

Équivalent outillé : `mcl.py gate --couche <id> --unitaire "<cmd cat.1>" --integration "<cmd cat.2>"
--regression "<cmd suite intégrale>"` puis `mcl.py figer --couche <id>`.

## 2. Exactement deux catégories de tests

Pas un continuum de combinaisons partielles. Ce qui les distingue est leur **cible**, non leur outillage (MCL
n'a donc pas besoin de trancher le débat sur les définitions de « unitaire » et « intégration »).

- **Catégorie 1** — cible : le **contrat propre** de la couche (entrées, sorties, cas d'erreur, de façon fine).
- **Catégorie 2** — cible : la **jonction** (la couche `k+1` branchée sur l'ensemble réel `{0 → k}`).

## 3. Catégorie 1 : le test unitaire de la couche

La nouvelle couche respecte-t-elle **son propre contrat** ? Ses dépendances **externes sont toujours doublées**.
Pour ses dépendances internes, deux régimes :

- **Par défaut : les couches réelles figées** (test **sociable**, école classiciste dont MCL se réclame). Ces
  couches sont construites, validées, gelées : les utiliser ne coûte aucune doublure, ne pose aucun problème
  de fidélité, et reste rapide puisqu'elles sont pures (l'externe est doublé depuis l'étape 6). La
  construction par couches figées rend les collaborateurs réels disponibles au moment précis où on en a besoin.
- **En option justifiée : la doublure interne** (test **solitaire**), seulement quand une couche réelle est
  devenue lente, quand on veut isoler un diagnostic, ou quand on veut spécifier le comportement de la couche
  courante face à des réponses internes difficiles à provoquer. Choix de commodité ; risque de fidélité
  **réduit, non nul** (la doublure peut être dérivée de la couche cible et vérifiée contre elle ; une doublure
  interne qui dérive de la couche réelle ment exactement comme un stub trop simplifié).

Dans les deux régimes, les seules doublures **structurellement obligatoires** sur toute la construction
restent celles des dépendances **externes**.

## 4. Catégorie 2 : le test d'intégration sur le bloc réel

La couche est branchée **directement sur l'ensemble réel déjà construit, sans doublure interne**. Cible : la
jonction — l'interaction entre la nouvelle couche et le système existant fonctionne-t-elle comme prévu ? Le
bloc étant réel, chaque test traverse toute sa profondeur : choisir des scénarios qui parcourent des **chemins
représentatifs de cette profondeur**, pas seulement l'interface immédiate entre les deux couches du dessus.
« Représentatif » qualifie le choix des scénarios ; il **n'exige pas une couverture exhaustive** du bloc.

La couche 0 n'a pas de catégorie 2 (rien en dessous) : son gate se réduit à la catégorie 1 + régression.

## 5. Ce que la méthode ne fait pas

Elle ne teste **pas** successivement `{k+1}`, puis `{k+1 + k}`, puis `{k+1 + k + k−1}` comme autant de
sous-ensembles isolés. Cette **sur-isolation** :
- multiplierait les configurations (`k` configurations à la couche `k`, croissance quadratique du total) ;
- surtout, testerait des **sous-systèmes fictifs** : isoler trois couches du reste exigerait de re-doubler la
  quatrième, donc de recréer une frontière qui n'existe pas dans le système réel.

Deux niveaux suffisent parce que `{0 → k}` est **un seul système intégré et validé** : chaque jonction interne
a été testée **au moment de sa création**, puis est **re-traversée par chaque test de catégorie 2 ultérieur**.
La couverture des jonctions **s'accumule**. L'argument est auto-porté : le protocole garantit lui-même ses deux
préconditions (gel des couches inférieures ; régression intégrale à chaque couche).

## 6. Le calendrier des tests

```
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
```

(Le schéma est celui du document. Lecture cohérente avec I.7 et III.6, qui fixent le régime par défaut :
« isolation » désigne la **cible** du test — le contrat propre de la couche — et non l'obligation de doubler
les couches inférieures, qui restent réelles et figées par défaut ; la doublure interne n'est qu'une option
justifiée, section 3.) À chaque niveau : un test unitaire ciblé, un test
d'intégration sur le bloc réel, une régression globale. Jamais une cascade de tranches partielles.

## 7. Ce que le gel gèle, ce qu'il laisse libre

FIGER gèle le **contrat public** : interface, comportements documentés, suite de tests comme spécification
exécutable. C'est ce que les consommateurs ont le droit de tenir pour acquis. L'**implémentation interne**
reste révisable, **à comportement constant et sous harnais complet** : rien ne change sans que la suite de la
couche et la régression intégrale repassent au vert immédiatement.

| Opération | Régime |
|---|---|
| Réviser l'implémentation (contrat constant) | Libre sous harnais ; de préférence regroupée aux checkpoints pour amortir le coût |
| Changer le contrat | Défigeage formel, propagation conditionnelle ; la propagation coûte des couches, donc elle s'anticipe |
| Corriger un défaut | Défigeage formel aussi ; la confiance dans la couche est entamée ; un test capturant le cas s'ajoute à sa suite |

## 8. Loi de Hyrum

« Comportement constant » s'entend au sens du **contrat documenté et de la suite de tests**. Des observables
non documentés (ordre d'itération, format de messages) peuvent changer, et des consommateurs peuvent en
dépendre par accident. Deux règles : **les consommateurs ne codent que contre le contrat documenté** ; toute
casse de ce type découverte **tranche le comportement et enrichit la suite**.

## 9. Exécution par l'agent : règles opératoires

1. Ne jamais écrire le code d'une couche avant que **toutes** les couches dont elle dépend soient figées
   (vérifier avec `mcl.py statut` : colonne « constructible maintenant »).
2. Les couches parallèles d'une même profondeur peuvent être écrites dans la même passe ; chacune passe son
   propre gate et son propre gel.
3. Finaliser le contrat de la couche (fichier `mcl/contrats/couche-<id>.md` + types/interfaces) **avant**
   l'implémentation ; écrire les tests de catégorie 1 contre ce contrat.
4. **Exécuter réellement** les commandes de test à chaque couche. Ne jamais déclarer un gate vert sans
   l'avoir exécuté ; si l'environnement ne permet pas l'exécution, le dire et laisser la couche « non figée ».
5. Un seul delta par gate : ne pas mélanger dans un même gate la construction d'une couche et des révisions
   d'autres couches (la localisation mécanique en dépend).
6. Après le gel, ne plus toucher au contrat ni aux tests de la couche sans `mcl.py defiger`.
7. Rapporter à l'utilisateur, couche par couche : unités construites, contrat finalisé, nombre de tests par
   catégorie, résultat de la régression intégrale, statut (figée).

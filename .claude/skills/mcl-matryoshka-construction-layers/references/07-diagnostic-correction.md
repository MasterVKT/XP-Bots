# 07 — Quand ça casse : diagnostic et correction

Source : I.7, II.2 (Zeller 1999), II.5, III.7. Le *regression gate* est non négociable : **procéder à la couche
suivante avec un test en échec est la source principale des bugs d'intégration difficiles à diagnostiquer.**

## Sommaire
1. La propriété achetée par le gate : un delta unique sur une base verte
2. L'aiguillage, mécanique
3. La limite épistémique du gel
4. La remontée de couches (séquentielle, dichotomie)
5. Le protocole correctif en quatre points
6. Coût : sondes contre couches
7. Déroulé outillé

---

## 1. Un delta unique sur une base entièrement verte

Un échec au gate se produit face à un **delta unique appliqué à une base entièrement verte**. Le déclencheur est
donc **mécaniquement localisé** : c'est la couche qu'on vient d'ajouter. Deux cas :
- défaut **dans cette couche** : la cause coïncide avec le déclencheur, la chasse au bug n'a pas lieu ;
- **défaut latent d'une couche plus basse**, révélé par un usage inédit : la cause est ailleurs ; la chasse
  n'est pas supprimée, elle est **bornée par construction**.

*Ancrage* : delta debugging (Zeller, 1999), héritiers `git bisect` & co. *Apport* : la précondition du delta
debugging (petit delta, base verte), que la pratique courante ne réunit qu'accidentellement, devient
**permanente par construction**.

## 2. L'aiguillage, mécanique

Signal d'aiguillage : le **test unitaire (catégorie 1) de la couche courante**.

- Catégorie 1 de la couche courante **en échec** → **régression locale**. Corriger la couche courante. La
  cause coïncide avec le déclencheur.
- Catégorie 1 **verte** mais intégration ou régression **en échec** → la cause est dans l'**interaction, ou
  plus bas**. Ouvrir le diagnostic par **remontée de couches**.

`mcl.py gate` applique cet aiguillage automatiquement si `--unitaire` est fourni (champ `aiguillage` du
journal : `regression_locale` ou `interaction_ou_amont`).

## 3. La limite épistémique du gel

Une couche gelée est **validée par sa suite de tests, non prouvée correcte** (un test montre la présence de
défauts, jamais leur absence). Un usage nouveau peut exercer un chemin que la suite ne couvrait pas. Les
**défauts amont existent** ; le protocole les traite au lieu de prétendre les avoir supprimés.

## 4. La remontée de couches

La granularité par tranches, écartée comme protocole systématique, **redevient pertinente en mode diagnostic
réactif**. Isoler le niveau fautif en testant des tranches munies d'une **doublure de coupe** temporaire
(doublure qui remplace la partie du bloc située sous le point de coupe).

- **Remontée séquentielle** : descendre couche par couche jusqu'à ce que la tranche casse. Simple, jusqu'à
  **N sondes**.
- **Dichotomie** : couper au milieu de la pile et resserrer par moitiés, à la manière d'un `bisect` appliqué
  aux couches. De l'ordre de **log N sondes**.

Ces sondes testent des sous-systèmes fictifs, **et c'est assumé** : ce sont des **instruments de diagnostic
jetables**. Les doublures de coupe **se suppriment sitôt le niveau localisé**. Ce coût ne se paie que lorsqu'un
échec l'exige. Pour l'agent : écrire les sondes dans un emplacement temporaire clairement marqué (par exemple
`tests/_diagnostic/`), hors des fichiers de contrat, et les supprimer avant le gate suivant.

## 5. Le protocole correctif

Localiser le niveau fautif (couche `k`) n'est que la moitié du travail.

1. **Défiger** la couche `k` (`mcl.py defiger --couche k --nature correction --motif "…"`) et corriger, **en
   ajoutant à sa suite un test qui capture le cas révélé**.
2. Si la correction ne touche que l'**implémentation interne** (contrat inchangé) : revalider `k`, re-figer,
   relancer la régression globale. **La propagation s'arrête là.**
3. Si la correction **modifie le contrat** de `k` : la vérification se propage. Chaque couche consommatrice
   est re-vérifiée contre le nouveau contrat, et défigée à son tour si elle doit s'adapter (déclarer alors la
   nature `modification`, arbitrage et trace : `08-gate-gouvernance-parallelisme.md`). Le **contrat est
   l'arbitre** de la frontière entre les deux cas.
4. Dans tous les cas, **corriger à la source, jamais au symptôme**. Compenser le défaut de `k` par un
   contournement dans une couche supérieure masque le défaut, installe une divergence entre le contrat et le
   comportement réel, et lègue les deux à toutes les couches futures.

## 6. Coût : sondes contre couches

La **remontée ne coûte que des sondes** ; la **propagation coûte des couches**. C'est le vrai coût des défauts
amont, et la raison pour laquelle il figure dans les hypothèses réfutables (H2 : de l'ordre de log N sondes ;
propagation nulle si le contrat reste inchangé).

## 7. Déroulé outillé

```
mcl.py gate --couche 2 --unitaire "<cat.1 de 2>" --integration "<cat.2 de 2>" --regression "<suite>"
   → ROUGE, aiguillage interaction_ou_amont
(sondes jetables : remontée séquentielle ou dichotomie → niveau fautif = 1a)
mcl.py defiger --couche 1a --nature correction --motif "cas X révélé par l'intégration de 2"
(test capturant le cas ajouté à la suite de 1a ; correction à la source)
mcl.py gate --couche 1a --unitaire "<cat.1 de 1a>" --regression "<suite>"   → VERT
mcl.py figer --couche 1a
mcl.py gate --couche 2 … → VERT ; mcl.py figer --couche 2
```
Pendant que `1a` est défigée, `mcl.py gate --couche 2` est refusé (invariant) : c'est voulu.

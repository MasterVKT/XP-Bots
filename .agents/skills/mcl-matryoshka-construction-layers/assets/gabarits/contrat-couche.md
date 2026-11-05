# Contrat de la couche [id] — [nom]

> Rédigé en deux temps (étape 5). **Esquisse** pendant la cartographie : responsabilité + signature
> approximative. **Finalisation** au moment de construire la couche, avant toute implémentation, un niveau
> d'avance sur son premier consommateur, jamais plus. Une fois la couche validée, ce fichier est **figé**
> (`mcl.py figer`) : il ne change plus sans défigeage formel tracé (`mcl.py defiger`).
>
> Discipline du contrat minimal : couvrir le besoin **cartographié** (ce que les consommateurs présents sur
> la carte requièrent) et rien de plus. Pas de paramètre spéculatif, pas d'axe de généricité « pour plus
> tard », pas d'interface d'indirection sans deuxième cas réel. Étroit d'abord, étendre sur demande réelle
> (extension additive : nouvelle méthode, ou paramètre optionnel à valeur par défaut conservatrice).

- **Statut** : esquisse / finalisé / figé (date, gate de référence)
- **Consommateurs cartographiés** : couches … (unités …)
- **Dépend de** : couches … (réelles et figées) ; frontières externes … (doublées)

---

Unité : [nom]
Responsabilité : [une phrase]
Signature : [interface de fonction, méthode ou classe]
Entrée : [type, contraintes, exemples]
Sortie : [type, garanties, exemples]
Effets de bord : [aucun / liste]
Erreurs, exceptions : [conditions de déclenchement]

---

Unité : [nom]
Responsabilité : [une phrase]
Signature : […]
Entrée : […]
Sortie : […]
Effets de bord : […]
Erreurs, exceptions : […]

---

## Spécification exécutable

Le contrat public gelé comprend aussi la suite de tests de la couche (spécification exécutable) :
`[chemin des tests de catégorie 1]` et `[chemin des tests de catégorie 2]`.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Observables non documentés (ordre d'itération,
format exact des messages…) : non garantis. Toute casse découverte de ce type tranche le comportement et
enrichit la suite.

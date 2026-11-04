# Défigeage [AAAA-MM-JJ] — couche [id] — [extension | modification | correction]

> Trace courte de type ADR (Architecture Decision Record). Une à quelques lignes suffisent. C'est la mémoire
> de la gouvernance et la matière première de l'évaluation (extensions contre modifications contre
> corrections). Doubler cette fiche de l'entrée `mcl.py defiger` au journal.

- **Quoi** : [contrat ou défaut concerné, unité(s)]
- **Pourquoi** : [besoin réel apparu / défaut amont révélé par un usage inédit / …]
- **Nature et circuit** :
  - extension additive ou révision d'implémentation → revue standard (le harnais fait autorité) ;
  - modification de contrat → arbitrage entre demandeur, propriétaire de la couche et consommateurs listés ;
  - correction de défaut → test capturant le cas ajouté à la suite de la couche, correction à la source.
- **Rayon constaté** (dépendances inverses de la carte, `mcl.py rayon --couche [id]`) :
  directs [..] ; transitifs [..]
- **Participants** : demandeur [..], propriétaire [..], consommateurs [..]
- **Décision** : [..]
- **Cascade** (modification seulement, dans l'ordre des couches) : [couche → re-vérifiée / défigée / re-figée]
- **Clôture** : couche re-figée le [..] après gate vert ; régression globale verte le [..].

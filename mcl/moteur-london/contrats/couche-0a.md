# Contrat de la couche 0a — parametres_london

- **Statut** : finalisé le 06/11/2026, avant implémentation ; gel après gate vert. Corrigé le 06/11/2026 par défigeage `correction` : fins LF pour la conservation des empreintes après normalisation Git.
- **Consommateurs cartographiés** : couches 1a, 1b, 1c, 1d, 1e et 2.
- **Dépend de** : aucune couche de cet artefact.

Unité : parametres_london
Responsabilité : Valider et typer le bloc London.
Signature : `charger_parametres_london(technique: ExportTechnique) -> ParametresLondon` ;
`ParametresLondon` (dataclass immuable : chaque clé du bloc London, plus `commun: ParametresCommuns`) ;
`CLES_LONDON` ; `ErreurParametresLondon(ValueError)`.
Entrée : export technique analysé par le noyau. Toutes les clés London sont obligatoires, aucune autre admise.
Sortie : heures en `datetime.time`, nombres finis positifs (buffers pouvant être nuls), fractions corps et
clôture dans ]0, 1], entiers positifs sans booléen, identifiant déclaré dans les priorités communes. Les trois
options désactivées doivent être exactement `False`. Le nombre de M15 du range égale sa durée divisée par
`timeframe_seconds` ; bornes du range et gel alignés sur leurs unités ; début de séance < fin des entrées ≤
sortie forcée ; début du range < fin du range ≤ début de séance ; minimum de largeur ≤ maximum ; quota de sens
≤ quota total. Aucun seuil métier n'est recopié.
Effets de bord : aucun.
Erreurs, exceptions : `ErreurParametresLondon` pour toute entrée mal typée, non finie, incomplète ou incohérente.

## Spécification exécutable

`tests/robot/moteur_london/test_cat1_c0a_parametres_london.py` ; pas de catégorie 2 à cette profondeur.

## Comportements documentés (loi de Hyrum)

Les noms des champs sont ceux de l'export ; `commun` est le bloc typé du noyau, conservé sans copie.
Le texte des erreurs n'est pas garanti. La construction directe est validée comme le chargement.

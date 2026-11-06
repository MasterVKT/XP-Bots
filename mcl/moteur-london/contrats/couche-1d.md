# Contrat de la couche 1d — stop_local

- **Statut** : finalisé le 06/11/2026, avant implémentation ; gel après gate vert. Corrigé le 06/11/2026 par défigeage `correction` : fins LF pour la conservation des empreintes après normalisation Git.
- **Consommateurs cartographiés** : couche 2, moteur London.
- **Dépend de** : couches 0a et 0b réelles et figées ; noyau et données réels ; aucune frontière externe.

Unité : stop_local
Responsabilité : celle du document 02, §6.3, sans ajout de règle métier.
Signature : `calculer_stop(bougie: BougieEnrichie, range_: RangeLondon, sens: Sens, tick_size: Decimal, parametres: ParametresLondon) -> StopLocal | RefusLondon`.
Entrée : paramètres London typés, valeurs du noyau et bougies enrichies réelles, selon la signature.
Sortie : valeur validée ou refus fermé conforme au document 01, §9.3.
Effets de bord : aucun accès externe ; seule la classe de quotas conserve son état interne.
Erreurs, exceptions : `ErreurLondon` pour les violations décrites ci-dessous.

La bougie M15 doit être valide, avec A > 0, et son jour doit être celui du range. Guard = max(tick_size,
structural_buffer_atr × A). À l'achat, les trois composantes sont bas − guard, haut_range − boundary_stop_inside_atr × A,
clôture − minimum_chart_stop_atr × A ; le niveau est leur minimum. À la vente, les trois expressions sont
haut + guard, bas_range + boundary_stop_inside_atr × A, clôture + minimum_chart_stop_atr × A ; le niveau est leur
maximum. Distance = signe × (clôture − niveau). Une distance non positive ou au-delà de maximum_chart_stop_atr × A
donne STOP_TOO_WIDE, sans plafonnement. La borne maximale est incluse. Le multiple d'objectif vient de
l'export. Les composantes et toutes les égalités contraignantes sont exposées, dans l'ordre BOUGIE, FRONTIERE,
PLANCHER_ATR. Mauvais types, données manquantes, non finies, taille de tick ou sens incorrects lèvent ErreurLondon.

## Spécification exécutable

`tests/robot/moteur_london/test_cat1_c1d_stop_local.py` et
`tests/robot/moteur_london/test_cat2_c1d_stop_local.py`.

## Comportements documentés (loi de Hyrum)

Les comparaisons n'ajoutent aucune tolérance ; les tests aux bornes utilisent des valeurs dyadiques.
Le texte exact des erreurs n'est pas garanti. Les refus rendent les codes et détails du noyau, sans nouveau code.

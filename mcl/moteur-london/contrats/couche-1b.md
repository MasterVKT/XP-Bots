# Contrat de la couche 1b — gel_atr_h1

- **Statut** : finalisé le 06/11/2026, avant implémentation ; gel après gate vert. Corrigé le 06/11/2026 par défigeage `correction` : fins LF pour la conservation des empreintes après normalisation Git.
- **Consommateurs cartographiés** : couche 2, moteur London.
- **Dépend de** : couches 0a et 0b réelles et figées ; noyau et données réels ; aucune frontière externe.

Unité : gel_atr_h1
Responsabilité : celle du document 02, §6.3, sans ajout de règle métier.
Signature : `construire_gel(jour: date, bougies: Iterable[BougieEnrichie], parametres: ParametresLondon) -> GelATRH1 | None`.
Entrée : paramètres London typés, valeurs du noyau et bougies enrichies réelles, selon la signature.
Sortie : valeur validée ou refus fermé conforme au document 01, §9.3.
Effets de bord : aucun accès externe ; seule la classe de quotas conserve son état interne.
Erreurs, exceptions : `ErreurLondon` pour les violations décrites ci-dessous.

Cette fonction pure choisit la dernière H1 valide de fin ≤ F, F étant l'instant local configuré du gel.
Son âge F − fin doit être ≤ h1_seconds, borne comprise. Son rang doit être ≥ warmup_closed_h1_bars − 1 et son
ATR strictement positif. Une H1 invalide est exclue ; une H1 valide trop récente mais insuffisamment
initialisée ou non positive ne permet pas de revenir artificiellement à une autre. La disponibilité réelle
de la candidate est conservée, même tardive. L'appelant ne lance le gel qu'une fois F atteint et conserve la
première version valide, sans correction ultérieure (P-09). H1 après F exclue ; mauvais type, unité, durée ou
mélange de symboles lève ErreurLondon. None signifie absence de candidate admissible.

## Spécification exécutable

`tests/robot/moteur_london/test_cat1_c1b_gel_atr_h1.py` et
`tests/robot/moteur_london/test_cat2_c1b_gel_atr_h1.py`.

## Comportements documentés (loi de Hyrum)

Les comparaisons n'ajoutent aucune tolérance ; les tests aux bornes utilisent des valeurs dyadiques.
Le texte exact des erreurs n'est pas garanti. Les refus rendent les codes et détails du noyau, sans nouveau code.

# Contrat de la couche 1c — bougie_cassure

- **Statut** : finalisé le 06/11/2026, avant implémentation ; gel après gate vert. Corrigé le 06/11/2026 par défigeage `correction` : fins LF pour la conservation des empreintes après normalisation Git.
- **Consommateurs cartographiés** : couche 2, moteur London.
- **Dépend de** : couches 0a et 0b réelles et figées ; noyau et données réels ; aucune frontière externe.

Unité : bougie_cassure
Responsabilité : celle du document 02, §6.3, sans ajout de règle métier.
Signature : `evaluer_cassure(bougie: BougieEnrichie, range_: RangeLondon, tick_size: Decimal, parametres: ParametresLondon) -> Cassure | RefusLondon`.
Entrée : paramètres London typés, valeurs du noyau et bougies enrichies réelles, selon la signature.
Sortie : valeur validée ou refus fermé conforme au document 01, §9.3.
Effets de bord : aucun accès externe ; seule la classe de quotas conserve son état interne.
Erreurs, exceptions : `ErreurLondon` pour les violations décrites ci-dessous.

La bougie valide M15 fournit A et TR. A absent donne WARMUP/ATR_M15_INDISPONIBLE ; A non positif donne
NO_SETUP/ATR_NON_POSITIF. Une bougie invalide donne NO_SETUP/PAS_DE_CASSURE. Puis R > 0, TR ≤ plafond × A et
corps/R ≥ minimum sont exigés dans cet ordre. Les détails sont BOUGIE_PLATE, TR_EXCESSIF, CORPS_INSUFFISANT.
Buffer = max(tick_size, breakout_buffer_atr × A). Achat : clôture > haut du range + buffer et clôture > ouverture ;
vente symétrique. Aucun croisement de la clôture précédente n'est demandé. La fraction de clôture dans le sens
retenu doit être ≥ signal_close_location_min. Un échec donne PAS_DE_CASSURE ou CLOTURE_ELOIGNEE. Les mesures
rendues sont la fraction de corps, la fraction de clôture directionnelle et le buffer. Jour du range et jour
de bougie doivent coïncider ; taille de tick, types et durée incorrects lèvent ErreurLondon.

## Spécification exécutable

`tests/robot/moteur_london/test_cat1_c1c_bougie_cassure.py` et
`tests/robot/moteur_london/test_cat2_c1c_bougie_cassure.py`.

## Comportements documentés (loi de Hyrum)

Les comparaisons n'ajoutent aucune tolérance ; les tests aux bornes utilisent des valeurs dyadiques.
Le texte exact des erreurs n'est pas garanti. Les refus rendent les codes et détails du noyau, sans nouveau code.

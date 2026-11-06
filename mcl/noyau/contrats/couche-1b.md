# Contrat de la couche 1b — instrument

- **Statut** : finalisé le 05/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : couche 2 (`journal` : courtier, contrat) ; plus tard
  `execution-coordinateur` (dimensionnement, frais, marge, garde de fermeture native), `infrastructure` (lecture
  C04 par `mt5_specifications`) et `points-entree` (qualification, règle de liaison)
- **Dépend de** : couches 0a (`instant`), 0b (`nombres`) et 0c (`configuration`), réelles et figées ; aucune
  frontière externe

---

Unité : instrument
Responsabilité : Représenter et valider les profils d'instrument et de compte de C04, sans champ manquant valant zéro.
Signature : `Intervalle(debut_ms, fin_ms)` ; `HorairesCotation(seances, fermetures, debut_validite_ms, fin_validite_ms)`
avec `ouvert_a(instant_ms) -> bool` et `prochaine_fermeture_apres(instant_ms) -> int | None` ;
`ProfilInstrument` ; `ProfilCompte` ; `ResultatProfil(profil, non_prets)` ;
`construire_profil_instrument(champs: Mapping[str, object], commun: ParametresCommuns) -> ResultatProfil` ;
`construire_profil_compte(champs: Mapping[str, object], commun: ParametresCommuns) -> ResultatProfil` ;
`CHAMPS_INSTRUMENT`, `CHAMPS_COMPTE` (noms des champs, dans l'ordre) ; `ErreurInstrument(ValueError)`.
Entrée : champs lus du courtier, par nom. Instrument : `symbole`, `symbole_courtier`, `sous_jacent`,
`devise_base`, `devise_cotation`, `devise_marge`, `mode_calcul`, `taille_contrat`, `tick_size`, `point`, `digits`,
`valeur_tick`, `volume_min`, `volume_max`, `volume_pas`, `volume_limite` (0 : pas de limite agrégée, selon la
convention du courtier), `distance_stops_min_points`, `niveau_gel_points`, `mode_negociation`, `mode_execution`,
`modes_remplissage`, `protections_a_l_entree`, `convention_declenchement_verifiee`,
`commission_par_lot_par_cote`, `commission_minimum_par_ordre`, `commission_nulle_confirmee`, `devise_frais`,
`swap_achat`, `swap_vente`, `marge_initiale`, `marge_maintenance`, `horaires` (`HorairesCotation`),
`releve_ms`. Compte : `entite`, `serveur`, `plateforme`, `type_compte`, `devise`, `levier`, `mode_marge`,
`mode_stop_out`, `niveau_appel_marge`, `niveau_stop_out`, `releve_ms`. Montants et tailles : nombres convertis
par 0b ; intervalles : instants entiers UTC `[debut, fin)`.
Sortie : `ResultatProfil` dont `profil` n'existe que si `non_prets` est vide ; `non_prets` liste, dans l'ordre
des champs, chaque champ absent, `None`, de mauvais type ou hors bornes (détail de `ENVIRONMENT_NOT_READY`,
C04). Contrôles croisés : symbole hors de `universe_priority` → `symbole` ; commission et minimum nuls sans
confirmation → `commission_par_lot_par_cote` ; `volume_max < volume_min` → `volume_max` ; devise du compte
différente de `account_currency` → `devise` ; levier différent de `account_leverage` → `levier`. Horaires :
séances moins fermetures exceptionnelles, sur la période de validité ; `ouvert_a` dit si l'instant est dans une
séance effective ; `prochaine_fermeture_apres` rend la fin de la séance effective en cours, ou `None` si le
marché est fermé à cet instant.
Effets de bord : aucun.
Erreurs, exceptions : `ErreurInstrument` pour un champ inconnu dans `champs`, des intervalles vides,
chevauchants ou non triés, une question posée hors de la période de validité, une fermeture dont l'heure n'est
pas connue (séance effective atteignant la fin de validité).

---

## Spécification exécutable

`tests/robot/noyau/test_cat1_c1b_instrument.py` et `tests/robot/noyau/test_cat2_c1b_instrument.py`.

## Comportements documentés (loi de Hyrum)

`modes_remplissage` est un `frozenset` de textes ; les décimaux gardent la représentation décimale la plus courte
des flottants lus. Le texte des messages d'erreur n'est pas garanti.

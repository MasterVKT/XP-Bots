# Contrat de la couche 1c — couverture_flux

- **Statut** : finalisé le 06/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : couches 2a (`validation_bougies`) et 3 (`flux_bougies`)
- **Dépend de** : couche 0a (réelle et figée) ; noyau figé (`c1b_instrument` : `Intervalle`, `HorairesCotation`) ;
  aucune frontière externe

---

Unité : couverture_flux
Responsabilité : Classer un intervalle en couvert, fermeture officielle ou trou.
Signature : `parties_ouvertes(horaires: HorairesCotation, debut_ms: int, fin_ms: int) -> tuple[Intervalle, ...]` ;
`classer_intervalle(debut_ms, fin_ms, horaires, couverture) -> StatutCouverture` ;
`RegistreCouverture(periodes)` et `RegistreCouverture.depuis_registre_de_trous(debut_ms, fin_ms, trous)` ;
`JournalConnexions()` avec `connecter(instant_ms)`, `deconnecter(instant_ms)` ; les deux sources exposent
`periodes(jusqua_ms) -> tuple[Intervalle, ...]`.
Entrée : intervalle `[debut, fin)` ; horaires de cotation du noyau (séances moins fermetures exceptionnelles) ;
source de couverture (P-01) : en historique, la période de la source moins les trous déclarés par son registre ;
en direct, les périodes de connexion du robot (une connexion ouverte court jusqu'à `jusqua_ms`).
Sortie : `parties_ouvertes` : séances effectives coupées à `[debut, fin)`. `classer_intervalle` :
`FERMETURE_OFFICIELLE` si aucune partie n'est ouverte ; `COUVERT` si chaque partie ouverte est entièrement
contenue dans l'union des périodes couvertes ; `TROU` sinon ; `INCONNU` si l'intervalle sort de la période de
validité des horaires (aucune couverture ne peut alors être établie). Une source sans registre ne couvre rien.
Effets de bord : aucun pour les fonctions ; le journal des connexions retient ses périodes.
Erreurs, exceptions : `ErreurDonneesTemps` pour un intervalle vide ou inversé, des horaires absents, une
question hors de la période de validité (`parties_ouvertes`), des périodes chevauchantes, une connexion ou une
déconnexion hors d'ordre ou en double.

---

## Spécification exécutable

`tests/robot/london_donnees_temps/test_cat1_c1c_couverture.py` et `tests/robot/london_donnees_temps/test_cat2_c1c_couverture.py`.

## Comportements documentés (loi de Hyrum)

Les périodes rendues sont triées et fusionnées. Le texte des messages d'erreur n'est pas garanti.

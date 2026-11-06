# Contrat de la couche 1a — constructeur_bougies

- **Statut** : finalisé le 06/11/2026 (figé par `mcl.py figer` après gate vert) ; étendu le 06/11/2026
  (défigeage `extension` : export et import de l'état complet, pour la reprise de la couche 3)
- **Consommateurs cartographiés** : couches 2a (`validation_bougies`) et 3 (`flux_bougies`)
- **Dépend de** : couche 0a (réelle et figée) ; noyau figé (`c0a_temps`, `c1a_marche`) ; aucune frontière externe

---

Unité : constructeur_bougies
Responsabilité : Agréger les ticks en bougies brutes, clore à l'événement de frontière, signaler les intervalles vides.
Signature : `BougieBrute(symbole, debut_ms, duree_ms, ouverture, haut, bas, cloture, nombre_evenements, instant_disponibilite_ms)`
avec `fin_ms` et `vide` ; `SortieConstructeur(bougies, anomalie)` ;
`ConstructeurBougies(symbole, duree_ms, debut_ms=None)` avec `ajouter(tick: Tick) -> SortieConstructeur`,
`derniere_fin_ms -> int | None`, `exporter() -> dict` et `ConstructeurBougies.importer(donnees: Mapping) ->
ConstructeurBougies` ; `SCHEMA_CONSTRUCTEUR = 'xp-constructeur-bougies-v1'`.
Entrée : ticks du noyau d'un seul symbole, dans l'ordre de réception ; durée entière > 0 ; `debut_ms` (reprise) :
borne alignée à partir de laquelle les intervalles sont suivis.
Sortie : intervalles `[T, T + durée)` alignés sur l'origine UTC (C03.2) ; le premier tick d'heure fournisseur ≥ fin
clôt la bougie et appartient à la suivante ; OHLC sur le Bid de tous les ticks de l'intervalle, dans l'ordre
d'arrivée ; chaque intervalle sans tick entre deux bougies (ou depuis `debut_ms`) est émis comme bougie brute
vide (prix absents, zéro événement), aucune n'est inventée ; disponibilité = max(heure de réception du tick qui
révèle la clôture, fin de l'intervalle) ; bougies émises dans l'ordre des intervalles. Un tick d'heure
fournisseur antérieure à l'ouverture courante, ou à la dernière fin émise, est ignoré et signalé par
`AnomalieDonnees(raison='TICK_ANTERIEUR')`. `derniere_fin_ms` : fin de la dernière bougie émise, sinon
`debut_ms`. `exporter` rend l'état complet (dernière fin et bougie ouverte comprises) en dictionnaire JSON
strict ; `importer` le restitue de sorte que la suite des sorties soit identique à un traitement continu.
Effets de bord : aucun ; état interne : bougie ouverte et dernière fin émise.
Erreurs, exceptions : `ErreurDonneesTemps` pour un tick d'un autre symbole, une durée invalide, un `debut_ms` non
aligné, une bougie brute incohérente, un état importé d'un autre schéma, incomplet, de mauvais type ou incohérent
(bougie ouverte non alignée, antérieure à la dernière fin, sans événement ou d'OHLC incohérents).

---

## Spécification exécutable

`tests/robot/donnees_temps/test_cat1_c1a_constructeur.py` et `tests/robot/donnees_temps/test_cat2_c1a_constructeur.py`.

## Comportements documentés (loi de Hyrum)

La M15 et la H1 sont construites par deux constructeurs indépendants à partir des mêmes ticks. Le texte des
messages d'erreur n'est pas garanti.

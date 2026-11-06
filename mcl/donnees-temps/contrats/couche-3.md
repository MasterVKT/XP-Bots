# Contrat de la couche 3 — flux_bougies

- **Statut** : finalisé le 06/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : `orchestration` (segment S2 du squelette, puis artefact `orchestration`) et
  `moteur-london` (types des bougies enrichies, repères de Londres)
- **Dépend de** : couches 0a, 0b, 1a, 1c, 2a et 2b (réelles et figées) ; noyau figé
  (`c0c_configuration.ExportTechnique`, `c1a_marche`, `c1b_instrument`) ; aucune frontière externe

---

Unité : flux_bougies
Responsabilité : Enveloppe : ticks et connexions → bougies M15 et H1 enrichies et état de trou par symbole.
Signature : `SCHEMA_FLUX = 'xp-flux-bougies-v1'` ; `EvenementFlux = BougieEnrichie | ChangementTrou |
AnomalieDonnees` ; `FluxBougies(symbole: str, technique: ExportTechnique, horaires: HorairesCotation,
couverture: SourceCouverture)` avec
`sur_tick(tick: Tick) -> tuple[EvenementFlux, ...]`,
`sur_connexion(connecte: bool, instant_ms: int) -> None`, `actualiser_horaires(horaires: HorairesCotation) -> None`,
`en_trou -> bool`, `calendrier -> CalendrierLondres`, `identite(unite: UniteTemps) -> IdentitePrechargement`,
`exporter_etat() -> dict` et `FluxBougies.reprendre(donnees: Mapping, technique, horaires, couverture) ->
FluxBougies`.
Entrée : ticks du noyau d'un seul symbole, dans l'ordre de réception ; export technique figé du noyau (paramètres
communs : durée M15 = `timeframe_seconds`, durée H1 = `h1_seconds`, `atr_period`, fuseau, jours actifs,
blackout ; empreinte canonique, qui signe l'état exporté) ; horaires de cotation du noyau ; source de couverture
de 1c (registre historique en rejeu, `JournalConnexions` en direct, alimenté par `sur_connexion`).
Sortie : un tick antérieur à l'ouverture M15 courante rend la seule `AnomalieDonnees('TICK_ANTERIEUR')` et n'est
agrégé dans aucune unité. Sinon, les bougies brutes M15 et H1 closes par le tick sont validées (2a), passées à la
chaîne de leur unité (2b) et rendues en `BougieEnrichie` : `jour_londres` et `jour_utc` = dates de Londres et UTC
de l'ouverture, `ouverture_locale` et `cloture_locale` = début et fin en heure de Londres (0b), `indicateurs` =
TR, ATR, A et rang de la chaîne de l'unité, absents pour une bougie invalide. Ordre : fin croissante, H1 avant
M15 à fin égale (la H1 close à t est connue quand la M15 close à t est traitée) ; un `ChangementTrou` du
validateur M15 précède immédiatement la bougie qui le provoque ; ceux du validateur H1 ne sont pas émis (l'état
de trou du symbole, `en_trou`, est celui de la M15). Une H1 n'est émise qu'à sa clôture, par le tick de
frontière : aucune donnée partielle n'est exposée. La sortie d'un préfixe de ticks est un préfixe de la sortie
complète (C11.1). `exporter_etat` rend un dictionnaire JSON strict de l'état complet par unité (constructeur,
bougie ouverte comprise, chaîne d'indicateurs, état de trou) ; `reprendre` le restitue : la suite des sorties
est identique à un traitement continu, quel que soit l'instant de l'export (C03.7). Horaires et couverture ne
font pas partie de l'état : l'appelant les fournit à la reprise, et une coupure non couverte reste un trou.
Effets de bord : état interne du flux ; `sur_connexion` enregistre la connexion ou la déconnexion dans le
`JournalConnexions` fourni comme couverture.
Erreurs, exceptions : `ErreurDonneesTemps` pour un symbole vide, des paramètres, horaires ou une couverture de
mauvais type, un tick d'un autre symbole ou de mauvais type, `sur_connexion` sans `JournalConnexions` ou hors
d'ordre, une unité inconnue, un état d'un autre schéma, symbole, empreinte de configuration ou durée, incomplet,
de mauvais type ou incohérent entre unités (dernière fin M15 hors de l'heure qui suit la dernière fin H1, ou H1
qui refuserait un tick accepté par la M15).

---

## Spécification exécutable

`tests/robot/donnees_temps/test_cat1_c3_flux.py` et `tests/robot/donnees_temps/test_cat2_c3_flux.py`.

## Comportements documentés (loi de Hyrum)

Les clés du dictionnaire exporté ne sont une interface que pour `reprendre`. Le texte des messages d'erreur n'est
pas garanti. Une bougie M15 et une H1 de même fin sont émises par le même tick, la H1 d'abord.

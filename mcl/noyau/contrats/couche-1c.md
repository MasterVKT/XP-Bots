# Contrat de la couche 1c — domaine

- **Statut** : finalisé le 05/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : couche 2 (`journal`) ; plus tard `moteur-london` (signaux et absences de
  signal), `execution-coordinateur` (intentions, issues, motifs), `controles-fondamentaux` et `contexte-ia`
  (décisions des contrôles)
- **Dépend de** : couche 0a (`instant`), réelle et figée ; aucune frontière externe (bibliothèque standard
  `hashlib` pour l'empreinte de clé)

---

Unité : domaine
Responsabilité : Définir sens, signal technique, clé d'intention, issues, décisions des contrôles et motifs fermés.
Signature : `Sens` (`ACHAT`, `VENTE` ; `signe` ±1 ; `oppose()`) ; `Motif` (22 codes : les 20 motifs minimaux de
C09, `ENVIRONMENT_NOT_READY` de C04, `AI_CONTEXT_VETO` de A07) ; `VERSION_DETAILS = '1'` ;
`DETAILS_ENUMERES: Mapping[Motif, frozenset[str]]` ; `MOTIFS_A_DETAIL_LIBRE` ;
`verifier_motif(motif, detail) -> tuple[Motif, str | None]` ;
`CleIntention(deploiement, strategie, symbole, cloture_ms, sens)` avec `texte()` et `empreinte(longueur)` ;
`SignalTechnique(strategie, symbole, cloture_ms, sens, cloture_prix, atr_reference, stop_technique, multiple_objectif, contexte)` ;
`AbsenceDeSignal(strategie, symbole, cloture_ms, motif, detail, contexte)` ; `ResultatTechnique` (l'un ou
l'autre) ; `NatureIssue` (`REMPLIE`, `REFUSEE`, `EXPIREE`, `CLOTUREE`) ; `CauseCloture` (`STOP_LOSS`,
`TAKE_PROFIT`, `GARDE_QUOTIDIENNE`, `ARRET_GLOBAL`, `FLATTEN`, `ANNONCE`, `HEURE_SORTIE`, `DUREE_MAXIMALE`,
`FERMETURE_NATIVE`, `BLACKOUT`) ; `Issue(cle, nature, instant_ms, motif=None, detail=None, cause=None)` ;
`DecisionFondamentale(admise, motif=None, detail=None, cloture_obligatoire=False)` ; `ContexteIA` (`BLOCK`,
`NEUTRAL`) ; `DecisionContexteIA(etat, evenement=None)` avec `motif_et_detail()` ; `ErreurDomaine(ValueError)`.
Entrée : textes et instants entiers (0a) ; prix et ATR en flottants 64 bits ; contexte : correspondance de
valeurs JSON (textes, nombres finis, booléens, `None`, listes, correspondances à clés textuelles).
Sortie : objets immuables ; contexte figé (correspondances en lecture seule, listes en tuples). Détails : pour
un motif à détails énumérés, le détail appartient à l'ensemble du document 01, §9.3 (version 1) ; pour un motif
sans détail, il vaut `None` ; pour `ENVIRONMENT_NOT_READY`, un identifiant de champ ou de fonction ; pour
`AI_CONTEXT_VETO`, l'identifiant de l'événement. Signal : `stop_technique < cloture_prix` à l'achat,
`> cloture_prix` à la vente ; `atr_reference > 0` ; `multiple_objectif > 0`. Clé d'intention : texte
`deploiement|strategie|symbole|cloture_ms|sens`, empreinte = préfixe hexadécimal du SHA-256 de ce texte, de 1 à
64 caractères. Issues : `REMPLIE` sans motif ni cause ; `REFUSEE` avec un motif autre que `SIGNAL_EXPIRED` ;
`EXPIREE` avec `SIGNAL_EXPIRED` ; `CLOTUREE` avec une cause, motif facultatif. Décision fondamentale : admise
sans motif ni clôture ; refusée avec `FUNDAMENTAL_INVALID`, `FUNDAMENTAL_DIRECTION` ou `NEWS_WINDOW`. Décision
de contexte IA : `BLOCK` avec un identifiant d'événement, `NEUTRAL` sans ; jamais d'autorisation.
Effets de bord : aucun.
Erreurs, exceptions : `ErreurDomaine` pour toute valeur hors de ces ensembles, tout texte vide, tout instant
refusé par 0a, tout nombre non fini, toute combinaison incohérente.

---

## Spécification exécutable

`tests/robot/noyau/test_cat1_c1c_domaine.py` et `tests/robot/noyau/test_cat2_c1c_domaine.py`.

## Comportements documentés (loi de Hyrum)

`Sens`, `Motif`, `NatureIssue`, `CauseCloture` et `ContexteIA` sont des `StrEnum` : leur valeur est leur nom. Le
texte des messages d'erreur n'est pas garanti.

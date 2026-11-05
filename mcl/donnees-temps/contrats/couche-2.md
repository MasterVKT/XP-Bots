# Contrat de la couche 2 — etat-indicateurs (artefact `donnees-temps`)

- **Statut** : finalisé (phase 2, 2026-11-05) ; gel tracé dans `mcl/donnees-temps/journal.jsonl`.
- **Consommateurs cartographiés** : couche 3 (`pipeline_marche`) ; hors artefact : `app` (spécification des
  indicateurs de la méthode, persistance au redémarrage).
- **Dépend de** : couche 1c (`EtatEMA`, `EtatRSI`, `EtatATR`, noms des indicateurs) ; amont figé : `amont-noyau`
  (`Bougie`, port `Stockage`, JSON canonique) ; frontière externe doublée : `stockage-etat` (doublure mémoire
  `tests/robot/doublures/stockage_memoire.py`, adaptateur SQLite en phase 9).
- **Module** : `src/xpbots/donnees_temps/c2_etat_indicateurs.py`
- **Sources normatives** : C03 points 7, 8 à 11 ; plan maître 7.A.

---

Unité : etat_indicateurs (types `SpecIndicateurs`, `Indicateurs`, `EmpreintePrechargement`)
Responsabilité : Précharger, appliquer, persister et restaurer les états récursifs des indicateurs d'un symbole et
tracer l'empreinte du préchargement.
Signature : `SpecIndicateurs(periodes_ema, periode_rsi, periode_atr, decalages_ema, prechauffage)` ;
`EtatIndicateursSymbole(spec)` ; `appliquer(bougie) -> Indicateurs` ; `precharger(bougies) -> EmpreintePrechargement` ;
`reinitialiser()` ; `exporter() -> dict` ; `EtatIndicateursSymbole.importer(spec, dict)` ;
`sauvegarder(stockage, cle)` ; `EtatIndicateursSymbole.restaurer(spec, stockage, cle, empreinte_attendue=None)` ;
propriétés `compte`, `pret`, `derniere_cloture_ms`, `empreinte_prechargement`.
Entrée : bougies Bid valides d'un symbole, clôtures strictement croissantes ; spécification fournie par l'appelant
à partir de `config/` (périodes EMA, RSI et ATR, décalages comme EMA50 de t−4, préchauffage
`warmup_closed_m15_bars`).
Sortie : `Indicateurs(valeurs, a_t, compte)` après chaque bougie : `valeurs` contient les seuls indicateurs
disponibles parmi `ema_<n>`, `ema_<n>_t_moins_<k>`, `rsi_<n>`, `atr_<n>`, `tr` ; `a_t` = ATR de la bougie
précédente s'il est strictement positif, sinon `None` (C03 point 11) ; `compte` = bougies valides appliquées ;
`pret` est vrai dès que `compte` ≥ préchauffage (la 1 000e bougie est la première décidable, comme
`ema_setups`). L'empreinte du préchargement (première ouverture, dernière clôture, nombre, SHA-256 des OHLC
canoniques) est fixée à la bougie qui atteint le préchauffage.
Effets de bord : états internes ; lecture et écriture par le port `Stockage` (JSON canonique, flottants restitués à
l'identique).
Erreurs, exceptions : `ValueError` pour une spécification invalide (dont un préchauffage trop court pour rendre
tous les indicateurs disponibles) ; `ValeurInvalide` pour une bougie invalide ou non postérieure à la précédente ;
`PrechargementInsuffisant` si moins de bougies que le préchauffage ; `EtatIncompatible` pour un préchargement sur
un état non vierge, un état importé d'une autre spécification ou une empreinte différente de celle attendue.

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/donnees_temps/test_c2_cat1_*.py`) : chronologie de disponibilité de chaque
  indicateur, `ema_50_t_moins_4` égal à l'EMA50 quatre bougies plus tôt, `a_t` égal à l'ATR précédent,
  `pret` à la bougie du préchauffage, empreinte déterministe et sensible à une bougie modifiée, bougie invalide ou
  rétrograde refusée, préchargement insuffisant ou sur état non vierge refusé, export puis import à l'identique,
  spécification ou empreinte incompatibles refusées, réinitialisation, validation de la spécification.
- Catégorie 2 (`tests/robot/donnees_temps/test_c2_cat2_*.py`) : bloc réel {0 → 2} (bougies construites par la
  couche 1b) : reprise après redémarrage par le port `Stockage` identique au flux continu ; préchargement puis flux
  identique au flux seul.

## Comportements documentés (loi de Hyrum)

Le format exporté porte le schéma `xp-etat-indicateurs-v1` ; il change par version, jamais en silence.

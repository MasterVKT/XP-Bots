# Contrat de la couche 0 — parametres-et-seances (artefact `donnees-temps`)

- **Statut** : finalisé (phase 2, 2026-11-05) ; gel tracé dans `mcl/donnees-temps/journal.jsonl` (`mcl.py figer`).
- **Consommateurs cartographiés** : couches 1a (`sessions_londres`), 1b (`constructeur_bougies`), 3
  (`pipeline_marche`) ; hors artefact : `execution-coordinateur`, `controles-fondamentaux`, `app`.
- **Dépend de** : aucune couche interne ; amont figé : `amont-noyau` (`BundleTechnique`, `ConfigurationInvalide`,
  `figer`) ; frontières externes doublées : aucune.
- **Module** : `src/xpbots/donnees_temps/c0_parametres_seances.py`
- **Sources normatives** : C02 (bloc `common`), C03 points 2, 3 et 5, C04 (séances natives) ; plan maître 7.A.

---

Unité : parametres_techniques
Responsabilité : Charger et valider le bloc `common` de la configuration figée en objet immuable.
Signature : `charger_parametres_techniques(bundle: BundleTechnique) -> ParametresTechniques` ;
`ParametresTechniques.valeur(cle)` ; propriétés `periode_m15_s`, `periode_h1_s`, `prechauffage_m15`,
`prechauffage_h1`, `periode_atr`, `fuseau_sessions`, `jours_actifs`, `blackout_debut`, `blackout_fin`, `univers`,
`empreinte`.
Entrée : bundle technique déjà lu strictement par le noyau.
Sortie : objet immuable ; chaque clé du schéma (73 clés exactement) est contrôlée par genre : texte non vide, date
`AAAA-MM-JJ`, heure `HH:MM:SS`, fuseau IANA chargeable, entier strictement positif ou positif, nombre fini
strictement positif, booléen, liste non vide de textes, liste de jours distincts 0 à 6, liste de nombres finis
positifs, dictionnaire de nombres finis strictement positifs ; `empreinte` = empreinte du bundle.
Effets de bord : aucun.
Erreurs, exceptions : `ConfigurationInvalide` si une clé manque, est en trop, est nulle, a un mauvais type (un
booléen n'est jamais un entier) ou une valeur hors genre ; `FonctionNonImplementee` (sous-classe) si `bar_price`,
`bar_alignment`, `atr_method` ou `atr_signal_reference` demandent une variante autre que celle implémentée (Bid,
UTC, Wilder, ATR de la M15 précédente).

---

Unité : analyser_heure (outil de l'unité parametres_techniques)
Responsabilité : Convertir un texte `HH:MM:SS` en heure, sans tolérance de format.
Signature : `analyser_heure(texte: str) -> datetime.time`
Entrée : texte de configuration.
Sortie : heure sans fuseau, secondes comprises.
Effets de bord : aucun.
Erreurs, exceptions : `ConfigurationInvalide` si le format ou les bornes sont invalides.

---

Unité : calendrier_seances
Responsabilité : Représenter les séances de cotation natives d'un symbole sur une période connue et dire si un
instant est en séance.
Signature : `CalendrierSeances(symbole, ouvertures, connu_de_ms, connu_jusqua_ms)` ;
`en_seance(instant_ms) -> bool` ; `portion_ouverte(debut_ms, fin_ms) -> tuple[tuple[int, int], ...]` ;
`prochaine_fermeture(instant_ms) -> int | None`.
Entrée : intervalles UTC `[début, fin)` en ms, triés, disjoints, contenus dans la période connue
`[connu_de_ms, connu_jusqua_ms)` ; ces données viennent de l'environnement courtier ou du manifeste de données,
jamais d'une supposition.
Sortie : appartenance à une séance ; intersection d'un intervalle avec les séances ; fin de la séance en cours,
`None` si le marché est fermé à l'instant donné.
Effets de bord : aucun.
Erreurs, exceptions : `ValueError` à la construction si les intervalles sont mal formés, chevauchants ou hors
période ; `CalendrierInconnu` pour une question qui sort de la période connue (traduit en `ENVIRONMENT_NOT_READY`
par les consommateurs).

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/donnees_temps/test_c0_cat1_*.py`) : clés manquantes ou en trop, valeurs nulles,
  booléens refusés comme entiers, nombres non finis, fuseau inconnu, heure mal formée, variantes non implémentées,
  empreinte égale à celle du bundle, propriétés lues dans `config/` ; séances : début inclus, fin exclue,
  intervalles chevauchants ou non triés refusés, portion ouverte, prochaine fermeture, question hors période.
- Catégorie 2 : aucune (couche 0, rien en dessous).

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Le texte exact des messages d'erreur n'est pas garanti.
Toute valeur normative est lue dans `config/`, jamais recopiée.

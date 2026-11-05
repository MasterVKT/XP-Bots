---
name: xp-bots-market-data-causality
description: "Données de marché et causalité de XP-Bots (C03 et cahier de données) : ticks Bid/Ask UTC à la milliseconde avec ordre stable, bougies M15 et H1 Bid alignées UTC, sessions Europe/London et changements d'heure, préchargement 1 000 M15 et 300 H1, trous de données, provenance et empreintes, absence d'anticipation, calendriers et permissions avec heures de connaissance, collecte prospective des traces IA. Utiliser pour collecter, valider, convertir ou rejouer des historiques et pour vérifier qu'une décision n'utilise aucune information future. Déclencheurs : données historiques, ticks, Bid/Ask, M1, bougie, OHLC, UTC, Europe/London, heure d'été, préchargement, trou de données, provenance, causalité, anticipation, lookahead, Dukascopy, Parquet, C03."
---
<!-- xp-bots:generated-skill-mirror source=.agents/skills/xp-bots-market-data-causality/SKILL.md generator=.agents/hooks/skill_mirrors.py : ne pas éditer -->
> Copie générée de `.agents/skills/xp-bots-market-data-causality/SKILL.md` par `.agents/hooks/skill_mirrors.py --write`. Ne pas éditer : modifier la source puis régénérer. Répertoire des ressources de ce skill : `.agents/skills/xp-bots-market-data-causality/` ; les chemins de ressources ci-dessous sont relatifs à la racine du dépôt.

# Données de marché, temps et causalité

## Ressources

- Autorité : C03 des deux spécifications ; cahier de collecte
  `docs/data/03_Donnees_Historiques_Requises_et_Validation.md` (formats, champs, bornes UTC, blocs de protocole).
- Provenance historique : `docs/validation/provenance_diagnostic_v3.json` (chemins de l'ancien workspace,
  cache M1 archivé hors du dépôt) ; récupération décrite dans `docs/maintenance/NETTOYAGE_ET_MERGE.md`.
- Référence : `replay_bar_data` et `local_decision_in_window` de `reference/technical.py` ; tests de causalité
  par préfixe dans `tests/check_technical.py`.

## Workflow

1. Avant d'utiliser une série : relever source, fuseau d'origine, précision, méthode d'extraction, trous connus,
   date de récupération et SHA-256 (section 2 du cahier) ; une série d'un autre fournisseur ne reproduit pas
   l'exécution du courtier lié.
2. Construire les bougies selon C03.2 : intervalles `[T, T+900 s)` et `[T, T+3600 s)` alignés sur l'époque UTC,
   OHLC Bid, tick de frontière rattaché à la bougie suivante ; H1 visible seulement à sa clôture.
3. Traiter les trous selon C03.5–C03.6 : pas de remplissage synthétique à prix constant ; un trou inexpliqué
   bloque les entrées et efface replis et ranges en attente.
4. Prouver la causalité : modifier une bougie future ne change aucune décision passée (C11 point 1) ; reprendre
   le test de préfixe de `tests/check_technical.py` sur tout nouveau calcul.
5. Stocker les données privées dans les emplacements ignorés (`data/raw/`, `data/cache/`, `data/private/`) ;
   ne jamais committer de prix bruts. Rejouer `python tools/verify_project.py`.

## Garde-fous

- Séparer jours Londres (logique des stratégies) et jour UTC (perte quotidienne) ; jamais un décalage constant.
- M1 sert à un diagnostic préalable ; M15 seul ne valide pas un scalping ; aucun tick généré ne remplace en
  silence un tick absent dans un test final.
- Les blocs de dates de C10 sont fixés avant chargement : le test réservé ne s'ouvre pas pour régler un seuil
  et la période 01/05–03/11/2026 reste un diagnostic.
- Un calendrier enrichi après coup, des valeurs macro révisées ou des news réinterrogées aujourd'hui sont des
  fuites d'information.

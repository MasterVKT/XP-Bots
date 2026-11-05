---
name: xp-bots-ema-rsi-repli
description: "Méthode S01 Triple EMA + RSI + repli M15 (EMA_V3) de XP-Bots : tendance EMA15/25/50 et pente EMA50, armement, repli dans la zone EMA15–EMA50 sur 8 bougies, bougie de reprise, RSI14 Wilder 40/50/60, stop structurel, objectif 1,5 D, six entrées par jour Londres, cooldown, veto IA spécifique A07. Utiliser pour concevoir, porter, tester ou vérifier le moteur EMA, ses états et sa concordance avec reference/technical.py. Déclencheurs : EMA, EMA15/25/50, RSI14, repli, pullback, reprise, armement, cooldown, S01, EMA_V3, spécification 01."
---

# Méthode S01 — Triple EMA + RSI + repli

## Ressources

- Autorité : `livrables/strategies_m15/01_Triple_EMA_RSI_Repli_M15_Specification_IA.md`, sections S01.1–S01.6,
  C03 (indicateurs), C06 (conversion des prix) et A07 (insertion du veto IA).
- Valeurs : bloc `ema` de `config/parametres_figes_v3.json` (ne jamais les recopier dans le code porté).
- Référence de comparaison : `reference/technical.py` (`ema`, `wilder`, `rsi`, `add_indicators`,
  `trend_side`, `arm_context`, `pullback_valid`, `ema_signal`, `ema_setups`, `rounded_levels`).

## Workflow

1. Relire S01.2 (machine à états `IDLE`, `ARMED_*`, `PULLBACK_*`, `COOLDOWN`, `OWNED_POSITION`) et lister
   les transitions à implémenter ou à vérifier, avec leurs inégalités strictes ou larges exactes.
2. Lire le code de `ema_setups` : il compte des configurations potentielles sans position possédée, sans
   compteur de fills ni exécution. Noter explicitement ce que le robot réel doit ajouter (S01.4, C07, C08).
3. Porter ou modifier les indicateurs en respectant les graines de C03.8–C03.11 (EMA graine SMA, Wilder,
   RSI 50/100/0 aux cas nuls, `A_t` = ATR14 de t−1) ; comparer à `reference/technical.py` sur les mêmes séries.
4. Couvrir les cas d'acceptation S01.6 et C11 concernés par des tests du robot réel : RSI de repli 40 admis,
   signal 49,999 refusé, âge 9 annulé, TR > 2,5 A refusé, stop incluant l'extrême de la bougie de signal,
   septième entrée refusée, veto A07 consommant le repli sans consommer d'entrée remplie.
5. Rejouer les contrôles de référence : `python tests/check_technical.py`, puis `python tools/verify_project.py`.
6. Pour une construction complète du moteur, enchaîner avec `xp-bots-mcl-robot-planning`.

## Garde-fous

- La bougie d'armement n'est jamais aussi bougie de repli ou de signal ; le premier signal complet consomme le
  repli même si le stop est trop large ou l'exécution refusée.
- Un indicateur natif de plateforme portant le même nom (EMA, ATR) n'a pas forcément la même graine : comparer
  les valeurs, ne pas supposer l'égalité.
- Aucune sortie RSI 70/30, aucun trailing, break-even ou sortie partielle ; le seuil de corps relatif
  appartient à London, pas à EMA.
- Le compteur de six entrées se remet à zéro au changement de jour Londres, jamais par un redémarrage.
- Le veto IA ne choisit ni sens, ni stop, ni volume ; il n'ajoute qu'un refus (A07).

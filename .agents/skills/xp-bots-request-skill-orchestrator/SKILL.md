---
name: xp-bots-request-skill-orchestrator
description: "Routeur XP-Bots à exécuter en premier pour chaque requête, tapée ou non (nouvelle demande, plan validé, notification, passe corrective, sous-tâche, reprise, compaction) : part de la sélection déterministe du hook ou de select_skills.py, l'ajuste selon le code réel, retient le plus petit ensemble de skills utiles et annonce la couverture tâche → skill. Déclencheurs : toute requête dans XP-Bots, orchestrateur, routeur, sélection de skills, quelle skill utiliser."
---

# Orchestrateur des requêtes XP-Bots

## Workflow

1. Partir de la sélection injectée (origine indiquée). Sans hook :
   `python .agents/skills/xp-bots-request-skill-orchestrator/scripts/select_skills.py --explain "<requête>"`.
2. Vérifier le code réellement concerné (`rg`, lecture ciblée) ; ajouter ou retirer une skill en une ligne.
3. Annoncer la couverture tâche → skill ; toute tâche sans skill va au contrôle 4 de l'audit.
4. Charger seulement les `SKILL.md` retenus et appliquer `.agents/PROJECT_RULES.md`.
5. Finir par `xp-bots-completion-audit` (pied d'audit et marqueur).

## Requêtes non tapées

- Notification ou réveil : garder sélection et base de la requête en cours, sans router sur la notification.
- « continue », « vas-y », plan approuvé : même requête, sélection conservée et complétée.
- Passe corrective : recharger cette skill avec la sélection de remédiation, puis exécuter le brief.
- Sous-tâche : charger l'utile seulement ; jamais de marqueur d'audit.
- Reprise ou compaction : relire la requête en cours rappelée par le hook.

## Catalogue

<!-- catalogue:debut -->
- `xp-bots-request-skill-orchestrator` — routage et couverture (toujours en premier)
- `xp-bots-completion-audit` — audit de fin, remédiation, pied et marqueurs
- `xp-bots-skill-gap-detector` — lacunes, registre, création ou extension de skill
- `xp-bots-maintain-agent-skills` — skills, hooks, miroirs, adaptateurs, validateurs
- `mcl-matryoshka-construction-layers` — méthode MCL : couches inside-out gelées
- `xp-bots-mcl-robot-planning` — plan MCL d'un robot ou composant XP-Bots
- `xp-bots-ema-rsi-repli` — S01 : EMA15/25/50, RSI14, repli, reprise
- `xp-bots-london-breakout` — S02 : range 02:00–07:00 Londres, ATR H1, cassure, quotas
- `xp-bots-risk-execution-contracts` — C06–C09 : prix, dimensionnement, coordinateur, ordres
- `xp-bots-broker-account-qualification` — C04 : compte, symboles, micro, frais, marge
- `xp-bots-fundamental-permissions` — C05 : permissions externes, annonces, calendrier
- `xp-bots-llm-integration-contracts` — A01–A12 : IA distante, veto, budget, snapshot
- `xp-bots-market-data-causality` — C03 : ticks Bid/Ask, UTC/Londres, causalité
- `xp-bots-validation-replay` — C10–C11, A13–A15 : rejeu, coûts, A/B, acceptation
- `xp-bots-specification-consistency` — cohérence spécifications, exports, preuves
- `xp-bots-deployment-readiness` — PAPER_AB, démo, réel : go/no-go, arrêts, secrets
<!-- catalogue:fin -->

## Garde-fous

- Le plus petit ensemble utile ; une demande documentaire ne charge pas les skills métier.
- Aucune skill n'autorise à modifier une valeur figée ; MCL structure, les skills métier fixent les contrats.

---
name: xp-bots-maintain-agent-skills
description: "Gouvernance des agents AI de XP-Bots : maintenir la source unique .agents/skills, les copies générées de .claude/skills, les adaptateurs (AGENTS.md, CLAUDE.md, .clinerules), les hooks de Claude Code, Codex et Copilot, le moteur agent_lifecycle.py, lifecycle.json, le routage et les validateurs. Déclencheurs : skill, skills, hook, hooks, orchestrateur, routage, miroir, gouvernance, cycle de vie, AGENTS.md, CLAUDE.md, Codex, Copilot, Cline, Claude Code, pied d'audit, marqueur, compatibilité des outils."
---
<!-- xp-bots:generated-skill-mirror source=.agents/skills/xp-bots-maintain-agent-skills/SKILL.md generator=.agents/hooks/skill_mirrors.py : ne pas éditer -->
> Copie générée de `.agents/skills/xp-bots-maintain-agent-skills/SKILL.md` par `.agents/hooks/skill_mirrors.py --write`. Ne pas éditer : modifier la source puis régénérer. Répertoire des ressources de ce skill : `.agents/skills/xp-bots-maintain-agent-skills/` ; les chemins de ressources ci-dessous sont relatifs à la racine du dépôt.

# Maintenance de la gouvernance des agents

## Workflow

1. Lire `.agents/agent-integrations.json` (registre des outils, miroirs, adaptateurs, chemins obsolètes) et
   `.agents/COMPATIBILITY.md` (versions vérifiées, limites) avant toute modification.
2. Modifier uniquement la source canonique : `.agents/skills/<nom>/`, `.agents/hooks/`, les données de
   routage de l'orchestrateur ou le registre. Jamais `.claude/skills/` à la main.
3. Régénérer et contrôler les copies : `python .agents/hooks/skill_mirrors.py --write`, puis `--check`.
4. Valider : `python .agents/skills/xp-bots-maintain-agent-skills/scripts/validate_governance.py`, puis la suite
   complète `python .agents/skills/xp-bots-maintain-agent-skills/scripts/run_governance_suite.py`
   (miroirs, validateur, sélecteur, cycle de vie, registre et générateur, tests négatifs sur copie temporaire).
5. Pour un outil supplémentaire : ajouter un mode `<événement>-<outil>` et son format de sortie dans
   `.agents/hooks/lifecycle.json` et le moteur, déclarer le fichier de hooks dans le registre, documenter la
   vérification de version dans `COMPATIBILITY.md` ; jamais un second moteur.
6. Après toute modification d'un fichier de hooks : signaler à l'humain la ré-approbation nécessaire (Codex
   demande une revue des hooks nouveaux ou modifiés ; Claude Code peut exiger `/hooks` ou un redémarrage).

## Garde-fous

- Un seul exemplaire du moteur, des lanceurs, des générateurs et des validateurs pour tous les outils et les
  deux stratégies ; les différences passent par la configuration.
- Les clés du pied d'audit et les marqueurs ne changent qu'avec le moteur, `lifecycle.json`, la skill d'audit
  et les tests dans la même modification.
- Toute garantie annoncée a son test négatif ; un test qui exerce les portes neutralise `XPBOTS_GATE_ACTIVE`.
- Les empreintes de MCL consignées dans le registre ne se réécrivent qu'avec une évolution justifiée et tracée.
- Avant de soupçonner le code devant un hook muet : vérifier l'espace disque et le journal d'erreurs du
  dossier d'état (`xp-bots-lifecycle-errors.log`).

# Claude Code — pointeur vers les instructions communes

@AGENTS.md

Spécificités de Claude Code (version 2.1.318 vérifiée, détails dans `.agents/COMPATIBILITY.md`) :

- Les skills chargées par Claude Code sont les copies générées de `.claude/skills/` ; la source éditable est
  `.agents/skills/`. Ne jamais éditer une copie.
- Les hooks de `.claude/settings.json` appellent `.agents/hooks/invoke-agent-hook.sh`, puis le moteur unique
  `.agents/hooks/agent_lifecycle.py`. Sous Windows, ils exigent Git Bash (Git for Windows).

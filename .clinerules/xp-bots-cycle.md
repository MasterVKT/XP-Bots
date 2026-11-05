# XP-Bots — règle permanente pour Cline

Cline lit `AGENTS.md`, qui fait autorité ; cette règle ne le remplace pas. Aucun hook de fichier n'est
installé pour Cline : sa documentation courante a déplacé les hooks vers des plugins SDK non vérifiés pour ce
dépôt (voir `.agents/COMPATIBILITY.md`). Le cycle s'exécute donc par appels explicites au moteur commun.

1. Au début de chaque tâche, obtenir la sélection déterministe et la base de comparaison :
   `python .agents/hooks/agent_lifecycle.py --mode prompt-cline --text "<requête de l'humain>"`.
2. Appliquer `xp-bots-request-skill-orchestrator` puis les skills retenues (copies lisibles dans
   `.claude/skills/`, source dans `.agents/skills/`).
3. Avant `attempt_completion`, écrire la réponse finale prévue (avec pied d'audit et marqueur) dans
   `.local/cline-final.md`, puis lancer
   `python .agents/hooks/agent_lifecycle.py --mode completion-cline --input-file .local/cline-final.md`.
   Ce contrôle n'exécute que les portes rapides. Si `decision` vaut `block`, exécuter le brief (deux passes au
   plus), puis recommencer.
4. Ne jamais émettre `[XP-BOTS-AUDIT:OK]` ou `[XP-BOTS-AUDIT:BLOQUE]` dans une sous-tâche.

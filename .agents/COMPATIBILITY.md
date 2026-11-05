# Compatibilité des outils AI et activation du cycle de vie

Vérification du **5 novembre 2026**. Les normes des outils changent vite : refaire la vérification de la
section 2 à chaque mise à jour d'un outil, puis mettre à jour ce fichier et `.agents/agent-integrations.json`.

## 1. Fiche de contexte de la mise en place

| Élément | Constat |
|---|---|
| Racine | Dépôt Git XP-Bots (ancres d'identité de `AGENTS.md` présentes) ; poste de référence `D:\PROJETS\XP-Bots`, mise en place exécutée dans un conteneur Linux distant |
| Interpréteur | Python 3.13.18 ici ; Python 3.13 invoqué par `python` sur le poste de référence |
| Système | Linux et shell POSIX ici ; Windows et PowerShell sur le poste de référence |
| Outils AI | Claude Code 2.1.318 installé ici ; Codex, GitHub Copilot et Cline non installés ici |
| État initial | Aucun `.agents/`, `AGENTS.md`, hook ni moteur ; MCL réel dans `.claude/skills/` (19 fichiers, identiques au ZIP) |
| Contrôles initiaux | `python tools/verify_project.py` vert : 30 contrôles projet et 288 contrôles de référence |
| Noms retenus | `xp-bots` ; `xp-bots-request-skill-orchestrator`, `xp-bots-completion-audit`, `xp-bots-skill-gap-detector`, `xp-bots-maintain-agent-skills` |

## 2. Matrice par outil

Certitude : **code** = chaînes du binaire ou du bundle publié ; **doc** = documentation officielle ;
**test** = exécution réelle observée dans ce dépôt.

| Question | Claude Code 2.1.318 | Codex 0.166.0 | Copilot CLI | Cline |
|---|---|---|---|---|
| Dossiers de skills de projet | `.claude/skills/` seulement ; `.agents/skills` n'apparaît que dans l'importateur Cursor (code) — découverte du miroir constatée en session (test) | `.agents/skills/` du dossier courant à la racine du dépôt (code, doc) | `.github/skills/`, `.agents/skills/`, `.claude/skills/` (code du bundle 1.0.63) | `.cline/skills/`, `.clinerules/skills/`, `.claude/skills/` (doc) |
| Homonymes | Non concerné : une seule source lue | Pas de fusion, les deux peuvent apparaître (doc) | Résolution non vérifiée : la copie de `.claude/skills/` a le même contenu d'instructions que la source | Skill globale prioritaire sur la skill de projet (doc) |
| Frontmatter, longueur | `name`, `description` | `name`, `description` ; `agents/openai.yaml` facultatif | `name`, `description` | `name` = dossier, description ≤ 1 024 caractères (doc) |
| Instructions permanentes | `CLAUDE.md` (import `@AGENTS.md`) ; `AGENTS.md` lu seulement en l'absence de `CLAUDE.md` par défaut (code) | `AGENTS.md` | `.github/copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md` (code) | `AGENTS.md` et `.clinerules/` (doc) |
| Fichier de hooks | `.claude/settings.json` | `.codex/hooks.json` | `.github/hooks/*.json`, `version: 1` (code) | Hooks déplacés vers des plugins SDK JavaScript (doc courante) : non installés |
| Événements utilisés | SessionStart (startup, resume, clear, compact), UserPromptSubmit, PostToolUse (ExitPlanMode et éditions), SubagentStart, Stop | SessionStart, UserPromptSubmit, SubagentStart, Stop (schémas JSON intégrés, code) | sessionStart, userPromptSubmitted, postToolUse, subagentStart, agentStop (code) | Appels manuels `prompt-cline` et `completion-cline` |
| Injection de contexte | `hookSpecificOutput.additionalContext` (code, test) | `hookSpecificOutput.additionalContext` (code) | `additionalContext` (code) | Sortie JSON lue par l'agent |
| Blocage de fin | `{"decision":"block","reason":…}` ; `last_assistant_message` fourni (code, test) | Même format ; `last_assistant_message` fourni (code) | `decision: block` + `reason` réinjecté comme message utilisateur ; pas de message final : lecture de la transcription (code) | Décision rendue par `completion-cline` |
| Windows | Hooks exécutés par Git Bash ; PowerShell seulement sans Git Bash (code) | Champ `commandWindows` exécuté par PowerShell (code) | Champs `bash` et `powershell` (code) | — |
| Approbation | Hooks de projet après confiance de l'espace de travail ; `/hooks` pour revoir (code) | Hooks nouveaux ou modifiés à revoir avant exécution : « hooks need review » (code) | Non documentée dans le bundle examiné | — |
| Requêtes non tapées | `source` du prompt (`system`, `loop_wakeup`…) et marqueurs de notification ; plan via PostToolUse `ExitPlanMode` | Continuations détectées sur le texte ; pas de hook de sortie de plan utilisé | Brief correctif réinjecté comme prompt, reconnu par son préfixe | — |

Sources consultées : binaire `/opt/claude-code/bin/claude` 2.1.318 ; paquet npm `@openai/codex@0.166.0-linux-x64`
(binaire, 29 octobre 2026) ; paquet npm `@github/copilot@1.0.63` (dernier bundle JavaScript lisible ; la 1.0.105
publiée le 28 octobre 2026 est un binaire compressé non inspectable) ; documentation du dépôt public
`cline/cline` (`docs/customization/skills.mdx`, `cline-rules.mdx`, `hooks.mdx`, `docs/sdk/plugins.mdx`) ;
pages officielles OpenAI `developers.openai.com/codex/skills` et `/codex/hooks` via résultats de recherche
(accès direct refusé par le réseau du conteneur).

## 3. Mécanisme commun

- Source unique `.agents/skills/` ; miroir généré `.claude/skills/` (Claude Code, Cline ; lu aussi par Copilot).
- Un seul moteur `.agents/hooks/agent_lifecycle.py`, configuré par `.agents/hooks/lifecycle.json` ; modes
  `<événement>-<outil>` ; sortie JSON en ASCII pur (échappements `\u`), insensible aux pages de code.
- Lanceurs : `invoke-agent-hook.sh` (POSIX et Git Bash, entrée standard transmise telle quelle) et
  `invoke-agent-hook.ps1` (Windows, copie octet par octet de l'entrée vers un fichier temporaire).
- État par session dans le dossier temporaire du système (`xp-bots-agent-lifecycle/`), pointeur de la dernière
  requête du dépôt (30 minutes), anti-doublon inter-outils (20 secondes), journal d'erreurs
  `xp-bots-lifecycle-errors.log`. Redirection : variable `XPBOTS_LIFECYCLE_STATE_DIR`.
- Fin de requête : marqueur, pied d'audit et portes machine sur les seuls fichiers modifiés depuis le début de
  la requête ; deux passes correctives au plus ; échec ouvert en cas d'erreur interne.

## 4. Activation pas à pas

1. **Claude Code** : ouvrir le dépôt, accepter la confiance de l'espace de travail ; vérifier `/hooks` (cinq
   événements) et `/skills` (seize skills). Sous Windows, installer Git for Windows. Après modification de
   `.claude/settings.json`, revoir les hooks dans `/hooks` ou redémarrer la session.
2. **Codex** : marquer le projet comme fiable, puis approuver les hooks de `.codex/hooks.json` quand Codex les
   signale comme nouveaux ou modifiés ; refaire cette approbation après chaque modification. Si aucun hook ne se
   déclenche avec une version antérieure, activer l'option expérimentale `codex_hooks` dans `~/.codex/config.toml`
   (non vérifié sur la 0.166.0, où l'option figure parmi les alias hérités).
3. **GitHub Copilot** (CLI, agent de dépôt) : les hooks de `.github/hooks/xp-bots-lifecycle.json` sont lus depuis
   la racine du dépôt ; une exécution distante ne voit que les fichiers **commités**.
4. **Cline** : aucun hook ; suivre `.clinerules/xp-bots-cycle.md` (appels explicites au moteur).

## 5. Commandes de vérification

```text
python .agents/hooks/skill_mirrors.py --check
python .agents/skills/xp-bots-maintain-agent-skills/scripts/validate_governance.py
python .agents/skills/xp-bots-request-skill-orchestrator/scripts/select_skills.py --test
python .agents/skills/xp-bots-maintain-agent-skills/scripts/run_governance_suite.py
python .agents/skills/xp-bots-maintain-agent-skills/scripts/run_governance_suite.py --real-repo-negative
python .agents/hooks/agent_lifecycle.py --run-gates
python tools/verify_project.py
```

## 6. Checklist manuelle par outil

| Outil | Détection des skills | Hooks | Injection constatée | Blocage puis levée |
|---|---|---|---|---|
| Claude Code | `/skills` liste les seize skills | `/hooks` montre SessionStart, UserPromptSubmit, PostToolUse, SubagentStart, Stop | Le contexte de début contient « Cycle obligatoire » et le catalogue | Répondre sans pied : le brief `[xp-bots:passe-corrective 1/2]` apparaît ; une réponse avec pied et `[XP-BOTS-AUDIT:OK]` passe |
| Codex | Sélecteur de skills : seize entrées depuis `.agents/skills/` | Approuver les hooks signalés à revoir | Message de statut « XP-Bots : sélection des skills » à chaque prompt | Même scénario que Claude Code |
| Copilot | `/skills` (CLI) | Fichier `.github/hooks/xp-bots-lifecycle.json` commité | Contexte de session « Cycle obligatoire » | Le brief revient comme message ; une réponse conforme termine |
| Cline | Onglet Skills : copies de `.claude/skills/` | Aucun | Sortie de `--mode prompt-cline` | `--mode completion-cline` rend `block` puis `allow` |

## 7. Limites connues

- Codex, Copilot et Cline n'ont pas pu être exécutés dans le conteneur : leurs configurations reposent sur le
  code de leurs paquets publiés et sur la documentation ; leurs tests réels restent à faire sur le poste.
- Le lanceur PowerShell n'a pas été exécuté sous Windows dans cette mise en place ; son comportement est couvert
  par revue et, si PowerShell est disponible, par un essai sur Linux consigné dans le compte rendu.
- Copilot 1.0.105 n'est pas inspectable (binaire compressé) : conventions relevées sur la 1.0.63.
- Copilot lit `.agents/skills/` et `.claude/skills/` : les skills peuvent apparaître en double, avec des
  instructions équivalentes (chemins de ressources réécrits dans la copie).
- Sans Git Bash, Claude Code sous Windows lance les hooks dans PowerShell : la commande `sh` échoue alors
  ouverte et seules les instructions permanentes s'appliquent.
- Copilot ne transmet pas le message final au hook de fin : sans transcription lisible, le marqueur et le pied ne
  sont pas vérifiés (les portes machine restent appliquées).
- Aucun outil de graphe de code n'est configuré : l'audit d'impact repose sur des recherches ciblées (`rg`).
- Disque saturé : les hooks échouent ouverts et n'injectent plus rien ; vérifier l'espace libre et le journal
  d'erreurs avant de soupçonner le code.

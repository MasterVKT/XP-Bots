---
name: xp-bots-llm-integration-contracts
description: "Complément IA distant de XP-Bots (A01–A12) : API distantes Groq, Gemini et OpenAI facultative, aucune inférence locale, schémas d'extraction et de notes, prompts exacts, validateur déterministe, preuve textuelle, veto OFFICIAL_UNSCHEDULED_POLICY et sa fenêtre, snapshot xp-ai-context-v1, IPC atomique, budget partagé et réservation transactionnelle, quotas de tokens, pannes NEUTRAL, PAPER_AB. Utiliser pour concevoir, porter ou auditer le service IA, son contrat de veto ou son budget, et la concordance des exports IA. Déclencheurs : veto IA, complément IA, extension IA, LLM, Groq, Gemini, OpenAI, budget IA, budget partagé, tokens, snapshot, RSS, briefing, llm_contracts.py, schémas et prompts IA, A01–A12."
---
<!-- xp-bots:generated-skill-mirror source=.agents/skills/xp-bots-llm-integration-contracts/SKILL.md generator=.agents/hooks/skill_mirrors.py : ne pas éditer -->
> Copie générée de `.agents/skills/xp-bots-llm-integration-contracts/SKILL.md` par `.agents/hooks/skill_mirrors.py --write`. Ne pas éditer : modifier la source puis régénérer. Répertoire des ressources de ce skill : `.agents/skills/xp-bots-llm-integration-contracts/` ; les chemins de ressources ci-dessous sont relatifs à la racine du dépôt.

# Contrats du complément IA distant

## Ressources

- Autorité : sections A01–A12 des deux spécifications (identiques hors A07 et une partie de A11) ; choix et
  coûts dans `docs/architecture/04_Integration_LLM_API_Choix_Couts_Validation.md`.
- Exports : `config/parametres_IA_integration_v1.json`, `schemas/schema_extraction_LLM_v1.json`,
  `schemas/schema_notes_IA_v1.json`, `prompts/prompts_IA_v1.json`.
- Référence : `reference/llm_contracts.py` (`parse_model_output`, `parse_advisory_output`,
  `build_policy_event`, `make_snapshot`, `overlay_decision`, `combined_entry_allowed`, `reserve_cost_usd`,
  `budget_admits`) ; ni client HTTP, ni persistance, ni verrouillage concurrent.
- État réel du lecteur depuis la phase 8 London : quatre couches communes figées sous
  `xpbots.contexte_ia`, dossier actif `mcl/london-contexte-ia/` ; snapshot complètement validé,
  cache causal avec preuves de réception et reprise pure, port réel BLOCK/NEUTRAL du coordinateur.
  La couture London reçoit des snapshots synthétiques et conserve ComplementAbsent en référence.
  L'oracle overlay_decision retourne avant de valider la fin d'une liste si le premier veto est actif :
  cette limite est testée ; un snapshot malformé entier reste refusé selon A10/A12. Le service,
  les lectures physiques et l'orchestration A/B complète restent à construire.
- Contexte non normatif : `docs/references/IA_Generative_Forex_Scalping_M15_v2.md`.

## Workflow

1. Situer la demande : collecte (A04), extraction et validation (A05), veto (A06), insertion par méthode
   (A07), appels et routeur (A08), budget (A09), cache et IPC (A10), journal (A11), pannes (A12).
2. Lire la fonction de référence correspondante et ses limites avant tout portage ; reproduire ses refus
   (clés en trop, doublons JSON, enums inconnues, citation non présente à l'identique dans le texte transmis).
3. Pour le budget : transaction exclusive avant chaque appel payant, réservation du coût maximal en `Decimal`,
   rapprochement après réponse ; un coût inconnu conserve sa réserve. Plafonds et quotas : valeurs de A09 et
   de l'export IA, jamais recopiées en dur.
4. Tester les cas A14 par des fixtures synthétiques : veto expiré à publication + 900 s exactement, heartbeat
   sans prolongation, snapshot corrompu, futur, en recul ou âgé de plus de 90 s, panne API neutre, deux robots
   consommant un même événement sans second appel.
5. Rejouer `python tests/check_llm.py`, puis `python tools/verify_project.py` ; aucun de ces contrôles n'appelle
   une API.

## Garde-fous

- Le LLM ne choisit jamais entrée, sens, stop, objectif, volume ou durée, et ne produit aucune permission.
- Aucun appel LLM, HTTP ou attente réseau entre le signal et l'ordre ; seule la copie mémoire du snapshot est
  lue (A03).
- Aucune inférence locale, même en secours ; le secours payant reste désactivé par défaut.
- `NEUTRAL` signifie aucun veto supplémentaire, jamais `ALLOW` ; une panne de C05 reste bloquante.
- Une conformité JSON ne prouve ni la qualité sémantique ni une rentabilité ; ne jamais interroger un modèle
  récent sur des news passées pour fabriquer un test « indépendant ».
- Ne jamais lire, afficher ou committer les clés de `.env` ; `.env.example` reste un gabarit vide.

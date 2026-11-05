---
name: xp-bots-completion-audit
description: "Audit de fin XP-Bots à appliquer avant chaque réponse finale, sans exception : double contrôle bidirectionnel de complétion, impact et non-régression, vérification adversariale, couverture des skills, inventaire des problèmes, plan de remédiation exécuté (deux passes au plus), pied d'audit vérifié par la machine et marqueur exact. Déclencheurs : fin de requête, audit, triple check, vérifier que tout est fait, passe corrective, brief correctif, pied d'audit, marqueur XP-BOTS-AUDIT."
---

# Audit de fin XP-Bots

## Workflow

1. **Complétion bidirectionnelle.** Lister les exigences de la requête d'origine (pas seulement du plan
   suivi). Chaque exigence pointe vers un résultat, un fichier, une commande exécutée, une observation ou une
   limite déclarée ; chaque fichier modifié (`git status --short`) pointe vers une exigence autorisée. Tout
   élément non relié est une omission ou un écart de périmètre jusqu'à preuve du contraire.
2. **Impact et non-régression.** Chercher les usages des éléments modifiés (`rg`, outil de graphe s'il est
   configuré), puis vérifier dans la source courante. Exécuter les validations les plus proches du risque :
   `python tools/verify_project.py` pour les ressources métier,
   `python .agents/skills/xp-bots-maintain-agent-skills/scripts/run_governance_suite.py` pour la gouvernance.
   Distinguer un échec préexistant (prouvé sur l'état initial) d'une régression introduite.
3. **Vérification adversariale.** Tenter de réfuter le résultat par une autre voie que l'implémentation :
   relecture à contexte vierge si l'outil le permet, sinon grille structure, liens, schémas, artefacts
   générés, contrats, permissions, configuration, documentation. Spécifique XP-Bots : concordance des deux
   spécifications avec `config/`, `schemas/`, `prompts/` ; ressources protégées intactes ; code de référence
   jamais présenté comme composant opérationnel.
4. **Couverture des skills.** Appliquer `xp-bots-skill-gap-detector` et reporter son classement.
5. **Inventaire** des problèmes, en tableau : identifiant, type (omission, régression, écart, défaut), preuve,
   fichier ou symbole, gravité, correction, validation.
6. **Plan de remédiation** ordonné, exécuté immédiatement après avoir rechargé l'orchestrateur, dans la limite
   de deux passes. Après deux échecs : livrer les blocages avec leurs preuves et le marqueur de blocage.
7. **Pied d'audit et marqueur** en toute fin de réponse (format ci-dessous).

## Portes machine

Le hook de fin exécute les portes déclarées dans `.agents/hooks/lifecycle.json` sur les seuls fichiers
modifiés depuis le début de la requête : portes rapides bloquantes (JSON strict, syntaxe Python, liens
Markdown, gouvernance) puis suites globales indicatives. Une porte bloquante en échec impose une passe même si
le marqueur est présent. Rejouer à la main : `python .agents/hooks/agent_lifecycle.py --run-gates`.

## Pied d'audit

Les quatre clés et les deux marqueurs sont lus littéralement par `.agents/hooks/agent_lifecycle.py` ; ne
jamais changer leur forme sans mettre à jour simultanément le moteur, sa configuration et ses tests.

```text
Pied d'audit XP-Bots
- completion: exigences prouvées / total, écarts éventuels
- impact: méthode de recherche, régressions trouvées ou « aucune »
- verifications: commandes exécutées et résultats
- couverture_skills: couvert / étendre / créer / consigner
[XP-BOTS-AUDIT:OK]
```

Marqueur de succès : `[XP-BOTS-AUDIT:OK]`. Marqueur de blocage assumé : `[XP-BOTS-AUDIT:BLOQUE]`, seulement
quand un blocage prouvé subsiste et est expliqué, y compris une question de clarification ou une attente de
l'humain (motif « en attente de réponse » dans la clé `completion`). Réservés au fil principal : jamais dans
une sous-tâche.

## Garde-fous

- Ne jamais ajouter de dépendance, de migration métier, d'action destructive ni de changement hors périmètre
  pour faire passer l'audit.
- Ne changer ni paramètre figé, ni empreinte attendue, ni preuve historique pour masquer un échec.
- Une vérification impossible est déclarée comme limite, jamais remplacée par une supposition.
- La migration de MCL vers `.agents/skills/` est une opération de gouvernance tracée dans
  `.agents/agent-integrations.json`, pas une correction métier.

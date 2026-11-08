---
name: xp-bots-risk-execution-contracts
description: "Contrats communs d'exécution et de risque de XP-Bots (C06–C09, aspects temps réel de C03) : TTL de signal et fraîcheur des cotations, prix exécutables Bid/Ask, conversion du stop, objectif, dimensionnement all-in à 0,5 %, réserve de glissement, coordinateur de compte partagé, réservations atomiques, priorités, ordres protégés, accusés ambigus, rapprochement, sorties obligatoires, gardes de perte quotidienne et globale, journal et motifs de refus. Utiliser pour concevoir ou vérifier le coordinateur, l'adaptateur d'exécution ou le dimensionnement. Déclencheurs : risque, dimensionnement, volume, lot, marge, spread, glissement, stop-loss, take profit, ordre, exécution, coordinateur, drawdown, MIN_VOLUME_OR_RISK_REJECT, C06, C07, C08, C09."
---
<!-- xp-bots:generated-skill-mirror source=.agents/skills/xp-bots-risk-execution-contracts/SKILL.md generator=.agents/hooks/skill_mirrors.py : ne pas éditer -->
> Copie générée de `.agents/skills/xp-bots-risk-execution-contracts/SKILL.md` par `.agents/hooks/skill_mirrors.py --write`. Ne pas éditer : modifier la source puis régénérer. Répertoire des ressources de ce skill : `.agents/skills/xp-bots-risk-execution-contracts/` ; les chemins de ressources ci-dessous sont relatifs à la racine du dépôt.

# Contrats d'exécution et de risque partagés

## Ressources

- Autorité : sections C06, C07, C08 et C09, identiques dans les deux spécifications de
  `livrables/strategies_m15/` ; valeurs dans le bloc `common` de `config/parametres_figes_v3.json`.
- État réel : journal du noyau et quinze couches du coordinateur partagées sous `xpbots.execution.c*`,
  suivies dans `mcl/london-execution-coordinateur/` (bilan et contrats). Le cycle C08, les sorties, le rapprochement et
  l'enveloppe sont figés ; S4 les exécute en papier synthétique explicite. L'adaptateur réel et la persistance physique restent à construire.
- Référence partielle : `rounded_levels` de `reference/technical.py` (niveaux arrondis et réserve), oracle
  des seuls tests. Le dimensionnement de phase 5 utilise un port courtier synthétique ; il ne constitue
  ni un portefeuille validé financièrement ni un modèle de remplissages réels.

## Workflow

1. Identifier le contrat touché et relire sa section : C06 (cotation, spread, écart d'entrée, conversion
   `B_SL` → SL exécutable, TP), C07 (budget gelé, `risque_all_in(v)`, cinq contraintes simultanées, arrondi vers
   le bas, gardes quotidienne et globale), C08 (ordre des traitements, clé d'intention persistante, timeout
   ambigu, protections, échéances de sortie, redémarrage), C09 (champs du journal, motifs minimaux).
2. Écrire d'abord le contrat de l'unité (entrées, sorties, motifs de refus) avant le code ; les motifs de refus
   sont ceux de C09, sans en inventer de synonymes.
3. Tester les cas de C11 (points 2, 5, 6, 7, 10, 11, 12 et 13) sur le composant réel : spread au plafond admis,
   TTL de cinq secondes expiré exclu, volume minimal au-delà du budget refusé, réservations atomiques entre
   deux robots, remplissage partiel et accusé inconnu sans doublon, arrêt non réinitialisé par un redémarrage.
4. Comparer les niveaux calculés à `rounded_levels` sur les exemples chiffrés S01.5 et S02.5.
5. Rejouer `python tools/verify_project.py` ; documenter tout écart entre code, texte et JSON comme défaut.

## Garde-fous

- Le spread est déjà dans les prix exécutables : ne jamais l'ajouter une seconde fois au risque.
- Pas de lot minimal forcé, de stop rapproché ou de risque augmenté pour atteindre le volume minimal :
  `MIN_VOLUME_OR_RISK_REJECT`.
- Une réponse d'ordre inconnue n'est pas un rejet : verrouiller et rapprocher avant toute nouvelle intention.
- Les profits flottants ne libèrent pas le risque réservé ; les robots ne clôturent jamais une position d'un
  autre propriétaire.
- Le levier change la marge, pas la perte au stop d'une même position.
- Aucun appel LLM ni réseau entre le signal et l'ordre (A03) : seul le snapshot mémoire est consulté.

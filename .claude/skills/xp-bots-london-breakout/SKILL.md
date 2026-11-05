---
name: xp-bots-london-breakout
description: "Méthode S02 London Breakout M15 (LONDON_V3) de XP-Bots : range fixe 02:00–07:00 Europe/London de 20 M15, ATR14 H1 figé à 07:00 et largeur admissible 0,50–4,00, fenêtre 08:00–11:00, bougie de cassure (buffer, corps 40 %, clôture 65 %), stop local à trois composantes, objectif 2 D, quotas deux entrées par jour et une par sens, veto IA A07. Utiliser pour concevoir, porter, tester ou vérifier le moteur London et ses horaires Londres/UTC. Déclencheurs : London, breakout, cassure, range London, 02:00–07:00, ATR H1, quotas, S02, LONDON_V3, spécification 02."
---
<!-- xp-bots:generated-skill-mirror source=.agents/skills/xp-bots-london-breakout/SKILL.md generator=.agents/hooks/skill_mirrors.py : ne pas éditer -->
> Copie générée de `.agents/skills/xp-bots-london-breakout/SKILL.md` par `.agents/hooks/skill_mirrors.py --write`. Ne pas éditer : modifier la source puis régénérer. Répertoire des ressources de ce skill : `.agents/skills/xp-bots-london-breakout/` ; les chemins de ressources ci-dessous sont relatifs à la racine du dépôt.

# Méthode S02 — London Breakout

## Ressources

- Autorité : `livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md`, sections S02.1–S02.6,
  C03 (temps, H1), C06 (conversion des prix) et A07 (insertion du veto IA).
- Valeurs : bloc `london` de `config/parametres_figes_v3.json`.
- Référence de comparaison : `reference/technical.py` (`london_signal`, `london_setups`,
  `local_decision_in_window`, `rounded_levels`).

## Workflow

1. Relire S02.1 : exactement 20 M15 ouvertes de 02:00 à 06:45 Londres, toutes valides ; gel de `A_H1` sur la
   dernière H1 clôturée au plus tard à 07:00, initialisée sur au moins 300 H1 et âgée d'au plus une heure.
2. Vérifier les horaires sur les deux régimes d'heure (été/hiver britanniques) : première clôture 08:15,
   dernière 10:45, aucune entrée sur la clôture de 11:00, sortie forcée 12:00 ou 7 200 s.
3. Lire `london_signal` et `london_setups` : ils ne gèrent ni quotas après fill, ni position, ni fondamental ;
   lister ce que le robot réel ajoute (S02.4, C07, C08).
4. Couvrir S02.6 et C11 par des tests du robot réel : W/A_H1 exactement 0,5 ou 4 admis, égalité au niveau plus
   buffer refusée, stop local `min/max` à trois composantes, conversion short en Ask, objectif 2 D, quota du sens
   compté au premier fill partiel, veto A07 sur la seule bougie courante.
5. Rejouer : `python tests/check_technical.py`, puis `python tools/verify_project.py`.
6. Pour une construction complète du moteur, enchaîner avec `xp-bots-mcl-robot-planning`.

## Garde-fous

- Ne jamais raccourcir le range, déplacer ses extrêmes ou remplacer une bougie après observation de la cassure ;
  range invalide = aucune entrée ce jour pour ce symbole.
- Une H1 partielle ou reçue après la décision n'entre jamais dans le gel ; pas de vote directionnel H1.
- Aucun franchissement récent requis (`fresh_close_cross_required` faux), aucun retest, aucune sortie sur
  retour dans le range.
- Un refus sans fill ne consomme pas le quota du sens ; un veto IA expiré n'autorise aucun rattrapage sur
  l'ancienne bougie.
- Utiliser `Europe/London` (base IANA), jamais un décalage UTC constant.

---
name: xp-bots-validation-replay
description: "Validation et rejeu de XP-Bots (C10–C11, A13–A15) : blocs chronologiques fixés avant chargement, expériences par bloc et rejeu continu à 100 USD, scénarios de coûts de référence et de stress, critères a priori (effectifs, espérance, profit factor, drawdown, rétention 80 %, fréquence), bootstrap de blocs de cinq jours, six perturbations de voisinage, comparaison V1/V3, protocole PAPER_AB, qualification sémantique et financière de l'IA, cas d'acceptation du robot réel. Utiliser pour planifier ou auditer un backtest, un rejeu, un test A/B ou une conclusion de rentabilité. Déclencheurs : validation, backtest, rejeu, replay, simulation, PAPER_AB, A/B, bootstrap, profit factor, espérance, drawdown, rentabilité, rétention, stress, test réservé, cas d'acceptation, C10, C11, A13, A14."
---

# Validation, rejeu et critères d'acceptation

## Ressources

- Autorité : C10, C11, S01.6 ou S02.6, A13, A14 des spécifications ; protocole de collecte en section 5 de
  `docs/data/03_Donnees_Historiques_Requises_et_Validation.md` ; valeurs `financial_*` et `bootstrap_*` de
  `config/parametres_IA_integration_v1.json`.
- Contrôles existants (hors ligne, synthétiques) : `tests/check_technical.py`, `tests/check_llm.py`,
  `tools/verify_project.py`. Composant construit depuis la phase 10 London : `src/xpbots/rejeu/c*`, huit unités figées dans `mcl/london-journal-rejeu/`. Le moteur reste `MoteurDecision` ; le rejeu archivé ne consulte aucun backend. L’esquisse EMA `mcl/journal-rejeu/` reste historique.

## Workflow

1. Classer la demande : contrôle de contrat (synthétique), test du robot réel (C11, A14), rejeu historique
   (C10), expérience A/B (A13), conclusion économique. Chacune a ses preuves et ses limites.
2. Pour un rejeu : fixer avant chargement les blocs de C10, le scénario de référence (délai 250 ms, un tick
   adverse) et le stress (spread ×1,25, 1 000 ms, deux ticks adverses) ; reproduire ordre intrabougie SL/TP,
   spread variable et TTL de cinq secondes ; chaque robot seul puis les deux sur un unique compte.
3. Calculer les critères a priori sans les retoucher : effectifs, espérance nette, profit factor, drawdown de
   fonds propres avec arrêt à 10 % réellement appliqué, rétention `N_V3 / N_V1`, fréquence avec jours à zéro ;
   bootstrap de blocs de cinq journées avec graine et réplications de l'export ; six perturbations rapportées
   sans sélection.
4. Pour PAPER_AB : deux portefeuilles complets rejoués à 100 USD, coût IA réel déduit une seule fois,
   effectifs minimaux de A13 ; réponses LLM archivées rejouées, jamais réinférées.
5. Vérifier que les contrôles existants restent verts : `python tools/verify_project.py` (inclut les deux
   suites) et rapporter leurs effectifs depuis `.local/reports/`.

## Garde-fous

- Un résultat insuffisant signifie « non validé », jamais une retouche jusqu'à obtenir une courbe gagnante ;
  les seuils sont des choix de gouvernance fixés a priori.
- Ne jamais soustraire encore les réserves de glissement du P&L ; ne pas additionner les courbes de comptes
  séparés ; un redémarrage n'est pas une récupération de drawdown.
- Référence nulle : rétention N/A, jamais 100 % ; référence < 50 trades : comparaison trop faible.
- Les contrôles du dépôt ne prouvent ni l'exécution des quatorze cas C11 sur un robot de courtier, ni la
  qualité d'une API jamais appelée, ni un gain financier.

## API de rejeu disponible

`c1a_ticks` exige un manifeste, vérifie l’empreinte avant exposition du lot et
ne trie ni ne comble les trous. `c1b_simulateur` consomme profils et tarifs datés.
`c2_executeur.executer_experience` compose les vrais moteur, coordinateur et
contrôles ; une fabrique de contrôles fraîche est obligatoire. L’accès au réservé
est gardé avant le lecteur. Les jours Forex sont distincts des jours de l’or.
`c3_rapports.produire_rapport` expose critères et preuves manquantes ; les fixtures
restent NON_VALIDE. Une facture réelle, même nulle, documente la consommation IA ;
sa simple absence n’est pas une gratuité. L’attestation A13 vérifie aussi le
maintien de C10 sous le gel. Les références V1 et observations de démonstration
sont des entrées explicites, jamais fabriquées par le rapport.
S1/S5 délèguent à ce bloc ; la CLI synthétique expose `--couts REFERENCE|STRESS`.
Le scénario `SYNTHETIQUE_S5` est une compatibilité explicite de tests de frontière,
indisponible dans la CLI. Aucun résultat de cette commande ne qualifie C04/C10.

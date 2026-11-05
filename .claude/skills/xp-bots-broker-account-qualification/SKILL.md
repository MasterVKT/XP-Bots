---
name: xp-bots-broker-account-qualification
description: "Qualification du compte et des instruments réellement disponibles pour XP-Bots (C04) : compte standard USD 100 USD levier 1:100, lecture des caractéristiques du courtier (symbole exact, contrat, tick, volume minimal et pas, frais, marge, stop-out, horaires, netting ou hedging), contrats micro, règle de liaison d'un seul symbole par sous-jacent, ENVIRONMENT_NOT_READY, faisabilité du volume minimal à 0,5 % de risque. Utiliser pour choisir ou vérifier un courtier, une plateforme (MT5 ou autre) ou un symbole, et avant tout backtest ou démo. Déclencheurs : courtier, broker, Deriv, FBS, FXCM, MT5, MQL5, compte standard, contrat micro, symbole, volume minimal, levier, OrderCalcMargin, C04."
---
<!-- xp-bots:generated-skill-mirror source=.agents/skills/xp-bots-broker-account-qualification/SKILL.md generator=.agents/hooks/skill_mirrors.py : ne pas éditer -->
> Copie générée de `.agents/skills/xp-bots-broker-account-qualification/SKILL.md` par `.agents/hooks/skill_mirrors.py --write`. Ne pas éditer : modifier la source puis régénérer. Répertoire des ressources de ce skill : `.agents/skills/xp-bots-broker-account-qualification/` ; les chemins de ressources ci-dessous sont relatifs à la racine du dépôt.

# Qualification du courtier, du compte et des instruments

## Ressources

- Autorité : section C04 des deux spécifications ; faisabilité chiffrée dans
  `docs/decisions/00_Decision_Conception_et_Faisabilite_V3.md` (sections 4 et 5).
- Données requises du contrat : section 3 de `docs/data/03_Donnees_Historiques_Requises_et_Validation.md`.
- Preuve publique datée, non contractuelle : `docs/validation/snapshot_public_Deriv_2026-11-04.json` et
  `docs/validation/diagnostic_faisabilite_v3.json` (aucun P&L).

## Workflow

1. Établir la fiche d'environnement de C04 pour le compte réel : entité, serveur, plateforme, compte, devise,
   levier, mode netting/hedging ; par symbole, toutes les caractéristiques listées en C04. Une valeur absente
   reste inconnue (jamais zéro) et produit `ENVIRONMENT_NOT_READY`.
2. Vérifier la faisabilité du volume minimal avant tout autre travail : risque all-in au volume minimal
   (C07, entrée et sortie pessimistes, frais réels) comparé au budget de 0,5 % des fonds propres.
3. Appliquer la règle de liaison de C04 : un seul symbole par sous-jacent, la plus petite exposition minimale
   vérifiée, puis le coût aller-retour documenté, puis l'ordre lexical ; consigner ce choix pour le déploiement
   et le backtest, sans bascule automatique ni mélange d'historiques.
4. Sur MT5, utiliser les fonctions natives citées en C04 (`OrderCalcProfit`, `OrderCalcMargin`,
   `OrderCheck`) en sachant que `OrderCalcMargin` ignore les positions déjà ouvertes.
5. Rédiger la conclusion : profil admissible, ou « compte incompatible avec la fréquence visée » (C10), sans
   déformer le risque ; conserver la fiche horodatée hors des preuves historiques (`.local/reports/` ou dossier
   privé ignoré par Git).

## Garde-fous

- Compte standard et contrat standard ne sont pas synonymes ; un tableau public ne prouve ni la disponibilité
  d'un contrat micro sur le compte de l'utilisateur, ni son pas, ni ses frais.
- Ne jamais remplacer un symbole Forex ou or par un indice synthétique ni arrondir un volume à la hausse.
- Les caractéristiques du courtier sont des données d'environnement, pas des paramètres de stratégie à deviner.
- Aucun identifiant, mot de passe ou numéro de compte dans le dépôt ; ne jamais passer d'ordre réel pour
  « tester » une caractéristique.
- XAUUSD reste spécifié mais non retenu comme praticable à 100 USD dans les configurations examinées.

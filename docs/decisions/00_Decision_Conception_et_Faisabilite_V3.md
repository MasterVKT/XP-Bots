# Deux méthodes M15 retenues — Décision de conception V3

**Mise à jour documentaire 3.1.0 : l’intégration LLM distante est désormais incluse directement dans les fichiers 01 et 02, sections A01–A15. Voir 04_Integration_LLM_API_Choix_Couts_Validation.md pour la décision et l’audit du document fourni. Le diagnostic chiffré ci-dessous reste celui du noyau technique V3.0, sans LLM.**

**4 novembre 2026 — Compte standard USD, 100 USD, levier 1:100.**

Je retiens deux versions séparées : **Triple EMA15/25/50 + RSI14 + repli**, et **London Breakout avec stop local de cassure**. Les règles sont entièrement chiffrées dans leurs fichiers autonomes pour un agent IA. Ce sont les versions de conception que je privilégie maintenant, **candidates à une validation économique**. Les données disponibles ne permettent pas de les qualifier de meilleures stratégies mondiales ni de garantir une rentabilité ou une rétention de 80 % des transactions.

Avec un minimum de 1 000 unités Forex, le compte de 100 USD reste trop contraint pour la fréquence visée dans le diagnostic. L'accès vérifié à des contrats de plus petite exposition constitue la piste la plus utile pour EURUSD/GBPUSD. **L'or n'est pas retenu comme instrument économiquement praticable avec 100 USD et 0,5 % de risque dans les configurations examinées**, même au minimum de 0,1 once du diagnostic. Les profils techniques XAUUSD sont néanmoins intégralement spécifiés pour leur évaluation.

## 1. Choix techniques précis

| Paramètre | Triple EMA + RSI + repli | London Breakout |
|---|---|---|
| Déclenchement | Reprise après contact EMA15–EMA50 | Clôture admissible hors du range + buffer |
| Base | EMA15/25/50, RSI14 Wilder | Range 02:00–07:00 Londres, 20 M15 |
| Tendance | EMA ordonnées et pente EMA50 sur 4 barres | Aucune condition d'EMA/RSI |
| RSI | Repli long ≥40 / court ≤60 ; signal long ≥50 / court ≤50 | Aucun RSI |
| Horizon de repli | 8 bougies maximum, contact antérieur admis | Pas de retest obligatoire |
| Qualité de signal | Corps directionnel, clôture dans les 35 % favorables | Corps ≥40 % du range de bougie, clôture dans les 35 % favorables |
| ATR | ATR14 M15 précédent ; buffer 0,10 ATR | ATR14 M15 précédent ; buffer cassure 0,05 ATR ; guard 0,10 ATR |
| H1 | Aucun filtre directionnel | Largeur de range entre 0,50 et 4,00 ATR14 H1 figé à 07:00 |
| Stop | Au-delà de l'extrême du repli et au moins 0,80 ATR depuis la clôture | Derrière la bougie, au moins 0,25 ATR dans le range et 0,80 ATR depuis la clôture |
| Distance technique maximale | 2,50 ATR ; refus si plus large | 2,50 ATR ; refus si plus large |
| Objectif brut | 1,50 fois la distance entrée–SL | 2,00 fois la distance entrée–SL |
| Fenêtre des bougies | Ouverture ≥08:00, clôture <16:00 Londres | Ouverture ≥08:00, clôture <11:00 Londres |
| Sortie au plus tard | 16:00 Londres ou 2 h après fill | 12:00 Londres ou 2 h après fill |
| Maximum d'entrées remplies | 6 par symbole/jour Londres | 2 par symbole/jour, une par direction |
| Risque par entrée | 0,50 % des fonds propres, frais et réserve compris | Identique |

Autres réglages communs : plafond de spread EURUSD **1,5 pip**, GBPUSD **2 pips**, XAUUSD **0,50 USD/once** ; réserve de glissement **0,05 ATR par jambe** ; gap maximal d'entrée **0,25 ATR** ; validité du signal **5 s** ; cotation âgée au plus de **2 s**. Stop et objectif attachés à l'entrée ; aucun trailing, break-even, martingale ou objectif partiel.

Les deux robots sur un compte commun : risque initial réservé total ≤**1 %**, au plus **deux positions**, une par sous-jacent, marge totale ≤**un tiers des fonds propres** ; arrêt quotidien à **−2 %** et arrêt persistant à **−10 % du pic de fonds propres**. Aucun de ces seuils ne garantit la perte maximale en cas de gap.

Les heures sont celles de Londres avec changement d'heure. À Douala, 08:00 Londres correspond à 09:00 en hiver britannique et 08:00 en été. La fin de fenêtre est exclue : un signal EMA à 16:00 ou Londres à 11:00 est trop tardif.

## 2. Pourquoi je retiens ces modifications

Le repli précédent exigeait simultanément plusieurs pentes, une tenue très stricte du RSI et une nouvelle touche de zone sur la bougie de signal. La V3 simplifie cette interprétation tout en gardant tendance, repli et reprise objectivement mesurables. La tolérance du RSI pendant le repli évite de traiter toute respiration comme une inversion ; l'absence de sortie automatique à RSI70/30 évite de supposer qu'une tendance doit s'arrêter à ce seuil. [Définition et comportement du RSI, Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI).

Le stop London à l'autre extrémité du range obligeait à financer toute la largeur nocturne. Le stop local exprime une invalidation plus proche de la cassure, avec garde et plancher de volatilité. Cela réduit mathématiquement l'exposition financière minimale nécessaire à un stop donné ; la possibilité d'être stoppé plus souvent doit être mesurée. L'ATR fournit une unité de volatilité, pas une direction ni une garantie de profit. [ATR, Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr).

J'écarte l'empilement de confirmations et les seuils élus comme « meilleurs » après les milliers de comparaisons précédentes. La conception favorise un nombre limité de mécanismes interprétables. La sélection a posteriori de la meilleure courbe parmi beaucoup d'essais augmente le risque de surajustement. [Bailey et collaborateurs](https://www.davidhbailey.com/dhbpapers/overfitting.pdf).

L'objectif EMA passe de 2R à 1,5R et London est ancré à 2R exécutables plutôt qu'à une projection de largeur de range. Ces choix fixent clairement le compromis gain/perte et l'horizon intraday ; leur effet sur l'espérance n'est pas connu. Hors coûts additionnels, les taux d'équilibre théoriques sont respectivement 40 % et 33,33 % si toutes les sorties se faisaient exclusivement à ces TP/SL. Les sorties horaires, gaps et frais modifient ces chiffres. Aucun taux de réussite réalisé n'est annoncé.

## 3. Sort des dix éléments proposés

| Élément | Décision V3 et rôle |
|---|---|
| Multi-timeframe | H1 actif pour normaliser la largeur du range London ; aucun accord directionnel H1 obligatoire |
| Fibonacci | Exclu des décisions ; aucun ancrage discrétionnaire ni niveau imposé |
| Bollinger | Exclu ; pas de filtre de largeur supplémentaire ou de sortie à la touche |
| ATR | Actif : unités de stop, buffers, contrôle des bougies, réserve de glissement et range H1 |
| Pivots journaliers | Exclu des entrées et sorties ; aucun avantage établi dans les essais précédents |
| Figures chartistes | Repli/reprise et cassure de range définis objectivement ; aucun double sommet/creux rare exigé |
| MFI | Exclu ; aucun besoin de volume global inexistant pour le Forex de gré à gré |
| Momentum | RSI et corps/clôture de bougie déjà utilisés ; aucun ROC additionnel obligatoire |
| DXY | Exclu du noyau ; le module fondamental externe peut employer ses propres données sans vote technique redondant |
| Croisement des moyennes | Ordre des EMA actif dans le repli ; aucun croisement récent exigé à chaque entrée |

L'expérience antérieure a couvert les 1 024 sous-ensembles de dix définitions fixes par méthode. Cela ne permet pas d'élire tous les usages ou réglages possibles d'un indicateur. Les V3 modifient le noyau et ne reprennent pas une combinaison gagnante sélectionnée dans cette matrice.

## 4. Diagnostic réellement effectué sur cette conception

Cache M1 Bid/Ask Dukascopy ; **11 mai–3 novembre 2026**, après préchargement à partir du 20 avril. Le début d'évaluation permet les 1 000 M15 et 300 H1 requises. Cette période était déjà exposée à la recherche précédente.

Le diagnostic calcule les configurations techniques et la possibilité de financer **le volume minimal**, avec le spread coté et les réserves de glissement V3. Il n'applique ni les positions déjà ouvertes, ni les quotas de fills, ni les permissions fondamentales, ni les annonces, ni l'exécution du courtier. **Il ne calcule aucun profit, aucun drawdown et aucune rétention effective de transactions.** Plusieurs configurations peuvent correspondre au même mouvement ou être simultanées.

Les ouvertures Bid et Ask M1 sont co-étiquetées à la même minute, sans preuve qu'elles proviennent du même tick synchrone ; ce n'est donc pas une cotation d'exécution reconstituée à la milliseconde. Les archives locales ont été récupérées par HTTP après échec d'HTTPS sur le flux historique ; leurs empreintes identifient les octets sans authentifier la source.

| Méthode | Symbole | Configurations techniques | Après spread/gap/cotation | Potentiellement finançables à 100 USD : minimum normal | Idem : exposition micro publique | Capital p80 au minimum normal, borne inférieure USD |
|---|---|---:|---:|---:|---:|---:|
| EMA | EURUSD | 234 | 234 | 37 | 234 | 200,90 |
| LONDON | EURUSD | 121 | 121 | 12 | 121 | 210,08 |
| EMA | GBPUSD | 251 | 249 | 3 | 249 | 278,45 |
| LONDON | GBPUSD | 164 | 164 | 2 | 164 | 275,53 |
| EMA | XAUUSD | 259 | 62 | 0 | 0 | 3156,67 |
| LONDON | XAUUSD | 126 | 36 | 0 | 0 | 3155,45 |

Minimum normal hypothétique : **1 000 unités** EURUSD/GBPUSD, **1 once** XAUUSD. Exposition micro publique diagnostiquée : **100 unités** Forex, **0,1 once** or. Les deux profils utilisent ici les **mêmes prix Dukascopy** ; ce ne sont pas des historiques de spreads Deriv.

Le « capital p80 » est le 80e percentile du capital nécessaire pour financer chaque configuration au **volume minimal**, sous la limite de risque et de marge, après les gardes de cotation. Les commissions sont exclues, aucune simultanéité de positions n'est simulée : c'est une **borne inférieure de faisabilité**, pas une proposition de dépôt ni une validation de la rétention de 80 % des trades. Le contrat micro divise cette exposition par dix dans le diagnostic, sans fabriquer de rentabilité.

L'or est très pénalisé à la fois par son stop et par le plafond de spread : seules 62/259 configurations EMA et 36/126 London passent les gardes de cotation, avant les refus de capital. Ce constat interdit de déclarer le seuil de 80 % satisfait pour XAUUSD.

Deux conceptions de fréquence ont été examinées : un brouillon London avec range 00:00–07:00 et franchissement récent obligatoire, puis la version retenue 02:00–07:00 sans franchissement récent obligatoire. Le brouillon donnait seulement 25 configurations EURUSD et 35 GBPUSD. Ces deux changements ont été faits après observation des **comptages**, sans calcul ni sélection de P&L. La conception finale reste donc exploratoire, même si ses paramètres sont maintenant gelés. Aucune nouvelle optimisation de profit n'a été exécutée.

## 5. Le point décisif pour ton compte

À 100 USD et 0,5 % de risque, le budget vaut 0,50 USD. Avec 1 000 unités EURUSD/GBPUSD, un pip vaut 0,10 USD : cinq pips entre entrée exécutable et stop utilisent déjà ce budget avant frais et réserves supplémentaires. Le levier modifie la marge, pas le montant de perte d'une même position à son stop.

Le [tableau officiel Deriv](https://deriv.com/trading-specifications), relevé en HTTPS et conservé dans le dossier, affiche des symboles micro aux expositions minimales plus faibles. Il **ne garantit pas** leur disponibilité sur ton compte standard ni leurs frais. Le robot devra vérifier le contrat dans le terminal. Les minima publiés par [FXCM](https://www.fxcm.com/markets/help/trading-station-desktop-what-is-the-smallest-trade-i-can-place/) et les caractéristiques des autres courtiers ne doivent pas être confondus avec cette offre.

**Mon choix pratique : étudier d'abord EURUSD, puis GBPUSD, sur une exposition minimale effectivement compatible avec 0,50 USD de risque.** Je ne retiens pas un élargissement du risque pour obtenir artificiellement plus d'opérations. Une impossibilité de dimensionnement ne doit jamais devenir un lot minimal forcé.

## 6. Analyse fondamentale et validation à réaliser

Chaque méthode possède un contrat précis vers l'agent fondamental : permissions ANY/LONG_ONLY/SHORT_ONLY, états ALLOW/NO_NEW/FLATTEN, séquence, heure de connaissance et validité maximale **15 minutes**. Un message absent ou périmé bloque les nouvelles entrées en mode combiné ; un changement de direction ne clôture pas automatiquement une position.

Les annonces HIGH concernées imposent la fermeture et l'absence d'entrée de **15 minutes avant à 15 minutes après**. Cela peut réduire la fréquence ; le comparatif V1/V3 doit utiliser le même flux fondamental et les mêmes annonces. Aucun bénéfice du fondamental n'est présumé.

Il faut des **ticks Bid/Ask EURUSD, GBPUSD et XAUUSD du 2 décembre 2019 au 3 novembre 2026 inclus**, les caractéristiques/frais du futur compte et le calendrier d'annonces. Pour tester l'ensemble, il faut aussi les permissions historiques causales du modèle fondamental. Le fichier 03 détaille les champs, les bornes UTC et la séparation des périodes ; DXY et volumes ne sont pas nécessaires.

Les essais précédents ont montré pourquoi les coûts doivent être centraux. Des travaux de banque centrale sur d'autres règles intraday n'ont pas trouvé d'excès de rendement avec coûts réalistes ; cela ne tranche pas nos V3, mais interdit de déduire la profitabilité de la seule élégance des signaux. [Neely et Weller](https://fraser.stlouisfed.org/docs/publications/frbsl_wp/1999-016.pdf).

## 7. Ressources actuelles et contrôles

Les deux spécifications autonomes à jour sont conservées aux chemins Git historiques :

- [Triple EMA + RSI + repli](../../livrables/strategies_m15/01_Triple_EMA_RSI_Repli_M15_Specification_IA.md).
- [London breakout](../../livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md).
- [Données historiques et protocole](../data/03_Donnees_Historiques_Requises_et_Validation.md).
- [Paramètres techniques figés](../../config/parametres_figes_v3.json).
- [Diagnostic historique sans P&L](../validation/diagnostic_faisabilite_v3.json).
- [Caractéristiques publiques Deriv, non contractuelles pour le compte](../validation/snapshot_public_Deriv_2026-11-04.json).
- [Contrôles actuels et leur portée](../validation/README.md).

Le triple contrôle porte sur les documents et les fonctions de référence. Il ne remplace ni la construction des robots de plateforme ni leurs tests sur ticks, démo et conditions de compte.

Les fonctions utiles ont une seule copie dans `reference/`. Les contrôles courants utilisent des séries synthétiques et ne demandent ni cache de prix ni clé API. Depuis la racine : `python tools/verify_project.py`.

Les anciens générateurs, résultats détaillés, V1/V2/V3.0, archives ZIP et caches M1 sont conservés hors du dépôt avec leurs empreintes. Leur emplacement et la méthode de récupération figurent dans le [registre de nettoyage](../maintenance/NETTOYAGE_ET_MERGE.md). Les gains/transactions de leurs simulations ne sont pas attribués aux stratégies actuelles.

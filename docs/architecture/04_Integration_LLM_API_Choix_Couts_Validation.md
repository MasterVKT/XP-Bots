# Intégration LLM des deux stratégies — choix, coûts et validation

**Version documentaire 3.1.0 — 4 novembre 2026 — API distantes uniquement.**

La solution retenue utilise un LLM pour comprendre des textes officiels, préparer des briefings et auditer les résultats. Elle définit aussi un veto étroit sur des décisions monétaires imprévues, à tester en A/B. Les deux méthodes gardent leurs règles techniques et leur risque de 0,5 % ; l'analyse fondamentale externe reste obligatoire.

**Aucune preuve ne permet de promettre que cette intégration rendra automatiquement ces robots beaucoup plus rentables.** La priorité pratique est un service gratuit partagé, sans appel dans le chemin d'entrée, sans inférence locale et avec une comparaison économique complète.

## 1. Solution retenue et budget

| Rôle | Solution | Dépense supplémentaire prévue |
|---|---|---|
| API principale | Groq gratuit, openai/gpt-oss-120b, JSON strict | 0 USD si offre gratuite du compte confirmée |
| Secours gratuit | Gemini, gemini-3.1-flash-lite, projet gratuit confirmé | 0 USD dans son quota effectif |
| Secours payant facultatif | OpenAI gpt-6-luna, Responses, désactivé par défaut | Sous-plafond 3 USD/mois |
| Collecte et cache | Service Python léger, SQLite, RSS officiels, données du socle | Aucun abonnement |
| Modèles locaux | Exclus par l'utilisateur | Aucun téléchargement ni inférence |

Une seule analyse sert aux deux robots et aux paires concernées. Plafonds communs : **24 tentatives/jour UTC**, **4 096 tokens d'entrée** et **2 048 de sortie/raisonnement par tentative**, **150 000 tokens réservés/jour**, **15 USD/mois pour l'ensemble des dépenses IA**. Pas de chaîne de modèles votant sur chaque trade, de VPS imposé ou d'outil web facturé.

Tarif OpenAI Standard court contexte vérifié : 0,10 USD/M entrée et 0,50 USD/M sortie. Si les 24 appels maximaux quotidiens étaient **tous payants**, coût maximal estimé : **0,7569408 USD pour 22 jours**, **1,0665984 USD pour 31 jours**, hors taxes/conversion. Le budget est néanmoins réservé transactionnellement et bloque à 3 USD API payante ou 15 USD global. Les tarifs sont revalidés au plus tard après sept jours. [Tarifs officiels](https://developers.openai.com/api/docs/pricing).

Le mode gratuit est le choix initial. Il n'est pas démontré identique aux modèles payants ; le protocole compare les routes sur 200 textes, avec écarts maximaux retenus de deux points de précision et cinq points de rappel. Une qualité comparable sur cette tâche étroite doit être mesurée, pas déduite du prix ou de la taille du modèle.

Avec 100 USD de capital, dépenser 15 USD chaque mois exigerait déjà 15 % de gain mensuel pour couvrir cette seule dépense. Le plafond n'est donc pas un objectif de consommation. Les coûts de trading, l'électricité et Internet restent des coûts réels distincts.

## 2. Ce qui est corrigé dans le document fourni

| Proposition de la référence | Décision |
|---|---|
| Appel du LLM avant l'ordre, délai possible de 20 s | Remplacé par des analyses asynchrones et un snapshot mémoire ; TTL d'entrée de cinq secondes conservé |
| Veto présenté comme usage « le plus rentable » | Hypothèse plausible, sans preuve spécifique à nos robots ; test A/B obligatoire |
| REDUCE et multiplication du lot par 0,5 | Écartés pour garder un risque déterministe et éviter les refus massifs de volume minimal |
| Tout échec LLM bloque toute entrée | Panne du complément = neutre ; C05 et les autres contrôles obligatoires restent bloquants |
| Ton hawkish implique automatiquement un sens Forex | Information de briefing seulement ; anticipations et relativité des devises empêchent cette équivalence générale |
| Température zéro assure la reproductibilité | Réponses toujours archivées ; température zéro ne garantit pas l'identité des réponses |
| Même prompt suffit à rendre les fournisseurs équivalents | Qualification séparée, suivi du modèle et contrôles de dérive |
| DeepSeek Flash à 0,14/0,28 USD/M | Tarif dépassé : la page actuelle affiche deepseek-flash V4.1, cache miss 0,15/0,30 entrée et 0,60/1,20 sortie selon l'heure ; non retenu dans le routeur |
| Un filtre ne peut jamais rendre positive une base négative | Faux comme énoncé mathématique général ; possible si un sous-ensemble exploitable existe, mais à prouver causalement |
| 384 appels/jour découlent nécessairement de M15 | Cela concerne quatre instruments 24 h/24 ; nos fenêtres et l'analyse partagée changent ce calcul |
| Compétences, daemon et Nyao déjà disponibles | Mentions de contexte non vérifiées, aucune dépendance supposée |
| Sources gratuites et hébergement toujours opérationnels | Droits, couverture, quotas et accessibilité vérifiés par l'adaptateur ; aucun VPS gratuit présumé |
| Secours local | Entièrement exclu conformément à la dernière instruction de l'utilisateur |

La [référence source](../references/IA_Generative_Forex_Scalping_M15_v2.md) est conservée sans modification ; elle n'est pas exécutée comme une liste d'instructions.

## 3. Portée des recherches

L'étude BNS de 2025 soutient l'intérêt de classer le langage propre au Forex, mais son portefeuille est **quotidien** et ses rendements sont présentés **avant frais**. Elle n'établit ni l'efficacité d'un veto générique gratuit en M15 ni celle de notre réglage. [Texte original, section stratégies](https://www.snb.ch/public/asset/en/www-snb-ch/publications/research/working-papers/2025/working_paper_2025_11/publications0_en/working_paper_2025_11.pdf).

StockBench, révisé en mars 2026, étudie des décisions quotidiennes sur actions ; les résultats de ses agents ne se transposent pas directement au Forex M15. [Publication](https://arxiv.org/abs/2510.02209). Les travaux de juin 2026 sur le biais d'anticipation montrent pourquoi une news passée soumise aujourd'hui à un modèle récent ne donne pas automatiquement un test indépendant. [Gao, Jiang, Yan](https://arxiv.org/abs/2512.23847).

Les documentations officielles confirment les sorties structurées chez [Groq](https://console.groq.com/docs/structured-outputs), [Google](https://ai.google.dev/gemini-api/docs/structured-output) et [OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs). La conformité JSON garantit une forme ; elle ne certifie ni vérité du classement ni rendement.

Les [quotas Groq](https://console.groq.com/docs/rate-limits) sont à lire sur le compte réel ; les [offres gratuites Gemini](https://ai.google.dev/gemini-api/docs/pricing) peuvent dépendre du modèle, du pays et du projet. Aucun compte API n'a été connecté pendant cette tâche, aucun quota individuel vérifié et aucun appel d'inférence facturé.

## 4. Veto retenu et différence entre méthodes

Le LLM extrait une classe d'événement, son acteur, son caractère actuel et une preuve textuelle exacte. Le code vérifie source officielle, calendrier, heures et fraîcheur. Seule une **décision monétaire annoncée, non programmée dans le calendrier du même issuer**, peut produire un veto de nouvelles entrées jusqu'à publication+15 minutes.

Il n'y a pas de filtre permanent de sentiment ni de veto vague « risk-off » pour toutes les paires. Une décision programmée déjà couverte par les gardes d'annonces ne reçoit pas un second filtre IA. Aucune hausse de rentabilité ou rétention de 80 % n'est encore mesurée.

- **Triple EMA** : veto au signal de reprise ; le repli est consommé et le cooldown normal s'applique. Aucun rattrapage sur cet ancien signal.
- **London** : veto sur la bougie courante sans consommer un quota de fill ; une nouvelle clôture peut être étudiée après expiration, strictement avant 11:00 Londres.
- **Positions existantes** : aucun changement de stop, objectif, taille ou clôture sur décision du LLM.
- **Fondamental externe absent** : toujours aucune entrée ; l'IA ne fabrique pas une permission neutre.

Les horaires, les prix Bid/Ask, la coordination des deux méthodes et les contraintes de volume de 100 USD restent ceux de V3. Une IA ne corrige pas un contrat trop gros pour le budget de risque.

## 5. Données et disponibilité

Flux officiels testés en lecture : Fed et BCE ont fourni des RSS ; BoE a répondu **HTTP 403 dans cet environnement**. La source n'est donc pas déclarée utilisable avant vérification dans le futur adaptateur. Cela limite la couverture de l'IA ; le calendrier et le module fondamental continuent à assurer leurs rôles.

Un service traite les publications sans les envoyer séparément pour chaque robot. Une publication ancienne ou repostée ne renouvelle jamais son veto. Le calendrier MT5, si utilisé, est converti depuis l'heure du serveur ; le testeur rejoue les exports. [Référence MetaQuotes](https://www.mql5.com/en/docs/calendar).

Les titres publics ne sont pas un flux instantané de toutes les annonces : l'architecture ne prétend pas battre la réaction du marché à une publication.

## 6. Validation et documents livrés

Les fichiers **01 et 02 existants sont mis à jour directement**, version documentaire 3.1.0, avec le contrat A01–A15 complet dans chacun : modèle, données, prompts, API, cache, timing, budget, veto, pannes, workflow spécifique, journal et tests. Ils restent autonomes pour l'agent qui construira les robots.

Le fichier 03 inclut les données LLM à archiver. Les configurations, schéma et prompts sont aussi exportés en JSON pour réduire les erreurs de transcription. Des fonctions de référence sans réseau vérifient format, causalité, frais maximaux et effet du veto ; ce ne sont pas des robots ou des clients API déployés.

La validation économique compare des portefeuilles complets, déduit le coût IA une seule fois, respecte la rétention de 80 % et nécessite assez d'événements réellement affectés. Les traces sont collectées prospectivement ; les réponses archivées sont rejouées avec leurs heures réelles.

Les anciens contrôles sont archivés ; les contrôles adaptés à la structure actuelle sont consignés dans [verification_projet.json](../validation/verification_projet.json). Il vérifie contrats/documentation et invariants, pas l'intelligence d'une API jamais appelée ni une rentabilité future.

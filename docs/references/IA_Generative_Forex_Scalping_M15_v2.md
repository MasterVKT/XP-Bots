# IA générative (LLM) en trading Forex — Scalping M15 sur paires majeures
## Version 2 optimisée — budget ≤ 10 $/mois — vérifiée au 4 novembre 2026

---

## 0. Réponse directe en 12 points

1. **Le LLM ne doit pas générer les signaux d'entrée M15.** Aucune preuve indépendante et non contaminée ne montre qu'un LLM prédit mieux le prix qu'un moteur quantitatif. Sur un benchmark sans contamination (mars–juillet 2025), la plupart des agents LLM de pointe n'ont même pas battu le simple « acheter et conserver ».
2. **Le meilleur usage, de loin, est le LLM en « filtre de veto contextuel »** : un moteur déterministe (règles techniques, votre robot MQL5) propose le trade ; le LLM, nourri de données factuelles fraîches (calendrier, news, état du marché), répond seulement *autoriser / réduire / bloquer*, au format JSON strict. Le défaut en cas de doute ou de panne est **« pas de trade »**.
3. **Deuxième usage à forte valeur : copilote de recherche hors-marché** (concevoir, coder, critiquer et faire auditer des stratégies et backtests). C'est là que le gain de productivité est le plus certain.
4. **Troisième usage : briefing macro pré-session** (Londres, New York) qui fixe un biais directionnel et les fenêtres interdites de la journée.
5. **Quatrième usage : journal de trading et post-mortem automatisés** — l'IA lit vos trades et détecte les erreurs récurrentes (heures, paires, configurations perdantes).
6. **À exclure** : trader la réaction à chaud des news (le prix bouge en secondes, un LLM met des secondes à répondre), lire des graphiques en image pour décider, systèmes multi-agents « à la TradingAgents » appelant de gros modèles à chaque bougie (coût et quotas incompatibles), et le critère de Kelly en scalping.
7. **Architecture à coût quasi nul** : Groq gratuit (principal) + Gemini gratuit (secours) + modèle local Ollama (dernier recours, CPU) + DeepSeek payant à l'usage uniquement comme filet (< 1–3 $/mois). Données : flux MT5 du courtier, calendrier économique intégré à MT5, flux JSON public de ForexFactory, Finnhub gratuit, flux RSS des banques centrales. **Total réaliste : 0 à 3 $/mois.**
8. **Règle de budget cruciale** : appeler le LLM *par événement* (signal candidat, briefing), jamais *à chaque bougie*. Chaque bougie × 4 paires = 384 appels/jour, ce qui dépasse les quotas gratuits ; en mode événementiel (~50 appels/jour), tout tient dans les quotas gratuits.
9. **La validation est l'avantage réel** : test A/B du même robot *avec* et *sans* filtre LLM, sur des données postérieures à la date de connaissance du modèle, avec spreads et commissions réels, puis 2 à 3 mois en démo. Si le filtre n'améliore pas l'espérance nette ou le drawdown, on le retire.
10. **Un biais de mémorisation fausse la plupart des backtests de LLM** : une étude de 2026 attribue environ 37 % de la capacité prédictive apparente d'un LLM sur des rendements boursiers à la mémorisation de ses données d'entraînement. Tout backtest d'un LLM sur une période antérieure à sa date de connaissance est donc suspect.
11. **Attente réaliste** : le gain attendu d'un LLM bien intégré n'est pas « +15–30 % » mais une **réduction des pertes évitables** (trades pris dans des contextes macro hostiles, autour des annonces, en régime anormal). C'est mesurable, modeste, et réel seulement si votre stratégie de base a déjà une espérance positive après coûts.
12. **Le LLM n'ajoute pas d'avantage à une stratégie sans avantage.** Il ne transforme pas une espérance négative en espérance positive ; il peut au mieux améliorer une stratégie déjà viable.

---

## 1. Triple vérification de la réponse précédente — corrections

| # | Affirmation précédente | Statut après vérification | Correction |
|---|---|---|---|
| 1 | « +15–30 % annualisés supérieurs aux benchmarks » | **Trompeur** | Chiffre réel issu d'une revue de 27 articles, mais uniquement en **backtest**, majoritairement sur actions US, avec une période de test médiane de **1,3 an**. Les benchmarks récents sans contamination (StockBench 2025) montrent que la plupart des agents LLM ne battent pas l'achat-conservation. |
| 2 | « Sharpe 1,8–2,4 vs 0,9–1,3 » | **Non sourcé** | Retiré. Aucune source ne l'étayait. |
| 3 | « 18–25 % annualisés sur annonces FOMC (Interactive Brokers 2024) » | **Non sourcé** | Retiré. L'article cité est un tutoriel QuantInsti qui décrit une méthode, sans ces résultats. |
| 4 | « Le RAG fait passer la précision de 66,8 % à 85,7 % » | **Mal attribué** | Ce chiffre concerne une méthode par *graphes de connaissances* (RoG) sur des tâches de raisonnement générales, pas le RAG ni le trading. |
| 5 | « 100 % de précision sur les prix via tool learning » | **Hors contexte** | Il s'agit de requêtes de *consultation* de prix boursiers, pas de prédiction. Seul enseignement valide : ne jamais demander au LLM un chiffre qu'on ne lui a pas fourni. |
| 6 | « Probabilité de gain 70–80 % » | **Sans fondement** | Retiré. Aucune donnée ne permet un tel chiffre. |
| 7 | « Coût 50–200 $/jour » | **Estimation non sourcée** | Remplacé par un calcul explicite (section 5). |
| 8 | Période de TradingAgents « juin–novembre 2024 » | **Contradictoire** | La version arXiv indique une simulation du 1er janvier au 29 mars 2024 ; le site du projet mentionne juin–novembre 2024. Dans les deux cas : fenêtre courte, 3 actions US, pas de Forex. |
| 9 | Stack recommandée (o1, GPT-4o, Claude Sonnet, Pinecone, AWS) | **Hors budget** | Éliminée (contrainte ≤ 10 $/mois). |
| 10 | « Latence 200–500 ms inacceptable pour scalping » | **Mal posé pour M15** | En M15, la latence API est sans importance pour l'analyse de contexte. Le vrai problème est que les news sont intégrées dans le prix en secondes (section 2). |
| 11 | « Taille de position par critère de Kelly » | **Dangereux** | Remplacé par un risque fixe de 0,5 à 1 % du capital par trade. Kelly suppose une espérance connue avec précision, ce qui n'est jamais le cas en scalping. |
| 12 | « LLM-RL hybride prouvé efficace » sur Forex | **Surévalué** | Les études RL Forex citées sont des simulations ; aucune preuve live robuste. Option non retenue pour un budget nul. |

---

## 2. Contraintes réelles du scalping M15 sur les majeures (ce qui détermine où l'IA peut servir)

### 2.1 Vitesse d'intégration des news
- Une étude LMAX/Macro Hive sur données à la milliseconde (Fed, NFP, CPI) montre que **60 % des variations de prix de l'heure suivant une annonce se produisent dans la première minute, et 30 % dans les deux premières secondes**.
- Les travaux académiques plus anciens (Andersen, Bollerslev et al., NBER) confirment que l'ajustement du prix à la surprise macro est quasi immédiat, et que les mauvaises nouvelles ont plus d'impact que les bonnes.
- **Conséquence** : un LLM gratuit (quelques secondes de réponse, plus le temps de récupérer la news) arrive **toujours trop tard** pour trader la réaction. En revanche, en M15, il a amplement le temps de décider s'il faut **éviter** une fenêtre ou **réduire** l'exposition avant et après.

### 2.2 Coûts de transaction
- En M15, les objectifs de gain sont typiquement de quelques pips à une vingtaine. Le spread et la commission représentent donc une part importante de chaque trade. Tout filtre IA doit être évalué **net de coûts**.
- Les spreads s'élargissent fortement autour des annonces, au roulement quotidien (environ 23 h heure de Douala en hiver, 22 h en été) et pendant la session asiatique sur EUR/USD et GBP/USD. Un filtre de contexte est précisément utile pour ces fenêtres.

### 2.3 Sessions vues depuis Douala (UTC+1, pas de changement d'heure au Cameroun)
| Période | Londres (hiver, GMT) | New York (hiver, EST) | Chevauchement |
|---|---|---|---|
| Novembre → mars | ~09 h00 – 18 h00 WAT | ~14 h00 – 23 h00 WAT | **~14 h00 – 18 h00 WAT** (liquidité maximale) |
| Fin mars → octobre (heure d'été UK/US) | ~08 h00 – 17 h00 WAT | ~13 h00 – 22 h00 WAT | **~13 h00 – 17 h00 WAT** |

Attention aux 2–3 semaines par an où les États-Unis et le Royaume-Uni n'ont pas encore changé d'heure en même temps. Le robot doit raisonner en heure du serveur du courtier et en UTC, jamais en heure « locale supposée ».

### 2.4 Statistique de départ à garder en tête
- Les avertissements réglementaires européens (ESMA) indiquent que **74 à 89 % des comptes CFD de particuliers perdent de l'argent**. La CFTC américaine indique qu'environ deux traders Forex particuliers sur trois perdent chaque trimestre.
- L'IA ne change pas ce point de départ ; elle peut seulement réduire certaines erreurs.

---

## 3. Ce que l'IA générative apporte réellement — classement des usages (tous ≤ 10 $/mois)

### U1 — Filtre de veto contextuel en temps réel ★★★★★ (le plus rentable)
**Principe** : votre moteur déterministe (robot MQL5 ou Python) détecte une configuration d'entrée. Avant d'envoyer l'ordre, il transmet au LLM un dossier factuel compact. Le LLM renvoie une décision structurée.

**Ce que le moteur envoie au LLM (contexte factuel, jamais d'opinion) :**
- Paire, sens, heure UTC, session en cours.
- Événements du calendrier dans les ± 60 minutes pour les deux devises de la paire (titre, impact, prévision, précédent, et valeur réelle si publiée).
- 5 à 10 titres de news récents concernant ces devises (horodatés).
- État du marché calculé par le moteur : spread actuel vs spread médian, ATR M15 vs médiane 20 jours, tendance H1/H4 (haussière/baissière/neutre), distance aux niveaux clés.
- Le briefing de session du jour (usage U2).

**Ce que le LLM renvoie (contrat de sortie, à valider par le code) :**
| Champ | Type | Valeurs autorisées | Rôle |
|---|---|---|---|
| decision | texte | `ALLOW`, `REDUCE`, `BLOCK` | Décision finale |
| size_multiplier | nombre | 0, 0,5 ou 1 uniquement | Ajuste le lot calculé par le moteur |
| reason_code | texte | liste fermée : `NEWS_WINDOW`, `MACRO_CONFLICT`, `ABNORMAL_SPREAD`, `ABNORMAL_VOL`, `CB_SPEAKER`, `RISK_OFF`, `OK` | Traçabilité et statistiques |
| confidence | nombre | 0 à 1 | Sert au journal, pas à la décision |
| rationale | texte | 1 phrase maximum | Lecture humaine |

**Règles de sécurité obligatoires côté code :**
- Toute réponse hors format, hors liste, ou absente dans le délai imparti (ex. 20 s) est traitée comme `BLOCK`.
- Le LLM ne peut **jamais** ouvrir un trade de lui-même, ni augmenter la taille au-delà de ce que le moteur a calculé, ni déplacer le stop-loss.
- Les vetos « durs » (annonce à fort impact dans ± 15 min, spread > 2 × médiane) sont codés **en dur dans le moteur**, sans LLM. Le LLM n'intervient que pour les cas *nuancés* (discours de banquier central non programmé, titre géopolitique, divergence entre biais macro et sens du trade).

**Pourquoi c'est le meilleur usage** : il exploite la force réelle du LLM (comprendre du texte et du contexte) sans lui confier ce qu'il fait mal (prédire des prix). Les recherches sur le sentiment Forex vont dans ce sens : la Banque nationale suisse (2025) montre que des LLM open source affinés sur des articles d'analyse FX surpassent les méthodes classiques à la fois en classification de sentiment et en performance de stratégie. Une étude EUR/USD (2024) montre que l'ajout de variables textuelles extraites par LLM réduit l'erreur de prévision (environ –10 % d'erreur absolue moyenne) par rapport aux seules données chiffrées — un gain d'information modeste mais réel, cohérent avec un usage de filtre plutôt que de générateur.

### U2 — Briefing macro pré-session ★★★★☆
**Principe** : 2 à 3 appels par jour (vers 08 h 30 WAT avant Londres, 13 h 30 WAT avant New York, éventuellement 22 h WAT pour le lendemain). Le LLM reçoit : calendrier du jour, résumé des news des 12 dernières heures, décisions et discours récents des banques centrales (Fed, BCE, BoE, BoJ, BNS, RBA, BoC), variation des taux 2 ans si disponible.

**Sortie attendue** (structurée) : pour chaque devise majeure, un biais `HAWKISH/DOVISH/NEUTRAL` motivé en une ligne ; la liste des fenêtres horaires à éviter ; un drapeau « régime risk-off » oui/non ; les paires à privilégier et celles à éviter ce jour-là.

**Usage par le moteur** : le briefing est injecté dans chaque appel U1 et peut servir de filtre directionnel (ex. ne prendre que les ventes d'EUR/USD quand le biais USD est nettement plus restrictif que l'EUR). Ce filtre directionnel doit lui-même être testé en A/B.

Votre compétence `macro-fx-strategist-m15` est le bon support pour formaliser ce prompt et ce format de sortie.

### U3 — Copilote de recherche et de développement hors-marché ★★★★★ (gain de productivité le plus certain)
**Tâches** :
- Transformer une idée de stratégie en spécification exacte (règles d'entrée, sortie, filtres, gestion du risque), puis en code MQL5 ou Python.
- Générer des **variantes** systématiques d'une stratégie (paramètres, filtres de session, filtres de volatilité) à tester en lot.
- Écrire les scripts de backtest walk-forward, d'analyse Monte-Carlo, de calcul des métriques.
- La recherche académique sur le « minage d'alpha » par LLM (AlphaAgent, Chain-of-Alpha, cadres LLM + recherche arborescente) montre que la méthode qui fonctionne est une **boucle fermée** : le LLM propose une formule, le moteur de backtest la mesure, le résultat est renvoyé au LLM qui l'améliore, avec des garde-fous contre la redondance et le surapprentissage. C'est reproductible gratuitement avec un LLM gratuit et VectorBT ou le testeur de stratégie MT5.

**Où le faire gratuitement** : version gratuite de Claude.ai ou de Gemini pour la conception et la revue de code ; API gratuite Groq/Gemini pour les boucles automatisées ; modèle local pour les longues boucles nocturnes.

### U4 — Auditeur adversarial des stratégies et backtests ★★★★☆
**Principe** : un second appel LLM, avec un rôle explicite de critique, reçoit la description de la stratégie, le code et le rapport de backtest, et doit lister : risques de surapprentissage (trop de paramètres, trop peu de trades), biais d'anticipation (utilisation de la bougie non clôturée, d'une donnée future), coûts sous-estimés, dépendance à une seule période ou une seule paire.

**Intérêt** : c'est l'application la plus sûre du principe « débat entre agents » de la littérature, mais appliquée là où l'erreur ne coûte rien (hors marché).

### U5 — Journal de trading et post-mortem automatisés ★★★★☆
**Principe** : chaque soir, le daemon exporte les trades du jour (heure, paire, sens, résultat en R, décision LLM, raison, conditions de marché). Le LLM produit un résumé et, une fois par semaine, une analyse des motifs : quelles heures, paires, raisons de veto sont associées aux pertes ; le filtre a-t-il bloqué plus de gagnants que de perdants ?

**Point clé** : le LLM *décrit et suggère* ; les statistiques elles-mêmes (taux de réussite, espérance, drawdown) sont **calculées par le code**, jamais par le LLM.

### U6 — Superviseur d'exécution et détecteur d'anomalies ★★★☆☆
**Principe** : le daemon Python surveille le robot MQL5 (connexion, ordres rejetés, glissement anormal, positions sans stop-loss, nombre de trades anormal). Les règles de détection sont codées ; le LLM sert à **rédiger l'alerte Telegram** compréhensible et à proposer l'action (couper le robot, attendre). C'est l'architecture que vous avez déjà conçue avec Groq en principal et Gemini en secours.

### U7 — Score de sentiment des textes FX ★★★☆☆
**Principe** : convertir les titres de news en score par devise. Variante gratuite et locale : FinBERT (petit modèle, tourne sur CPU) ou petit LLM local. Variante API : modèle gratuit Groq.
**Limite démontrée** : sur actions, une étude 2025 trouve un pouvoir explicatif du sentiment de news sur le rendement du lendemain statistiquement significatif mais très faible (R² ≈ 0,01). Le sentiment est donc un **ingrédient du filtre U1**, pas une stratégie en soi.

### U8 — Lecture de graphiques par vision ★☆☆☆☆
Utile pour la **pédagogie** (expliquer une configuration à des apprenants Xprience) ; à **exclure** de la décision de trading : imprécis sur les niveaux de prix, non reproductible, et tout ce qu'il « voit » est déjà disponible sous forme numérique pour le moteur.

### Usages éliminés et pourquoi
| Usage | Raison d'élimination |
|---|---|
| LLM qui décide seul d'acheter/vendre à chaque bougie | Aucune preuve d'avantage ; quotas gratuits dépassés ; non reproductible |
| Trader la réaction immédiate aux annonces | Prix ajusté en secondes ; LLM trop lent |
| Framework multi-agents complet type TradingAgents avec gros modèles | Coût élevé (nombreux appels de modèles de raisonnement par décision) ; testé sur actions, pas Forex |
| Abonnement Claude Pro / ChatGPT Plus pour le système | 20 $/mois, au-dessus du budget (un abonnement déjà détenu pour d'autres usages reste utilisable pour U3, mais il n'entre pas dans le système automatisé) |
| VPS Windows payant dédié | Généralement ≥ 10 $/mois ; alternatives en section 4.4 |
| API de données payantes (Finnhub, Twelve Data, Polygon payants) | Au-dessus du budget ; le flux du courtier MT5 suffit pour le M15 |
| Affinage (fine-tuning) d'un modèle sur GPU loué | Coût et complexité ; gain non démontré pour un particulier |

---

## 4. Architecture recommandée (coût 0 à 3 $/mois)

### 4.1 Vue d'ensemble (flux d'une décision)

```
[Flux MT5 du courtier] ──► [Moteur déterministe : robot MQL5 / Python]
                                   │ configuration détectée sur clôture M15
                                   ▼
                         [Vetos durs codés] ── annonce ±15 min / spread anormal ──► PAS DE TRADE
                                   │ sinon
                                   ▼
        [Dossier factuel] ◄── calendrier MT5 + flux ForexFactory + news Finnhub/RSS + briefing U2
                                   │
                                   ▼
            [Routeur LLM] Groq gratuit → Gemini gratuit → DeepSeek (payant, centimes) → Ollama local
                                   │ JSON strict, délai max 20 s
                                   ▼
                    [Validation du JSON par le code] ── invalide / absent ──► PAS DE TRADE
                                   │ valide
                                   ▼
          ALLOW : lot × 1   |   REDUCE : lot × 0,5   |   BLOCK : pas de trade
                                   │
                                   ▼
             [Ordre avec SL/TP côté serveur] ──► [Journal SQLite/CSV] ──► [Alerte Telegram]
```

### 4.2 Répartition des rôles entre composants
| Composant | Responsabilité exclusive | Ne doit jamais faire |
|---|---|---|
| Moteur déterministe (MQL5) | Signaux, calcul du lot (risque fixe 0,5–1 %), SL/TP, vetos durs, exécution | Dépendre du LLM pour fonctionner : si le LLM est indisponible, il applique le mode sûr (pas de trade, ou trades seulement hors fenêtres sensibles selon votre choix testé) |
| Daemon Python | Collecte des données externes, appels LLM, validation JSON, journal, alertes, supervision | Envoyer des ordres sans passer par les règles du moteur |
| LLM | Interprétation du contexte textuel, briefings, rédaction, critique | Produire des prix, des niveaux, des tailles, des statistiques |
| Humain (vous) | Revue hebdomadaire, activation/désactivation, évolution des règles | Contourner les limites de risque en séance |

### 4.3 Communication MQL5 ↔ Python
- Le paquet Python officiel `MetaTrader5` fonctionne **uniquement sous Windows** avec le terminal installé ; il donne accès aux bougies, ticks, positions, et à l'envoi d'ordres.
- Méthode simple et robuste pour faire dialoguer le robot MQL5 et le daemon : **fichiers partagés** dans le dossier commun du terminal (`Common\Files`). Le robot écrit une requête (fichier JSON nommé par identifiant unique) ; le daemon la lit, appelle le LLM, écrit la réponse ; le robot lit la réponse à la bougie ou au tick suivant, avec délai maximal. Aucun serveur réseau à exposer.
- Alternative : le daemon pilote tout via le paquet Python `MetaTrader5` et le robot MQL5 ne sert qu'à l'exécution. Plus simple à tester, mais moins proche de votre robot existant.
- Sous Linux, MT5 fonctionne via Wine (procédure officielle MetaQuotes), et le paquet `mt5linux` relie Python Linux à MT5 sous Wine par RPyC. Plus fragile ; à réserver si vous n'avez pas de machine Windows.

### 4.4 Hébergement sans dépasser le budget
| Option | Coût | Verdict |
|---|---|---|
| PC Windows personnel allumé pendant les sessions | 0 $ (électricité) | **Option par défaut.** Contrainte : coupures d'électricité/internet à Douala → SL/TP toujours posés côté serveur du courtier, onduleur recommandé |
| Oracle Cloud « Always Free » AMD micro | 0 $ | 1/8 OCPU et 1 Go de RAM : trop faible pour MT5 sous Wine de façon fiable ; possible pour un petit daemon Python |
| Oracle Cloud « Always Free » Ampere A1 (ARM) | 0 $ | Réduit en 2026 à 2 OCPU / 12 Go. **Processeur ARM : ne fait pas tourner MT5 (x86) nativement.** Bon pour héberger le daemon, Ollama avec un petit modèle, le journal. Disponibilité de capacité souvent difficile |
| VPS offert par le courtier | 0 $ sous conditions | Plusieurs courtiers offrent un VPS si dépôt ou volume minimum atteint — à vérifier chez le vôtre |
| VPS Windows payant | souvent ≥ 10 $/mois | Hors budget |

---

## 5. Pile technique gratuite ou quasi gratuite (vérifiée novembre 2026)

### 5.1 Modèles de langage
| Rôle | Fournisseur / modèle | Limites gratuites constatées | Remarques |
|---|---|---|---|
| Principal | **Groq** — `openai/gpt-oss-120b` | 30 req/min, 1 000 req/jour, 8 000 tokens/min, 200 000 tokens/jour (relevé 18 oct. 2026) | Très rapide ; limites par organisation (plusieurs clés n'ajoutent rien) ; Groq déclare ne pas entraîner sur vos données |
| Principal léger | Groq — `llama-3.1-8b-instant` | 30 req/min, 14 400 req/jour, 6 000 tokens/min, 500 000 tokens/jour (relevé août 2026) | Pour les tâches simples (classification de titres) |
| Secours | **Google Gemini** (AI Studio) — Flash / Flash-Lite | Ordres de grandeur 2026 : ~10–15 req/min, ~250 à 1 000 req/jour selon le modèle ; Google n'affiche plus les quotas exacts publiquement, ils sont visibles dans AI Studio | Les quotas ont été fortement réduits fin 2025 ; les données du niveau gratuit peuvent être utilisées par Google |
| Filet payant | **DeepSeek** — V4 Flash | Environ 0,14 $ / M tokens en entrée et 0,28 $ / M en sortie (tarifs 2026 rapportés ; vérifier sur api-docs.deepseek.com) | Recharge prépayée de quelques dollars ; consommation estimée < 1 $/mois en mode secours |
| Alternative payante | Claude Haiku 4.5 (Anthropic) | 1 $ / M entrée, 5 $ / M sortie | Environ 3,9 $/mois au volume de la section 5.3 : reste sous le budget, mais 4 à 10 fois plus cher que DeepSeek |
| Dernier recours local | **Ollama** — `qwen3:4b` ou équivalent 3–4 B, quantifié Q4 | Illimité, hors ligne | Sur CPU d'ordinateur portable : environ 7 à 10 tokens/s pour un modèle 3–4 B ; une réponse JSON de ~100 tokens prend ~10–15 s, compatible M15. Qualité inférieure : usage en dernier recours ou pour U7 |
| Sentiment local | FinBERT | Illimité | Classification rapide sur CPU ; anglais uniquement |

### 5.2 Données
| Besoin | Source gratuite | Limites |
|---|---|---|
| Prix, ticks, spreads M1–H4 | Terminal MT5 de votre courtier (via MQL5 ou paquet Python) | Ce sont les prix sur lesquels vous êtes exécuté : la meilleure source pour le M15 |
| Calendrier économique avec valeurs réelles | Calendrier économique intégré à MT5 (fonctions Calendar de MQL5) | Gratuit, intégré, inclut prévision/précédent/réel ; disponibilité dépend de la connexion MetaQuotes |
| Calendrier (secours) | Flux JSON public de ForexFactory (fourni par Fair Economy, faireconomy.media) | Semaine en cours (et suivante) ; **le flux gratuit ne contient pas les valeurs réelles publiées**, seulement prévision et précédent : suffisant pour les fenêtres d'exclusion |
| Titres de news | Finnhub (clé gratuite, ~60 appels/min, usage personnel non commercial) ; flux RSS des banques centrales (Fed, BCE, BoE, BoJ…) | Usage commercial interdit sur le gratuit Finnhub ; le sentiment Finnhub est payant (calculez-le vous-même) |
| Données forex externes (comparaison) | Alpha Vantage (25 appels/jour), Twelve Data (crédits gratuits limités) | Inutiles en production : le courtier suffit |

### 5.3 Calcul du budget de tokens (mode événementiel vs mode « chaque bougie »)
Hypothèses : ~2 000 tokens en entrée et ~300 en sortie par appel ; 22 jours de trading par mois.

| Mode | Appels/jour | Tokens/jour | Tient dans Groq gratuit (gpt-oss-120b : 200 k tokens/jour) ? | Coût si 100 % payant DeepSeek V4 Flash | Coût si 100 % Claude Haiku 4.5 |
|---|---|---|---|---|---|
| **Événementiel** (≈ 3 briefings + ≈ 40 vetos + 1 journal + quelques alertes ≈ 50) | ~50 | ~115 000 | **Oui** | ≈ 0,40 $/mois | ≈ 3,85 $/mois |
| Chaque bougie M15 × 4 paires | 384 | ~883 000 | **Non** (4 × le quota) | ≈ 3 $/mois | ≈ 29 $/mois (hors budget) |

**Conclusion** : le mode événementiel est obligatoire, à la fois pour le budget et parce qu'il est conceptuellement correct (le LLM juge un *trade candidat*, il n'observe pas le marché en continu). Prévoir aussi la limite de 8 000 tokens/minute de Groq : pas plus de ~3 appels par minute ; mettre les requêtes en file d'attente.

### 5.4 Outils logiciels (tous gratuits)
- **MT5** : plateforme, testeur de stratégie (y compris optimisation et mode « ticks réels » selon les données du courtier).
- **Python** : `MetaTrader5`, `pandas`, **VectorBT** (backtests vectorisés rapides, variantes en lot), APScheduler (planification), SQLite (journal).
- **Telegram Bot API** : alertes et commandes d'arrêt d'urgence depuis le téléphone.
- **Ollama** : modèles locaux.

### 5.5 Récapitulatif du budget mensuel
| Poste | Coût |
|---|---|
| LLM principal et secours (Groq, Gemini) | 0 $ |
| Filet payant DeepSeek (rarement sollicité) | 0 – 1 $ |
| Données (MT5, ForexFactory, Finnhub gratuit, RSS) | 0 $ |
| Hébergement (PC local et/ou Oracle Always Free) | 0 $ |
| Outils (MT5, Python, VectorBT, Telegram, Ollama) | 0 $ |
| **Total** | **0 à ~3 $/mois** (marge confortable sous 10 $) |

---

## 6. Ingénierie des prompts pour ce système (spécifications, pas de code)

1. **Rôle fixe et étroit** : « Tu es un filtre de risque. Tu ne prédis pas le prix. Tu décides seulement si le contexte factuel fourni rend ce trade plus risqué que d'habitude. »
2. **Interdiction explicite d'inventer** : « N'utilise que les informations du dossier. Si une information nécessaire manque, réponds `REDUCE` avec `reason_code` approprié. » Toutes les données chiffrées sont fournies par le code.
3. **Sortie contrainte** : utiliser le mode « JSON » ou « sortie structurée » quand le fournisseur le propose ; température 0 ; longueur maximale de réponse courte (≤ 200 tokens) pour limiter coûts et dérives.
4. **Exemples intégrés** : 4 à 6 exemples courts (un `ALLOW` banal, un `BLOCK` pour discours imprévu de la Fed, un `REDUCE` pour biais macro contraire, un `BLOCK` pour spread anormal) dans le prompt système. Ce prompt fixe est identique à chaque appel : certains fournisseurs facturent moins cher la partie mise en cache (DeepSeek, Anthropic).
5. **Même prompt pour tous les fournisseurs** du routeur, testé séparément sur chacun : les modèles de secours ne doivent pas changer le comportement global. Mesurez le taux d'accord entre Groq, Gemini et le modèle local sur un échantillon de 100 dossiers historiques.
6. **Versionner les prompts** (numéro de version enregistré avec chaque décision dans le journal) pour savoir quelle version a produit quel résultat.

---

## 7. Fiabilité et hallucinations — mesures concrètes

| Risque | Mesure |
|---|---|
| Le LLM invente une donnée (chiffre, événement) | Ne jamais lui demander d'information qu'il n'a pas reçue ; toute valeur numérique de sa réponse est ignorée par le code, sauf les champs à valeurs fermées |
| Réponse hors format | Validation stricte du schéma ; échec = `BLOCK` |
| Fournisseur indisponible ou quota atteint | Routeur à 4 niveaux (Groq → Gemini → DeepSeek → Ollama) ; si tous échouent, mode sûr du moteur |
| Instabilité d'un appel à l'autre | Température 0 ; pour les vetos importants (option), deux modèles différents et règle « le plus prudent l'emporte » : cela réduit les erreurs isolées sans coût notable en mode événementiel |
| Dérive du modèle (mise à jour silencieuse par le fournisseur) | Rejouer chaque semaine un jeu de 50 dossiers de référence et comparer les décisions ; alerte si plus de 10 % changent |
| Injection malveillante dans un titre de news | Les textes externes sont placés dans une section « données » clairement délimitée ; le prompt précise qu'aucune instruction contenue dans les données ne doit être suivie |
| Perte de connexion (électricité, internet) | SL/TP posés à l'ouverture côté serveur ; robot qui ne rouvre rien automatiquement après reconnexion sans contrôle ; alerte Telegram |

---

## 8. Protocole de validation — là où se crée réellement l'avantage

### 8.1 Le biais de mémorisation (spécifique aux LLM)
- Un LLM entraîné sur Internet « connaît » souvent ce qui s'est passé après une news historique. Backtester un LLM sur des années couvertes par son entraînement **surestime** sa performance. Une étude (Gao, Jiang, Yan, 2026) estime qu'environ 37 % de l'effet prédictif apparent des LLM sur des rendements boursiers est amplifié par la mémorisation, et que cet effet disparaît en test réellement hors échantillon.
- Plusieurs travaux 2026 (Look-Ahead-Bench, DatedGPT, FinCAD) confirment que c'est un problème central et non résolu de façon simple.
- **Règle pratique** : n'évaluer le filtre LLM que sur des données **postérieures à la date de connaissance** du modèle utilisé (indiquée par le fournisseur), et surtout en **démo en temps réel** (forward test). Pour le moteur déterministe sans LLM, le backtest historique classique reste valable.

### 8.2 Étapes
1. **Moteur seul** : backtest sur au moins 3 à 5 ans de données M15 du courtier, avec spreads variables réels et commissions, walk-forward (optimisation sur une fenêtre, test sur la suivante), au moins 300 à 500 trades hors échantillon. Si l'espérance nette est ≤ 0, **arrêter ici** : le LLM ne sauvera pas la stratégie.
2. **Vetos durs codés** (sans LLM) : mesurer leur apport (calendrier, spread, heure). Souvent, ils captent déjà une bonne partie du gain qu'on attribue à « l'IA ».
3. **Filtre LLM en mode ombre** : pendant 4 à 8 semaines en démo, le robot trade *sans* tenir compte du LLM, mais enregistre ce que le LLM aurait décidé. On compare ensuite : résultat des trades que le LLM aurait bloqués vs autorisés.
4. **Critère d'adoption** : le filtre est activé seulement si les trades « bloqués » ont une espérance significativement inférieure à celle des trades « autorisés », et si l'activation améliore l'espérance nette *ou* le drawdown maximal sans réduire excessivement le nombre de trades.
5. **Démo active** 4 à 8 semaines supplémentaires avec le filtre actif, puis petit capital réel avec risque de 0,25 à 0,5 % par trade.
6. **Revue continue** : statistiques hebdomadaires par `reason_code` ; un code qui ne discrimine pas (trades bloqués aussi bons que les autorisés) est retiré.

### 8.3 Métriques à suivre (calculées par le code)
Espérance par trade en R, facteur de profit, drawdown maximal, nombre de trades, taux de blocage par le LLM, espérance des trades bloqués en mode ombre, taux de réponses invalides, latence, coût mensuel.

---

## 9. Contexte local (Cameroun / zone CEMAC)

- **Cadre réglementaire du trading Forex de particuliers** : selon les sources sectorielles consultées, le trading Forex de particuliers n'est pas spécifiquement encadré au Cameroun ; le ministère des Finances, la BEAC et la COSUMAF supervisent le secteur financier général sans délivrer de licence spécifique aux courtiers Forex de détail. En pratique, vous utiliserez un courtier étranger : choisissez-le d'abord pour sa régulation (autorités reconnues), la qualité d'exécution et les spreads sur les majeures, pas pour les bonus.
- **Réglementation des changes CEMAC** : la réglementation de la BEAC entrée en vigueur en 2019 prévoit notamment que les entreprises et les particuliers obtiennent une autorisation de la BEAC avant d'ouvrir un compte hors de la zone. L'application concrète aux comptes de trading et aux dépôts via cartes, portefeuilles électroniques ou mobile money mérite un avis juridique (votre compétence `juriste-strategiste-cameroun` est adaptée pour préparer cette analyse, à valider auprès d'un professionnel).
- **Fiscalité** : pas de régime spécifique clairement établi pour les gains de trading Forex de particuliers selon les sources consultées ; à faire confirmer par un fiscaliste avant de passer à un capital significatif.
- **Infrastructure** : coupures de courant et d'internet → stop-loss côté serveur obligatoire, onduleur, connexion de secours (partage 4G), et règle « pas de position ouverte pendant les absences prolongées » tant que vous n'avez pas d'hébergement permanent.
- **Fuseau** : Douala reste en UTC+1 toute l'année ; les décalages viennent des changements d'heure à Londres et New York (section 2.3).

---

## 10. Intégration dans votre écosystème existant

| Élément existant | Rôle dans l'architecture v2 |
|---|---|
| Robot Nyao Scalper v43 (MQL5, M15) | Moteur déterministe intérimaire. Étape 1 du protocole : le backtester tel quel, net de coûts, sur vos paires. Ajouter ensuite le point d'appel au filtre (requête/réponse par fichiers partagés) avant chaque ouverture |
| Daemon Python (Groq principal, Gemini secours, APScheduler, Telegram) | Devient le « routeur LLM + collecteur de données + journal ». Ajouter DeepSeek et Ollama comme niveaux 3 et 4, la validation de schéma, le mode ombre et le rejeu hebdomadaire |
| Compétence `macro-fx-strategist-m15` | Base du prompt du briefing U2 |
| Compétence `expert-scalper-m15` | Base des exemples intégrés au prompt de veto U1 et de l'auditeur U4 |
| Compétences `scalping-forex-ia` / `forex-robot-builder-m15` | Copilote U3 pour votre robot définitif (boucle génération → backtest → critique) |
| Activité de formation Forex (Xprience) | Les usages U3, U5 et U8 (pédagogie) sont directement réutilisables comme supports de formation |

---

## 11. Feuille de route sur 90 jours

| Semaines | Objectif | Livrable | Critère pour passer à la suite |
|---|---|---|---|
| 1–2 | Base saine | Backtest walk-forward du robot sur 3–5 ans, coûts réels | Espérance nette > 0 hors échantillon |
| 3 | Vetos durs | Fenêtres d'annonces, filtre de spread, filtre horaire codés dans le moteur | Amélioration mesurée ou neutralité |
| 4 | Données | Collecte calendrier MT5 + ForexFactory + news Finnhub/RSS dans le daemon | Données complètes et horodatées en UTC |
| 5 | Filtre LLM | Prompts U1 et U2 versionnés, routeur à 4 niveaux, validation du schéma | < 1 % de réponses invalides sur 200 dossiers tests |
| 6–11 | Mode ombre en démo | Journal de toutes les décisions LLM hypothétiques | Au moins 150 à 200 trades enregistrés |
| 12 | Décision | Analyse A/B bloqués vs autorisés, par `reason_code` | Adoption seulement si gain net démontré |
| 13+ | Démo active puis réel prudent | Filtre actif, risque 0,25–0,5 % | Revue hebdomadaire (U5) |

En parallèle et dès la semaine 1 : U3 et U4 pour développer votre robot définitif.

---

## 12. Ce qu'il faut attendre honnêtement

- **Gain probable** : moins de trades perdants dans les contextes défavorables (annonces, discours, régimes anormaux), un drawdown plus faible, une meilleure discipline grâce au journal. Ampleur : à mesurer sur vos propres données ; aucune source sérieuse ne permet de promettre un pourcentage.
- **Gain très probable** : une productivité de recherche et de développement nettement supérieure (U3, U4), qui accélère la mise au point de votre propre robot.
- **Gain improbable** : un LLM qui « devine » la direction du marché M15 mieux que les participants professionnels.
- **Critère de réussite** : le système est bon s'il fait mieux, net de coûts et en forward test, que **le même moteur sans LLM**. C'est la seule comparaison qui compte.

---

## Sources principales (consultées le 4 novembre 2026)

**Preuves sur les LLM en trading**
- Revue de 27 articles sur les agents LLM en trading — https://arxiv.org/html/2408.06361v1 ; résumé : https://www.globaltrading.net/llms-and-trading/
- StockBench (benchmark sans contamination, mars–juillet 2025) — https://arxiv.org/html/2510.02209v1
- Agent Market Arena (benchmark en temps réel) — https://arxiv.org/abs/2510.11695
- TradingAgents — https://arxiv.org/html/2412.20138v5 et https://tradingagents-ai.github.io/
- Banque nationale suisse, « FX sentiment analysis with large language models » (2025) — https://www.snb.ch/en/publications/research/working-papers/2025/working_paper_2025_11
- Prévision EUR/USD par fusion LLM + Bi-LSTM — https://arxiv.org/html/2408.13214v2
- Sentiment et rendements (R² ≈ 0,01) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5145647
- Minage d'alpha par LLM : Chain-of-Alpha — https://arxiv.org/pdf/2508.06312 ; LLM + MCTS — https://arxiv.org/html/2505.11122v1

**Biais de mémorisation**
- Gao, Jiang, Yan, « A Test of Lookahead Bias in LLM Forecasts » — https://arxiv.org/pdf/2512.23847v1 ; synthèse CFA UK — https://connect.cfauk.org/discussion/llms-research-lookahead-bias-for-prediction-tasks
- Look-Ahead-Bench — https://arxiv.org/pdf/2601.13770
- FinCAD — https://arxiv.org/abs/2605.24564

**Microstructure Forex et annonces**
- LMAX / Macro Hive (vitesse de réaction aux annonces) — https://financemagnates.com/forex/fx-market-reactions-to-events-millisecond-data-helps-traders-capture-90-of-movements/amp
- Andersen, Bollerslev, Diebold, Vega (NBER w8959) — https://www.nber.org/system/files/working_papers/w8959/w8959.pdf

**Coûts et quotas**
- Groq (quotas gratuits) — https://www.developersdigest.tech/models/free-api/groq ; https://localaimaster.com/blog/groq-api-free-guide
- Gemini (quotas gratuits) — https://www.developersdigest.tech/rate-limits/google ; https://yingtu.ai/en/blog/google-gemini-api-free-tier-limits-2026
- DeepSeek (tarifs) — https://dev.to/khushi_dubey/deepseek-api-pricing-2026-models-token-costs-and-how-to-optimize-536f ; référence officielle : https://api-docs.deepseek.com/quick_start/pricing
- Claude Haiku 4.5 (tarifs) — https://pricepertoken.com/pricing-page/model/anthropic-claude-haiku-4.5
- Finnhub (niveau gratuit) — https://apicostcalc.com/finnhub.html
- Flux ForexFactory / Fair Economy — https://apify.com/gochujang/economic-calendar-tracker.md ; https://apify.com/ichigowa/economic-calendar-pro
- Oracle Cloud Always Free (réduction 2026) — https://docs.oracle.com/iaas/Content/FreeTier/resourceref.htm ; https://terminalbytes.com/oracle-cloud-free-tier-changes-2026
- Modèles locaux sur CPU — https://localaimaster.com/blog/run-llm-cpu-only ; https://itsfoss.com/testing-local-llms-without-gpu

**MT5 et intégration**
- MT5 sous Linux (Wine) — https://www.metatrader5.com/en/terminal/help/start_advanced/install_linux
- mt5linux — https://pypi.org/project/mt5linux/1.0.6/
- pdmt5 (wrapper du paquet MetaTrader5, Windows requis) — https://pypi.org/project/pdmt5/

**Risque et contexte local**
- Taux de comptes perdants (ESMA, CFTC) — https://www.financemagnates.com/forex/prop-firm-e8-markets-warns-retail-traders-off-cfd-brokers-as-industry-leans-harder-on-educational-labels/
- Forex au Cameroun (cadre) — https://daytrading.com/cm/forex
- Réglementation des changes BEAC — https://www.gabonreview.com/nouvelle-reglementation-du-marche-des-changes-la-beac-et-la-cae-sexpliquent/

---

*Document informatif, pas un conseil en investissement. Les quotas et tarifs des fournisseurs changent fréquemment : revérifier avant mise en production.*

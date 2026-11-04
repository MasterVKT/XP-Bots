# Données historiques exactes pour valider les deux robots M15 V3

Date du cahier de collecte : **4 novembre 2026**. Capital : **100 USD** ; compte **standard USD** ; levier **1:100**. Le courtier envisagé reste FBS, FXCM ou Deriv ; une série de prix d'un autre fournisseur ne reproduit pas automatiquement son exécution.

## 1. Instruments et dates

**EURUSD, GBPUSD, XAUUSD**. Fournir le **nom exact négociable** dans le compte, avec suffixe et variante micro éventuelle. Il faut l'historique du contrat qui sera réellement lié au robot ; ne pas assembler le prix normal et le spread micro.

Période demandée, bornes incluses :

**du 02/12/2019 à 00:00:00.000 UTC au 03/11/2026 à 23:59:59.999 UTC**.

La partie décembre 2019 sert au préchargement ; les performances commencent le 1er janvier 2020. Si un instrument n'existait pas sur cette période, indiquer sa première date disponible ; ne pas inventer le passé. Une période plus courte impose un protocole révisé et un constat d'effectif insuffisant si nécessaire.

## 2. Prix indispensables

Format privilégié : fichiers **Parquet** ou **CSV UTF-8 compressés**, séparés par symbole et mois ; un tick de cotation par ligne.

~~~text
canonical_symbol,broker_symbol,time_utc_ms,sequence,bid,ask
EURUSD,nom_exact,1609747200123,1,1.22500,1.22512
~~~

La ligne est illustrative. Conserver tous les ticks de changement Bid ou Ask, les cotations inchangées si disponibles et l'ordre natif des événements à même milliseconde. Si la séquence n'existe pas, conserver l'ordre original et le signaler. La résolution seconde seule ne permet pas de reconstituer exactement des événements simultanés.

Joindre : source, fuseau original, table historique vers UTC si nécessaire, unité/précision des prix, méthode d'extraction, trous connus, corrections fournisseur, date de récupération et empreintes SHA-256. Les volumes ne sont **pas nécessaires** à ces V3. Aucune clé de compte ni mot de passe n'est nécessaire.

**Si les ticks sont introuvables** : M1 Bid OHLC **et** Ask OHLC sur les mêmes dates pour un examen préalable, avec spreads historiques. M15 seul est insuffisant. Le M1 ne valide pas le TTL de cinq secondes, l'ordre des touches SL/TP ni la qualité des remplissages. Aucun résultat de ce secours ne sera présenté comme test final.

## 3. Contrat et frais indispensables

Une fiche/export du terminal pour chaque symbole réel et chaque changement de conditions :

- entité, serveur, plateforme et type de compte exact ; devise USD ; levier de compte 100 ;
- taille/unité du contrat, type de calcul du profit, tick_size/point/digits, valeur du tick ;
- minimum, maximum et pas de volume ; limite cumulée ;
- commission d'entrée/sortie, minimum par ordre, autres frais, arrondis et conversion USD ; zéro seulement si confirmé ;
- calcul/paliers de marge, contraintes SL/TP, gel, modes de remplissage et de protection, mode netting/hedging et stop-out ;
- horaires de cotation, pauses quotidiennes, jours fériés, fermetures exceptionnelles et conventions de déclenchement Bid/Ask.

Un tableau de dates d'effet est nécessaire pour rejouer les conditions historiques. À défaut, un test appliquant les conditions actuelles à tous les prix passés sera explicitement **contrefactuel**. Les spreads publicitaires minimaux ne remplacent pas les Ask historiques.

Le snapshot public Deriv fourni dans le dossier n'établit ni l'accès aux symboles micro sur ton compte standard ni leurs pas/frais réels. Le terminal du compte doit les confirmer.

## 4. Annonces et fondamental

Pour appliquer la garde d'annonces : calendrier historique des événements HIGH liés à **USD, EUR et GBP**, sur la période d'évaluation, avec :

~~~text
event_id,currency,event_time_utc,impact,known_at_utc,calendar_version
~~~

Conserver les changements de date/importance et leur heure de connaissance. Un calendrier actuel enrichi après coup peut introduire une fuite d'information.

Pour mesurer le système **technique + analyse fondamentale externe**, fournir l'historique des permissions du modèle :

~~~text
canonical_symbol,sequence,issued_at_utc,known_at_utc,
valid_from_utc,valid_until_utc,direction,risk_state,
model_version,input_snapshot_id
~~~

Direction : ANY, LONG_ONLY ou SHORT_ONLY ; risque : ALLOW, NO_NEW ou FLATTEN. Il faut ce qui était réellement connu à chaque instant, pas un avis humain reconstruit après avoir vu les prix.

Si ces permissions n'existent pas, on peut mesurer le contrôle technique neutre, puis collecter le fondamental prospectivement en démo. Les valeurs macro révisées, la corrélation DXY et les titres de presse téléchargés aujourd'hui ne suffisent pas à recréer automatiquement ces permissions historiques.

## 5. Protocole fixé avant chargement

| Bloc | Dates UTC | Usage |
|---|---|---|
| Initialisation | 02/12/2019–31/12/2019 | 1 000 M15 ; 300 H1 pour Londres |
| Développement | 01/01/2020–31/12/2022 | Contrôle du robot ; pas de recherche de millions de réglages |
| Validation | 01/01/2023–31/12/2024 | Robustesse chronologique |
| Test réservé | 01/01/2025–30/04/2026 | À conserver non consulté jusqu'au gel du robot et des règles |
| Déjà exploré | 01/05/2026–03/11/2026 | Diagnostic ; jamais étiqueté « final indépendant » |
| Démo prospective | 05/11/2026–04/02/2027, puis extension si besoin | ≥60 journées de marché et ≥100 trades clos par méthode |

Le test réservé est rétrospectif ; son caractère non consulté doit être vérifié au moment de la collecte. S'il a déjà servi à un autre réglage, le déclarer exposé. Le véritable contrôle prospectif commence après le gel.

Rejouer chaque méthode seule, puis les deux sur un seul compte de 100 USD. Tester séparément les expositions normales et les symboles micro **réellement disponibles**, sans changer le budget de risque.

Les seuils d'acceptation, coûts de référence/stress, rétention de 80 %, mesures d'incertitude et contrôles de voisinage sont fixés dans chacun des deux fichiers de stratégie. Aucun taux de réussite ou rendement cible n'est utilisé pour fabriquer des trades.

## 6. Ce qui est déjà disponible et ce qu'il manque

Le cache archivé hors du dépôt contient des M1 Bid/Ask Dukascopy du **20/04/2026 au 03/11/2026** pour EURUSD, GBPUSD et XAUUSD. Ce sont des données de diagnostic déjà exploitées, pas les ticks du futur compte standard. Elles ne couvrent ni la période longue demandée ni les permissions fondamentales.

Il manque donc, pour une conclusion adaptée à ton compte : les ticks des symboles réellement négociés, leurs coûts/contraintes, le calendrier historique et, pour le test combiné, les permissions fondamentales causales. Il n'est pas nécessaire de récupérer un indice DXY, un MFI, du volume mondial ou du Level 2.


## 7. Données supplémentaires pour tester l'extension LLM 3.1

Les historiques techniques ci-dessus restent nécessaires. Pour l'IA, archiver prospectivement : RSS/textes effectivement reçus et leurs published_at/first_seen/SHA-256, calendrier tel que connu, requêtes et réponses LLM, provider/model/prompt/schema, heures de départ/réception/validation, tokens facturés, réserves de budget et snapshots consommés par les EA.

Un test LLM sur les news historiques de 2020–2026 réinterrogées aujourd'hui n'est pas déclaré indépendant. Le test économique principal utilise la collecte postérieure au gel, puis rejoue **les réponses originales**. Aucun modèle local n'entre dans la collecte ni dans le secours.

Comparer un bras de référence et un bras avec veto IA, chacun à 100 USD, mêmes coûts/fondamental ; simuler le portefeuille complet, pas seulement retirer les pertes qui auraient été bloquées. Les seuils A13 exigent aussi assez d'événements réellement affectés ; aucun délai fixe de trois mois ne suffit à lui seul.

Pour les chemins actuels et la récupération du cache historique : [registre de nettoyage](../maintenance/NETTOYAGE_ET_MERGE.md). Le cache est facultatif pour les contrôles synthétiques du dépôt.

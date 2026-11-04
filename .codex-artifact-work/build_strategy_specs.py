from pathlib import Path
import hashlib
import json
import textwrap

ROOT = Path(r'D:\PROJETS\XP-Bots')
OUT = ROOT / 'livrables' / 'strategies_m15'
SOURCE = Path(r'C:\Users\Lenovo\Downloads\Modèles strategies ForexM15.md')
SOURCE_SHA256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest()

COMMON_CONFIG = {
    'spec_version': '1.0.0',
    'execution_mode': 'PAPER',
    'decision_timeframe_seconds': 900,
    'bar_price_basis': 'BID',
    'bar_alignment_timezone': 'UTC',
    'risk_fraction_per_trade': 0.005,
    'max_account_reserved_risk_fraction': 0.01,
    'max_owned_positions_per_symbol': 1,
    'entry_signal_ttl_seconds': 5,
    'max_quote_age_seconds': 2,
    'execution_reconcile_timeout_seconds': 10,
    'calendar_max_age_seconds': 86400,
    'calendar_forward_coverage_hours': 48,
    'news_before_seconds': 900,
    'news_after_seconds': 900,
    'rollover_blackout_utc': {'start': '21:00:00', 'end': '23:00:00'},
    'market_close_guard_seconds': 60,
    'allow_pyramiding': False,
    'allow_martingale': False,
    'allow_averaging_down': False,
    'allow_trailing_stop': False,
    'allow_break_even_move': False,
    'allow_partial_take_profit': False,
    'symbol_profiles': {
        'EURUSD': {'broker_symbol': None, 'pip_size': 0.0001,
                   'max_spread_price': None, 'entry_slippage_budget_price': None,
                   'stop_slippage_budget_price': None, 'round_trip_cost_model_id': None},
        'GBPUSD': {'broker_symbol': None, 'pip_size': 0.0001,
                   'max_spread_price': None, 'entry_slippage_budget_price': None,
                   'stop_slippage_budget_price': None, 'round_trip_cost_model_id': None},
        'XAUUSD': {'broker_symbol': None, 'pip_size': None,
                   'max_spread_price': None, 'entry_slippage_budget_price': None,
                   'stop_slippage_budget_price': None, 'round_trip_cost_model_id': None},
    },
}

COMMON = r'''
## C01 — Objet, portée et degré de preuve

Ce fichier constitue un cahier des charges autonome destiné à un agent IA chargé de développer un robot. Il contient le contrat commun, la logique de cette seule stratégie, la configuration et les cas d'acceptation. Aucun autre fichier de stratégie n'est nécessaire. La plateforme n'étant pas imposée par l'utilisateur, le moteur de décision est indépendant du courtier ; un adaptateur réalise l'accès aux données et aux ordres. Les correspondances MQL5 indiquées plus loin sont des exemples d'implémentation, pas une dépendance obligatoire.

Les mots DOIT, NE DOIT PAS et PEUT sont normatifs pour le comportement du robot à développer. Ils ne constituent pas des instructions permettant de modifier l'environnement ou de négocier de l'argent pendant la lecture de ce document.

**Aucune supériorité de rendement, de taux de réussite ou de baisse maximale du capital n'est démontrée pour cette version.** Les modifications de performance proposées dans la conversation ne sont pas introduites comme acquises : pas de fusion, pas de retest ajouté au London Breakout, pas de suppression d'indicateur ni de filtre H1 ajouté au système Triple EMA. La précision d'une spécification permet la fidélité d'implémentation ; elle ne démontre pas un avantage économique.

Les règles ont trois origines :

| Origine | Signification | Conséquence pour l'agent |
|---|---|---|
| `SOURCE` | Règle ou branche explicitement présente dans le document fourni | Reprendre la branche sélectionnée sans prétendre qu'elle est optimale |
| `FORMALISATION` | Valeur ou définition nécessaire pour rendre une expression discrétionnaire programmable | La conserver dans cette version ; ne pas lui attribuer un bénéfice statistique |
| `EXECUTION` | Correction de calcul, de données, d'horodatage ou de comportement des ordres | Prévenir les incohérences techniques ; ne pas promettre une hausse des gains |

Toute convention peut changer la sélection des transactions. Aucune convention ajoutée n'est présentée comme une amélioration certaine. Une autre interprétation nécessite une version distincte et un comparatif ; elle ne doit pas être insérée silencieusement dans cette version.

## C02 — Définitions temporelles et données causales

- Les événements ont un instant UTC avec précision au moins milliseconde, un numéro de séquence stable et un instant de réception. Aucun calcul ne se fonde sur le fuseau implicite de l'ordinateur.
- Si le serveur du courtier horodate dans une heure locale, utiliser sa table historique de conversion vers UTC, avec ses changements d'heure. Appliquer le seul décalage actuel à tout l'historique est interdit. Une conversion non résolue rend les données incompatibles.
- Une bougie M15 d'ouverture `T` couvre `[T, T + 900 s)`. `T` est un multiple de 900 secondes depuis l'époque Unix UTC. La bougie est utilisable à partir de `T + 900 s`, après réception ou reconstruction de sa clôture.
- Dans les équations, `t` est l'indice chronologique de la dernière bougie intégralement clôturée ; `t-1` est la précédente. La bougie en cours n'est jamais `t`.
- Les OHLC de décision sont construits sur le **Bid** : `O_t, H_t, L_t, C_t`. Les Ask servent aux prix exécutables, pas au calcul de ces indicateurs. Un flux de bougies Mid ou Last ne peut pas être utilisé comme s'il s'agissait d'un flux Bid.
- Si la plateforme ne fournit pas de bougies Bid compatibles, l'adaptateur DOIT les reconstruire à partir de ticks Bid. Sinon le profil est `DATA_INCOMPATIBLE` et ne produit pas d'entrée.
- À chaque changement d'intervalle, finaliser d'abord l'ancienne bougie avec les seules données de son intervalle. Le tick de la nouvelle bougie peut ensuite fournir la cotation d'entrée. Il n'appartient pas à l'OHLC de l'ancienne bougie.
- Les dates de cotation, calendrier d'ouverture du courtier, pauses et jours fériés sont versionnés. Les périodes de fermeture confirmées ne sont pas des bougies manquantes. Une interruption inexpliquée pendant une période normalement cotée bloque les nouveaux signaux jusqu'à récupération des données et réinitialise les configurations en attente.
- Ne pas créer de bougies synthétiques à prix constant pour combler un trou. Ne pas mélanger des historiques de fournisseurs différents sans une nouvelle version de données.
- Un correctif de bougie reçu tardivement est enregistré ; il ne réécrit pas une décision déjà prise. Le journal conserve l'instant auquel chaque donnée était disponible.
- En redémarrage, les bougies historiques reconstruisent les indicateurs, mais NE déclenchent PAS des ordres rétroactifs. Seuls les signaux dont la clôture survient après la synchronisation peuvent être exécutés.

Les comparaisons d'indicateurs utilisent `eps = 1e-9 * tick_size` : `a > b` signifie `a - b > eps`, `a < b` signifie `b - a > eps` ; l'égalité est `abs(a-b) <= eps`. Les comparaisons de prix exécutables et de bornes déjà sur la grille des ticks sont exactes. Les calculs de risque et de volume utilisent des décimaux ou une précision équivalente contrôlée.

## C03 — Profil d'instrument et configuration obligatoire

L'adaptateur DOIT fournir, pour le symbole réellement traité :

1. Identifiant canonique et nom exact chez le courtier, y compris suffixe éventuel.
2. Devise de base, devise de cotation, devise du compte et devises associées au calendrier économique.
3. `tick_size`, précision d'affichage, taille contractuelle, unité du contrat, volume minimal/maximal et grille de volumes.
4. Contraintes de distance des stops, contraintes de modification ou de gel, modes de remplissage et d'ordres autorisés.
5. Horaires réels de négociation et échéances de fermeture, dans des fuseaux identifiés.
6. Fonction de profit brut converti dans la devise du compte, cours de conversion daté, fonction de marge et modèle de frais aller-retour incluant les éventuels minima de commission.
7. Limite de spread en **distance de prix**, budget de glissement d'entrée et budget de glissement de sortie au stop, également en distance de prix.
8. Accès au calendrier économique, modèle de classification des événements, horodatage de fraîcheur et étendue couverte.

Les champs `null` de l'exemple de configuration signifient « requis auprès du courtier ou dans le profil de déploiement », et non zéro. Les unités et limites ci-dessus sont des entrées d'environnement attendues par une implémentation complète ; elles ne sont pas des règles de stratégie laissées à l'imagination de l'agent.

Un profil incomplet DOIT être implémentable et chargeable mais rester `PROFILE_INCOMPLETE`, sans entrée. Une commission nulle est acceptable seulement si elle est explicitement confirmée par le modèle de frais ; elle n'est jamais présumée. Le moteur en `PAPER` fonctionne avec des profils synthétiques explicitement identifiés `TEST_ONLY`.

Pour les exemples Forex, un pip EURUSD/GBPUSD vaut `0.0001` de prix ; le point d'affichage peut être `0.00001`. Un pip n'est donc pas automatiquement un point. Pour XAUUSD, les paramètres sont exprimés en dollars par once et en ticks ; aucune convention universelle de pip ou de lot d'or n'est supposée. Les contraintes spécifiques de cette stratégie pour XAUUSD figurent dans la section S.

La valeur de `risk_fraction_per_trade = 0.005` reprend la borne de 0,5 % proposée dans le document fourni ; ce choix n'est pas présenté comme optimal. La limite de risque réservé du compte à 1 % est une convention d'exploitation globale, pas une estimation de perte maximale réelle.

## C04 — Passerelles d'abstention et sorties imposées

Les filtres suivants sont évalués avant tout envoi d'entrée. Ils n'annulent jamais l'obligation de gérer une position existante.

### C04.1 Cotations et spread

La cotation DOIT avoir `0 < bid <= ask`, être horodatée, non future et âgée d'au plus 2 secondes à l'instant de la décision. Le spread vaut `ask - bid`. Une entrée n'est autorisée que si `spread <= max_spread_price`, avec une limite renseignée par profil. Ne pas remplacer un spread inconnu par zéro. Une limite dépassée bloque une entrée ; elle ne constitue pas à elle seule une raison de fermer une position déjà ouverte.

### C04.2 Annonces économiques

Pour un événement pertinent à l'instant `N`, la fenêtre d'interdiction est `[N - 900 s, N + 900 s)`. Aucune nouvelle exposition ne peut être créée pendant cette fenêtre. À son début, annuler les entrées en cours d'envoi ou non exécutées lorsque c'est encore possible et demander la fermeture des positions appartenant au robot. Si plusieurs fenêtres se chevauchent, prendre leur union ; reprise seulement à la fin de cette union et sur un nouveau signal.

Sont pertinents les événements classés de forte importance par la table versionnée du fournisseur pour l'une des deux devises de la paire. Les décisions de taux, conférences monétaires, publications CPI/inflation et emploi de référence DOIVENT être explicitement mappées à cette catégorie ; pour USD cela inclut FOMC, conférence associée, CPI et NFP. Chaque conférence est un événement distinct de la décision qui la précède. Pour XAUUSD, utiliser les événements USD de cette table. Le prix de l'or peut aussi réagir à des événements non programmés ; ce filtre ne prétend pas les anticiper.

La fenêtre de 15 minutes reprend une convention du fichier source, et n'assure pas que les spreads ou la volatilité sont redevenus normaux. Les autres contrôles de cotation et d'exécution continuent à s'appliquer.

Le calendrier doit être âgé d'au plus 24 h et couvrir au moins les 48 prochaines heures. S'il devient indisponible ou périmé, bloquer les nouvelles entrées et conserver l'application des fenêtres déjà connues. Une position existante reste sous SL/TP et sous les autres obligations de fermeture ; une panne de calendrier ne déclenche pas à elle seule une nouvelle règle de sortie. Pour un backtest, distinguer un calendrier historiquement disponible d'un calendrier reconstitué a posteriori et signaler cette limite.

### C04.3 Rollover et fermeture du marché

Le créneau source `[21:00, 23:00)` UTC est conservé comme politique d'exploitation fixe. À 21:00 UTC, demander la fermeture des positions du robot et bloquer les entrées jusqu'à 23:00 UTC. Ne pas prétendre que le rollover effectif de tous les courtiers se produit à cette heure ; l'horaire réel est contrôlé séparément.

Au plus tard 60 secondes avant une fermeture ou pause effective du marché du symbole, demander la fermeture des positions et interdire les entrées jusqu'à réouverture, synchronisation des données et nouveau signal. Cette garde est une convention d'exécution ; elle n'est pas une garantie d'exécution avant fermeture.

### C04.4 Priorités

Séparer deux étapes : les **passerelles de contexte** concernent les données, la disponibilité des indicateurs, le profil, le calendrier et les heures autorisées ; elles conditionnent la création d'un signal. Les **passerelles d'exécution** concernent la cotation actuelle, le spread, les distances d'ordre, le volume, la marge et la réservation de risque. Un spread trop large à l'instant exact de la clôture n'efface pas à lui seul un signal : une cotation admissible peut encore arriver dans son TTL original. Seuls spread et fraîcheur de cotation peuvent attendre ainsi ; un refus structurel ou un refus de réservation/marge après calcul consomme l'intention sans envoi.

Les remplissages et sorties effectivement confirmés par le courtier font foi. Pour une décision nouvelle :

1. Réconcilier les événements de transactions reçus.
2. Appliquer la gestion d'urgence et les fermetures obligatoires, y compris l'heure de sortie propre à la stratégie.
3. Vérifier qu'aucune sortie n'est en attente, que le profil est prêt et que toutes les passerelles autorisent une entrée.
4. Évaluer un signal de clôture admissible.

Une fermeture obligatoire est gérée par horloge/timer et ne doit pas attendre la prochaine clôture M15. En absence de cotation négociable ou de connexion, l'exécution à l'heure exacte est impossible : conserver `EXIT_REQUIRED`, réessayer à la première possibilité réelle et journaliser le retard. Ne jamais inventer un remplissage au prix de la dernière bougie.

## C05 — Calcul du risque, volume et arrondis

Soient `E` le prix d'entrée attendu, `SL` le stop, `v` le volume et `equity` les fonds propres actuels du compte. Le budget de la transaction vaut `B = equity * 0.005` dans la configuration de référence.

Définir, sans compter deux fois le spread :

```text
long:  E_worst = ask + entry_slippage_budget_price
       X_worst = SL - stop_slippage_budget_price
short: E_worst = bid - entry_slippage_budget_price
       X_worst = SL + stop_slippage_budget_price

risk_estimate(v) = max(0, -gross_profit_in_account_currency(side, v, E_worst, X_worst))
                   + round_trip_fees_in_account_currency(v)
```

Le coût du spread est déjà présent dans la combinaison prix d'entrée Ask/Bid et prix de sortie applicable. Ne pas ajouter une deuxième fois un montant de spread à une simulation de transactions déjà exécutées au Bid/Ask. Les commissions, frais et glissements restent explicites. Le budget de glissement est une hypothèse d'estimation et ne borne pas réellement les gaps.

Après remplissage, recalculer l'estimation depuis le prix moyen d'entrée **effectif**, sans lui ajouter une seconde fois le budget de glissement d'entrée. Conserver le budget de glissement de sortie et les frais aller-retour estimés. Comparer au budget monétaire figé à la réservation ; les frais déjà payés font partie de ce total et ne sont pas ajoutés deux fois. Pour les positions déjà réservées, ne pas libérer du risque au motif d'un profit latent : leur réservation conservatrice reste détenue jusqu'à fermeture confirmée ou diminution de volume effectivement constatée.

Choisir le plus grand volume autorisé sur la grille du courtier tel que `risk_estimate(v) <= B`, que la marge soit suffisante et que la réservation globale reste autorisée. Si le modèle est linéaire, calculer une borne puis arrondir le volume vers le bas ; vérifier ensuite le coût effectif avec ses éventuels minima. Sinon, chercher directement sur la grille de volumes. Ne jamais arrondir au volume minimal supérieur si cela dépasse le budget ; refuser la transaction si aucun volume n'est admissible. Le plafond de volume courtier n'est pas dépassé et aucun fractionnement en plusieurs ordres n'est ajouté pour le contourner.

La réservation globale couvre les positions et entrées en vol de tous les robots participants. L'acquisition et la libération sont atomiques. La somme des estimations de perte au stop après l'entrée doit rester au plus `equity * 0.01`. Si des expositions externes empêchent d'évaluer ce total, le coordonnateur refuse la réservation au lieu de supposer qu'elles sont sans risque. Ce contrôle ne ferme pas les positions appartenant à d'autres systèmes.

Tous les prix d'ordre sont sur la grille `tick_size`. Les distances minimales courtier sont contrôlées **après** arrondi, avec la bonne cotation de référence. Si le stop ou l'objectif prescrit n'est pas légal, refuser l'entrée ; ne pas déplacer le stop pour rendre l'ordre acceptable. Ne pas confondre distances en points et distances de prix.

Les stops sont ordinaires, sauf contrat distinctement garanti par le courtier. Le risque estimé ne doit jamais être décrit comme une perte maximale garantie. Le résultat final est calculé à partir des exécutions et frais effectifs.

## C06 — Exécution, propriété des positions et reprise

### C06.1 Interfaces minimales

L'implémentation doit disposer d'équivalents de :

```text
MarketData.closed_bid_bars(symbol, start, end)
MarketData.latest_quote(symbol)
Instrument.describe(symbol, as_of)
Calendar.relevant_events(symbol, start, end, known_at)
CostModel.gross_profit(side, volume, entry, exit, as_of)
CostModel.round_trip_fees(volume, as_of)
RiskCoordinator.reserve(account, symbol, strategy_id, signal_id, risk)
Broker.precheck(order_request)
Broker.submit_protected_entry(order_request, client_order_id)
Broker.transactions_since(cursor)
Broker.owned_positions(strategy_id, symbol)
Broker.close_owned_position(position_id, close_request_id)
StateStore.atomic_commit(state, reservations, journal)
```

Les noms sont indicatifs ; les responsabilités sont obligatoires. Une implémentation MQL5 peut utiliser `OrderCalcProfit`, les propriétés de symbole, `OrderCalcMargin`, `OrderCheck`, `OrderSend` et `OnTradeTransaction`. Un retour positif de `OrderSend` ne signifie pas que la position a été effectivement exécutée : réconcilier les codes de retour, ordres, deals et positions.

### C06.2 Envoi d'une entrée

Un signal est identifié par `(strategy_id, spec_version, configuration_hash, broker_account, broker_symbol, side, signal_bar_close_utc)`. Un seul essai économique est autorisé par signal ; une reconnexion ne crée pas de nouvel essai.

Une intention est `SIGNAL_PENDING` avant son envoi. Une entrée est envoyée au marché sur la première cotation admissible disponible dans `[signal_close, signal_close + 5 s)`, après connaissance de la clôture. Si aucune cotation ne satisfait toutes les conditions dans cette fenêtre, expirer le signal et quitter SIGNAL_PENDING selon les règles de la stratégie, sans réutiliser le signal : SEEK_CONTEXT pour EMA, READY pour Londres avant cutoff si la session n'est pas consommée. Une demande déjà envoyée ne doit pas être dupliquée sous prétexte que son exécution dépasse ces cinq secondes.

Le marquage d'une clôture comme traitée, les transitions d'état et l'éventuelle création d'intention doivent être validés dans **une même transaction persistante**. Une boîte d'envoi durable associe intention, identifiant de requête et réservation avant l'effet externe d'envoi. Ne pas marquer une bougie comme traitée puis perdre son intention à la suite d'un crash. En cas d'incertitude après un envoi, la réconciliation prime sur une réémission ; aucune garantie magique d'exécution « exactement une fois » n'est supposée de l'API courtier.

L'ordre doit comporter un SL protecteur accepté avec l'entrée et un objectif conforme. Si la plateforme ne permet pas une protection attachée ou un mécanisme réellement équivalent documenté, cet adaptateur est incompatible avec cette version ; ne pas ouvrir délibérément une position sans stop. Après remplissage, vérifier la protection effective et ajuster uniquement le TP si la stratégie exige de le recalculer depuis le prix réel.

Si un TP provisoire est exécuté avant la confirmation du prix réel et son recalcul, comptabiliser cette sortie réelle et la signaler `PROVISIONAL_TP_EXECUTION`, comme écart d'exécution au ratio théorique. Ne pas réécrire le deal ni prétendre que le TP recalculé avait été atteint. Un adaptateur asynchrone ne garantit pas l'absence de cette course d'événements.

Un signal dont les cotations, le stop, l'objectif ou le risque deviennent invalides avant l'envoi est abandonné. Aucune entrée limite, stop d'entrée ou poursuite ultérieure n'est substituée au marché. Le robot n'élargit pas un SL existant et n'augmente jamais une position déjà ouverte.

### C06.3 Résultats asynchrones, partiels et erreurs

- `FILLED` : enregistrer prix/volume effectifs, installer ou vérifier le TP exact prévu, recalculer le risque estimé réel et consommer le signal.
- `PARTIAL` : conserver uniquement le volume rempli, annuler le reliquat lorsque le courtier le permet, protéger et gérer ce volume ; ne pas renvoyer le solde. Si l'annulation est encore en vol, conserver la réservation correspondante.
- Sur plusieurs deals successifs d'une même entrée, mettre à jour le prix moyen pondéré et le volume cumulé depuis les deals confirmés ; appliquer à nouveau le contrôle de risque et la règle de TP propre à la stratégie. L'annulation demandée d'un reliquat n'autorise pas à ignorer un deal supplémentaire arrivé avant sa confirmation.
- `REJECTED` : journaliser le motif, consommer le signal et libérer la réservation seulement après confirmation qu'aucun remplissage n'existe.
- `UNKNOWN/TIMEOUT` : après dix secondes sans état concluant, entrer en `RECONCILE_REQUIRED`. Bloquer les nouvelles entrées, interroger les transactions et ordres existants ; ne pas renvoyer l'ordre sans preuve de son absence et, même alors, ne pas réutiliser un signal expiré.
- Risque post-remplissage supérieur au budget figé à la réservation, protection absente, volume inattendu ou incohérence de propriété : demander la fermeture de la position propre au robot, passer en `HALTED`, journaliser l'incident. Les pertes éventuelles restent comptabilisées. Ne pas masquer l'incident par une modification rétroactive du budget.

Une fermeture est idempotente par identifiant de position et motif. Une fermeture partielle non voulue laisse `EXIT_REQUIRED` sur le reliquat jusqu'à confirmation d'absence de position. La réservation n'est libérée qu'au prorata du volume effectivement fermé et après réconciliation des entrées encore en vol.

### C06.4 Sens Bid/Ask

```text
Achat: entrée Ask ; sortie Bid ; SL touché si Bid <= SL ; TP touché si Bid >= TP.
Vente: entrée Bid ; sortie Ask ; SL touché si Ask >= SL ; TP touché si Ask <= TP.
```

Les extrêmes du signal proviennent toujours des bougies Bid. Pour une vente, le déclenchement du stop est sur Ask : cela peut intervenir avant que le graphique Bid semble atteindre ce niveau. Ne pas corriger ce phénomène en ajoutant silencieusement un spread au stop.

### C06.5 Positions simultanées et redémarrage

Une seule position propre à ce robot et à ce symbole à la fois, en comptant les entrées en vol. Aucun pyramiding, renfort après perte, martingale, déplacement au point mort, trailing stop ou sortie partielle volontaire dans cette version.

En compte netting, obtenir un verrou exclusif `(account, symbol)` avant une entrée et le conserver jusqu'à absence de position et d'ordre en vol. Si un autre robot ou une position manuelle utilise déjà ce symbole, refuser l'entrée ; ne jamais fusionner les expositions ou fermer la position d'autrui. En compte hedging, isoler les tickets par stratégie et utiliser quand même le coordonnateur de risque du compte.

Persister : version/hash de configuration, identifiants des signaux consommés, dernière bougie traitée, état de stratégie, range ou repli en cours, ancre des indicateurs si applicable, positions/ordres attendus, réservations, événements calendrier connus, curseur de transactions et motifs d'arrêt. Au démarrage, réconcilier ce stockage avec le courtier avant toute décision. Un conflit non résolu implique `RECONCILE_REQUIRED`. Une position découverte reste sous gestion de sortie même si le profil n'autorise plus de nouvelles entrées.

## C07 — Journal et résultats auditables

Émettre un journal structuré UTF-8, JSONL ou format équivalent, comportant au minimum :

- `run_id`, version de spécification, hash de configuration et hash/identifiant des données ;
- `event_utc`, `received_utc`, `event_sequence`, date de session et fuseaux utilisés ;
- symbole, état avant/après, signal_id, OHLC utilisés et valeurs de tous les indicateurs ou bornes utilisés ;
- résultats et motifs de chaque passerelle : données, calendrier, spread, risque, marge, session ;
- Bid/Ask, âges des données, profil de contrat, volume calculé/arrondi, risque réservé ;
- prix et identifiants demandés, codes de retour, remplissages réels, SL/TP réels ;
- résultat brut, commissions, autres frais, financement réellement facturé, résultat net et risque initial de référence ;
- erreurs, déconnexions, dépassements de temps et impossibilités de fermeture.

Conserver les signaux refusés et les raisons d'absence de transaction, pas seulement les gains. Un trade ne change pas d'identifiant après perte ou fermeture d'urgence. Les agrégats doivent être reproductibles depuis les transactions enregistrées.

Codes minimaux : `PROFILE_INCOMPLETE`, `DATA_INCOMPATIBLE`, `DATA_GAP`, `WARMUP`, `NEWS_BLACKOUT`, `CALENDAR_UNAVAILABLE`, `ROLLOVER_BLACKOUT`, `MARKET_CLOSING`, `STALE_QUOTE`, `SPREAD_TOO_WIDE`, `SIGNAL_EXPIRED`, `NO_VALID_VOLUME`, `BROKER_DISTANCE_INVALID`, `RISK_CAP`, `MARGIN_INSUFFICIENT`, `SYMBOL_LOCKED`, `ENTRY_REJECTED`, `RECONCILE_REQUIRED`, `PROTECTION_FAILURE`, `EXIT_REQUIRED`, `HALTED`. Les codes propres à la stratégie s'ajoutent à cette liste.

## C08 — Exigences de simulation et de validation économique

L'agent doit livrer séparément la **conformité logicielle** et les **résultats de marché**. L'achèvement du développement n'autorise pas à écrire « stratégie rentable » sans résultats vérifiables.

1. Même moteur déterministe pour replay, paper et exécution connectée ; seuls les adaptateurs de données/exécution changent.
2. Replay de ticks Bid/Ask, spread variable, frais et glissements explicités. Les bougies M15 servent à la décision, pas à inventer l'ordre intrabougie des touches SL/TP.
3. Si seul OHLC est disponible et si SL et TP sont touchés dans la même bougie, le cas est `AMBIGUOUS_INTRABAR`. Un calcul secondaire peut présenter des bornes pessimiste/optimiste ; il ne constitue pas une exécution précise ou un backtest de référence.
4. Respecter la causalité des indicateurs, signaux, calendriers et conversions monétaires ; ne pas entrer au Close déjà observé si ce prix n'était plus négociable.
5. Séparer chronologiquement conception, validation et période finale non utilisée pour choisir les paramètres. Consigner toutes les variantes essayées ; ne pas sélectionner la meilleure puis appeler son historique « hors échantillon ».
6. Mesurer nombre de trades, durée, taux de réussite, gains/pertes moyens, espérance nette, profit factor net, baisse maximale des fonds propres, séries de pertes, exposition et incidents d'exécution. Si le dénominateur du profit factor est nul, signaler la valeur non finie et la taille de l'échantillon.
7. Présenter les résultats par symbole, période et année ; aucun succès EURUSD ne valide automatiquement XAUUSD. Quantifier l'incertitude ; utiliser des blocs temporels pour le rééchantillonnage si la dépendance entre transactions le nécessite.
8. Comparer la sensibilité aux coûts et aux conventions avant d'affirmer un bénéfice. Aucun nombre fixe de transactions, profit factor ou taux de réussite n'est une preuve suffisante à lui seul.
9. L'environnement de livraison par défaut est `PAPER`. Un mode connecté existe dans la configuration ; il reste distinct des fixtures synthétiques et n'est pas activé par la lecture de cette spécification.

Les valeurs de test dans ce document sont synthétiques. Les checks décrits ici ne constituent ni un backtest sur prix réels ni une validation de rentabilité.

## C09 — Cas communs d'acceptation

| ID | Entrée ou situation | Résultat exigé |
|---|---|---|
| C-T01 | Une bougie n'est pas clôturée | Aucun signal de décision issu de ses OHLC |
| C-T02 | Deux callbacks annoncent la même clôture | Un seul traitement économique, aucun ordre dupliqué |
| C-T03 | Cotation âgée exactement de 2 s, puis de 2,001 s | Première admissible sur ce critère ; seconde refusée |
| C-T04 | Spread égal au maximum, puis supérieur d'un tick | Premier admissible ; second refusé |
| C-T05 | Événement à 13:30 UTC | Blocage de 13:15 inclus à 13:45 exclu ; fermeture demandée à 13:15 |
| C-T06 | Fenêtres de deux annonces qui se chevauchent | Aucune réouverture entre les deux fenêtres |
| C-T07 | Calendrier périmé et position propre déjà ouverte | Pas d'entrée ; gestion de la position existante maintenue |
| C-T08 | Signal clôturé à 08:15:00, cotation à 08:15:04,999 puis à 08:15:05 | Première dans TTL ; seconde hors TTL |
| C-T09 | Minimum de lot supérieur au volume compatible avec le budget | Refus ; aucun arrondi vers le minimum |
| C-T10 | Stop prescrit incompatible avec distance courtier | Refus ; aucune modification du stop de stratégie |
| C-T11 | Achat avec Bid sous SL mais Ask au-dessus | Déclenchement de la sortie au stop selon Bid |
| C-T12 | Vente avec Ask au-dessus du SL mais Bid en dessous | Déclenchement de la sortie au stop selon Ask |
| C-T13 | Réponse d'envoi positive mais absence de deal confirmé | Pas d'état FILLED fictif ; réconciliation |
| C-T14 | Timeout, puis notification de remplissage tardive | Une seule position ; aucun second ordre |
| C-T15 | Remplissage partiel | Annulation du reliquat, protection du volume reçu, pas de complément |
| C-T16 | Redémarrage alors qu'un ordre est en vol | Réconciliation avant toute nouvelle entrée |
| C-T17 | Compte netting déjà occupé sur ce symbole par un autre système | Pas d'entrée et aucune fermeture de la position d'autrui |
| C-T18 | Marché fermé à une échéance de fermeture obligatoire | EXIT_REQUIRED persiste ; pas de sortie simulée fictive |
| C-T19 | SL et TP touchés dans une bougie sans ticks | AMBIGUOUS_INTRABAR ; aucune victoire choisie arbitrairement |
| C-T20 | Deux robots réservent simultanément plus de 1 % au total | Le coordonnateur refuse au moins la réservation qui dépasserait le plafond |

Deux fixtures numériques communes doivent être reproduites sans arrondi supérieur :

```text
C-N01 — Forex synthétique, compte USD
equity = 20 000 USD ; risque = 0,005 => budget = 100 USD
achat exécuté/estimé = 1,1000 ; SL = 1,0988
contrat = 100 000 EUR par lot ; glissements de test = 0
perte brute par lot = 120 USD
frais aller-retour = 7 USD par lot ; grille = 0,01 lot
volume maximal = floor((100 / 127) / 0,01) * 0,01 = 0,78 lot
risque estimé = 0,78 * 127 = 99,06 USD
0,79 lot donnerait 100,33 USD => interdit

C-N02 — Or synthétique, compte USD
equity = 10 000 USD ; risque = 0,005 => budget = 50 USD
distance entrée-stop = 8 USD/once ; contrat de test = 100 onces/lot
frais aller-retour = 7 USD/lot ; grille = 0,01 lot ; glissements = 0
perte brute par lot = 800 USD ; risque avec frais = 807 USD/lot
volume maximal = 0,06 lot ; risque = 48,42 USD
0,07 lot donnerait 56,49 USD => interdit
```

Ces tailles contractuelles sont propres aux fixtures ; elles ne remplacent pas les métadonnées d'un courtier réel.

## C10 — Livrables exigés de l'agent chargé du développement

- Moteur de stratégie, adaptateurs, schéma validé de configuration et gestion persistante des états.
- Mode de replay déterministe, mode paper et séparation explicite du mode connecté.
- Jeux de tests couvrant C-T, C-N et S-T, avec observations d'états et d'ordres, et non seulement captures de graphiques.
- Journal structuré, export des trades et signaux refusés, rapport de conformité associant chaque exigence à son implémentation.
- Instructions d'installation et d'utilisation adaptées à la plateforme retenue, dépendances figées et procédures de reprise.
- Rapport de validation économique distinct s'il est effectivement réalisé ; sinon mention explicite de son absence.
- Zéro règle de décision ajoutée en silence. Toute divergence documentée doit être résolue ou nommée comme variante avant de déclarer la conformité à cette version.
'''

EMA_CONFIG = {
    'strategy_id': 'M15_TRIPLE_EMA_RSI_PULLBACK',
    'indicator_min_closed_bars': 500,
    'ema_periods': [15, 25, 50],
    'rsi_period': 14,
    'slope_lookback_bars': 1,
    'exit_mode': 'FIXED_R_2',
    'take_profit_r_multiple': 2,
    'strong_body_fraction_min': 0.60,
    'strong_close_end_fraction_max': 0.25,
    'hammer_dominant_wick_body_ratio_min': 2,
    'hammer_other_wick_body_ratio_max': 1,
    'use_h1_filter': False,
    'use_london_range': False,
    'max_position_duration_bars': None,
}

EMA = r'''
## S01 — Identité et choix retenus

Stratégie : **Triple EMA 15/25/50 + RSI 14 + repli M15**, indépendante du London Breakout.

| Élément | Règle de cette version | Origine |
|---|---|---|
| Indicateurs | EMA 15, 25 et 50 sur Close Bid M15 ; RSI Wilder 14 | SOURCE |
| Contexte acheteur/vendeur | Ordre strict des EMA, pentes orientées, prix dans le sens de la tendance | SOURCE, inégalités formalisées |
| Repli | Interaction avec zone EMA 25–50 ; RSI ne franchissant pas 50 à contre-sens sur les clôtures | SOURCE, déroulement formalisé |
| Déclencheur | Rejet de la zone par bougie forte ou marteau symétrique | SOURCE ; géométrie FORMALISATION |
| SL | Un tick strictement au-delà de l'extrême du repli | SOURCE ; marge minimale FORMALISATION |
| TP | 2 fois la distance de prix entrée réelle–SL, avant frais | Branche fixe SOURCE |
| Réglages de bougies | 60 %, quart de range, ratios de mèches 2 et 1 | FORMALISATION, non optimisés |
| Pente | Différence sur une bougie clôturée | FORMALISATION, non optimisée |
| Durée maximale | Aucune limite en nombre de bougies ; sorties C04 applicables | FORMALISATION évitant d'inventer une sortie à 2 h |

Le filtre H1 et le remplacement par EMA 20/50 discutés précédemment sont exclus : leur bénéfice dans ce contexte n'a pas été établi. Le RSI reste obligatoire. Aucun range de session, breakout ou retest de Londres n'intervient.

La branche alternative « sortir quand RSI atteint 70/30 » du texte source n'est pas combinée au TP fixe. Les niveaux 70 et 30 peuvent être affichés dans les diagnostics mais NE déclenchent ni sortie, ni refus d'entrée dans cette version. Une hausse au-dessus de 70 n'est pas un ordre de vente automatique.

## S02 — Calcul reproductible des indicateurs

### S02.1 Ancrage

Le jeu de données ou l'état persistant définit `indicator_epoch_utc`, ouverture de sa première bougie valide. Cette ancre est enregistrée dans le manifeste. Charger au moins 500 bougies M15 clôturées depuis cette ancre avant la première décision de stratégie. Les indicateurs traversent les week-ends sans réinitialisation, sur les seules bougies de périodes effectivement cotées.

Recalculer en replay depuis cette même ancre, ou restaurer exactement l'état incrémental persistant. Recommencer à chaque nouvelle bougie une EMA sur seulement les 500 dernières bougies produirait un autre indicateur et est interdit. Un indicateur natif n'est accepté qu'après comparaison avec les équations et les graines ci-dessous ; sinon implémenter le calcul de référence.

### S02.2 EMA

Pour chaque période `n` de `{15,25,50}`, numéroter les clôtures depuis l'ancre à partir de zéro :

```text
alpha_n = 2 / (n + 1)
EMA_n[n-1] = moyenne(C[0], ..., C[n-1])
EMA_n[t] = alpha_n * C[t] + (1-alpha_n) * EMA_n[t-1], pour t >= n
```

Avant la graine, la valeur est indisponible, pas zéro. La pente vaut `EMA_n[t] - EMA_n[t-1]`. Aucune valeur future ou bougie H1 n'entre dans le calcul.

### S02.3 RSI de Wilder

Pour les différences `d_t = C_t - C_(t-1)` : `gain_t = max(d_t,0)` et `loss_t = max(-d_t,0)`. La première moyenne utilise les 14 différences `d_1 ... d_14`, puis :

```text
avg_gain[14] = somme(gain[1:15]) / 14
avg_loss[14] = somme(loss[1:15]) / 14
avg_gain[t] = (13*avg_gain[t-1] + gain[t]) / 14
avg_loss[t] = (13*avg_loss[t-1] + loss[t]) / 14
si avg_gain == 0 et avg_loss == 0 : RSI = 50
sinon si avg_loss == 0 : RSI = 100
sinon si avg_gain == 0 : RSI = 0
sinon RSI = 100 - 100/(1 + avg_gain/avg_loss)
```

Les tests d'absence de variation ici sont exacts à partir des différences de prix sur la grille des ticks ; aucune division par zéro n'est autorisée. Sur un repli, le respect de RSI 50 est vérifié aux clôtures, pas continuellement entre deux ticks.

## S03 — Prédicats de contexte et géométrie des bougies

Les prédicats utilisent les indicateurs calculés jusqu'à la clôture `t`, y compris celle-ci.

```text
order_long(t)  := EMA15_t > EMA25_t > EMA50_t
order_short(t) := EMA15_t < EMA25_t < EMA50_t

slopes_long(t) := pour n=15,25,50 : EMA_n[t] > EMA_n[t-1]
slopes_short(t):= pour n=15,25,50 : EMA_n[t] < EMA_n[t-1]

context_long(t)  := order_long(t)  ET slopes_long(t)  ET C_t > EMA15_t ET RSI_t > 50
context_short(t) := order_short(t) ET slopes_short(t) ET C_t < EMA15_t ET RSI_t < 50

zone_low(t)  = min(EMA25_t, EMA50_t)
zone_high(t) = max(EMA25_t, EMA50_t)
touch_zone(t) := L_t <= zone_high(t) ET H_t >= zone_low(t)

range_t = H_t - L_t
body_t = abs(C_t - O_t)
upper_wick_t = H_t - max(O_t,C_t)
lower_wick_t = min(O_t,C_t) - L_t
```

Une bougie invalide (`H < max(O,C)`, `L > min(O,C)`, prix non finis) bloque les signaux jusqu'à réparation des données. Une bougie sans range, ou un doji de corps nul, ne fournit aucun déclencheur.

```text
strong_long(t) := C_t > O_t
                  ET body_t >= 0.60 * range_t
                  ET H_t - C_t <= 0.25 * range_t

strong_short(t):= C_t < O_t
                  ET body_t >= 0.60 * range_t
                  ET C_t - L_t <= 0.25 * range_t

hammer_long(t) := C_t > O_t ET body_t > 0
                  ET lower_wick_t >= 2 * body_t
                  ET upper_wick_t <= body_t

hammer_short(t):= C_t < O_t ET body_t > 0
                  ET upper_wick_t >= 2 * body_t
                  ET lower_wick_t <= body_t
```

Les comparaisons de ratios à leurs bornes sont inclusives. Le filtre fort et le filtre marteau forment un OU ; l'agent ne doit pas demander qu'une bougie satisfasse simultanément les deux. La symétrie haussière/baissière est obligatoire.

## S04 — Machine à états et cycle de repli

États propres à la stratégie : `SEEK_CONTEXT`, `ARMED_LONG`, `ARMED_SHORT`, `PULLBACK_LONG`, `PULLBACK_SHORT`, `SIGNAL_PENDING`, `ENTRY_IN_FLIGHT`, `POSITION_OPEN`. Les états d'exploitation C s'appliquent par-dessus ces états.

### S04.1 Évaluation d'une clôture sans position

Traiter une clôture une seule fois. Si une passerelle de contexte C04 bloque le trading, effacer le contexte/repli et revenir à `SEEK_CONTEXT`. Il faudra un contexte nouvellement observé sur une clôture ultérieure ; ne pas reprendre un vieux repli après une annonce ou un trou de données. La cotation et le spread sont contrôlés à l'étape d'exécution et peuvent attendre dans le TTL prévu, sans altérer cette séquence.

En `SEEK_CONTEXT`, si `context_long(t)` est vrai, passer à `ARMED_LONG` ; sinon si `context_short(t)` est vrai, passer à `ARMED_SHORT` ; sinon rester. Une bougie qui arme le contexte ne démarre pas simultanément un repli. Il faut donc avoir constaté le contexte sur une clôture antérieure.

### S04.2 Passage ARMED vers PULLBACK

Pour `ARMED_LONG`, à une clôture ultérieure :

1. Si `order_long(t)` est faux, ou `C_t < EMA50_t`, ou `RSI_t < 50`, invalider. Revenir à SEEK_CONTEXT puis seulement armer un contexte éventuellement présent sur cette clôture, sans créer un repli le même événement.
2. Sinon, si `touch_zone(t)` est vrai, démarrer `PULLBACK_LONG` à `start_index=t`, avec `pullback_low=L_t`, `pullback_high=H_t`. La bougie de premier contact peut aussi être la bougie de rejet : évaluer S05 après initialisation des extrêmes.
3. Sinon conserver ARMED_LONG. Les pentes peuvent temporairement se retourner sans que l'ordre des EMA soit rompu ; elles seront exigées au déclenchement.

Pour `ARMED_SHORT`, utiliser `order_short`, invalider si `C_t > EMA50_t` ou `RSI_t > 50`, puis démarrer le repli sur `touch_zone(t)` et initialiser les mêmes extrêmes.

### S04.3 Suivi d'un repli

À chaque clôture en `PULLBACK_LONG`, mettre à jour `pullback_low=min(pullback_low,L_t)` et `pullback_high=max(pullback_high,H_t)`, y compris la bougie de rejet. Puis invalider si ordre long perdu, clôture sous EMA50 ou RSI sous 50. L'invalidation a priorité sur tout déclencheur de la bougie.

Pour `PULLBACK_SHORT`, mettre à jour les extrêmes puis invalider si ordre short perdu, clôture au-dessus EMA50 ou RSI au-dessus 50.

Le RSI égal à 50 est toléré pendant le repli, mais une entrée exige ensuite son retour strict du bon côté de 50. Une mèche au-delà de l'EMA50 n'invalide pas à elle seule un repli ; une clôture au-delà l'invalide. Il n'existe pas de nombre maximal de bougies de repli dans cette version. Si une limite est souhaitée ultérieurement, ce sera une variante évaluée séparément.

## S05 — Conditions d'entrée exactes

Après mise à jour et sans invalidation de S04 :

```text
signal_long(t) := état PULLBACK_LONG
                  ET context_long(t)
                  ET touch_zone(t)
                  ET (strong_long(t) OU hammer_long(t))

signal_short(t):= état PULLBACK_SHORT
                  ET context_short(t)
                  ET touch_zone(t)
                  ET (strong_short(t) OU hammer_short(t))
```

Le contexte au déclenchement impose notamment que le Close repasse au-delà de l'EMA15 ; pendant le repli, cette condition de prix n'était pas exigée. Le signal DOIT lui-même toucher la zone : une bougie ultérieure qui repart sans toucher la zone n'est pas un rejet admissible dans cette formalisation.

Un repli donne au plus un signal. Au premier signal, figer ses bornes, consommer le repli et passer à SIGNAL_PENDING, même si la transaction est ensuite refusée par les contraintes d'exécution. Cela évite de requalifier le même repli à chaque bougie. Si l'entrée n'a pas été envoyée ou a été refusée, revenir à SEEK_CONTEXT ; il faudra attendre une clôture ultérieure pour armer. Aucun ordre n'est retardé jusqu'à une confirmation H1.

Si aucune nouvelle position n'est autorisée (position existante, entrée en vol, verrou de symbole), ne pas accumuler de signaux. À la fermeture de la position, réinitialiser le contexte et attendre une nouvelle clôture pour armer une nouvelle configuration. Ne pas entrer et réentrer sur la même clôture.

## S06 — Stop, objectif et gestion d'une position

Sur le signal, définir le SL à partir des extrêmes du repli déjà observés :

```text
SL_long  = (ceil(pullback_low / tick_size) - 1) * tick_size
SL_short = (floor(pullback_high / tick_size) + 1) * tick_size
```

Ces formules placent le stop strictement au-delà de l'extrême, même si un prix d'extrême est légèrement hors grille. Sur des extrêmes déjà alignés, cela représente un tick de marge. Aucun coefficient ATR ni nombre fixe de pips n'est ajouté.

Calculer le volume selon C05. Si `E_real` est le prix moyen effectivement exécuté :

```text
Achat : D = E_real - SL ; doit être > 0
        TP = ceil((E_real + 2*D) / tick_size) * tick_size
Vente : D = SL - E_real ; doit être > 0
        TP = floor((E_real - 2*D) / tick_size) * tick_size
```

Pour l'envoi protégé initial, utiliser le prix d'entrée attendu courant pour calculer un TP provisoire, puis demander immédiatement sa réconciliation depuis le prix réel sans élargir le SL. Un refus définitif de modification, ou l'absence de confirmation d'un objectif conforme dix secondes après connaissance du remplissage, est un incident d'exécution : demander la fermeture et HALTED. En cas de nouveau deal partiel, recalculer immédiatement depuis le nouveau prix moyen et appliquer la même échéance au dernier ajustement requis. Le ratio est un ratio de **distance de prix brut**, pas un ratio net garanti après frais.

Les seules sorties normales sont SL, TP et fermetures obligatoires C04. Ne pas sortir automatiquement sur croisement inverse, RSI 70/30, fin du repli ou durée de deux heures. Ne pas déplacer le stop après progression favorable. Une clôture de signal opposé n'ouvre pas une position inverse tant que la position courante existe.

## S07 — Pseudocode normatif de décision

```text
on_closed_bar(t):
    reconcile_broker_events()
    update_reference_indicators(t)
    if bar_already_processed(t): return
    # Tous les changements de cet événement, dont processed(t), sont commités ensemble.
    if owned_position_or_entry_in_flight_or_signal_pending(): return
    if not ready_or_context_gates_open(t.close): reset_setup(); return

    if state == SEEK_CONTEXT:
        arm_context_if_present(t)
        return

    if state in {ARMED_LONG, PULLBACK_LONG}:
        if state == PULLBACK_LONG: update_pullback_extremes(t)
        if invalid_long(t): reset_setup(); arm_context_if_present(t); return
        if state == ARMED_LONG and touch_zone(t): start_pullback_long(t)
        if state == PULLBACK_LONG and signal_long(t):
            freeze_and_consume_setup(t)
            create_one_long_intent_with_deadline(t.close + 5 seconds)
        return

    if state in {ARMED_SHORT, PULLBACK_SHORT}:
        if state == PULLBACK_SHORT: update_pullback_extremes(t)
        if invalid_short(t): reset_setup(); arm_context_if_present(t); return
        if state == ARMED_SHORT and touch_zone(t): start_pullback_short(t)
        if state == PULLBACK_SHORT and signal_short(t):
            freeze_and_consume_setup(t)
            create_one_short_intent_with_deadline(t.close + 5 seconds)
        return

on_quote_or_timer(now):
    reconcile_broker_events()
    apply_mandatory_exits_even_without_bar_close(now)
    if entry_intent_exists:
        if now >= intent.deadline: expire_intent(); return
        if quote_is_stale_or_spread_too_wide: wait_only_until_original_deadline()
        else if context_or_structural_gate_fails: expire_intent(); return
        else:
            validate_stop_target_and_quote()
            calculate_volume_and_atomically_reserve_risk()
            submit_once_with_attached_protection()
```

Une cause structurelle signifie stop/objectif de mauvais côté, profil devenu incompatible, configuration invalidée ou fermeture obligatoire : annuler définitivement l'intention. Un refus de risque ou de marge consomme aussi l'intention sans envoi. Un spread temporairement trop large ou une cotation périmée peuvent attendre une nouvelle cotation, uniquement dans le TTL original ; ne pas décaler sa fin.

## S08 — Exemples synthétiques de bout en bout

### S08.1 Achat Forex et image vendeuse

Les indicateurs suivants sont des sorties de référence injectées dans le test de machine à états, pas une prétendue reconstruction depuis une seule bougie.

À la clôture précédente : contexte haussier établi, donc ARMED_LONG. Sur la bougie de contact/rejet :

```text
tick_size = 0,00001
EMA15 = 1,10070 ; EMA25 = 1,10060 ; EMA50 = 1,10000
EMA15_precedente = 1,10069 ; EMA25_precedente = 1,10059 ; EMA50_precedente = 1,09999
RSI = 54 ; aucun RSI inférieur à 50 pendant le repli
O = 1,10030 ; H = 1,10110 ; L = 1,10020 ; C = 1,10100
```

Le range vaut 0,00090 ; le corps 0,00070 : 77,78 % du range ; la mèche haute vaut 0,00010 : 11,11 % du range. La bougie touche la zone, clôture au-dessus EMA15 et valide un signal long.

Sur une cotation admissible après clôture : Bid 1,10100 ; Ask 1,10102. Avec ce prix moyen d'achat effectif et le plus bas de repli 1,10020 :

```text
SL = 1,10019
D = 1,10102 - 1,10019 = 0,00083 = 8,3 pips
TP = 1,10102 + 2*0,00083 = 1,10268
gain visé = 16,6 pips bruts ; coûts et volume traités séparément
```

L'image vendeuse s'obtient par réflexion de tous les prix Bid et des EMA autour de la constante 2,20000 : `prix' = 2,20000 - prix`, en échangeant High et Low, et `RSI'=100-RSI`. La cotation d'entrée vendeuse de fixture est Bid 1,09898 ; Ask 1,09900. Avec sommet du repli 1,09980 : SL 1,09981, distance 0,00083 et TP 1,09732. Ce test vérifie les branches vendeuses et les bonnes cotations, sans présumer de rentabilité.

### S08.2 Or

Si le profil réel autorise XAUUSD et si tous les prédicats S03–S05 sont satisfaits : entrée effective hypothétique 4 000,00 USD/once, extrême bas de repli 3 992,01, tick 0,01. Alors SL 3 992,00, distance 8,00 et TP 4 016,00 USD/once. Le volume est calculé depuis le contrat et les frais réels. Il n'existe pas de stop universel de « 15 pips or » dans cette stratégie.

## S09 — Cas spécifiques d'acceptation

| ID | Situation | Résultat exigé |
|---|---|---|
| S-T01 | Moins de 500 bougies disponibles depuis l'ancre | WARMUP, aucune entrée |
| S-T02 | Série de prix constante | EMA constantes ; RSI 50 ; pas de contexte strict |
| S-T03 | Série strictement croissante dès la graine RSI | RSI 100, pas de division par zéro |
| S-T04 | Série strictement décroissante | RSI 0, branche short possible seulement si tous autres critères vrais |
| S-T05 | Contexte constaté pour la première fois et contact de zone dans cette même bougie | Armer seulement ; pas de repli ni d'entrée sur cette bougie |
| S-T06 | Contexte antérieur puis contact/rejet fort selon S08.1 | Un signal long, SL 1,10019, TP 1,10268 au prix réel indiqué |
| S-T07 | RSI égal à 50 durant le repli puis 54 sur rejet valide | Repli conservé puis signal possible |
| S-T08 | Une clôture RSI 49,99 durant le repli long | Invalidation, même si RSI revient ensuite à 54 |
| S-T09 | Mèche sous EMA50 mais clôture au-dessus et autres conditions valides | Pas d'invalidation pour cette seule mèche |
| S-T10 | Clôture sous EMA50 et bougie de fort corps haussier | Invalidation prioritaire, pas de signal long |
| S-T11 | Rejet seulement sur bougie en cours | Pas de signal avant clôture |
| S-T12 | Corps de 60 % et distance Close–extrême favorable de 25 % | Bornes incluses |
| S-T13 | Marteau valide sans corps fort | Signal possible car OU, si autres critères vrais |
| S-T14 | Doji, même avec longue mèche | Aucun déclencheur |
| S-T15 | Bonne bougie de reprise mais aucun contact de zone sur cette bougie | Pas de signal de rejet dans cette version |
| S-T16 | Premier signal du repli refusé pour risque | Repli consommé ; pas de répétition sur le même repli |
| S-T17 | RSI franchit 70 après entrée long en mode fixe | Pas de sortie RSI |
| S-T18 | EMA se croisent contre une position ouverte | Pas de sortie supplémentaire ; SL/TP et C04 restent actifs |
| S-T19 | Réflexion vendeuse de S08.1 | Un signal short, SL 1,09981, TP 1,09732 |
| S-T20 | Annonce commence pendant un repli | Repli effacé ; nouveau contexte requis après la fenêtre |
| S-T21 | Recalcul intégral depuis ancre et restauration incrémentale | Valeurs et signaux identiques dans la tolérance définie |

## S10 — Limites explicitement conservées

- Les moyennes et le RSI reposent sur les mêmes prix ; leur association n'est pas une confirmation statistiquement indépendante démontrée.
- Le repli peut précéder un retournement complet. Un stop structurel n'empêche ni perte ni glissement.
- La géométrie de bougie, la définition des pentes et la séquence du repli sont des conventions nécessaires, pas des résultats d'optimisation.
- La stratégie n'a pas de filtre H1, ADX, ATR, volume, session de Londres ou résistance H1 ajouté.
- Les trois symboles cités partagent le même moteur ; leur rentabilité doit être évaluée séparément avec leurs profils propres.
'''

LONDON_CONFIG = {
    'strategy_id': 'M15_LONDON_BREAKOUT_CLOSE',
    'range_timezone': 'UTC',
    'range_start': '02:00:00',
    'range_end': '06:00:00',
    'entry_start_timezone': 'Europe/London',
    'entry_start_local': '08:00:00',
    'entry_cutoff_timezone': 'UTC',
    'entry_cutoff': '10:00:00',
    'force_exit_timezone': 'UTC',
    'force_exit': '12:00:00',
    'entry_mode': 'M15_CLOSE_MARKET',
    'stop_mode': 'OPPOSITE_RANGE_BOUNDARY',
    'target_range_multiple': 1.5,
    'max_filled_entries_per_session': 1,
    'weak_body_fraction_below': 0.30,
    'opposing_wick_fraction_above': 0.50,
    'use_retest': False,
    'use_ema': False,
    'use_rsi': False,
    'use_h1_filter': False,
    'entry_buffer_price': 0,
    'symbol_strategy_profiles': {
        'EURUSD': {'max_range_width_price': 0.0060},
        'GBPUSD': {'max_range_width_price': 0.0060},
        'XAUUSD': {'max_range_width_price': None},
    },
}

LONDON = r'''
## S01 — Identité et branche sélectionnée

Stratégie : **London Breakout sur clôture M15**, autonome et sans aucun filtre de tendance ou repli ajouté.

Le document source présente plusieurs alternatives incompatibles si on les superpose. Cette spécification en sélectionne exactement une à chaque étape :

| Élément | Règle retenue | Origine et statut |
|---|---|---|
| Range | 02:00 inclus à 06:00 exclu, UTC | Branche SOURCE ; pas d'extension à 07:00 |
| Début d'observation | 08:00 heure locale de Londres | FORMALISATION d'une ouverture londonienne ; pas une amélioration démontrée |
| Déclencheur | Clôture M15 strictement au-delà d'une borne | Branche SOURCE |
| Entrée | Marché après connaissance de la clôture | Branche SOURCE ; ni Buy Stop ni Sell Stop |
| Buffer d'entrée | Zéro au-delà de la condition de clôture | Aucun buffer 3–5 pips ajouté à la branche par clôture |
| Filtre de bougie faible | Corps < 30 % ET mèche de rejet > 50 % du range | SOURCE pour le principe ; seuils FORMALISATION |
| Largeur maximale EURUSD/GBPUSD | 60 pips, soit 0,0060 de prix | SOURCE, non validée comme optimale |
| SL | Borne opposée du range | Branche SOURCE ; pas de stop au milieu |
| TP | 1,5 fois la largeur depuis la borne cassée | Branche SOURCE, non validée comme optimale |
| Fin des entrées | 10:00 UTC exclu | SOURCE |
| Fermeture obligatoire | 12:00 UTC | SOURCE ; justification horaire d'origine corrigée |
| Entrées exécutées | Au plus une par date de session | FORMALISATION de la consommation d'une opportunité journalière |

Les ordres Buy Stop/Sell Stop en OCO, le stop au milieu du range, l'objectif à 2 largeurs et l'objectif ATR quotidien sont d'autres branches du texte source. Ils NE sont PAS implémentés comme modes alternatifs cachés dans cette version. Un autre choix nécessite sa propre version et un comparatif. Leur exclusion ne signifie pas qu'ils seraient moins rentables.

Le retest, les EMA, le RSI, le filtre H1 et une largeur exprimée en multiples d'ATR discutés dans la conversation ne sont pas ajoutés : aucun bénéfice certain dans les conditions de l'utilisateur n'a été démontré.

## S02 — Horaires et journée de session

La clé de session `session_date` est la date civile UTC du range. Le range de cette date est `[02:00,06:00)` UTC et reste dans cette date. À la date de session, convertir **08:00 Europe/London** en UTC à l'aide d'une base de fuseaux versionnée pour obtenir `entry_start_utc`.

En conditions de fuseaux actuelles, cette heure correspond à 08:00 UTC en hiver britannique et 07:00 UTC en été britannique. Les bornes du range restent UTC fixes : elles ne se décalent pas avec Londres. Cela conserve la fenêtre de range sélectionnée dans le fichier source ; il ne faut pas transformer silencieusement l'ensemble des heures en heures locales londoniennes.

```text
range_start_utc = session_date 02:00:00 UTC
range_end_utc = session_date 06:00:00 UTC
entry_start_utc = conversion(session_date 08:00:00 Europe/London -> UTC)
entry_cutoff_utc = session_date 10:00:00 UTC
force_exit_utc = session_date 12:00:00 UTC
```

Vérifier au chargement : `range_start < range_end <= entry_start < entry_cutoff < force_exit`. Une relation invalide produit `SESSION_CONFIG_INVALID`, sans entrée.

L'heure 12:00 UTC est une sortie temporelle choisie dans la source. **Elle ne représente pas la fin du chevauchement Londres–New York.** Cette correction factuelle ne remplace pas la sortie par une autre heure prétendument plus rentable.

Les jours admissibles sont lundi à vendredi UTC, uniquement si le courtier cote effectivement le symbole. Pas d'exclusion arbitraire de lundi ou vendredi, ni de sélection mardi–jeudi issue de tableaux non sourcés.

Exemples de conversion à tester :

| Session | 08:00 Londres en UTC | Première bougie de décision de cette fenêtre | Heure à Douala du début de fenêtre |
|---|---:|---|---:|
| 2026-01-15 | 08:00 | 08:00–08:15 UTC | 09:00 |
| 2026-07-15 | 07:00 | 07:00–07:15 UTC | 08:00 |
| 2026-11-03 | 08:00 | 08:00–08:15 UTC | 09:00 |

La fenêtre d'entrée porte sur la totalité de la bougie de décision : `bar.open >= entry_start_utc` ET `bar.close < entry_cutoff_utc`. Ainsi la clôture de 10:00 est exclue, et une bougie commencée avant l'ouverture de Londres ne déclenche pas à l'ouverture. L'ordre lui-même DOIT être envoyé avant 10:00 UTC, même si son TTL de cinq secondes finirait plus tard. Les confirmations d'exécution tardives restent traitées normalement.

## S03 — Construction et gel du range

Pour une session complète, attendre les **16 bougies Bid M15** dont les ouvertures vont de 02:00 à 05:45 UTC. Après clôture de la dernière à 06:00, calculer :

```text
range_high = max(H_t pour bar.open >= 02:00 et bar.close <= 06:00)
range_low = min(L_t pour les mêmes 16 bougies)
W = range_high - range_low
```

Le range est ensuite figé pour toute la session. Les bougies 06:00–06:15 et suivantes NE l'élargissent PAS. Ne pas reconstituer un range plus favorable après une cassure ou une perte.

Refuser la session entière si : une bougie attendue manque, les horodatages sont dupliqués ou contradictoires, OHLC invalide, aucun profil de largeur maximale n'est défini, `W <= 0` ou `W > max_range_width_price`. Une largeur exactement au maximum est admise. Une fermeture courtier pendant cette fenêtre implique absence de range complet et donc absence de transaction ce jour-là ; ne pas raccourcir le range pour compenser.

Pour EURUSD et GBPUSD : `max_range_width_price=0.0060` équivaut à 60 pips avec un pip de 0,0001. Ce seuil reprend le document ; sa capacité à sélectionner de meilleures transactions n'a pas été démontrée.

Pour XAUUSD : `max_range_width_price` est une **entrée obligatoire de profil**, en USD/once, sans valeur universelle proposée. Le robot et ses tests DOIVENT prendre en charge ce champ, mais le profil d'or reste `PROFILE_INCOMPLETE` tant qu'il n'est pas renseigné. Ne pas convertir arbitrairement « 60 pips Forex » en un seuil d'or. Fournir ce paramètre de déploiement ne nécessite pas de modifier le code de stratégie ; il reste une hypothèse à évaluer, pas une optimisation certifiée.

## S04 — Déclencheurs de clôture et bougies faibles

Calculer, sur la bougie de décision clôturée `t` :

```text
range_t = H_t - L_t
body_t = abs(C_t - O_t)
upper_wick_t = H_t - max(O_t,C_t)
lower_wick_t = min(O_t,C_t) - L_t

weak_long(t) := body_t < 0.30*range_t ET upper_wick_t > 0.50*range_t
weak_short(t):= body_t < 0.30*range_t ET lower_wick_t > 0.50*range_t
```

Si `range_t <= 0`, la bougie ne déclenche pas. Si les OHLC sont incohérents, appliquer C02, sans signal. Les seuils 30 % et 50 % sont des définitions opératoires du texte « corps étroit et longue mèche de rejet » ; ils ne sont pas les résultats d'une optimisation.

Le signal est :

```text
signal_long(t) := range_session_valide
                  ET session_non_consommee
                  ET bar.open >= entry_start_utc
                  ET bar.close < entry_cutoff_utc
                  ET range_t > 0
                  ET C_t > range_high
                  ET NON weak_long(t)

signal_short(t):= mêmes conditions communes
                  ET C_t < range_low
                  ET NON weak_short(t)
```

Une mèche seule au-delà du range ne suffit jamais. `C_t == range_high` et `C_t == range_low` ne sont pas des cassures. Les deux signaux ne peuvent pas être vrais simultanément pour un range de largeur positive.

La couleur de la bougie n'est pas un filtre supplémentaire : une clôture au-delà de la borne suffit si elle n'est pas faible au sens ci-dessus. Le Close précédent n'est pas obligé d'être à l'intérieur du range. Si une clôture précédente a été refusée, une nouvelle clôture admissible dans la fenêtre peut produire un signal, tant qu'aucune entrée n'est encore en vol et que la session n'est pas consommée.

La version n'attend ni retour au niveau, ni test d'une moyenne. Si le marché a déjà quitté le range avant Londres, une bougie admissible après le début de fenêtre peut toujours déclencher ; le contrôle de TP valide de S06 empêche seulement de viser un objectif déjà dépassé. Ne pas inventer un filtre supplémentaire de distance à la borne.

## S05 — Machine à états et consommation journalière

États : `WAIT_RANGE`, `BUILDING_RANGE`, `RANGE_INVALID`, `WAIT_ENTRY_WINDOW`, `READY`, `SIGNAL_PENDING`, `ENTRY_IN_FLIGHT`, `POSITION_OPEN`, `SESSION_DONE`, `EXIT_REQUIRED`. Les états de panne C s'appliquent également.

```text
Avant 02:00 : WAIT_RANGE.
02:00 à 06:00 : BUILDING_RANGE, aucune entrée.
À 06:00 : valider les 16 bougies et figer les bornes.
    range invalide -> RANGE_INVALID jusqu'à la session suivante.
    range valide -> WAIT_ENTRY_WINDOW jusqu'à entry_start_utc.
À entry_start_utc : READY si range valide et session non consommée.
Sur une clôture admissible : créer au plus une intention avec TTL C06 ; SIGNAL_PENDING.
Après envoi : ENTRY_IN_FLIGHT ; ne pas traiter un nouveau signal.
Au premier remplissage, même partiel : session_consumed=true ; POSITION_OPEN.
Après toute fermeture de ce volume : SESSION_DONE, pas de deuxième entrée ce jour.
À 10:00 : plus aucun nouvel envoi ; expirer les intentions non envoyées.
À 12:00 : demander fermeture de toute exposition de la session ; SESSION_DONE après confirmation.
```

Une intention refusée avant envoi, expirée sans envoi ou rejetée avec preuve d'absence de deal ne consomme pas l'unique entrée de la session. Son signal est néanmoins consommé ; seul un signal d'une clôture ultérieure peut être envisagé. Un résultat inconnu bloque la session en réconciliation, sans présumer absence de remplissage.

Une entrée exécutée puis fermée au stop, à l'objectif, sur annonce, à 12:00 ou en urgence consomme dans tous les cas l'entrée journalière. Il n'y a pas de retournement automatique dans l'autre sens après un stop.

Au changement de date UTC, ne pas libérer artificiellement une session ayant encore un ordre inconnu ou une exposition. Réconcilier et fermer l'exposition en retard avant de préparer une nouvelle entrée. Le range de la nouvelle date peut être calculé à titre informatif, mais aucune nouvelle entrée n'est autorisée tant que l'ancien risque subsiste.

Au démarrage en cours de journée, reconstruire le range depuis les 16 bougies historiques de la session sans déclencher sur les clôtures déjà passées. Avant de déclarer la session non consommée, réconcilier le stockage avec les deals et ordres identifiés par ce `strategy_id` pour cette date, y compris ceux d'un précédent hash de configuration. Un changement de configuration ne remet pas le quota journalier à zéro. Si l'historique nécessaire ne peut pas être obtenu et si l'état persistant n'est pas fiable, rester RECONCILE_REQUIRED pour cette session.

## S06 — Stop, objectif et vérification au prix d'exécution

Sur le signal de clôture :

```text
Achat : SL = range_low
        TP = ceil((range_high + 1.5*W) / tick_size) * tick_size

Vente : SL = range_high
        TP = floor((range_low - 1.5*W) / tick_size) * tick_size
```

Les bornes du range proviennent de ticks valides ; elles sont sur la grille de prix. Si ce n'est pas le cas, rejeter les données plutôt que modifier les bornes. Le TP est arrondi vers l'extérieur pour ne pas réduire la projection demandée. L'objectif est projeté **depuis la borne cassée**, pas depuis le prix d'entrée.

Avant envoi, achat seulement si `SL < ask < TP` ; vente seulement si `TP < bid < SL`, puis contrôles de distances courtier, risque et marge. Le prix attendu défavorable utilisé pour le volume ne doit pas traverser l'objectif : si `E_worst >= TP` à l'achat ou `E_worst <= TP` à la vente, refuser cette intention comme `TARGET_ALREADY_REACHED`. Le ratio de distance net ou brut n'est pas forcé à 2R.

Après remplissage, les SL/TP du range restent **fixes**, même si le prix réel diffère. Ne pas recalculer le TP à deux fois le risque, ce qui changerait de stratégie. Si le prix effectif est déjà au-delà de l'objectif ou du stop prescrit, fermer le volume propre en anomalie d'exécution et journaliser ; ne pas déplacer l'objectif pour maintenir la position.

La fermeture à 12:00 UTC est indépendante de l'atteinte du TP. Une position ne peut pas être conservée pour « lui laisser une chance » après cette heure. C04 peut imposer une sortie plus tôt sur annonce ou fermeture de marché.

**1,5 largeur de range ne signifie pas un gain de 1,5R.** Plus le prix d'entrée s'éloigne de la borne cassée, plus le risque jusqu'à la borne opposée augmente et plus la distance restante jusqu'à l'objectif diminue. Cette conséquence doit apparaître dans les rapports ; ne pas la masquer par un ratio annoncé constant.

## S07 — Pseudocode normatif

```text
on_timer_or_quote(now):
    reconcile_broker_events()
    apply_C04_and_noon_exit_if_required(now)
    if now >= entry_cutoff_utc: expire_unsent_intents()
    if entry_intent_exists and now < min(intent.deadline, entry_cutoff_utc):
        if not context_gates_open(now): expire_intent(); return
        if quote_is_stale_or_spread_too_wide: wait_only_until_original_deadline(); return
        if quote_and_gates_are_valid:
            validate_fixed_range_stop_and_target_against_executable_quote()
            calculate_volume_and_atomically_reserve_risk()
            submit_once_with_attached_protection()
    else if entry_intent_exists and now >= intent.deadline:
        expire_intent()

on_closed_bar(t):
    process_once_by_bar_close_and_session(t)
    if bar_belongs_to_range: accumulate_range_bar(t)
    if range_end_reached: freeze_or_invalidate_range_exactly_once()
    if not eligible_decision_bar(t): return
    if session_consumed or signal_pending or entry_in_flight or owned_position: return
    if not context_gates_open(t.close): journal_rejection(); return
    if signal_long(t): create_long_intent(t, min(t.close+5s, entry_cutoff_utc))
    else if signal_short(t): create_short_intent(t, min(t.close+5s, entry_cutoff_utc))

on_actual_entry_fill(fill):
    session_consumed = true
    verify_fixed_SL_TP_and_postfill_risk()
    persist_session_and_position()
```

À une échéance exacte, l'expiration/sortie obligatoire prévaut sur une entrée. Les transactions réellement exécutées restent reconnues même si leur notification arrive après l'échéance ; leur volume est géré et fermé conformément aux obligations en cours.

## S08 — Exemples synthétiques de bout en bout

### S08.1 Achat EURUSD

Supposer les 16 bougies de range complètes :

```text
range_high = 1,1000 ; range_low = 1,0980
W = 0,0020 = 20 pips ; maximum = 60 pips => range valide
clôture admissible après début de fenêtre : 1,1004, bougie non faible
cotation d'entrée : Bid 1,10040 ; Ask 1,10042
SL = 1,09800
TP = 1,10000 + 1,5*0,00200 = 1,10300
distance de risque = 0,00242 = 24,2 pips
distance de gain = 0,00258 = 25,8 pips
ratio brut de distances = 25,8 / 24,2 = environ 1,066
```

Il ne faut pas annoncer 1,5R ou 2R pour cette transaction. Les frais sont encore à soustraire et le volume dépend du risque estimé C05. Si ni SL ni TP ne sont atteints, fermer à 12:00 UTC au premier prix réellement négociable de sortie.

### S08.2 Vente EURUSD

Avec le même range, clôture admissible sous 1,0980 et cotation Bid 1,09758 ; Ask 1,09760 :

```text
entrée vente = 1,09758 ; SL = 1,10000
TP = 1,09800 - 1,5*0,00200 = 1,09500
distance risque = 24,2 pips ; gain brut visé = 25,8 pips
sortie au stop déclenchée par Ask >= 1,10000
sortie objectif déclenchée par Ask <= 1,09500
```

### S08.3 Or, profil de test uniquement

Un **profil synthétique explicitement renseigné** peut avoir `max_range_width_price=30 USD/once`. Avec range haut 4 000,00 et bas 3 990,00, largeur 10,00, achat effectif 4 002,00 : SL 3 990,00, TP 4 015,00, risque de prix 12,00 et gain visé 13,00 USD/once. La valeur 30 du profil est une fixture, **pas une recommandation ou un seuil validé pour XAUUSD**. Sans un profil explicite, le robot n'envoie pas d'entrée sur l'or.

## S09 — Cas spécifiques d'acceptation

| ID | Situation | Résultat exigé |
|---|---|---|
| S-T01 | Range 02:00–06:00 complet | Exactement 16 bougies incluses ; aucune bougie 06:00 incluse |
| S-T02 | Une des 16 bougies manque | RANGE_INVALID pour toute la session |
| S-T03 | Largeur EURUSD exactement 0,0060 puis 0,00601 | Première valide ; seconde invalide |
| S-T04 | Range plat W=0 | RANGE_INVALID |
| S-T05 | Mèche au-dessus range_high mais Close à l'intérieur | Pas de signal long |
| S-T06 | Close exactement sur range_high ou range_low | Pas de cassure |
| S-T07 | Bonne clôture à 08:00 hiver dont bougie ouverte à 07:45 | Exclue : bougie commencée avant fenêtre |
| S-T08 | Clôture à 08:15 hiver d'une bougie ouverte à 08:00 | Admissible sur le critère horaire |
| S-T09 | Clôture à 10:00 UTC | Exclue et pas d'entrée |
| S-T10 | TTL encore ouvert mais heure courante 10:00 UTC | Expiration ; aucun nouvel envoi |
| S-T11 | Bougie haussière faible : corps 20 %, mèche haute 60 % | Refus de cette clôture longue |
| S-T12 | Corps exactement 30 % ou mèche opposée exactement 50 % | Pas faible par les seuils stricts de S04 ; autres contrôles nécessaires |
| S-T13 | Close précédent déjà au-dessus de la borne, nouveau Close admissible et pas de fill | Nouveau signal possible ; pas d'exigence de croisement frais |
| S-T14 | Signal refusé sans aucun fill | Nouvelle clôture ultérieure possible ; pas de renvoi du même signal |
| S-T15 | Fill partiel puis annulation du reliquat | Session consommée et volume reçu géré |
| S-T16 | Achat stoppé puis cassure baissière le même jour | Pas de deuxième entrée |
| S-T17 | Signal valide avec quote Ask au-delà du TP fixe | TARGET_ALREADY_REACHED, aucune entrée |
| S-T18 | Position toujours ouverte à 12:00 UTC | Fermeture demandée sans attendre clôture M15 supplémentaire |
| S-T19 | Redémarrage après une entrée déjà exécutée et fermée | SESSION_DONE restauré ; pas de nouvelle entrée ce jour |
| S-T20 | Profil XAUUSD sans largeur maximale de range | PROFILE_INCOMPLETE pour l'or, Forex non bloqué si ses profils sont complets |
| S-T21 | 2026-01-15 / 2026-07-15 / 2026-11-03 | Débuts de fenêtre UTC 08:00 / 07:00 / 08:00 |
| S-T22 | Exemples S08.1 et S08.2 | TP fixes 1,10300 / 1,09500 ; risques 24,2 pips et gains 25,8 pips |
| S-T23 | Entrée après glissement à un prix différent | SL/TP restent ancrés au range, pas de recalcul à 2R |
| S-T24 | Range cassé avant Londres, puis clôture admissible dans la fenêtre | Signal possible si toutes les conditions, dont cible non dépassée, sont satisfaites |
| S-T25 | Le lendemain arrive avec une transaction inconnue du jour précédent | Réconciliation avant toute nouvelle entrée |

## S10 — Limites explicitement conservées

- Aucune preuve de rentabilité du créneau 02:00–06:00, du seuil 60 pips, de l'objectif 1,5 largeur ou de la sortie à 12:00 dans les conditions de l'utilisateur.
- L'attente d'une clôture peut retarder l'entrée et dégrader le rapport gain/risque de prix ; aucun filtre supplémentaire de ratio n'est inventé pour cacher ce problème.
- Un breakout peut échouer et le stop peut subir un glissement. Un range valide n'est pas une garantie de mouvement directionnel.
- La largeur maximale d'or doit être fournie et validée séparément ; un bon résultat Forex ne la détermine pas.
- Les heures UTC du range et la fenêtre liée à Londres sont volontairement distinctes et inscrites dans le manifeste ; ne pas décaler le range en même temps que l'ouverture de Londres.
'''

REFERENCES = r'''
## R01 — Références et portée

Le document local fourni par l'utilisateur est la source de la famille de règles et des branches choisies. Il est un matériau analysé, pas une preuve de performance. Les conventions ajoutées sont identifiées dans ce cahier des charges.

- [MQL5 — OrderCalcProfit](https://www.mql5.com/en/docs/trading/ordercalcprofit) : calcul du profit dans la devise du compte. Référence technique, sans conclusion de rentabilité.
- [MQL5 — Propriétés des symboles](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants) : grille de prix/volume, contraintes et caractéristiques courtier.
- [MQL5 — OrderSend](https://www.mql5.com/en/docs/trading/ordersend) : distinguer envoi accepté et transaction effectivement exécutée.
- [MQL5 — Tests de stratégies](https://www.mql5.com/en/docs/runtime/testing) : infrastructure de simulation ; ne valide pas économiquement cette spécification.
- [Neely et Weller — Intraday Technical Trading in the Foreign Exchange Market](https://fraser.stlouisfed.org/docs/publications/frbsl_wp/1999-016.pdf) : exemple de recherche où les coûts modifient les conclusions sur les règles étudiées ; ne constitue pas un test de ce robot.
- [Bailey et collaborateurs — The Probability of Backtest Overfitting](https://escholarship.org/uc/item/4w1110bb) : risque de sélection de configurations surajustées.
- [GOV.UK — Changements d'heure britanniques](https://www.gov.uk/when-do-the-clocks-change) : repères de fuseau ; ne démontre aucun avantage de séance.

Références techniques consultées le 3 novembre 2026. Les équations et priorités explicites de cette spécification gouvernent la conformité ; une différence d'initialisation d'un indicateur natif doit être résolue par l'implémentation du calcul de référence, pas masquée.

## R02 — Triple contrôle de livraison documentaire

Cette section sera complétée après les contrôles effectivement exécutés. Elle distingue la qualité du cahier des charges de la conformité d'un futur robot et de sa performance économique.
'''


def build(filename: str, title: str, config: dict, body: str) -> None:
    merged = {**COMMON_CONFIG, **config}
    header = f'''# {title}

Version normative : **1.0.0** — Date : **3 novembre 2026**.

Destinataire : agent IA chargé d'une implémentation intégrale et vérifiable.

Statut : **spécification déterministe ; rentabilité non validée**.

Source locale analysée : `C:/Users/Lenovo/Downloads/Modèles strategies ForexM15.md`.

SHA-256 du fichier source lu : `{SOURCE_SHA256}`.

Ce fichier est autonome. Les sections C forment le contrat technique, S la stratégie, P la configuration et R les références/contrôles. Aucune fusion des deux stratégies n'est autorisée dans cette version.

'''
    configuration = '\n## P01 — Configuration de référence sérialisable\n\n'
    configuration += ('Les champs non nuls fixent le comportement de cette version. Les champs `null` des profils courtier doivent être renseignés pour activer le symbole ; le `null` de durée maximale EMA signifie explicitement absence de durée maximale. Aucun paramètre de profil ne doit être inventé par l’agent pour produire artificiellement des résultats. Les conventions `FORMALISATION` et `EXECUTION` restent distinctes d’une optimisation de performance.\n\n')
    configuration += '```json\n' + json.dumps(merged, ensure_ascii=False, indent=2) + '\n```\n'
    text = header + textwrap.dedent(COMMON).strip() + '\n\n' + textwrap.dedent(body).strip() + '\n' + configuration + '\n' + textwrap.dedent(REFERENCES).strip() + '\n'
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / filename
    target.write_text(text, encoding='utf-8', newline='\n')
    print(json.dumps({'path': str(target), 'bytes': target.stat().st_size, 'lines': len(text.splitlines())}, ensure_ascii=False))


if __name__ == '__main__':
    build('01_Triple_EMA_RSI_Repli_M15_Specification_IA.md',
          'Triple EMA + RSI + repli M15 — Spécification intégrale pour implémentation IA',
          EMA_CONFIG, EMA)
    build('02_London_Breakout_M15_Specification_IA.md',
          'London Breakout M15 — Spécification intégrale pour implémentation IA',
          LONDON_CONFIG, LONDON)

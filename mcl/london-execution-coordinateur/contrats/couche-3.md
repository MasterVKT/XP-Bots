# Contrat de la couche 3 — dimensionnement

- **Statut** : finalisé le 06/11/2026 avant son implémentation.
- **Consommateurs cartographiés** : 4, 6.
- **Dépend de** : 0a, 0d, 1a, 1b, 1c, 2a.

Unité : dimensionnement
Responsabilité : Plus grand volume admissible, risque, budget gelé, fonds propres de référence, contrôle natif et proposition de réservation liée à sa version, ou refus C09.
Signature : `PlanDimensionnement` ; `dimensionner(signal, niveaux, profil, compte, registre, gardes, port, commun, deploiement, *, plan_initial=None, volume_rempli=None, prix_reel=None, frais_entree_reels=None)`
Entrée : Signal et niveaux réels ; profil C04 qualifié, instantané du compte, registre unique et gardes initialisées avec les mêmes paramètres communs explicitement fournis par la composition ; port externe ; plan initial et remplissage confirmé pour réduction.
Sortie : Plus grand volume admissible, risque, budget gelé, fonds propres de référence, contrôle natif et proposition de réservation liée à sa version, ou refus C09.
Effets de bord : état mémoire explicite seulement ; ni fichier, ni horloge, ni réseau. Les appels de calcul ne passent que par le port déclaré.
Erreurs, exceptions : ValueError propre à la couche pour entrée mal formée ; un refus métier est une valeur motivée C09.

Le budget B=risque par entrée×équité de l’instantané est gelé pendant toute la tentative. La grille est celle des multiples exacts du pas natif, sans epsilon de prix ; minimum incohérent avec le pas → environnement non prêt. Le balayage est descendant depuis le maximum natif, borné par la limite agrégée positive du profil et, après fill, par le volume réellement rempli. Il ne suppose ni frais proportionnels ni monotonie d’une fonction de frais vérifiée. Il n’augmente jamais un volume pour atteindre le minimum.

Chaque candidat respecte simultanément le risque individuel, les réserves du compte, les places et l’unicité d’actif, la marge totale après ordre et les bornes/droits natifs. Le contrôle natif total est autoritatif pour les positions réelles ; les marges des réserves non matérialisées s’y ajoutent. La marge isolée seule ne suffit jamais. La comparaison de marge est en Decimal à l’équité×fraction chargée (P-06), égalité admise, plus marge libre et stop-out du contrôle natif. Les modes internes normalisés FULL, BUY_ONLY et SELL_ONLY décrivent les droits d’entrée ; autre mode ou sens interdit → ENVIRONMENT_NOT_READY/mode_negociation. Ce sont des libellés du profil d’adaptation, pas des valeurs numériques MT5 recopiées.

Une position externe bloque toute entrée ; un arrêt global ou quotidien reste prioritaire. Une erreur de calcul n’est jamais remplacée par zéro. La dernière version du registre est recontrôlée après les calculs ; le plan ne réserve pas lui-même et ne peut être appliqué qu’avec son numéro de version par 1c. Le port de calcul, le profil et le compte sont fournis par le futur coordinateur après lecture C04, avant envoi ; cette couche pure ne prétend ni connecter ni qualifier un compte réel.

Après remplissage, le plan initial fournit le budget et l’équité de référence gelés : une équité nouvelle ne recalcule pas B. Le volume et la position possédée sont confirmés, le SL reste celui du plan initial, TP est recalculé au prix réel, seule la réserve de sortie subsiste et les coûts d’entrée réels restent comptés. La position/réserve de cette seule clé est remplacée pour les calculs ; toutes les autres restent incluses. Le plan rendu indique le volume à conserver ; aucun volume admissible signifie clôture de sécurité par la phase 6, et non une augmentation de risque. Cette couche n’envoie pas de réduction ni d’ordre et ne vérifie pas un TP sur une cotation future.

Si aucun volume ne respecte le budget de risque : MIN_VOLUME_OR_RISK_REJECT. Si des volumes respectent ce budget mais échouent sur les réserves ou la marge, conserver le refus correspondant à ces contraintes. Les droits de cotation, permissions et TTL sont les contrôles distincts du futur coordinateur et ne sont jamais levés par un plan financier.

## Spécification exécutable

### Extension additive du 07/11/2026, phase 6

`revalider_avant_envoi(plan, signal, profil, compte, registre, gardes, port, commun)` réutilise le même calcul C07 sur le seul volume préparé, après confirmation de persistance et juste avant transmission. La réservation initiale non remplie doit encore correspondre exactement ; seule cette réservation est exclue d'un registre local pour éviter un double comptage. Les autres positions, réserves et verrous restent présents. Budget et équité de référence restent gelés ; les spécifications, frais et contrôles natifs sont courants. Aucun volume de remplacement n'est proposé, aucun budget ou risque réservé n'augmente, aucun état du registre réel ne change. Risque nouveau supérieur à la réserve initiale → environnement non prêt ; dépassement du budget ou contrainte native → refus C09 existant. La version réelle est recontrôlée après tous les appels externes. Le coordinateur consomme un refus sans retransmettre. Le comportement de `dimensionner` est conservé.

`test_cat1_c3_dimensionnement.py` : C11.6/C11.7, L-01, cinq contraintes, P-06, frais non linéaires et réduction ; `test_cat2_c3_dimensionnement.py` : arbitrage réel et réservation atomique entre les deux méthodes, compte partagé.

## Comportements documentés (loi de Hyrum)

Les valeurs exposées sont immuables. Les messages d'exception ne sont pas contractuels. Les détails de refus sont ceux du noyau, sans nouveau motif métier. Les seuils viennent des paramètres chargés. Les calculs décimaux n'altèrent jamais le contexte global.

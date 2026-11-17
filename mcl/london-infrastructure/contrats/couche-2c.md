# Couche 2c — les sept calculs courtier natifs

Finalisé avant code. Session/type/noyau/exécution gelés. Aucun import de 2a,
2b ou 2d ; l'enveloppe 3 injecte les callbacks de valeurs publiques.

`CalculsMT5(session,commun,liaisons,instant_ms,*,profil,qualification_compte,
proprietaire,flux_externe,assiette_stop_out)` implémente exactement les sept
méthodes de CalculCourtier. `actualiser_instant(t)` fixe l'instant explicite,
sans horloge. `profil(symbole,t)` et `qualification_compte(t)` rendent les
vrais profils qualifiés courants ou refus. `proprietaire(ticket)` rend une
PositionCompte appartenant à une intention connue et rapprochée, ou None.
`flux_externe(t,solde)` reçoit le Decimal du solde réellement lu et rend un
booléen prouvé par l'historique complet de compte ; une variation de ce solde
encore inexpliquée reste bloquante, sans enrichir la garde comme un bénéfice.
None ou donnée inconnue refuse. La base de stop-out MONEY est explicitement
qualifiée EQUITY ou FREE_MARGIN ; aucune déduction implicite.

Précision avant premier gel, le 13/11/2026 : le solde est transmis au callback
pour détecter un flux apparu entre deux rapprochements. Cette valeur provient
du même account_info que l'équité et la marge ; aucun second relevé de solde
n'est substitué. P11-08 : la neutralisation appartient au vrai moteur 1b, via
la BaseReconstituee qualifiée, et non à l'adaptateur de calcul.

profit appelle order_calc_profit (BUY/SELL natif, symbole exact, volume/prix),
marge appelle order_calc_margin. Leurs réponses sont des Decimal finis ;
None/exceptions passent par SessionMT5, valeurs négatives de marge refusées.
frais_aller_retour et frais_sortie utilisent les frais qualifiés USD du profil,
avec minimum par ordre et calcul Decimal sous contexte explicite. Zéro est
admis seulement si confirmé. Aucune estimation de swap ou de spread ajoutée.

etat_compte lit account_info et toutes les positions natives. Equity/balance/
margin viennent du même relevé ; aucun numéro de compte n'est conservé. Le
profil courant doit correspondre aux métadonnées natives. Les tickets connus
reçoivent leur vraie clé et risque initial du registre de propriété, jamais
une attribution par symbole/magic seuls. Les autres positions restent externes
(clé et risque None), y compris hors univers, et bloquent les admissions par
le vrai C07. Champ manquant ou relevé partiel = exception d'environnement,
normalisée ENVIRONMENT_NOT_READY par appeler_calcul.

controler projette seulement les champs connus d'OrdreCalcule : DEAL protégé,
sens, prix, volume, SL/TP, filling qualifié (FOK puis IOC puis RETURN), GTC.
Pas de deviation/magic/comment inventés ; 2d effectuera le dernier order_check
sur la requête complète exacte juste avant order_send. Retour ControleNatif
avec résultat de order_check, marge totale, fonds libres et garde de stop-out.
Le code est symbolique ou un entier natif encodé, jamais le commentaire libre.
Le contrat actuel C3 classe un contrôle préliminaire refusé en MARGIN_REJECT,
CONTROLE_NATIF ; le code natif exact reste au journal de calculs. Le classement
complet du dernier order_check/order_send appartient à 2d puis au cycle C08.

En remplacement, rechercher la position réellement possédée de la clé, vérifier
volume et SL fixe natif, puis order_check SLTP de son ticket. Conserver marge
et fonds libres du compte courant ; ne pas ajouter une nouvelle marge d'entrée
ni utiliser les zéros éventuellement rendus pour une simple modification.
Stop-out PERCENT : equity / margin × 100 strictement au-dessus du seuil natif ;
marge nulle connue distinguée d'un champ absent. MONEY : comparaison stricte
de l'assiette qualifiée. Aucune valeur métier figée recopiée dans le code.

Tests 1 : appels natifs exacts, zéro/inconnu, frais USD, toutes positions,
codes et champs, stop-out dans les deux modes et remplacement sans double
marge. Tests 2 : vrai dimensionnement/coordinateur sur les profils produits
par 2a ; grille, volume minimal trop risqué, marge/positions externes, frais.
Contrat poste 13.1 : comparer profits/marges et account_info natifs, sans
order_send ni passage en réel.

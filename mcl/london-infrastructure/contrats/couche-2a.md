# Couche 2a — qualification native et horaires D12

Finalisé avant code, le 10/11/2026. Parents 0a et 1 gelés. Ce module ne lit aucun
fichier et n'importe aucun SDK ; SessionMT5 et les octets reçus sont injectés.

`SpecificationsMT5(session, commun, table, qualification, liaisons, *,
seances_max_age_ms, fermetures_max_age_ms, max_jours_horaires,
ecart_horloges_max_ms, etat=None)` conserve des liaisons fixes et une preuve
externe explicite `xp-qualification-mt5-v1`. La qualification est un document
strict, daté (`known_at_utc_ms`, `valid_until_utc_ms`), identifié par
`decision_id`, avec `preuves`, `catalogue_complet`, `compte`, `symboles` et les
bornes `debut_horaires_ms`, `fin_horaires_ms`. Les réglages d'ingénierie sont
explicites ; ils ne changent aucun seuil de stratégie ni les valeurs C07.
P11-20 précise le champ obligatoire `convention_ticks`, établi par S01 : `UTC`
ou `SERVEUR_S01`. Le premier ne décale pas les epochs SDK ; le second utilise
la table qualifiée. Un champ absent, inconnu ou non textuel refuse la preuve.
`convention_ticks(t)` restitue ce choix validé sous les mêmes bornes de connaissance
et de validité que les autres preuves, sans l'inférer du décalage D12.

Le compte qualifié donne entite, serveur, type_compte, devise, levier,
mode_marge, mode_stop_out, empreinte_compte_sha256, assiette_stop_out (None en PERCENT ; EQUITY ou
FREE_MARGIN en MONEY), historique_complet, exclusivites_netting. L'état natif
doit concorder avec cette preuve. L'empreinte vaut SHA-256 de serveur + NUL +
numéro natif décimal et reste dans le registre privé ; elle détecte aussi un
changement vers un autre compte du même serveur. Le numéro natif n'est ni
conservé ni journalisé ; aucun identifiant réel n'entre dans le dépôt.
Chaque symbole du catalogue donne canonique, sous_jacent, trois champs de
commission, devise_frais, convention_swap, protections_a_l_entree,
convention_declenchement_verifiee, modes_remplissage, flags_natifs (filling_mode,
order_mode, trade_exemode, chart_mode), minuit_egal_fin_24h,
cout_aller_retour_usd_volume_min, longueur_commentaire_max,
historique_ticks_complet. Les noms exacts des quatre flags sont ceux du SDK.
Les coûts monétaires du document sont des textes décimaux finis positifs ou
nuls. La convention swap est une preuve, pas un calcul de frais inventé.

`compte(t)` et `instrument(canonique,t)` rendent les vrais ProfilCompte et
ProfilInstrument, construits par les fonctions publiques du noyau, ou un
RefusExecution ENVIRONMENT_NOT_READY. Relecture des champs natifs à chaque
appel ; None, champ absent, droits non compatibles, preuve future/périmée,
divergence serveur/compte/flags refusent. STANDARD est une preuve externe
distincte du mode DEMO/REAL natif. Les modes FOK/IOC/RETURN sont qualifiés,
MARKET+RETURN interdit ; chart_mode doit correspondre au Bid de C03.
Les protections doivent être disponibles dans order_mode et prouvées à
l'entrée. CLOSE_ONLY permet la lecture d'un profil défensif, jamais une entrée
admise par le vrai vérificateur C04 du coordinateur.

Le catalogue prouvé complet est interrogé pour vérifier le minimum de chaque
sous-jacent : exposition minimale native (taille_contrat*volume_min), puis
coût aller-retour USD documenté, puis nom lexical. Une liaison qui ne satisfait
plus cet ordre refuse sans basculer vers un autre symbole. Aucune heuristique
de suffixe, aucune valeur quantitative absente remplacée par zéro.

`recevoir_exports(t, *, seances, fermetures)` reçoit les octets courants pour
chaque symbole lié et les fermetures. JSON UTF8 strict sans doublons ni nombres
non finis ; champs exacts de D12. Jours 0..6 exactement, cotation/négociation
séparées, heures HH:MM:SS (fin 24:00:00 admise), intervalle passant minuit
admis ; 00→00 vaut 24h seulement avec preuve. Expansion sur les dates serveur
couvertes et conversion de CHAQUE borne par la table S01 ; intersection quote/
trade, ordre et absence de chevauchement, fermetures explicites, validité
limitée à la qualification. Aucun offset courant extrapolé, aucune ouverture
déduite d'une cotation. Les heures serveur et GMT d'export doivent concorder
dans l'écart mesuré explicite et ne pas venir du futur.

Version croissante par fichier ; même version/mêmes octets = doublon sans
renouvellement ; recul ou même version/autre contenu = refus. Une absence ou
une lecture invalide invalide l'usage courant du fichier, tout en conservant
la dernière version acceptée pour détecter les reculs. Fraîcheur fondée sur
première réception ET date native d'export/relevé. La méthode rend les nouvelles
réceptions acceptées (nom, version, octets, réception) ; la coquille archive
toutes ces versions dans son journal durable.

`convertir_serveur(texte)` est un callback pur pour C05. `preuve(symbole,t)` rend
une copie validée de la qualification du symbole et `preuve_compte(t)` celle du
compte, pour les calculs et l'enveloppe physique. `exporter_etat()` conserve
la dernière réception/version de chaque fichier, ses octets, ses erreurs et
l'empreinte de configuration. La reprise valide et relit ces octets à leur
heure initiale ; elle n'acquiert aucune fraîcheur.

Tests catégorie 1 : SDK externe doublé seulement, vrais noyau/session ; champs
inconnus/manquants, zéro versus inconnu, flags et coûts, sélection minimale,
horaires/fermetures, versions, redémarrage, table ambiguë et invalidation.
Catégorie 2 : les profils produits alimentent le véritable dimensionnement et
le coordinateur, y compris une fermeture exceptionnelle nouvellement connue.
Test physique sous XPBOTS_CONTRATS_MT5=1 seulement : confronter le compte et
chaque profil lié au registre qualifié, sans ordre.

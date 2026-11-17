# Couche 2b — collecte native causale

Finalisé avant code. Parents réels 0a, 1 et noyau gelés ; aucun import latéral.
`FluxMT5(session,table,liaisons,departs_utc_ms,*,taille_lot,max_ticks_lot,
historique_complet,etat=None,convention_ticks='SERVEUR_S01')` : les départs, plafonds et preuves S08 sont
explicites par symbole ; aucune couverture déduite d'un Bid isolé.

`lire(t) -> LotFluxMT5(ticks,couvertures,erreurs,a_jour)` interroge COPY_TICKS_ALL
par dates datetime aware UTC. `convention_ticks` est le choix explicite qualifié
par S01 : UTC conserve les epochs du SDK documentés par copy_ticks_from/range ;
SERVEUR_S01 emploie la table qualifiée pour les recherches, retours et reprises.
Ce dernier défaut conserve les appelants déjà munis d'une table S01 de leur
source. La composition de production fournit toujours le choix C04 explicite.
Aucune convention n'est inférée de la table D12 ni des cotations reçues.
Le début demandé est arrondi à la seconde inférieure pour supporter
l'interface native ; les lignes antérieures au curseur sont ignorées après
validation de l'ordre, sans renouveler une cotation déjà reçue.

Curseur par symbole = dernière ms native + préfixe COMPLET des occurrences
à cette ms ; comparaison ordonnée (heure, Bid, Ask, flags), jamais set de
déduplication. Les occurrences identiques ont chacune un numéro de réception
global. Nouvelle requête incluant le préfixe ; réécriture, suppression ou
préfixe incomplet → trou, pas d'avancement. Si le lot est plein, différer toute
sa dernière milliseconde tant que sa fin n'est pas prouvée par une ligne à une
heure suivante ou par un lot non plein. Un préfixe trop volumineux augmente la
requête jusqu'au plafond explicite ; dépassement → trou, jamais perte silencieuse.
Un lot plein contenant des millisecondes complètes peut avancer sur celles-ci,
en laissant intégralement la dernière à la scrutation suivante. La couverture
s'arrête à cette frontière ; a_jour reste faux jusqu'au rattrapage complet.

Conversion et validation de tout le bloc avant mutation du curseur ; ordre
natif stable, prix finis positifs, flags entiers, fournisseur ≤ réception.
Un échec de lecture/connexion, None, champ absent, future quote, table non encore
connue ou historique S08 non prouvé ne crée aucun tick ni couverture. Une
conversion S01 absente ou ambiguë refuse en SERVEUR_S01 ; elle ne redécale
pas les ticks d'une source explicitement qualifiée UTC.
Les autres symboles peuvent progresser indépendamment ; l'ordre global de
réception suit l'ordre fixe des liaisons. Aucun tri correctif ni interpolation.

La couverture rendue est celle du préfixe historique effectivement lu et prouvé
complet par S08. Un rattrapage partiel ne couvre pas le futur de ce préfixe.
`a_jour` est par symbole ; la coquille bloque l'autorisation d'une nouvelle
entrée tant qu'un transport incomplet n'est pas rattrapé et livré au vrai C03.
Le vrai FluxBougies décide ensuite de la validité et du préchargement ; aucune
lecture de ses champs privés, aucune seconde construction de bougie.

`exporter_etat()` conserve empreinte de la configuration/table, numéro global,
dernière réception et curseurs complets/couverture. Reprise stricte, causalité
et grille des champs, sans relancer une commande ni renouveler les réceptions.
L'empreinte engage la convention choisie afin de refuser un ancien état calculé
sous l'hypothèse erronée de conversion serveur (correction P11-20).
Catégorie 1 : tableaux NumPy du faux SDK, doublons dans la même ms, lots pleins,
préfixes réécrits, silence, coupure/reconnexion/rattrapage, dates UTC et erreurs.
Catégorie 2 : vrais ticks produits injectés dans FluxBougies et MoteurDecision ;
frontière M15/H1, numéros stables, aucune entrée rétroactive.
Contrat physique sous XPBOTS_CONTRATS_MT5=1 : lecture seule d'un intervalle récent
qualifié, comparaison des occurrences natives et des valeurs normalisées.

# Couche 4 — ressources et cycle de vie physiques

Contrat finalisé avant code le 14/11/2026. Dépendances réelles : feuilles
0a à 0h, session 1 et courtier 3, paramètres communs du noyau. Frontières :
fichiers et import lazy du SDK officiel. Aucun accès réseau explicite, API
LLM, secret ou .env. La carte doit déclarer verrou et noyau avant installation.

InfrastructurePhysique(commun,meta,liaisons,*,racine,max_octets_echange,
snapshot_max_octets,sdk=None,chemin_terminal=None,common_files_attendu=None)
possède HorlogeSysteme, SessionMT5, VerrouProcessus, DepotSQLite,
JournalFichiers, SourcesControles et LecteurSnapshot réels. Le SDK injecté
est le faux externe des tests ; en son absence seulement, import_module du
paquet MetaTrader5 épinglé. L'import du module d'assemblage est inerte.
La session s'attache sans identifiants selon D02 et vérifie son mode natif.

meta contient exactement deploiement, mode, empreintes et commit ; les
empreintes technique/ia et le commit sont des hexadécimaux de format attendu.
Le nom de déploiement passe par le vrai JournalFichiers avant de servir à
un chemin. Le dépôt est racine/runtime/<deploiement>/etat.sqlite et le
journal racine/logs/<deploiement>. L'identité SQLite ajoute l'empreinte du
compte effectivement attaché, sans conserver login. Une identité étrangère
refuse la reprise, sans réinitialiser le livre.

Le verrou FILE_COMMON/XPBots/execution/v1/coordinateur.lock est pris avant
l'ouverture de SQLite et la réparation JSONL. Il exclut tout second
coordinateur XP-Bots dans le même dossier commun, même avec un autre
déploiement. Il ne limite pas les deux bras logiques PAPER_AB dans l'instance.
Le périmètre commun est une décision d'ingénierie : pas de supervision de
plusieurs terminaux simultanés pendant cette phase.

Pour DEMO et REEL, un lien durable proprietaire_<empreinte_compte>.json
conserve schéma, compte hashé, déploiement et empreinte du chemin d'état
canonique. Une autre identité ou une base disparue refuse, avant création
d'un état vide ; changer de dossier ou de déploiement n'efface pas les
inconnus et les arrêts du compte. Le lien existant n'est jamais réécrit
automatiquement. Une migration exige un état rapproché et une décision
tracée de mise en service ; elle reste une opération humaine de phase 13.
Les livres PAPER/PAPER_AB sont fictifs et ne revendiquent pas cette propriété
financière du compte natif. Tous les modes gardent le verrou de processus.

La construction ouvre le dépôt, puis reconstruit les JSONL par
journal.publier(depot.evenements()). La coquille peut ensuite charger et
décoder son checkpoint réel. initialiser_courtier(table,qualification,
parametres,*,etat=None) construit une seule instance de CourtierMT5 avec
ces états publics. parametres contient ses dix réglages et départs nommés,
aucune règle métier recopiée. Une seconde initialisation refuse. L'empreinte
du compte du courtier doit être celle de l'assemblage et de la qualification.
La propriété courtier refuse tant que cette étape n'a pas réussi.

Les propriétés horloge, session, depot et journal exposent les objets réels.
lire_controles() ferme les fichiers, date après le retour de SourcesControles
et rend les ReceptionFichier avec cette heure de connaissance. lire_snapshot()
rend octets/None, heure après lecture et code, sur le chemin A10 exact
XPBots/ai/v1/context_latest.json. Aucun renouvellement de séquence ni parsing
C05/IA ici. lecture_ticks(chemin) rend le lecteur réel 0f, sans matérialiser
une seconde série ; seules les entrées de ticks gzip prévues sont acceptées.

Les aides lire_configuration et ecrire_fichier réutilisent les lecteurs et
écritures atomiques 0d. Elles refusent un .env réel, y compris derrière un
lien, et ne remplacent un fichier existant que sur demande explicite du
consommateur. Ces fonctions n'importent pas le SDK. Les erreurs opérationnelles
utilisent des codes statiques, jamais le commentaire libre du courtier.

fermer(attente_ms) est idempotente. Elle joint d'abord les tâches par la vraie
API 3. Si une tâche native reste active, rend False et garde session, base
et verrou possédés ; aucune libération prématurée de la propriété. Après leur
arrêt effectif, ferme les ressources et libère le verrou même en cas d'erreur
de fermeture. Les erreurs de construction nettoient les ressources acquises.
Aucun ordre n'est envoyé par construction, lecture, réparation ou fermeture.

L'artefact inclut aussi les sources d'export MQL5 et leurs fixtures D12.
Leurs empreintes font partie du gel 4. Les tests statiques et les vrais
lecteurs C05/2a vérifient les formats ; compilation et confrontation native
restent des contrats physiques explicites de 13.1, désactivés par défaut.
Le TSV fournit la table S01 et une couverture calendrier incluant les durées
CF forward + max_age et la cadence d'export ; ne jamais modifier C05 pour
rendre valide un export insuffisant.

Catégorie 1 : import inerte, assemblage sans émission, lectures causales,
chemins/tailles, identités persistantes, exclusion et nettoyage, sources MQL5,
formats D12 et versions de dépendances. Catégorie 2 : vrai courtier, C05,
SQLite/JSONL restaurés, snapshot et ticks, défense pendant stockage dégradé,
arrêt borné qui garde la propriété native. Faux SDK seul, vrais fichiers et
verrous ; contrat du poste ignoré sans activation 13.1 explicite.


## Extension — archives et gel du code avant les commandes

`lire_fichier(chemin,max_octets,*,racine=None)` lit les octets physiques par
le vrai lecteur borné 0d, après la même résolution et garde .env. Avec racine,
le chemin résolu doit rester sous cette racine existante. Les erreurs restent
statiques. Aucun SDK, décodage ni écriture ; une empreinte porte sur les octets
effectivement lus, sans réencodage JSON.

`empreinte_robot(racine,max_octets)` recalcule l'inventaire des sources Python
src/xpbots, des sources MQL5 et des ressources JSON config/schemas/prompts.
Les cinq dossiers doivent être présents et non vides. Les liens de source
non qualifiés et chemins résolus hors racine sont refusés, ainsi que les .env.
Le plafond borne la somme des octets lus. Le résultat xp-empreinte-robot-v1
contient la liste triée (nom relatif, SHA des octets), l'empreinte liée à ces
noms et contenus, et la taille totale. Ni Git, ni prix, ni journaux, ni données
privées ne sont lus. L'inventaire ne vient pas d'un manifeste fourni : ajouter,
retirer ou modifier une source change le gel. Ce mécanisme est la preuve de
contenu du code pour la garde C10, pas une autorisation d'ordre.

Tests : octets exacts, bornes, .env et traversée refusés avant lecture ; vrai
writer 4 et lecteur 0d ; empreinte stable et modifications/ajouts/suppressions
détectés. Les API précédentes et les contrats du poste 13.1 sont conservés.

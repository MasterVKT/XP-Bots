# Couche 2 — boucle directe et propriétaire du cycle physique

La boucle reçoit ConfigurationApplication, InfrastructurePhysique réelle,
TableHeureServeur qualifiée et qualification C04. Elle compose 1a, 1b et 1f,
sans remplacer leurs décisions. SDK et horloge sont les seules frontières
doublées dans les tests ; SQLite et fichiers temporaires sont réels.

API : `BoucleDirect(application,infrastructure,table,qualification)` possède
le moteur, les livres et SessionDurable ; les ressources physiques restent
possédées par l'enveloppe. `iterer()` exécute un passage et rend ses seules
sorties réelles (sans historique cumulatif). `attendre()` utilise la vraie
horloge monotone et la prochaine échéance. `executer(jusqua_ms=None,
max_iterations=None)` répète ce même chemin et permet une fin opérationnelle
bornée. `archive_incident()` exporte seulement l'état COMMITé et les décisions
SQLite correspondantes, par le codec, pour la commande de rapport 1e.
Les propriétés moteur, livres et session exposent leurs objets publics réels.

## Démarrage

La persistance est ouverte et réparée par 4. Son initialisation est conservée
dans le journal externe. Une reprise recharge l'initialisation et les journaux
par SessionDurable, reconstruit les livres PAPER une fois, vérifie le moteur
par rejouer_incident, puis utilise le checkpoint complet et les constructeurs
C08. Aucune attente de cotation n'est transmise rétroactivement. Les réponses
inconnues et arrêts persistants demeurent actifs. Une incohérence n'ouvre pas
un nouveau compte. Les observations fraîches sont reçues après leur lecture,
jamais antidatées au checkpoint.

Une première session crée ses livres PAPER au début UTC du jour courant avec
le capital CF, sans utiliser le solde du compte natif. Le moteur démarre à
l'heure réelle ; les ticks de préchargement conservent l'heure fournisseur
et leur heure de réception du lot. Les horaires qualifiés couvrent l'historique,
mais la couverture initiale est vide. Toute entrée reste bloquée pendant le
rattrapage. L'initialisation des calculs du moteur est archivée avant ses entrées.

## Cycle D-09

Le propriétaire traite les réponses et observations, les fichiers C05, l'IA
et les minuteries à leurs heures réelles de réception. Les profils courants
proviennent de SpecificationsMT5 ; leur validité n'est jamais prolongée par
une lecture. Les observations natives ne remplacent pas le compte PAPER.
Les défenses issues d'un premier événement sans bougies partent avant le
traitement potentiellement long des ticks de rattrapage. La lecture du lot de
ticks est ensuite datée après I/O ; les faits MARCHE portent les horaires
courants et seulement la couverture connue. L'indicateur a_jour est consommé
par les gardes d'admission, sans supprimer les calculs défensifs.

La cadence de boucle est celle du registre (100 ms D-09), celle des contrôles,
du snapshot et de la minuterie vaut 1 s ; la plus proche échéance métier peut
réveiller plus tôt. Le temps monotone sert à attendre ; l'UTC réel date les
faits. Le retard ne crée pas d'événement antidaté ni d'entrée rétroactive.
Les cadences du service export restent celles de D-12, produites par 0.

Après chaque sortie, les commandes défensives sont soumises avant toute
persistance. Le vrai COMMIT des décisions et intentions fournit la preuve C08.
La confirmation est datée après la persistance, à l'heure réelle, de sorte
que TTL, cotation et C05 soient recontrôlés au dernier instant. Une entrée
native est préparée sans travailleur, puis le livre natif PREPARE et la
confirmation moteur sont COMMITés avant autorisation. Un échec du COMMIT
n'autorise aucune entrée. Les livres PAPER utilisent les mêmes commandes et
le vrai simulateur C10, sans order_send. Les opérations de livre sont archivées
en delta, avec des curseurs avancés seulement après COMMIT réussi.

Une panne de stockage bloque les nouvelles entrées, déclenche une alerte
déterministe et conserve le traitement des protections et clôtures. Une panne
de projection JSONL après COMMIT est signalée séparément. Pas de renvoi aveugle
après un accusé inconnu. Les erreurs de lecture C05 interrompent la permission
du symbole ; une erreur de snapshot vaut NEUTRAL selon le lecteur réel.

L'arrêt borné conserve les ressources et le verrou tant qu'un travailleur
natif reste actif, selon l'assemblage 4. Le retour de boucle archive le dernier
état et rend un rapport opérationnel sans prétendre à une qualification financière.

Catégorie 1 : cadences, temps post-I/O, rattrapage, reprise, décisions démo/réel,
double COMMIT, stockage indisponible et alertes. Catégorie 2 : vrais blocs 0→2,
séance London PAPER complète depuis le faux SDK, fichiers d'échange temporaires,
journaux C09 complets, absence d'ordre natif, replay identique C11.14 dès
l'initialisation, A/B indépendant, reprise avec arrêt et attente inconnue.


## Gardes physiques de mise en service

Avant de construire le courtier, la boucle appelle verifier_autorisations.
REEL exige une décision DEPLOIEMENT_REEL concordante et les deux preuves
C10_RESERVE/C10_DEMO. Un veto DEMO/REEL exige la décision A13 concordante.
Les chemins référencés passent par lire_fichier 4, plafonné à 64 Mio par
rapport (limite technique des documents, distincte du dossier d'échange).
Le SHA des octets est vérifié AVANT parsing. Le dossier fermé
xp-dossier-validation-v1 contient commit, empreintes technique/ia et rapport
xp-rapport-rejeu-v1 : identité identique au registre, statut VALIDE, matrice
complète et attestations C04/gel/démo présentes. Une déclaration de statut du
registre ne suffit pas. Pour A13, au moins le rapport prospectif London est
VALIDE avec ses preuves réelles attestées. Un rapport NON_VALIDE, incomplet,
étranger, altéré ou non concordant refuse le démarrage. PAPER et PAPER_AB
n'obtiennent aucune autorisation native à partir d'une archive.

Les dossiers de validation de phase 11 demeurent NON_VALIDE : ils ne peuvent
activer ces modes. Leur qualification effective appartient à la phase 13.

Précision avant les tests complémentaires du 14/11/2026 : le statut VALIDE
doit être concordant avec les critères publiés par le rapport C10. Les tableaux
applicables VALIDATION/RESERVE, les effectifs externes et le voisinage sont
présents et satisfaits. Aucun seuil ou calcul financier n'est recopié dans la
boucle ; un rapport contradictoire ou privé de ses critères est refusé.
Les tests de jonction utilisent aussi la scène causale décrite dans
tests/robot/outils/scenario_london_direct.py : seul le faux terminal reçoit les
ticks du préfixe connu ; les fichiers d'échange sont réels et versionnés. La
publication C05/calendrier est à la minute, les séances à l'heure. Le pilote
accéléré respecte les échéances moteur/livre ; la cadence 100 ms/1 s est
vérifiée séparément par l'horloge externe. Ni signal ni ordre du cœur n'est
substitué dans ces cas.

Correction P11-18, cas rouge du 14/11/2026 : les retours du livre C10 sont
transmis selon leur type public. Un rapprochement rend ObservationNative et
sa base UTC contemporaine ; un accusé rend ReponseCourtier. La boucle conserve
l'ordre des retours et ne les confond pas dans une liste d'accusés. Ces faits
restent de nouvelles entrées datées après les opérations physiques ; les
défenses sont toujours soumises avant la tentative de COMMIT.

Raccordement P11-17 après les gels des supports 1b/1f : la reconstruction d'un
déploiement existant consomme ses marqueurs de reprise archivés, puis crée le
nouveau moteur par les constructeurs C08 et transmet son checkpoint court à
SessionDurable(reprise=...). Le premier démarrage ne crée pas de marqueur.
Le prochain COMMIT conserve ainsi l'emplacement de cette reprise dans le
journal externe. La sonde de TIMEOUT natif et de rapport après redémarrage
est réintégrée aux tests de catégorie 2 avant le gel de la boucle.

La concordance A13 concerne tous les verdicts publiés : un critère ECHEC
invalide le dossier, même si le statut global est VALIDE. Les critères
NON_EVALUABLE ne sont admis que si C3 les déclare explicitement dans
criteres_non_applicables. La qualification sémantique QUALIFIE_DECLARE exige
aussi sa liste non vide de critères satisfaits. Cette vérification ne
recalcule ni effectif, ni ratio, ni seuil financier ou sémantique.

La jonction de compte vérifie les flux C07 déjà implémentés : un dépôt natif
qualifié neutralise la base une seule fois ; les pics de solde des transactions
closes entre observations restent consommés par la garde. Les arrêts quotidien
et global passent dans le COMMIT et restent actifs après reprise. Aucun calcul
de flux ou de garde n'est ajouté dans la boucle ; ses faits proviennent du
vrai adaptateur et du même coordinateur.

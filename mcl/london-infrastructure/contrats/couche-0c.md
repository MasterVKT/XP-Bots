# Couche 0c — dépôt SQLite durable
Statut : finalisé le 10/11/2026 avant code. Frontières réelles : sqlite3 et fichiers.
DepotSQLite(chemin,meta), fermer(), charger() -> bytes|None, dernier_numero -> int,
arrets() -> tuple[(bras,type,actif,depuis,decision)],
entrees() -> tuple[bytes], evenements() -> tuple[(numero,instant,decision,entree)],
persister(numero,instant_ms,etat,*,entrees=(),decisions=(),intentions=(),reservations=(),arrets=()) -> numero.
etat et entrées sont des bytes JSON stricts canoniques fournis par le codec ;
une décision est bytes JSON canonique C09. Les espaces supplémentaires
restent dans le checkpoint de session. Chaque intention : (cle,statut,contenu),
chaque réservation : (cle,risque,volume), chaque arrêt : (bras,type,actif,decision).
Initialisation meta immuable (schema, déploiement, empreintes, mode/commit fournis).
Version du schéma physique xp-etat-sqlite-v1 ; mismatch refuse sans écrasement.
WAL, synchronous FULL, BEGIN IMMEDIATE ; état, delta d’entrées, décisions,
intentions, réservations et arrêts sont atomiques ; rollback sur toute erreur.
Un seul processus écrivain, timeout SQLite explicite ; pas de preuve avant COMMIT.
Numéros d’événement strictement successifs, répétition identique idempotente,
répétition différente et trou refusés. Entrées numérotées successives et uniques.
Intentions uniques mises à jour, réservations remplacées dans la transaction ;
un arrêt actif persiste et ne peut être levé sans décision datée non vide fournie.
Les octets exacts sont conservés ; pas de JSON non fini, doublon ou non canonique.
Erreur : ValueError pour contrat, sqlite3.Error/OSError pour stockage. Context manager.
Tests : vraie base temporaire, redémarrage, rollback, concurrence, corruption et arrêts.

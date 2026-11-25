# Couche 2b — routeur

Statut : contrat finalisé le 17/11/2026 après gel de ses dépendances, avant code.
Consommateur : planificateur. Dépend de types, tokens, validation, budget,
fournisseurs et des ports transaction, HTTP et temps.

Unité : routeur. Responsabilité : une file durable, une route par fournisseur
et par job, admission A08–A09 avant transport, validation et facturation séparées.
Signature : RouteurIA(ressources,depot,http,horloge,profils=(),*,paiement_autorise=False),
enregistrer(job), en_attente(), annuler(job_id,raison), reprendre(), executer(job).
Les méthodes rendent bool, tuple de JobIA, ResultatIA, tuple d'IDs et ResultatIA.
Le propriétaire garantit un seul worker ; une réentrée sur la même instance est refusée.

Enregistrer est idempotent pour le même job complet ; réutiliser son ID avec
un autre contenu est refusé. Le registre conserve le dossier exact et les
instants, sans clé. executer restitue un résultat terminal déjà archivé sans
appel. Un RUNNING retrouvé devient INCONNU, sans réinférence ; reprendre annule
les anciennes attentes et signale les tentatives inconnues au démarrage.

Le délai global court depuis la prise du job, au plus la durée exportée et
son utilité restante. Chaque transport a le timeout exporté, réduit au temps
restant. Un recul d'horloge est refusé. Les fournisseurs suivent l'export,
sans répétition ; seuls les appels réellement admis comptent dans les trois
tentatives, avec les pauses exportées avant les secours. Une route non qualifiée,
désactivée, trop proche, hors quota ou payante non autorisée est ignorée sans
transport. Aucun profil par défaut ne prétend disposer d'une clé ou de quotas.

La réservation est commitée avant HTTP. L'enveloppe complète passe par 1a et
1e ; l'extraction reste entière, les notes peuvent perdre seulement des
documents entiers. La validation d'une note ne connaît que les IDs du dossier
effectivement envoyé et explicitement admis par le job. Les agrégats en amont
sont anonymisés ; le port HTTP ajoute les secrets séparément en couche 4.

Chaque tentative archive requête hors secret, hashes prompt/schéma, modèle,
dossier transmis, instants, réponse brute bornée, usage et erreur statique.
L'usage est lu indépendamment du texte, y compris une erreur HTTP ou une sortie
incomplète. Un usage connu est rapproché exactement une fois ; absent, il garde
sa réserve. Un dépassement désactive la route et refuse la sortie exploitable.
401/403 désactivent et alertent ; 429 persiste Retry-After en secondes ou date
HTTP ; timeout/5xx passent au suivant. Les exceptions ne sont jamais journalisées
en clair. Une réponse trop tardive reste archivée et sans résultat exploitable.
Une valeur Retry-After au-delà du calendrier représentable bloque jusqu'au
dernier instant UTC représentable ; elle ne se transforme jamais en délai nul.
Ignorer une route non admissible ne répète pas la pause du même secours.

Les jobs sans aucune admission terminent AUCUNE_ROUTE_ADMISSIBLE. Le planificateur
peut reporter une tâche non urgente sous un nouveau job daté, sans retenter un
article déjà classé ni dépasser les plafonds globaux. Aucune attente n'a lieu
dans un moteur de trading, et aucun échec ne crée permission ou veto.

test_cat1_c2b_routeur.py couvre file, échéances, secours, erreurs et reprise.
test_cat2_c2b_routeur.py traverse budget, enveloppes, tokens et validateurs réels ;
seuls HTTP, transaction et horloge sont doublés aux frontières. Les contrats
HTTP physiques sont écrits en 4 et différés à 13.6.

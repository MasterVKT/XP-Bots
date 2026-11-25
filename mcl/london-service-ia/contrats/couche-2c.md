# Couche 2c — collecteur

Statut : contrat finalisé le 17/11/2026, avant code, dépendances 0/1c gelées.
Consommateur : planificateur. Dépend de types, normalisation et ports transaction,
HTTP, temps et sélection d'archives.

Unité : collecteur. Responsabilité : collecte officielle A04 et mémoire causale
des textes, indépendante de l'inférence et des moteurs.
Signatures : CollecteRSS(issuer,recu_ms,couverture,nouveaux,statut,anomalies=()),
CollecteurRSS(ressources,depot,http,horloge,*,selectionner=None), collecter(issuer),
documents(issuer=None,*,debut_ms=None,fin_ms=None,known_at_ms=None).

Le port selectionner(filtres) retourne des lignes source_items, avec issuer,
bornes de publication [début,fin), connaissance maximale incluse, et éventuellement
URLs ou hashes de dédoublonnage. La mémoire transactionnelle est le défaut de
test ; la couche 4 fournit des requêtes SQLite indexées et FTS5 pour éviter de
charger toute l'archive à chaque heartbeat. Ce port ne reçoit ni opinion LLM
ancienne ni secret. Chaque ligne porte un document immutable et content_known_at.
Le sélecteur et sa sortie sont recontrôlés pour la causalité et les filtres.
Les statuts sont RECU, NON_MODIFIE, DIFFERE et ERREUR. Les réponses XML brutes
sont archivées par empreinte dans feed_state, reliées aux IDs normalisés ;
elles ne sont jamais soumises comme une preuve de classification déjà validée.

Les feeds et seuils viennent de l'export. Un appel avant next_poll_ms ne fait
aucun HTTP. Les headers conditionnels proviennent uniquement d'un flux reçu et
normalisé ; 304 garde sa couverture antérieure et ne crée aucun texte ni job.
Un 304 sans copie antérieure est partiel. Les refus, corps trop gros, temps
dépassé et XML invalide rendent PARTIAL et appliquent max(backoff,Retry-After).
La BoE 403 n'entraîne ni contournement ni substitution. Pas d'images ou pièces jointes.
Un Retry-After dépassant le calendrier représentable reste bloquant jusqu'à
son dernier instant représentable. Une requête 304 après une panne restaure
la couverture de la dernière copie validée, sans renouveler ses textes.

Les redirections sont suivies manuellement, au plus trois, seulement HTTPS
sur une origine officielle configurée ; aucun hop non qualifié n'est envoyé.
Le corps est borné au téléchargement et de nouveau contrôlé à cette couche.
Une horloge en recul ou une réponse future est refusée sans création causale.

La normalisation réelle est suivie du dédoublonnage URL/hash avec les archives.
Un même texte conserve ID, publication et première vue ; son dernier passage
peut être tracé séparément. Une correction a une nouvelle ligne et son propre
content_known_at, même si publication et première vue originelles sont conservées.
L'ancienne ligne n'est jamais réécrite. Seuls les IDs nouveaux sont rendus dans
nouveaux, et un second poll ou un redémarrage n'en crée pas un autre.

Les résultats indiquent explicitement COMPLETE/PARTIAL. Une absence de texte
ne devient jamais une permission. Les tests des deux catégories traversent le
normaliseur réel ; seuls les ports externes sont doublés. Les probes API/RSS
physiques restent différées en 13.6, sans réseau courant.

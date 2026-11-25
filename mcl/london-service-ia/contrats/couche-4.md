# Couche 4 — service physique

Contrat finalisé le 25/11/2026 après CP3, avant code. Consommateur : processus
partagé et lecteur IA externe. Dépend des couches publiques 0 à 3 et des ports
physiques, du noyau, de C05 et de l’infrastructure existante.

API : DepotServiceSQLite(chemin,ressources,*,creer=True), transaction(operation),
selectionner_documents(filtres), selectionner_jobs(), selectionner_evenements(t),
chercher_textes(texte,*,issuer=None,known_at_ms), fermer(), contexte de fermeture ;
HorlogeService(horloge_systeme=None), maintenant_ms(), attendre(secondes) ;
TransportHTTP(ressources,horloge,*,ouvreur=None,cles=None,autoriser_http_reel=False),
__call__(RequeteHTTP) ; PublieurSnapshot(ressources,chemin,horloge), __call__(bytes) ;
CalendrierService(ressources,depot,chemin,convertir_serveur,table_importance,
table_appariement,horloge,*,max_octets), actualiser(), __call__(t) ;
ServiceIA(ressources,chemin_base,chemin_snapshot,*,horloge=None,ouvreur=None,
cles=None,profils=(),autoriser_http_reel=False,paiement_autorise=False,
calendrier=None,cas_derives=(),routes_auditees=(),agregats=None), collecter(), inferer(),
heartbeat(), demarrer(), arreter(), fermer(), etat() ; main(argv=None).

SQLite emploie BEGIN IMMEDIATE, WAL, synchronous FULL, tables minimales A10
et auxiliaires TABLES_IA. Les montants restent des chaînes décimales. Le mapping
paresseux détecte aussi les modifications imbriquées ; succès commite tout,
exception annule tout, retour sans alias. Aucun verrou transactionnel pendant
HTTP. Colonnes et index réels permettent recherche issuer/date/connaissance,
jobs en attente, événements actifs et FTS5 sans charger toute l’archive.
Identité schema/config/instance persistée ; pas de base existante non qualifiée
adoptée ni reset de budget/séquence. Deux connexions utilisent le registre réel.

Le transport est inactif sans autorisation ou ouvreur injecté. Il impose HTTPS,
endpoints et headers allowlist, timeout et lecture cap+1, fermeture immédiate,
aucune redirection implicite. Le statut et Retry-After restent disponibles
sur corps trop grand ; les consommateurs refusent ce corps sans l’archiver.
Les clés sont injectées seulement dans Request ; aucun secret dans types,
dossiers, snapshot, journaux ou erreurs affichées. Un corps reflétant une clé
est rejeté. Les doublures remplacent seulement l’ouvreur externe.

Le calendrier lit uniquement D12, borné par le lecteur binaire existant, avec
conversion serveur explicitement qualifiée et mapping issuer/type versionné.
Versions et disponibilités sont datées et archivées. La copie mémoire répond
sans I/O à l’instant demandé ; une lecture invalide n’est pas masquée par le
cache. Aucune permission ou donnée de compte n’est obtenue par le service IA.

La publication réutilise ecrire_atomique, avec les reprises de l’export, ancien
fichier préservé à échec, séquence réservée par le vrai writer1f avant I/O.
Verrou global du snapshot, identité base/manifeste et nettoyage des ressources
sur échec empêchent deux producteurs ou une recréation silencieuse de base.

Trois boucles séparent collecte, unique inférence et heartbeat. Un HTTP lent
ne bloque pas le heartbeat ou un moteur extérieur. La reprise ne réinfère pas ;
un usage antérieur inconnu suspend les nouvelles inférences et conserve sa
réserve. Les événements validés gardent leur échéance. Alertes locales, aucun
envoi à une messagerie. Le calendrier invalide n’est jamais une permission.

CLI distincte python -m xpbots.service_ia, ressources exactes et profils publics
datés, HTTP réel inactif par défaut (H08/13.6), payant désactivé. Aucun veto réel
activé : PAPER_AB, fournisseurs NON_QUALIFIE sans A13. Aucun .env réel lu par
l’agent, aucun SDK/compte/ordre, aucune nouvelle dépendance.

Catégorie 1 : fichiers et SQLite réels, rollback, concurrence, reprise, verrou,
secret synthétique, limites HTTP et publication. Catégorie 2 : composition et
couture réelle service → fichier → lecteur → séance London PAPER_AB entière,
été/hiver, états indépendants, aucun filtrage rétrospectif des trades. Tests
de contrat trois API/trois RSS écrits et ignorés sans XPBOTS_CONTRATS_API=1.
Ces fixtures ne qualifient ni réseau, terminal, sémantique ni rentabilité.

Le paramètre calendrier du service est un port déjà composé ou un dictionnaire
des paramètres publics de CalendrierService (la base et l’horloge sont celles
du service). Une horloge de test peut fournir attendre_arret(stop,secondes)
pour piloter les boucles sans attente réelle. Les lectures de calendrier sont
ordonnées par séquence persistée, même à timestamp identique ; une nouvelle
version mémoire n’est publiée qu’après l’archive durable de ses preuves.

Étendu le 25/11/2026 (défigeage `extension`, raccordements physiques A11).
Le fichier optionnel agregats (CLI executer --agregats) est lu dans la boucle
collecte par le lecteur borné existant, sans attente de l'inférence. Objet fermé
xp-code-aggregates-v1 : schema, metriques et decisions. Les deux listes passent
ensemble au vrai port recevoir_metriques de couche 3, qui valide causalité,
anonymisation, identifiants immuables et atomicité. Le service ne recalcule
aucune performance. Une empreinte persistée évite les réimports inchangés ;
un échec conserve les données précédentes et la collecte RSS continue. Aucun
chemin .env ni chemin de sortie du service ne peut servir d'entrée.

Le heartbeat affiche les alertes persistées via le port local alerter de
l'infrastructure, même sans HTTP. Codes et descriptions affichés sont statiques,
sans contenu de réponse ni nom de fichier. Les alertes identiques déjà affichées
ne sont pas répétées après reprise. L'échec de publication est également une
alerte locale ; les workers restent indépendants. Aucune messagerie.

Corrigé le 25/11/2026 (défigeage correction, cascade de 3) : la couture SQLite
→ sélecteur indexé → planificateur → fichier → lecteur vérifie aussi le retrait
d'un veto déjà actif après suspension du fournisseur. L'archive reste intacte
et la reprise republie un contexte sans ce veto ; aucune réinférence.
Le lecteur déjà informé conserve sa preuve jusqu'à l'échéance propre selon
A10 ; le snapshot vide n'introduit aucune révocation. Un nouveau lecteur
ne reçoit pas le veto du fournisseur suspendu. Ces deux effets sont testés.

# Couche 0d — journaux physiques
Statut : finalisé le 10/11/2026 avant code. Frontière réelle : fichiers.
JournalFichiers(racine,deploiement).publier(evenements) -> None,
ajouter(evenements) -> None ;
evenements = tuples (numero,instant_ms,decisions,entrees), décisions = bytes C09
déjà canoniques (produits par serialiser du noyau), entrées = tuple de bytes
JSON stricts portant numero, instant_reception_utc_ms, type_evenement, contenu typé.
Le dépôt SQLite est l’autorité ; publier, uniquement à la reprise, répare et réécrit atomiquement les
fichiers quotidiens decisions_AAAA-MM-JJ.jsonl et entrees_AAAA-MM-JJ.jsonl.
En marche, ajouter append/flush/fsync/ferme seulement le delta d’événements
successifs, sans relire ni recopier le journal croissant ; répétition ignorée
seulement après comparaison aux octets déjà publiés dans l’instance. Un append
échoué interdit tout append suivant avant réparation par publier. Une panne
entre deux fichiers laisse SQLite autoritaire et sera réparée par publier
sous logs/deploiement, dans l’ordre du journal, sans double ligne après reprise.
Un fichier temporaire est flush/fsync/fermé avant os.replace ; le contenu complet
est validé avant publication. Aucun secret ni numéro de compte n’est ajouté.
ecrire_atomique(chemin,octets), lire_octets(chemin,max_octets), lire_json(chemin,max_octets),
ecrire_json(chemin,document) et alerter(code,detail) couvrent les besoins physiques
de la coquille, sans stratégie ni horloge ; JSON strict UTF8, doublons et NaN refusés.
Un identifiant de déploiement est un basename sûr ; aucune traversal ni chemin absolu.
En PAPER_AB, les enveloppes C09 du moteur portent les identifiants
deploiement:REFERENCE et deploiement:IA. Le journal du déploiement racine accepte
exactement ce suffixe concordant avec le bras de l'enveloppe, dans ce seul mode.
Les octets restent inchangés et les deux comptes restent distincts dans C09 ;
aucun deux-points n'est ajouté aux chemins physiques. Un autre déploiement,
un suffixe croisé ou un suffixe en mode simple est refusé avant toute écriture.
Erreurs : ValueError format/contrat, OSError stockage. Les commandes défensives
C08 ne sont pas conditionnées à la réussite de ce journal.
Tests : C09 réel, mêmes octets après reprise, crash simulé à la frontière replace,
deux jours UTC, taille et JSON hostiles.

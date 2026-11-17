# Service d'export D12

Le service [XPBotsExport.mq5](Services/XPBotsExport.mq5) publie uniquement le
calendrier HIGH et les séances natives du terminal. Il ne produit aucun
signal, indicateur, permission fondamentale ou ordre. Les contrats sont
ceux du [document 08](../docs/architecture/robot_london_v3/08_contrats_frontieres.md)
et de [l'infrastructure](../mcl/london-infrastructure/contrats/couche-4.md).

La source principale dépend de quatre includes locaux. Atomic gère le JSON
UTF-8, la réservation des versions et le remplacement des fichiers ;
TimeTable lit les paramètres et la table S01 ; Calendar dépend de ces deux
modules ; Sessions dépend d'Atomic. Les includes ne possèdent pas d'état
mutable global. OnStart possède la cadence et le verrou du service.

En phase 13.1, copier le fichier principal et le dossier XPBotsExport dans
MQL5/Services du terminal qualifié, puis compiler le service dans MetaEditor.
Conserver le journal de compilation et comparer les exports aux fonctions
natives. Les contrôles ordinaires de ce dépôt n'ouvrent pas MetaEditor,
n'installent pas de terminal et ne prouvent pas cette compilation.

Le service lit parametres_service.tsv dans le dossier FILE_COMMON réel,
XPBots/export/v1. Ce TSV UTF-8 sans BOM porte le schéma xp-parametres-export-v1,
le serveur exact, la version de table, couverture_future_secondes, les segments
UTC en secondes avec leur décalage et les symboles exacts du courtier. Il ne
contient aucun identifiant de connexion. Les segments viennent de la sonde
S01 ; aucun décalage actuel n'est extrapolé à une autre date.

La couverture calendrier doit inclure news_forward_coverage_seconds et
news_calendar_max_age_seconds de CF, plus la cadence d'export. Le service
demande actuellement un export calendrier toutes les soixante secondes et
les séances toutes les heures ; il vérifie l'arrêt avec une attente de cent
millisecondes. Ces cadences sont des constantes d'ingénierie à tracer au
registre, sans modifier les seuils C05. Une lecture incomplète native,
une heure ambiguë ou une table hors couverture empêche la publication.

Chaque sortie JSON possède un fichier .version persistant. Sa nouvelle
version est réservée et fermée avant le remplacement du JSON ; un saut est
admis, un retour ne l'est pas. Un export existant sans compteur ne redémarre
pas silencieusement à un. Ne pas effacer ces compteurs pour faire accepter
un export. Un verrou execution.lock exclut deux services simultanés.

Le service ne crée pas fermetures_exceptionnelles.json : ce relevé des avis
du courtier appartient à l'opérateur. Les permissions C05 viennent du module
fondamental externe, sur leur autre chemin D11. Le snapshot IA appartient
au service IA de phase 12. L'absence ou l'obsolescence d'une de ces sources
garde les effets prévus par les vrais lecteurs Python.

Les [fixtures](../tests/robot/fixtures/mql5_exports/README.md) sont synthétiques.
Elles vérifient les formats et la causalité des lecteurs, avec des contrôles
statiques du code MQL5. Elles ne qualifient ni le courtier ni ses historiques,
ses frais, ses droits ou la latence de son terminal. Ces preuves restent à
recueillir explicitement en phase 13.1 avant toute mise en service native.

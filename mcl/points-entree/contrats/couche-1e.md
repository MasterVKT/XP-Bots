# Couche 1e (profondeur 2) — rapports C10 et incident

`rapporter_archives(configuration, archives)` charge chaque archive par 1c,
vérifie sa configuration intégrale et appelle le vrai produire_rapport C10.
Aucun verdict financier n'est fabriqué et une déclaration de preuve seule
n'est pas une attestation. Les fixtures demeurent NON_VALIDE.

`rapporter_incident(configuration, archive)` reçoit une archive typée contenant
la composition initiale, les appels d'initialisation, les entrées réelles, le
checkpoint de journal et les octets C09 effectivement persistés. Il reconstruit
par 1f avec backend interdit dès l'initialisation, compare le checkpoint puis
les octets C09 dans leur ordre exact. Une différence refuse le rapport. Il
restitue le nombre d'entrées, les empreintes du journal C09 et de l'état final,
et les commandes reconstruites. Il ne prétend pas avoir comparé ces commandes
à un historique de transport qui n'a pas été fourni.

Le test de répétition générale accumule les sorties réellement rendues par
chaque itération de la boucle, sans remplacer le moteur, et compare en outre
toutes les commandes et tous les états à ceux du rejeu, ainsi que les octets
SQLite/JSONL. L'application de production n'accumule pas ces sorties en mémoire
à chaque itération. Une archive d'incident complète est exportée sur demande
ou à l'arrêt, pas recopiée dans chaque checkpoint régulier.

Les entrées physiques demeurent dans l'infrastructure. Le codec est celui de
l'orchestration ; aucune classe, fabrique, import ou permission d'ouverture du
test réservé ne provient du contenu d'une archive. La CLI de rapport ne charge
pas le SDK. Schéma fermé `xp-archive-incident-v1` ; une archive ne fournit jamais
une décision de déploiement ni un droit d'envoi natif.

Catégorie 1 : schémas, configuration étrangère, troncature/altération C09 ou
journal, absence de preuve, rapport conservateur. Catégorie 2 : vraies archives
C10 de 1c, vrai moteur reconstruit par 1f et journaux physiques de 1b/4, backend
interdit ; égalité exacte des décisions, états et commandes reconstruits.

Raccordement P11-17 après gels de 1b/1f du 14/11/2026 : la session peut porter
la clé optionnelle `reprises`, tuple des marqueurs de reprise C08 restitués par
1b. Le rapport la transmet au rejeu 1f qui refait les constructeurs C08 au bon
préfixe et compare les marqueurs. Les autres clés restent fermées ; une reprise
retirée, déplacée ou altérée doit produire un rejet lorsque l'état reconstruit
diverge. Les décisions C09 avant et après redémarrage restent comparées dans
leur ordre exact ; aucune commande native n'est renvoyée par ce rapport.

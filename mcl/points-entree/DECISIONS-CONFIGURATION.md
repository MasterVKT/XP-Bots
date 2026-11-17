# Configuration des points d'entrée — phase 11

Le registre d'exécution est distinct des exports métier conservés. Il les lie
par leurs empreintes d'octets, avec le commit, les symboles natifs, les références
de qualification et les décisions datées. Il ne contient aucun accès au compte.
Les références C10 et A13 doivent également être contrôlées par les commandes
natives ; une déclaration du registre ne vaut pas preuve financière.

Les cadences proviennent de D-09 et du service MQL5 construit : boucle de 100 ms,
minuterie et lecture des contrôles chaque seconde, export du calendrier chaque
minute et des séances chaque heure. Les autres valeurs du gabarit sont des
constantes d'ingénierie modifiables sous registre, sans optimisation sur un
résultat. La capacité native réserve une place aux défenses. La limite de 64
jours pour les horaires permet de qualifier un préchargement H1 couvrant les
week-ends ; elle ne prouve aucune couverture et ne remplace jamais S01/S08.

P11-09 est traité dans le générateur pur : l'horizon du calendrier est la somme
des durées de couverture future et de péremption lues dans CF, augmentée de la
cadence d'export. Le test transmet cet horizon au vrai contrôle C05 : il demeure
exploitable entre deux exports et jusqu'à sa péremption, sans renouvellement
fictif de fraîcheur. Le service MQL5 conserve son plafond de lecture de 131 072
octets et n'infère aucun décalage horaire. La commande physique de génération
reste à brancher dans l'enveloppe de cet artefact.

Les gabarits du registre et des fermetures restent volontairement inexécutables :
les heures, la version, le déploiement et les preuves inconnus sont nuls. Les
renseigner relève de la qualification prévue en phase 13. L'implémentation de la
phase 11 se valide avec des fixtures explicites et des frontières temporaires.

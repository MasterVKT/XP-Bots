# Points d'entrée — construction, phase 11

Artefact composant `points-entree`, paquet `xpbots.app`, mode pur dans le composite
London existant. Les entrées physiques passent par l'infrastructure commune.
Applicable : structure déterministe connue, contrats stabilisables, oracle des
sorties existant. Pas de recherche de stratégie. Neuf unités sont nécessaires :

| Couche | Unité | Entrées → sorties | Dépendances internes |
|---|---|---|---|
| 0 | configuration | registre + CF + instant → configuration validée ; gabarits et paramètres MQL5 | aucune |
| 1a | livre_papier | opérations natives et ticks → livre C10 réel ; journal incrémental et reprise causale | 0 |
| 1b | session_durable | checkpoint moteur, entrées et états externes → COMMIT SQLite et JSONL réparables | 0 |
| 1c | cli_rejeu | demande C10 et chemins → expérience et rapport du bloc réel | 0 |
| 1d | cli_qualification | registre et adaptateurs → rapport C04 sans ordre | 0 |
| 1f | composition_moteur | initialisation et ports → vrai moteur London ; reconstruction sans backend | 0 |
| 1e | cli_rapports | journal/résultats archivés → rapports ; rejeu incident sans backend | 0, 1a, 1c, 1f |
| 2 | boucle_direct | configuration → contrôles, ticks, minuteries, persistances et exécution continue | 0, 1a, 1b, 1f |
| 3 | principal | arguments → commande et code de sortie | 0, 1c, 1d, 1e, 2 |

Les unités 1a à 1d sont parallèles au sens du DAG ; chacune a son gate et son
gel. La composition 1f et les rapports 1e ont leurs dépendances explicites dans
la carte analysée ; leurs identifiants ne désignent pas leur profondeur.
Le livre PAPER ne dépend pas de la persistance : il expose des
opérations publiques et un checkpoint, sans connaître SQLite. La session durable
archive des valeurs canoniques ; elle ne choisit ni admission ni remplissage.
Le cycle de direct les compose. Les anciennes entrées EMA restent exclues de
la carte ; `rejeu_squelette` conserve sa compatibilité par couture tracée.

Question-test : la configuration se teste sans CLI ni livre ; le livre se teste
avec le seul simulateur figé ; le dépôt se teste avec le vrai SQLite et moteur
figés ; chaque commande se teste sans boucle ; la boucle exige les deux supports ;
la composition exige les ports de compte et les contrats du moteur et des
contrôles ; les rapports exigent les
archives et la reconstruction réelles ; le principal exige les commandes.
Aucune dépendance inférée de l'ordre du flux.

Amonts : noyau, orchestration, London, C05, lecteur IA, exécution, rejeu,
infrastructure, tous réels et figés. Frontières : seul le SDK et l'horloge sont
doublés en tests ; fichiers et SQLite temporaires réels. Aucun SDK réel ni API.
Contrats esquissés ci-dessus puis finalisés juste avant chaque couche ; strict
et zéro divergence. Catégorie 1 = contrat propre ; catégorie 2 = blocs réels.
Gate par unité : ses deux catégories (0 sans catégorie 2), suite London intégrale
des deux lignées et verify_project.py ; gel immédiat sans modification d'arbre.
Checkpoints après les niveaux 1 et 3. La régression conserve L-01…L-19 des
couches métier. La jonction physique ajoute C11.14 et la répétition PAPER
complète dans la boucle et sa couture, sans verdict financier.

Coût : gates intégraux croissants et sérialisation des dépendances. La séparation
livre/persistance ajoute deux supports nécessaires à la reprise, sans deuxième
moteur ni simulateur. Aucun choix produit n'est ouvert ; cadre D-01…D-18 suivi.

## État de construction au 14/11/2026

0, 1a, 1b, 1c, 1d et 1f sont gelées. 1b a été corrigée formellement pour
conserver les décisions fournies dont le COMMIT avait échoué (P11-14).
Les checkpoints courts de l'orchestration ont été revalidés et gelés en amont
(P11-13/P11-15) : reprise par rejeu public, puis checkpoint complet et C08.
1e et 2 sont gelées après leurs tests de fichiers et de SQLite réels et la
régression intégrale de 1 384 tests (14 contrats physiques différés). La couche 3
est également figée après son gate de 1 393 tests : 1 379 exécutés avec succès
et 14 contrats physiques différés. Ses quatre tests de contrat et cinq tests
de jonction couvrent les huit commandes, l'archive d'incident, le gel réel et
sa conservation sous verrou entre processus. Un changement d'inventaire est
refusé avant les prix, même si leur fichier est absent. La seule erreur de
raccordement révélée avant ce gel concernait le nom du délai de fermeture ;
les tests physiques vérifient désormais la fermeture effective des ressources.
Les tests natifs de phase 13.1 sont recensés dans l'infrastructure ; la
présente construction n'importe jamais le SDK réel dans ses contrôles.
1b et 1f ont été étendues et regelées pour l'extension additive P11-17 : les
reprises C08 sont archivées au préfixe concerné et reconstruites par leurs
constructeurs réels. Le raccordement 1e/2 et la sonde native C11.14 sont verts,
y compris le refus d'un rapport dont le marqueur de reprise a été retiré.
Le cas natif court de flux qualifiés, pics de solde intermédiaires, arrêts et
redémarrage passe aussi ; ses données sont synthétiques et aucun envoi n'a lieu.

Le checkpoint de consommation avant 3 relit aussi l'implémentation interne de
1f à contrat constant : le préfixe courant vient d'enumerate, au lieu de copier
le tuple du journal pour compter ses entrées avant chaque marqueur. Le journal
complet reste fourni aux seuls véritables constructeurs C08. Cette révision
repasse par le gate global intégral ; aucune interface ou suite gelée ne change.

## Bilan de clôture de la phase 11

Les neuf unités sont figées, avec leurs deux catégories et leurs gates
intégraux. La configuration, le livre PAPER, la session durable, le rejeu,
la qualification, les rapports, la composition commune du moteur, la boucle
directe et le principal conservent leurs responsabilités distinctes. La
clarification de la carte a séparé le livre de la durabilité et identifié 1f
comme composition partagée par direct et incident ; aucun second moteur de
décision ou simulateur n’a été construit.

`python -m xpbots.app` expose les huit commandes documentées dans le
[guide d’exploitation](../../docs/exploitation/LONDON_M15.md). Les contrôleurs
utilisent le même noyau, les mêmes calculs, le même London et les mêmes ports
C05/IA. Les fichiers passent par l’infrastructure. La qualification ne donne
aucune autorisation d’exécution ; le neutre technique est refusé en DEMO/REEL,
le réel exige la décision tracée et les preuves C10, le veto natif ses preuves
A13. Les dossiers contradictoires sont refusés sans modifier ni recopier les
seuils des exports.

La session durable persiste les deltas et toutes les décisions fournies qui
restent non COMMITées. Une reprise d’écriture ne perd donc pas le journal C09.
La boucle exige le COMMIT du cœur puis celui de la préparation native avant
l’autorisation du worker. Un délai de persistance peut faire expirer le signal
avant l’envoi. Les défenses restent prioritaires pendant les pannes de stockage
ou de flux ; une réponse native inconnue ne provoque pas de renvoi. Le redémarrage
conserve les gardes et références de flux externes, y compris leurs pics de
solde intermédiaires.

Les checkpoints courants engagent les faits connus par empreinte et métadonnées
sans recopier les historiques de stratégies, C05 ou preuves IA. Le rejeu public
reconstitue une fois le checkpoint complet, puis les vrais constructeurs C08.
Les reprises sont archivées au préfixe concerné et rejouées par 1f ; leur absence
est refusée. La répétition courte instrumentée a produit un remplissage et une
clôture, un checkpoint de 20 037 octets et une dernière persistance de 13,3 ms.
C’est une mesure locale synthétique, pas une borne de latence ; le premier lot
de préchargement et la confrontation au poste restent distincts.

Le gel du test réservé engage l’inventaire réel du code et des ressources.
La première ouverture, les consultations et les refus persistent sous verrou
entre processus avant toute lecture de prix, préchargement compris. Un registre
corrompu ou un changement d’inventaire ne recrée pas le premier gel. Les erreurs
avant démarrage ferment effectivement les ressources ; un worker encore actif
conserve leur propriété jusqu’à sa fin.

La répétition PAPER utilise la vraie boucle directe, FauxMT5, CommonFiles et
SQLite temporaires. Son journal d’entrées, ses décisions C09, ses livres et son
état se rejouent à l’identique (C11.14). Les cas de panne, de timeout et de
redémarrage passent aussi, avec les deux comptes PAPER_AB indépendants. Le CP4
revalide ces consommateurs après la correction horaire P11-20 de l’infrastructure.

L’artefact comprend 90 tests (60 de catégorie 1 et
30 de catégorie 2). La suite globale recense 1403 tests :
1389 réussis et 14 contrats physiques différés. Les 70 tests du
squelette restent verts. Les valeurs et ressources protégées n’ont pas changé.

### Vérification adversariale

La baseline saine et chacune des 38 variantes ont exécuté la suite
intégrale sur une copie jetable hors du dépôt, avec SDK réel interdit. Les
38 mutations sont détectées par les tests ci-dessous ; une erreur
de syntaxe, d’import ou de harnais ne compte pas comme détection.
La sélection complète est contrôlée avant chaque exécution. Lorsqu’une variante
fait échouer une fixture de classe ou de module, ses cas non exécutés sont
décomptés explicitement ; ils ne sont pas présentés comme des tests lancés.
La cohorte de 876 fichiers est engagée par le SHA-256
`7cde58c2061016d3992bd235e5489287400c34e90f57305415d03356bb5928fe`. Le défaut de comptage local H11-01 a été corrigé en
séparant cette sélection des cas réellement exécutés ; les cinq premières
preuves ont été conservées après reconstitution exacte de la même cohorte.
Une interruption du processus pendant M11-30 a ensuite laissé 29 détections
validées ; M11-30 à M11-38 ont été exécutées sur une nouvelle copie de même
empreinte, sans compter le résultat partiel interrompu.
Les documents de clôture sont finalisés ensuite, puis l’archive exacte de
l’index fait l’objet de sa propre régression, sans les quinze fichiers
initialement modifiés par l’utilisateur.
Le fichier d’initialisation du paquet de tests d’infrastructure contient une
docstring seule ; sa fin de ligne CRLF a été normalisée en LF pour correspondre
au blob Git. Son AST reste identique et aucun contrat gelé n’est modifié.

| Mutation | Cible | Altération volontaire | Détection par la suite intégrale |
|---|---|---|---|
| M11-01 | infrastructure/0a | Inverse la conversion UTC vers heure serveur sur un segment qualifie. | 2 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c0a_types.py), comportement Python |
| M11-02 | infrastructure/0b | Decale les receptions physiques d une milliseconde. | 4 échec(s), 18 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c0b_horloge.py), comportement Python |
| M11-03 | infrastructure/0c | Autorise la levee d un arret durable sans decision et refuse la reprise tracee. | 1 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c0c_sqlite.py), comportement Python |
| M11-04 | infrastructure/0d | Colle les decisions et entrees sans separateur JSONL dans la projection incrementale. | 8 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c0d_journal.py), comportement Python |
| M11-05 | infrastructure/0e | Expose un snapshot depassant la borne de lecture. | 1 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c0e_snapshot.py), comportement Python |
| M11-06 | infrastructure/0f | Calcule le SHA de contenu sur des lignes differentes des octets decompresses. | 5 échec(s), 7 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c0f_ticks.py), comportement Python ; 1398/1403 cas exécutés, 5 bloqués par fixture |
| M11-07 | infrastructure/0g | Recherche la permission sous le symbole natif au lieu du symbole canonique D11. | 11 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c0g_controles.py), comportement Python |
| M11-08 | infrastructure/0h | Rend le contexte sans conserver le verrou physique acquis. | 3 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c0h_verrou.py), comportement Python |
| M11-09 | infrastructure/1 | Desactive la garde du type de compte en DEMO. | 2 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c1_session.py), comportement Python |
| M11-10 | infrastructure/2a | Accepte la qualification exactement a son expiration exclusive. | 4 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c2a_convention.py), comportement Python |
| M11-11 | infrastructure/2b | Reemet le prefixe natif deja consomme au meme instant serveur. | 10 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c2b_flux.py), comportement Python |
| M11-12 | infrastructure/2c | Ne compte qu un cote des frais aller retour natifs. | 1 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c2c_calculs.py), comportement Python |
| M11-13 | infrastructure/2d | Supprime la revalidation du TTL et de la fraicheur avant emission native. | 2 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c2d_transport.py), comportement Python |
| M11-14 | infrastructure/3 | Date les ticks a l appel precedent et non au retour effectif de la collecte. | 0 échec(s), 1 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c3_courtier.py), comportement Python |
| M11-15 | infrastructure/4 | Recree une base absente pour un compte deja lie au lieu de refuser la perte d etat. | 1 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c4_assemblage.py), comportement Python |
| M11-16 | points-entree/0 | Autorise la neutralite technique en mode natif. | 1 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/points_entree/test_cat1_c0_configuration.py), comportement Python |
| M11-17 | points-entree/1a | Rend le livre disponible malgre une interruption physique declaree. | 1 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/points_entree/test_cat1_c1a_livre_papier.py), comportement Python |
| M11-18 | points-entree/1b | Perd les decisions fournies pendant la panne du precedent COMMIT. | 0 échec(s), 3 erreur(s) ; [cas de test](../../tests/robot/points_entree/test_cat1_c1b_session_durable.py), comportement Python |
| M11-19 | points-entree/1c | Retire l autorisation explicite avant le vrai verrou C10 du reserve. | 3 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/points_entree/test_cat1_c1c_rejeu.py), comportement Python |
| M11-20 | points-entree/1d | Presente une lecture C04 comme une autorisation d execution. | 2 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/points_entree/test_cat1_c1d_qualification.py), comportement Python |
| M11-21 | points-entree/1e | Omet les reprises C08 en reconstruisant le rapport d incident. | 0 échec(s), 1 erreur(s) ; [cas de test](../../tests/robot/points_entree/test_cat2_c2_persistance_entree.py), comportement Python |
| M11-22 | points-entree/1f | Ne reconstruit plus C08 aux prefixes archives. | 2 échec(s), 1 erreur(s) ; [cas de test](../../tests/robot/points_entree/test_cat2_c1f_composition.py), comportement Python |
| M11-23 | points-entree/2 | Autorise une preparation native apres echec de son second COMMIT. | 1 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/points_entree/test_cat2_c2_persistance_entree.py), comportement Python |
| M11-24 | points-entree/3 | Permet un nouvel inventaire au reserve apres la premiere ouverture persistante. | 1 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/points_entree/test_cat2_c3_reserve.py), comportement Python |
| M11-25 | execution-coordinateur/1b | Omet le flux externe identifie dans la base quotidienne courante. | 5 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_execution_coordinateur/test_cat1_c1b_flux_courants.py), comportement Python |
| M11-26 | execution-coordinateur/1c | Conserve la tentative refusee au lieu de liberer seulement sa reservation. | 8 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_execution_coordinateur/test_cat1_c1c_tentative.py), comportement Python |
| M11-27 | execution-coordinateur/4 | Ne rend pas reessayable un refus de prix non definitif connu. | 6 échec(s), 2 erreur(s) ; [cas de test](../../tests/robot/london_execution_coordinateur/test_cat1_c4_refus_prix.py), comportement Python |
| M11-28 | execution-coordinateur/6 | Conserve un ancien horaire comme qualifie pour la planification de sortie. | 0 échec(s), 2 erreur(s) ; [cas de test](../../tests/robot/london_execution_coordinateur/test_cat2_c6_horaires_courants.py), comportement Python |
| M11-29 | orchestration/0 | Refuse le fait de marche physique type pourtant admis par le contrat. | 1 échec(s), 26 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat2_c3_marche.py), comportement Python |
| M11-30 | orchestration/2 | Accepte une version de couverture en recul ou reecrite. | 2 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/orchestration/test_cat1_c2_marche.py), comportement Python |
| M11-31 | orchestration/3 | Decode les etats scelles sans verifier leur sceau. | 4 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat2_c3_marche.py), comportement Python |
| M11-32 | journal-rejeu/1b | Ignore la mise a jour qualifiee des horaires et tarifs du livre. | 3 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_rejeu/test_cat1_c1b_profil_courant.py), comportement Python |
| M11-33 | couture/S1-direct | Ne transmet aucun tick du flux physique au moteur London. | 5 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/points_entree/test_cat2_c2_defenses.py), comportement Python |
| M11-34 | couture/S7 | Transforme le code de succes de la vraie commande en echec de processus. | 3 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/points_entree/test_cat2_c3_reserve.py), comportement Python |
| M11-35 | frontiere/MQL5-D12 | Exporte les annonces LOW au lieu des HIGH. | 2 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat1_c4_source_mql5.py), contrôle de source MQL5 non compilée |
| M11-36 | couture/S6 | Retire les separateurs JSONL de la facade historique raccordee au writer physique. | 5 échec(s), 1 erreur(s) ; [cas de test](../../tests/robot/squelette/test_bout_en_bout.py), comportement Python |
| M11-37 | regression/P11-20-UTC-FLUX | Ignore le choix C04 UTC pour le flux alors que D12 est decale de deux heures. | 1 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat2_c3_courtier.py), comportement Python |
| M11-38 | regression/P11-20-UTC-DEFENSE | Ignore le choix C04 UTC pour la cotation de cloture et rend le tick frais artificiellement perime. | 1 échec(s), 0 erreur(s) ; [cas de test](../../tests/robot/london_infrastructure/test_cat2_c3_courtier.py), comportement Python |

### Livrables et limites

Les cartes strictes, contrats et journaux MCL décrivent les composants réels.
Les documents de traçabilité ont été alignés sur les unités construites et les
miroirs des skills régénérés depuis leur source canonique. La lecture d’expert
du document 05 complète la relecture, la skill externe n’étant pas disponible.
Le contrôle de publication porte aussi sur l’archive exacte de l’index, séparée
des quinze modifications initiales conservées hors commit.

Ces essais n’utilisent aucun SDK réel et ne qualifient ni terminal ni compte.
Les quatorze contrats physiques et la compilation MQL5 relèvent de 13.1 ; les
rapports synthétiques restent NON_VALIDE. Le service IA demeure la phase 12,
à construire seulement sur nouvelle demande, sans API réelle avant 13.6.

### Portabilité des fichiers à la clôture

Le contrôle de l’index a également détecté des espacements terminaux dans les
fiches 1c et 1d et dans trois tests de 1c et 1e. Les couches 1c, 1d et 1e ont
été défigées en correction, normalisées, puis revalidées et refigées dans cet
ordre. Chaque gate a rejoué les 1 403 tests et les 30/288 contrôles de ressources.
Les AST des tests et les caractères des fiches hors espacement sont conservés ;
aucun comportement, seuil ou coût n’a changé. Les cinq journaux MCL concernés
ont ensuite été enregistrés en LF : leurs préfixes JSON historiques sont
identiques, avec les neuf événements réels de défigeage, gate et gel ajoutés
au seul journal des points d’entrée. Les empreintes des contrats correspondent
aux nouveaux gels ; la campagne de mutations conserve sa cohorte originale et
l’archive exacte de publication vérifie la forme finale.

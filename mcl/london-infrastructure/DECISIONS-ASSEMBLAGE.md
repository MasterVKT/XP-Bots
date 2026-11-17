# Décisions physiques de phase 11

Les feuilles 0a à 0g, la session et les quatre adaptateurs ont leurs propres
gates et gels. Le transport 2d conserve les commandes avant émission, exige
la preuve du COMMIT natif et ne transforme jamais un accusé en remplissage.
Les remplissages viennent des transactions réellement observées. Les refus
de prix suivent la correction amont tracée de C08, sans entrée complémentaire
d'un partiel ni retransmission d'une commande inconnue.

L'enveloppe 3 compose les quatre instances réelles sur une seule session et
les mêmes liaisons. Ses callbacks sont les API publiques, sans accès privé
aux composants. Elle date les ticks après le retour du SDK ; la couverture
reste celle que 2b a prouvée. Les réceptions physiques C05 et A10 suivent la
même règle dans l'assemblage 4. Ni mtime ni redémarrage ne renouvellent la
fraîcheur d'un contenu identique.

La question d'indépendance MCL a identifié un verrou de processus comme
une feuille supplémentaire 0h, au lieu de le cacher dans 4. Il utilise les
primitives système non bloquantes, sans fichier O_EXCL à supprimer après un
crash. Ses trois tests de vrais processus passent, ainsi que son gate de
1 253 tests. Les imports msvcrt/fcntl sont déclarés pour cette feuille et
confinés à l'infrastructure par les gardes transverses.

L'assemblage tient un verrou commun pendant toute sa vie. Deux déploiements
ne peuvent pas posséder simultanément le même dossier FILE_COMMON, ce qui
évite deux coordinateurs indépendants sur le compte. Une fermeture bornée
avec un worker encore vivant conserve session, dépôt et verrou. Ce choix
sérialise également les terminaux qui partagent ce dossier ; la phase ne
fournit pas une supervision de plusieurs terminaux concurrents.

La portée financière native est persistante. En DEMO/REEL, un lien par
empreinte de compte fixe le déploiement et le chemin d'état. Un autre chemin,
une autre identité ou une base disparue refuse. L'identité SQLite inclut
aussi l'empreinte du compte attaché ; changer de compte ne recharge pas un
ancien livre. Aucun numéro de compte brut n'est stocké. Ces contrôles ne
remplacent pas la décision humaine de mise en service ni le rapprochement
C08. Une migration doit conserver les arrêts et les inconnus et être tracée
en H-12 ; le programme ne réinitialise pas automatiquement ces identités.

PAPER et PAPER_AB possèdent des livres fictifs indépendants de l'argent du
terminal ; ils ne revendiquent pas ce lien de propriété financière natif.
Leur dépôt reste lié à sa configuration, son mode, son code et sa source de
compte. Le vrai simulateur de phase 10 appartient à la coquille applicative,
pas à cet assemblage ; aucun second simulateur n'est construit ici.

Le service MQL5 est un producteur de fichiers externe au cœur. Sa structure
d'includes est contrôlée, ses sources et les fixtures D12 font partie du gel
4, et les vrais lecteurs Python confrontent leurs formats. Les durées C05
ne sont pas changées pour accepter un export. Le générateur de TSV de la
coquille doit inclure forward + max_age et la cadence d'export pour résoudre
P11-09. Compilation, comparaison aux fonctions natives, complétude S08 et
latence réelle S06 restent à qualifier explicitement en 13.1.

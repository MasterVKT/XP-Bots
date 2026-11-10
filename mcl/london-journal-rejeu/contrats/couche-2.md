# Couche 2 — exécuteur du rejeu sur le moteur unique

Unité : executeur_rejeu ; dépendances 0a/0b/1a/1b et composants métier figés.
La couche compose le vrai London par sa fabrique injectable, les bras C09, le
coordinateur, C05 et le lecteur IA. Elle ne recalcule aucune admission, bougie,
permission ou décision technique. Bibliothèque standard et entrées mémoire.

SourceTicks(manifeste, lire) conserve un ManifesteTicks et une fonction de lecture
de lignes ; sa construction ne lit rien. AutorisationReserve(option_expresse,
empreinte_robot, verifier_gel) contient un choix explicite, un SHA-256 et le port
externe d'attestation. Le SHA ne suffit pas : verifier_gel(empreinte) doit rendre
exactement True. RegistreReserve vérifie, avant lire et avant toute itération, si
l'intervalle demandé OU l'intervalle du manifeste recoupe le bloc réservé chargé
de 0b. Sans autorisation valide : refus tracé, aucun appel du lecteur. Une seule
ouverture par empreinte de robot est journalisée ; une empreinte changée est
refusée. Les autres expériences sous ce même gel sont des consultations tracées.
Le port physique de preuve du robot complet relève de la qualification future ;
les tests emploient une doublure de cette seule frontière externe.

DemandeRejeu identifie déploiement, BlocC10, scénario de coûts nommé de 0b,
mode REJEU ou PAPER_AB, longueur d'empreinte native, autorisation et écart éventuel.
Signature : DemandeRejeu(identifiant, bloc, scenario, mode, longueur_empreinte,
autorisation=None, ecart=None). ControlesRejeu(fondamental=None,
source_fondamentale=None, lecteur_ia=None, source_ia=None, scenario=None) et
ControlesRejeu.technique_neutre(configuration) exposent le point de composition.
StockageMemoireRejeu.persister(lot) confirme la révision exacte et les références.
La qualification synthétique n'est jamais présentée comme un historique courtier.
Un bloc entièrement inclus dans la période explorée du 01/05 au 03/11/2026 est
étiqueté DIAGNOSTIC malgré son nom fourni. Les blocs réservés et prospectifs sont
également classés par leurs dates, jamais par un nom fourni. Un continu conserve ses segments diagnostiques explicitement, avec
la date V3 du protocole. Les dates et scénarios sont fixés avant toute lecture.
Pour le bloc diagnostic autonome V3, les entrées commencent au plus tôt à la
date V3 du protocole ; son passé ne sert qu'au préchargement. Le continu garde
ses dates propres et annote séparément la portion déjà explorée.

appliquer_ecart(configuration, ecart, mode) accepte exactement l'un des six
triples de 0b et seulement REJEU : coefficient d'objectif sur les méthodes,
coefficient de buffer structurel, OU durée maximale. Une seule famille de
paramètres change ; l'export sur disque reste intact. La configuration dérivée
porte une nouvelle empreinte canonique, la demande et le journal conservent
l'empreinte d'origine et le triple explicite. Aucun réglage n'est sélectionné.

executer_experience(configuration, demande, source, conditions, fabriques=None,
fabrique_controles=None, registre_reserve=None, factures=()) construit un compte neuf au
capital configuré et un coordinateur par bras. Les fabriques par défaut sont le
vrai London ; des fabriques injectées permettent chaque méthode seule et leur
portefeuille commun sur UN compte. PAPER_AB partage les arrivées et les ticks,
avec deux livres indépendants, REFERENCE sans veto et IA avec lecteur réel.
fabrique_controles(premier_ms) fournit de nouvelles instances C05/IA, leurs
sources liées et, le cas échéant, TECHNICAL_CONTROL_NEUTRAL explicitement nommé.
Une expérience ne réutilise jamais des sources consommées ou un contrôle futur.
ControlesRejeu conserve ces cinq objets ; sa fabrique neutre nommée demande un
appel explicite. Les factures originales sont validées et conservées comme
poste économique distinct, sans débit implicite du livre natif. Elles restent
toutes disponibles au bilan de projet ; les rapports filtrent les coûts de
chaque expérience par ses bornes sans perdre les dépenses de recherche passées.

Les ticks antérieurs au début alimentent les vraies couches de préchargement ;
un adaptateur de stratégie remplace seulement leurs signaux par une absence
WARMUP canonique M15_INSUFFISANTES avec contexte prechargement=True, sans ordre.
Il ne transmet aucune donnée future. Un second exemplaire réel de la fabrique,
sans issues de positions/quotas, compte les configurations techniques brutes ;
ce compteur ne produit aucune commande. Les vrais signaux et refus restent
ceux de la stratégie et du coordinateur actifs. Les observations et premiers
remplissages donnent les entrées, y compris les positions encore ouvertes.

Les caractéristiques datées sont lues par le port de calcul au temps courant.
La grille technique de la fabrique reste celle de sa composition ; un changement
historique de tick_size incompatible avec cette grille fait échouer explicitement
l'expérience au précontrôle, sans appliquer au passé une grille actuelle. Les
autres caractéristiques et frais datés sont consommés causalement par le port.

piloter(ticks, moteur, executions, stockages=None, fin_exclusive_ms=None) conduit un MoteurDecision réel :
échéances sans tick, réponses natives sur les ticks bruts, transmission au moteur
des mêmes quotes stressées une seule fois, sorties de tous les bras avant entrées,
persistance puis confirmation de la révision exacte, envoi et rapprochement. Une
réponse qui change la révision annule la preuve précédente ; aucune boucle
alternative de décision ne survit dans S5. Les transports et stockages sont
distincts par bras, et les scénarios de coûts doivent être identiques entre bras.
Le résultat comprend journal canonique, réponses et journal d'entrées avec tous
les calculs initiaux et événementiels, rejouable par MoteurDecision.rejouer sans
backend courtier. Le stockage par défaut est une transaction mémoire explicite.
Avec une borne finale, les échéances sans tick continuent jusqu'à cette borne,
puis une observation terminale sans prix est journalisée. Le manifeste doit
englober la période demandée ; ses trous restent visibles et ne réduisent pas
les jours de fréquence. La couverture complète et l'absence de position ouverte
sont deux conditions distinctes du statut complet.

rejouer_experience(resultat, fabriques=None, fabrique_controles=None) reconstruit
les bras depuis leurs observations, profils et calculs initiaux archivés, puis
appelle le vrai MoteurDecision.rejouer pour chaque entrée. Les sept méthodes du
port backend lèvent si elles sont consultées. Aucun lecteur de prix n'est appelé.
Le résultat contient les enregistrements rejoués et les états finaux des bras.

Extension additive du 10/11/2026 pour le consommateur 3 : ResultatExperience
conserve conditions=(), une tuple de ConditionContrat classée par symbole et
dates, en plus de la provenance des prix et des réceptions archivées. Un rapport
ne peut déclarer deux coûts comparables sur la seule égalité de leurs noms
REFERENCE/STRESS ; les conditions effectives et connues doivent aussi concorder.
Le défaut vide conserve les constructeurs précédents et signifie preuve absente.

ResultatExperience et ResultatBrasRejeu sont des instantanés des trades, courbes,
premiers fills, configurations brutes, signaux, refus, états et arrêts persistants,
provenance, écart et journaux. Les instants sans quote ne créent aucun prix.
Les refus sont comptés par clé, instant et motif ; les tentatives de spread et
d'écart d'entrée refusées sont conservées en plus de l'issue terminale éventuelle.
Une position encore ouverte en fin de couverture est signalée INCOMPLET, jamais
liquidée au dernier prix pour améliorer un rapport. Les jours de fréquence sont
dérivés des horaires qualifiés, indépendamment des trous de collecte. jours porte
le panel commun de tous les symboles ; jours_forex conserve le dénominateur C09
des seuls EURUSD/GBPUSD, fournis par symboles_forex_c09(). Une entrée XAUUSD ne
peut remplir l'objectif de fréquence Forex. Le régime fondamental réel ou neutre
nommé est conservé séparément du scénario de coûts.

executer_blocs, executer_continu et executer_perturbations composent des
expériences distinctes. Les blocs repartent au capital initial ; le continu garde
un seul compte et ses arrêts pendant toute sa période. Le portefeuille combiné
est réellement coordonné, jamais obtenu par addition de comptes. Les six écarts
sont tous exécutés et rapportés, avec pertes et arrêts. La V1 absente est une
preuve manquante ; aucune série n'est fabriquée pour son remplacement.

Erreurs : ErreurRejeu pour source, gel, dates, mode, scénario, écart ou composition
incohérente ; refus du lecteur après un accès réservé invalide prouvé par compteur.
Tests propres : ouverture avant lecture, empreinte attestée, refus de changement,
diagnostic non renommable, dérivations exactes et capital non réinitialisé.
Jonctions : vrais London préchargés en été/hiver, référence/stress, A/B avec veto
archivé, préchargement sans ordre, fonds propres et arrêts, délais sans tick,
rejeu exact du journal sans backend, deux méthodes sur un compte et six écarts.

# Couche 2d — transport et observation natifs C08

Contrat finalisé avant code, le 13/11/2026, précisé sur fixtures le 14/11/2026, d'après le document 08 et les
contrats gelés 0a, 0b, 1, noyau et exécution. Aucun import latéral de 2a/2b/2c.
La carte doit préciser la dépendance réelle vers horloge avant installation.
Les décisions détaillées sont dans CONCEPTION-2D.md, sans modifier C06–C09.

## API

`ExecutionMT5(session, commun, table, liaisons, horloge, *, profil, preuve,
qualification_compte, preuve_compte, longueur_empreinte, max_taches_natives, depuis_utc_ms,
etat=None,convention_ticks='SERVEUR_S01')` reçoit les composants réels et des callbacks de profils/preuves
publics courants. HorlogeSysteme est la seule lecture d'heure physique.
preuve_compte fournit notamment l'exclusivité netting qualifiée. Le registre
est lié à une empreinte du compte réel (jamais son numéro brut) et au mode de
marge ; un changement de compte n'autorise pas la reprise des anciens tickets.
La preuve courante d'exclusivité netting doit être rapprochée après redémarrage
avant toute clôture d'une position nette. L'ordre des références du registre
est un compteur entier persistant, pas leur ordre lexical dans du JSON canonique.
Le position_id historique n'est pas supposé égal au ticket courant : conserver
leur liaison. Un changement ultérieur de ticket pour le même identifier natif
demande un rapprochement opérateur et bloque les nouvelles entrées ; le cœur
gelé ne réécrit pas rétroactivement le ticket de ses transactions déjà connues.
Un compte netting sans position ni ordre conserve l'exclusivité qualifiée pour
la première entrée ; toute position ou tout ordre courant non possédé la retire.

- `preparer_entrees(commandes, instant_ms) -> PreparationNative` enregistre
  uniquement des ENTREE, sans appel d'émission ni démarrage de tâche.
  PreparationNative expose revision et references, pas une fausse preuve.
- `autoriser_entrees(preuve: PreuvePersistance)` exige la révision et l'ensemble
  exact des références natives préparées, après le COMMIT du registre natif.
  Une répétition déjà autorisée est inerte ; une preuve étrangère/périmée refuse.
- `soumettre_defenses(commandes, instant_ms)` démarre TP/CLOTURE/ANNULATION
  immédiatement, indépendamment de la preuve de stockage. RAPPROCHEMENT,
  MINUTERIE et ALERTE ne sont jamais traduits en nouveaux ordres de marché.
- `collecter() -> ReceptionNative` date après extraction des résultats bruts et
  rend instant_ms, reponses et alertes, sans attendre une tâche bloquée.
- `observer(*, depuis_flux_ms=None) -> RapportObservationMT5` lit les faits natifs complets, date leur
  connaissance et rend observation (ou None si indisponible), base_utc, alertes.
  Les réponses de fills/protections/clôtures sont dans l'ObservationNative.
  depuis_flux_ms est le dernier instant public des gardes restaurées. Le
  rapport conserve les faits normalisés et leurs premières heures de
  connaissance ; une répétition identique garde sa référence et son heure.
  Les positions sont rapprochées par identifier natif vers leur ticket courant.
  Une lecture impossible conserve les intentions mais invalide la preuve
  monétaire courante et l'exclusivité netting ; elle rend observation=None.
- `proprietaire(ticket) -> PositionCompte | None` expose seulement la propriété
  rapprochée pour CalculsMT5. `flux_externe(instant_ms,solde)` rend un booléen seulement
  si l'état monétaire est connu ; un flux non neutralisé reste bloquant.
  Le solde réel différent du dernier solde rapproché bloque jusqu'à un nouveau
  rapprochement. La base et le pic sont neutralisés dans la vraie couche 1b,
  sur l'historique depuis le dernier état des gardes (depuis_flux_ms).
- `exporter_etat()` rend le registre durable sans threads, locks ni SDK ;
  `fermer(attente_ms) -> bool` attend de façon bornée et garde inconnue une
  émission non terminée. Le main ne bloque jamais sur order_send.

## Persistance, concurrence et reprises

Déduplication par référence pour toute la vie du déploiement. Une référence
répétée avec autre contenu est invalide. Une clé ne peut avoir deux entrées
actives. Une autre référence ENTREE de cette clé est permise exclusivement
après un refus de prix non permanent, explicite et sans fill ; conserver les
anciennes références. None, timeout, connexion et code inconnu n'autorisent
aucun renvoi. Refus permanent et remplissage interdisent aussi un complément.

Le cœur confirme d'abord sa propre persistance ; la coquille prépare le registre
natif, le joint à la transaction physique du checkpoint après confirmation,
puis construit la preuve native sur ce COMMIT réel. Aucun SDK order_send avant
ce dernier succès. Défenses immédiates même si le stockage échoue.

Tâches natives daemon bornées par le réglage explicite max_taches_natives ;
ne pas mettre une défense derrière une entrée bloquée dans une unique file
séquentielle. Saturation/échec de tâche = alerte et état conservateur, sans
accusé de succès.
La capacité doit dépasser une tâche et la dernière place reste réservée aux
défenses : une entrée supplémentaire est refusée localement avant émission.
Contrôler le TTL réel avant et après le contrôle natif ; une
entrée expirée n'est jamais envoyée. Un échec local de transport connu avant
émission est un refus d'environnement identifié, pas un code natif fabriqué.

La reprise d'une entrée préparée/en cours persistée est inconnue, jamais
retransmise. Les preuves positives de transactions/positions/ordres reprennent
le cycle réel. Une tâche inconnue du processus précédent n'acquiert pas par
redémarrage une preuve de terminaison ; une absence vide ne l'efface pas.

## Requêtes et classement

ENTREE : requête exacte protégée DEAL, symbole, type BUY/SELL, volume, price,
SL/TP ensemble, deviation_points, filling qualifié, GTC, magic/comment D08.
Recontrôler l'identité par identifier_courtier et la limite de commentaire.
TP : SLTP du ticket possédé, SL inchangé. CLOTURE : volume effectivement possédé,
sens opposé et Bid/Ask natif frais ; filling qualifié et identité de l'intention.
ANNULATION : REMOVE du seul reliquat identifié. Pas de clôture d'un tiers.
Un profil courant non disponible n'empêche pas par principe une défense : le
profil qualifié conservé de l'entrée peut servir à fermer le ticket possédé ;
une cotation illisible ou périmée reste toutefois un fait inconnu, jamais
une heure inventée. Le time_msc de symbol_info_tick suit `convention_ticks`,
UTC ou SERVEUR_S01, qualifiée explicitement pour le flux SDK. Le défaut S01
conserve les appelants existants ; le courtier fournit le choix C04 obligatoire.
La signature de reprise engage cette convention (P11-20). order_check avec la
requête exacte avant chaque order_send.

Les retcodes du SDK sont comparés aux constantes de l'objet injecté, pas à des
nombres recopiés. DONE, DONE_PARTIAL et PLACED donnent seulement ACK ACCEPTE.
Les quatre refus de prix de §2.6 donnent REFUSE/definitif=False. Refus connus de
volume, risque et droits : REFUSE/definitif=True. TIMEOUT/CONNECTION, None,
exception après émission, autre code : INCONNU. Un précontrôle refusé n'envoie
rien ; conserver son code et la certitude d'absence d'émission. Le cœur demeure
l'unique responsable des issues, quotas, retries et échéances.

## Faits observés

positions_get et orders_get de tout le compte, puis history_orders_get et
history_deals_get sur la couverture demandée ; account_info brut cohérent.
Pas de test de vérité d'un tableau, pas de None assimilé à une liste vide.
Les historiques utilisent datetime aware UTC, convertis par la table S01.
Toute heure d'exécution future ou hors table invalide le fait. Une lecture
incomplète interdit les preuves d'absence et la reconstitution de base.
Les états terminaux des ordres historiques exigent aussi une heure de fin
native causale. Deux relevés des positions et ordres encadrent l'historique,
et le solde et la marge doivent rester identiques pendant cette lecture.
S08 doit qualifier la complétude de ce relevé à sa réception ; une fixture
ne prouve pas l'atomicité ou la latence de publication du terminal réel.
Après le premier relevé, le changement de solde doit être exactement expliqué
par les nouveaux mouvements et corrections de frais ; sinon le compte reste
bloqué. Un capital déjà neutralisé dont le montant est corrigé exige une
décision de traitement explicite. Les faits non qualifiés lus sont conservés
dans transactions_lues ; ils n'autorisent ni attribution ni entrée.

Appartenance : intention enregistrée + identité D08 exacte + symbole + vrais
tickets/position_id rapprochés. Jamais le symbole ou magic seuls. Tous les
tiers restent externes. Netting : preuve d'exclusivité et absence de contribution
étrangère nécessaires ; sinon le vrai C08 conserve verrou et refus.

Regrouper les vrais deals d'entrée : volume cumulé, moyenne pondérée, première
exécution, frais commission+fee réellement connus, volume courant et SL/TP
natifs. Une correction tardive de frais est une version du même deal, sans
second quota. Références stables par contenu, sans réémission à chaque poll.
Un reliquat n'est annulé que par preuve des ordres courants et de l'état
terminal de l'ordre historique, ou par exécution de tout le volume demandé.
Un partiel ne déclenche jamais d'entrée complémentaire.

Les deals de sortie prouvent les fermetures partielles/totales : cause SL/TP
native, ou cause de la commande CLOTURE correspondante. Une intervention non
classable dans l'énumération publique alerte et bloque le rapprochement ; ne
pas inventer un motif ni une cause. Les faits sont conservés pour l'opérateur.

Une PreuveAbsence exige quatre lectures complètes concordantes, historique
S08 qualifié, aucune trace attribuable et terminaison d'envoi établie ; le
cycle vérifie sa fenêtre temporelle. Aucun silence ne devient un rejet.

ObservationNative contient un EtatCompte brut sans positions attribuées et
sépare positions, ordres, réponses et preuves. Utiliser MouvementCompte et
reconstituer_base_utc réels pour le solde, sans refaire le drawdown. Dépôts et
retraits identifiés restent des flux externes signés ; les commissions ne sont
pas neutralisées comme du capital. Un effet monétaire non qualifié, une preuve
de minuit absente ou un flux non neutralisé bloque ENVIRONMENT_NOT_READY ;
aucun redémarrage ou changement de date ne l'efface silencieusement.

## Tests et limites

Catégorie 1 : requêtes et précheck exacts, preuve/duplication, codes/None,
timeout et ACK tardif, seconde référence après prix seulement, SDK bloqué et
défense, partiels/reliquat, frais/protections, autres propriétaires, reprise et
absence positive contre historique incomplet. Catégorie 2 : vrais coordinateur
0→6 et moteur, une seule issue/quota, inconnu sans doublon, compte et journal
rejouables. Le faux SDK est la seule doublure de courtier.

Contrat physique 13.1 ignoré par défaut : observation du compte démo et
comparaison réelle des champs/tickets/SL/TP, en lecture seule. Pas d'envoi
d'ordre automatique de la suite ; les sondes réelles S02/S03/S04/S06 restent
des actions humaines tracées de 13.1. La concurrence/latence du SDK et la
complétude S08 ne sont pas qualifiées par des fixtures.

# Couche 2 — État des permissions

Statut : finalisé avant code, 09/11/2026 ; 0 et 1a figées. C05 et document 01 §2.1.

`RegistrePermissions(commun, etat=None)` conserve l'historique causal des permissions acceptées et
des interruptions explicitement signalées, la dernière séquence par symbole, les curseurs heartbeat
et le temps logique observé. EtatPermissions, PermissionRecue, InterruptionPermission, SuiviHeartbeat,
ConsultationPermission, ReceptionPermission et EvenementSuivi sont des valeurs immuables exportables.
Une PermissionRecue conserve le vrai MessagePermission et la réception locale distincte de known_at.

`recevoir(symbole, octets, reception_ms) -> ReceptionPermission` emploie le vrai validateur 1a. La
réception est le temps logique du nouvel événement et ne recule pas. Une séquence supérieure valide
remplace la permission courante ; une séquence inférieure ou réécrite est rejetée sans changement de
permission. Une relecture identique est ignorée, même après expiration : l'identité est comparée dans
le contexte de réception original déjà validé, sans renouveler la validité ni résoudre une interruption.
Une nouvelle donnée invalide est rejetée et ne détruit pas le dernier message encore valide (D-11).

`interrompre(symbole, instant_ms)` marque une interruption non résolue. Une nouvelle permission de
séquence supérieure la résout ; une simple relecture ne la résout pas. L'interruption n'est jamais
déduite d'un heartbeat manqué ou d'un fichier invalide : ces deux événements ont leurs règles propres.

`consulter(symbole, instant_ms) -> ConsultationPermission` utilise seulement les événements reçus
au plus tard à l'instant demandé. Elle porte la dernière PermissionRecue éventuelle et un détail
ABSENTE, INTERRUPTION ou PERIMEE, ou aucun détail si elle est utilisable. Un état de risque ou une
direction n'est pas transformé ici en décision : c'est la responsabilité de 3. La fin de validité est
exclusive et aucun message futur ne devient disponible par restauration ou interrogation historique.

`avancer(instant_ms) -> tuple[EvenementSuivi,...]` est monotone et idempotent au même instant. Le
heartbeat est attendu à issued_at + fundamental_expected_heartbeat_seconds puis à sa cadence chargée.
Chaque minute attendue sans nouvelle permission est journalisée ; un saut de temps regroupe les
échéances manquées dans un événement portant le nombre, la première échéance et l'instant réel de
détection. Le suivi s'arrête à l'expiration exclusive. Une expiration franchie donne aussi un événement
unique. Le message reste utilisable avant expiration malgré une alerte heartbeat.

Les nouvelles réceptions d'un même instant sont traitées avant avancer, afin qu'un heartbeat valide
arrivant exactement à son échéance ne soit pas déclaré manqué. L'appelant pilote ce temps logique ;
aucune horloge n'est consultée. `prochaine_echeance_ms(instant_ms)` rend la première échéance non
consommée (heartbeat ou expiration), ramenée à maintenant si elle est déjà due.

`etat` restitue l'intégralité des valeurs de reprise. L'import revalide tous les messages à leur
réception originale, l'ordre des événements, les séquences et les curseurs de heartbeat ; aucun
curseur ne peut supprimer une alerte non encore échue ou appartenir à une ancienne séquence.
Les appels mal typés, les reculs de temps et les états incohérents lèvent ErreurFondamental.
Les rejets de données externes rendent ReceptionPermission rejetée avec leur raison, sans ANY/ALLOW.

Tests : C11.8, durée exclusive, relecture expirée, recul et réécriture, interruption, heartbeat exact,
saut de temps, reprise sans renouvellement, export immuable et décisions historiques par préfixe.

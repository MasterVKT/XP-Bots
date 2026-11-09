# Couche 1b — Garde d'annonces

Statut : finalisé avant code, 09/11/2026 ; couche 0 figée. C05, D-12, document 08 §4.1.
Défigeage correction le même jour : retrait d’une ligne blanche finale du test, AST identique ; aucune signature ni règle modifiée.

`GardeAnnonces(commun, convertir_serveur, etat=None)` est un objet pur. La fonction externe
convertir_serveur(texte_natif) rend un instant UTC qualifié, ou lève une exception ; aucune conversion
implicite, heure locale du poste ou déduction d'un décalage constant. La table d'importance externe
est fournie à chaque réception sous forme de TableImportance versionnée.

`recevoir(octets, reception_ms, table) -> ReceptionCalendrier` valide les sept clés exactes de
xp-export-calendrier-v1 et les dix champs exacts par événement du document 08. Les heures natives
sont `AAAA.MM.JJ HH:MM:SS` ; export_gmt est interprété en UTC, et doit correspondre à la conversion
d'export_serveur. Les annonces portent l'importance haute explicitement reconnue par la table.
La réception ne précède pas l'export ; la couverture est un intervalle positif, les annonces y sont
contenues. Une couverture trop courte reste une information exploitable pour une clôture HIGH,
mais ne rend jamais le calendrier admissible pour une entrée.

Les versions sont strictement croissantes, sans obligation de continuité. Une relecture identique
de la même version est ignorée sans rafraîchir la connaissance ; version en recul ou réécrite,
format invalide ou conversion indisponible : rejet sans mutation de l'état valide. ReceptionCalendrier
porte acceptee, ignoree, raison et la version acceptée ou relue. Il ne produit aucune permission.

`etat -> EtatCalendrier(versions)` conserve toutes les versions immuables. Reprise : versions,
réceptions et exports ordonnés ; chaque known_at correspond exactement à sa première lecture ou
à la lecture d'un changement de contenu natif/UTC. Une table d'un autre fournisseur renouvelle la
connaissance ; un événement inchangé conserve sa première connaissance. Les historiques altérés
sont refusés. Une nouvelle version n'efface jamais une version antérieure.

`version_connue(instant_ms)` rend seulement la dernière version reçue au plus tard à cet instant.
`evaluer(symbole, instant_ms) -> DecisionFondamentale` applique les devises C05 et la fenêtre
[N−news_before_seconds, N+news_after_seconds). Annonce HIGH active : NEWS_WINDOW/ANNONCE_HIGH avec
clôture obligatoire, même si le calendrier est par ailleurs périmé ou insuffisant. Sans annonce active,
calendrier absent ou âgé de plus de news_calendar_max_age_seconds (export ou réception) :
NEWS_WINDOW/CALENDRIER_PERIME ; couverture ne contenant pas maintenant ou fin < maintenant +
news_forward_coverage_seconds : NEWS_WINDOW/COUVERTURE_INSUFFISANTE. Ces deux seuls défauts
ne demandent aucune liquidation. Les égalités de fraîcheur et de couverture sont admises.

`prochaine_echeance_ms(instant_ms)` rend la première borne future connue : début/fin de fenêtre,
perte de fraîcheur ou de couverture ; jamais de faux tick ou de temps système. Les décisions
historiques restent celles des versions alors reçues. ErreurFondamental pour un appel mal typé ou
un état incohérent ; une donnée externe invalide donne un résultat rejeté. Tests : bornes exactes,
trois symboles, annonce tardive, révision et relecture, reprise et causalité par préfixe.

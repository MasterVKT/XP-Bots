# Couche 1a — Validation d'une permission

Statut : finalisé avant code le 09/11/2026 ; couche 0 figée. C05 et D-11.

`decoder_message(octets, symbole_attendu, reception_ms, instant_ms, commun) -> MessagePermission`
valide l'objet UTF-8 strict aux onze clés exactes du schéma `fundamental-permission-v1`.
Les quatre heures sont obligatoirement ISO-8601 UTC avec trois décimales et suffixe Z. Le symbole
doit correspondre à la source attendue et appartenir à l'univers chargé. Séquence entière positive,
énumérations et identifiants non vides ; booléens, champs ajoutés ou manquants sont refusés.

`valider_message(message, reception_ms, instant_ms, commun) -> MessagePermission` valide aussi un
message déjà typé pour la restauration et les consommateurs réels. Aucun état n'est modifié.
`commun` est l'objet ParametresCommuns chargé ; aucune durée figée n'est recopiée.

Ordre exigé : issued_at ≤ known_at ≤ réception ≤ maintenant, issued_at ≤ valid_from ≤ maintenant
< valid_until. La durée valid_until−issued_at est strictement positive et au plus
fundamental_max_validity_seconds. La tolérance future chargée est appliquée aux heures de connaissance
et de début ; l'heure de fin est une échéance et peut être future. Une réception future est refusée.
La fin de validité est exclusive ; la borne maximale de durée est inclusive.

`ErreurPermission(ErreurFondamental)` porte `detail` INVALIDE ou PERIMEE, à traduire en C09 par
l'enveloppe. Un octet, type, schéma, symbole ou ordre temporel invalide donne INVALIDE ; une échéance
déjà atteinte, sur un message autrement cohérent, donne PERIMEE. La réception est rendue séparément
par les couches d'état ; elle ne remplace jamais known_at. Le rejet ne vaut pas ANY/ALLOW.

La monotonie de séquence, le maintien du dernier message, heartbeat et interruptions appartiennent
à 2. Le validateur ne lit aucun fichier ou horloge. Tests catégorie 1 : chaque condition et ses bornes ;
catégorie 2 : décodage et configuration réels, précision UTC et conservation du message.

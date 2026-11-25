# Couche 1b — validation des sorties

Statut : contrat finalisé le 17/11/2026 après gel de 0, avant code.
Consommateurs cartographiés : veto 2a et routeur 2b.
Dépend de : types 0 réels et gelés ; aucune dépendance vers les autres unités 1.

Unité : validation.
Responsabilité : accepter seulement une extraction ou une note conforme aux ressources IA et aux preuves réellement fournies.
Signature : valider_extraction(ressources,sortie,item) -> dict ;
valider_note(ressources,sortie,kind,evidence_ids) -> dict.
Entrée : sortie textuelle UTF-8, ressources chargées, item avec item_id et
provided_text textuels, kind BRIEFING/JOURNAL/WEEKLY_REVIEW et IDs de preuve
effectivement fournis ; aucun recours à un texte intégral non transmis.
Sortie : nouvel objet JSON strict, inchangé dans ses valeurs, conforme au
schéma exporté et aux plafonds lus dans la configuration IA.
Effets de bord : aucun ; aucune réparation ou seconde inférence.
Erreurs, exceptions : ErreurService pour sortie trop longue, JSON invalide,
doublons, non-finis, clé absente ou supplémentaire, type/enum incorrect,
item_id étranger, citation trop longue ou inventée, note hors bornes et preuve
non fournie. Les erreurs sont statiques, sans recopie du texte reçu.

## Spécification exécutable

test_cat1_c1b_validation.py couvre toutes les classes de refus, les bornes
exactes en octets et caractères, les citations et les notes sourcées.
test_cat2_c1b_validation.py compare les résultats et refus à parse_model_output
et parse_advisory_output sur les ressources et documents réels de la couche 0.

## Comportements documentés

Les clés requises, enums et versions sont celles des schémas exportés ; les
limites complémentaires A05/A11 proviennent de l’export IA. Une citation vide
peut être conforme au schéma d’extraction mais ne permet aucun veto A06.
Une extraction historique ou conditionnelle peut aussi être JSON valide ;
le constructeur A06 contrôle son admissibilité. Le validateur ne prétend pas
comprendre une négation mal classée par le modèle : cette compétence relève
de la qualification humaine A13. Il n’invente aucune heuristique linguistique.
Les notes gardent leur kind exact. Chaque observation cite une à la limite
exportée d’IDs connus ; les listes et textes ont leurs plafonds propres.
Un briefing n’a aucune hypothèse. La validation n’accorde jamais une permission,
ne produit aucun ordre et n’insère aucune note dans un snapshot exécutoire.

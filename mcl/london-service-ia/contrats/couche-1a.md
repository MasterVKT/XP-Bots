# Couche 1a — borne des tokens

Statut : contrat finalisé le 17/11/2026, après gel de 0 et avant code.
Consommateurs cartographiés : routeur 2b.
Dépend de : types 0 réels et gelés.

Unité : tokens.
Responsabilité : admettre seulement une requête complète dont la borne conservatrice tient dans l’export IA.
Signature : compter_entree(ressources,corps), preparer_requete(ressources,dossier,
construire,*,reduire_documents=False) -> RequeteBornee | None ;
RequeteBornee(requete,dossier,tokens_entree,documents_retires=()).
Entrée : ressources chargées, corps sérialisé en octets UTF-8, dossier JSON
strict et constructeur pur qui incorpore prompt, schéma et enveloppe API.
Sortie : borne égale au nombre d’octets du corps réellement envoyé, augmenté
de input_count_fallback_utf8_overhead_tokens ; admission inclusive à
max_input_tokens_upper_bound. Le résultat conserve le dossier effectivement
transmis et les IDs des documents retirés.
Effets de bord : aucun ; le constructeur est un port de fonction pure, sans
client HTTP, tokenizer local, horloge ou stockage.
Erreurs, exceptions : ErreurService pour type, JSON, UTF-8, ressources ou
constructeur hors contrat ; None si aucun dossier admissible ne tient.

## Spécification exécutable

test_cat1_c1a_tokens.py couvre les bornes exactes, UTF-8, le corps complet,
refus d’un texte trop long et réduction par documents entiers.
test_cat2_c1a_tokens.py traverse types et ressources réels et compare
token_input_upper_bound de la référence sur les corps réellement construits.

## Comportements documentés

Le compteur officiel n’étant pas disponible en bibliothèque standard, le
fallback conservateur A09 est utilisé. Le corps comprend le prompt, le schéma,
les données et l’enveloppe ; aucun secret n’entre dans ce corps. Cette unité
ne s’autorise aucune approximation par caractères ou mots. Le texte d’une
extraction n’est jamais tronqué : une négation ou condition peut se trouver
n’importe où dans ce texte. S’il ne tient pas intégralement, le résultat est
None et aucun appel n’est admissible pour ce dossier. Pour une note, le mode
explicite de réduction retire les derniers documents complets de la liste
documents, fournie en ordre de priorité par le planificateur. Le contenu d’un
document conservé est inchangé ; le routeur n’autorise ensuite que les IDs
effectivement transmis comme preuves. Un dossier portant provided_text ne
peut pas emprunter ce chemin de réduction. Les ressources et l’entrée restent
inchangées. La préparation ne lance jamais le transport.

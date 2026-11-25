# Couche 1e — fournisseurs

Statut : contrat finalisé le 17/11/2026 après gel de 0 et avant code.
Consommateurs cartographiés : routeur.
Dépend de : types.

Unité : fournisseurs.
Responsabilité : Construire les requêtes A08 et décoder leurs réponses sans transport implicite.
Signature : construire_requete(ressources,job,fournisseur,dossier=None) -> RequeteHTTP ;
decoder_reponse(ressources,fournisseur,reponse) -> RetourFournisseur(texte,
usage_brut,tokens_entree,tokens_sortie,modele_recu=None) ;
extraire_usage(ressources,fournisseur,reponse) -> UsageFournisseur(usage_brut,
tokens_entree,tokens_sortie,modele_recu=None).
Entrée : ressources et job réels, fournisseur allowlisté, dossier JSON strict
et réponse HTTP bornée en octets ; aucun secret ou SDK.
Sortie : enveloppe A08 exacte, prompt et schéma exportés ; texte final inchangé,
usage brut canonique et compteurs connus ou None. La propriété usage en rend une copie.
Effets de bord : aucun transport, fichier, base ni attente ; RequeteHTTP ne
porte que les en-têtes publics. Le transport 4 ajoutera seul l’authentification.
Erreurs, exceptions : ErreurService pour fournisseur inconnu, dossier ou
réponse invalide, taille, refus, troncature, outil ou statut non terminé.

## Spécification exécutable

test_cat1_c1e_fournisseurs.py confronte les trois requêtes aux gabarits A08,
les réponses et usages aux formes documentées, puis les classes de refus.
test_cat2_c1e_fournisseurs.py traverse job, ressources, corps et réponses réels,
avec extraction et notes ; aucun ouvreur réseau n’est utilisé.

## Comportements documentés

Le modèle, l’endpoint, les paramètres de raisonnement et les plafonds viennent
de l’export. Les messages/input sont de vraies listes ; les schémas sont des
objets, avec strict=true quand le gabarit l’impose. Aucun outil ni stockage
payant de prompt n’est activé. L’extraction contient exactement item_id,
title, issuer et provided_text, sans portefeuille ou signal ajouté par le code.
Les notes reçoivent seulement le dossier informatif anonymisé du producteur.

Groq exige finish_reason=stop et prend message.content ; Gemini exige STOP
sans blocage et concatène les parts textuelles non thought ; OpenAI exige
completed et parcourt les blocs output_text de tous les messages, sans
supposer que le premier bloc contient le texte. Refus et appels d’outil sont
inutilisables. Les traces de raisonnement ne deviennent jamais une sortie.
Les sorties restent soumises à 1b, sans réparation.

Une métrique absente, non entière, négative ou incohérente reste inconnue,
jamais zéro. Gemini calcule sortie totale=totalTokenCount−promptTokenCount.
OpenAI utilise output_tokens sans ajouter reasoning_tokens ; Groq utilise
prompt_tokens/completion_tokens. L’usage brut conserve ses détails, sans
double comptage. Le modèle reçu est conservé lorsqu’il est fourni. Les tests
factices ne qualifient aucun backend réel ; leurs contrats physiques sont en 4.

Le lecteur d’usage indépendant est précisé avant son implémentation pour le
consommateur 2b : il peut rapprocher une réponse tronquée, refusée ou hors
schéma lorsque ses métriques sont présentes, sans valider le texte pour veto.
Ce lecteur n’exige pas le succès HTTP ou le finish_reason ; il exige seulement
un corps HTTP borné et JSON strict. Le décodeur exécutoire reste plus strict.

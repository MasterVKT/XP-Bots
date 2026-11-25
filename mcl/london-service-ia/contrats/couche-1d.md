# Couche 1d — budget partagé et réservations

Statut : contrat finalisé le 17/11/2026 après gel de 0 et avant code.
Consommateurs cartographiés : routeur 2b ; tests physiques de la coquille 4.
Dépend de : types 0 ; stockage et transaction sont des ports externes.

Unité : budget.
Responsabilité : réserver avant chaque tentative, puis rapprocher sans double débit les coûts et quotas A09 partagés.
Signature : cout_maximal(ressources,entree=None,sortie=None),
budget_admet(ressources,depense,reserve,prochain,autres='0',taxes='0'),
ProfilRoute(fournisseur,modele,profil_facturation,quota_tokens_minute,
quota_requetes_minute,quota_requetes_jour,quota_tokens_jour,verifie_ms,
gratuit_confirme=False,projet_dedie=False,cle_disponible=False,
prix_entree=None,prix_sortie=None), ReservationAPI et DecisionBudget ;
RegistreBudget(ressources,depot).reserver(job,profil,entree_bornee,instant_ms,
*,paiement_autorise=False), rapprocher(tentative_id,tokens_entree,tokens_sortie,
usage_brut,instant_ms), signaler_echec(fournisseur,instant_ms,statut=None,
retry_after_ms=0), provisionner(mois,autres,taxes), consulter(mois) et etat_route(fournisseur).
Entrée : ressources, job et profil explicites, montants décimaux finis non
négatifs, tokens entiers et horodatages UTC ; aucun secret.
Sortie : admission avec réservation immuable ou raison de refus opérationnelle ;
rapprochement et consultations en copies de données JSON, montants en chaînes Decimal.
Effets de bord : une transaction injectée atomique par opération ; aucun SQLite,
HTTP, fichier ou temps physique dans cette unité. La vraie base est en 4.
Erreurs, exceptions : ErreurService pour donnée invalide. Profil incomplet,
route désactivée, quota, prix, temps ou budget inadmissible donnent un refus,
sans appel ni débit. Les raisons du service n’ajoutent aucun motif C09.

## Spécification exécutable

test_cat1_c1d_budget.py vérifie les bornes, quotas, profils, dates, réserves
inconnues, rapprochements et idempotence avec une transaction externe en mémoire.
test_cat2_c1d_budget.py compare cout_maximal et budget_admet aux oracles et
traverse les vrais types/job/ressources. La concurrence SQLite relève de 4.

## Comportements documentés

Les plafonds viennent de l’export IA. Les coûts utilisent Decimal et le profil
payant exporté, sans remise de cache. La route payante est désactivée par défaut,
exige projet dédié, revue de prix encore valide, mêmes modèle/prix et provisions
globales explicites ; une provision déclarée nulle peut être enregistrée.
Une route gratuite exige une confirmation de gratuité et de quotas effectifs ;
un projet Gemini payant n’est jamais traité comme gratuit. Une clé n’est décrite
que par sa disponibilité booléenne et reste exclusivement dans le transport.

Chaque réservation compte une tentative et tous ses tokens, même en échec.
EXTRACTION compte aussi dans le sous-plafond événementiel ; GOLDEN et notes
comptent dans les plafonds communs. Les quotas quotidiens sont UTC. Les quotas
effectifs du fournisseur sont bornés avec la fraction de sécurité exportée ;
le débit de requêtes est espacé, sans multiplier les clés. La transaction
écrit compteurs, état de route, tentative et budget avant tout transport ; elle
n’est pas conservée pendant HTTP. Une identité job/fournisseur ne se réserve
qu’une fois, y compris après redémarrage. Des tentatives inconnues gardent leur
réserve maximale ; aucun usage absent n’est assimilé à un coût nul.

Le rapprochement débite et libère seulement sa propre réserve, dans le mois
de la tentative d’origine. Il est idempotent. Une consommation supérieure à
l’enveloppe désactive la route et conserve l’usage réel pour investigation ;
un second rapprochement contradictoire ne déclenche jamais un second débit.
401/403 désactivent la route ; Retry-After ne raccourcit aucun espacement.
Les états utilisent api_budget, api_attempts, schedule_state et provider_state,
avec clés quota:jour, quota:fournisseur:jour et route:fournisseur. Ces états
sont partagés entre méthodes, notes et tests de modèle, sans compteur par robot.

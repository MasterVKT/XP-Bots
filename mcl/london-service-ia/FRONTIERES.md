# Frontières du service IA

Les contrats A04–A12 et le document 08 sont l’autorité. Le port HTTP reçoit
une requête immuable avec URL HTTPS, méthode, en-têtes, corps hors secret,
timeout et plafond ; il rend statut, en-têtes, corps borné et réception UTC.
La clé est fournie séparément à la coquille et ne rejoint aucune archive.
L’ouvreur factice reproduit exactement cette frontière, y compris erreurs,
redirections, refus, quotas, réponses tronquées et dépassements. La coquille
désactive les redirections implicites ; le collecteur contrôle chaque cible.

Le port transaction exécute une fonction sur les tables IA dans une seule
transaction exclusive ; succès valide tout, exception annule tout. La doublure
en mémoire copie l’état à l’entrée et ne publie qu’au succès. SQLite en couche
4 emploie BEGIN IMMEDIATE, des décimaux sérialisés comme chaînes et les tables
A10. Un coût inconnu conserve sa réserve ; une tentative interrompue ne devient
jamais une nouvelle tentative gratuite au redémarrage.

Le port de publication reçoit exclusivement les octets d’un snapshot validé.
L’implémentation réutilise ecrire_atomique de l’infrastructure : temporaire sur
le même volume, flush, fsync, remplacement. Les reprises Windows suivent les
délais de l’export IA ; le dernier fichier reste intact en cas d’échec. Le
numéro est réservé durablement avant publication et peut donc présenter des
trous, jamais reculer. L’horloge UTC et l’attente sont injectées ; les essais
emploient une horloge manuelle. La coquille réutilise HorlogeSysteme.

Le calendrier est reçu en octets D12 avec heure de réception et convertisseur
serveur qualifié fourni par l’appelant. GardeAnnonces valide le document ; une
table versionnée explicite associe les identifiants natifs à issuer et type
normalisé. Aucun classement n’est déduit par le LLM ou par le nom de l’annonce.
Les contrats physiques API/RSS restent ignorés sans XPBOTS_CONTRATS_API=1 et
autorisation humaine préalable en 13.6 ; aucun test courant ne les appelle.

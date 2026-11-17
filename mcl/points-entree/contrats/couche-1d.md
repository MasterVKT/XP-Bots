# Couche 1d — commande de qualification C04 (finalisé avant code)

`qualifier(application, infrastructure, table, qualification)` reçoit une
ConfigurationApplication validée pour qualification, une InfrastructurePhysique
réelle fraîchement ouverte par l'enveloppe, la table S01 réelle et la preuve C04
externe. La commande initialise le courtier en lecture seule, reçoit les exports
D12, relit le compte et chaque profil et produit un rapport pur. L'enveloppe
possède la durée de vie des ressources et écrit le rapport par l'infrastructure.
Le SDK n'est jamais importé par la commande et aucune commande d'ordre n'est
préparée, autorisée ou soumise, quel que soit le mode du registre.

Le rapport contient l'instant, les versions du paquet et du terminal, le serveur,
le type de compte déclaré par la session, la qualification canonique du compte,
les liaisons, les profils C04 et leurs horaires, la liste ENVIRONMENT_NOT_READY
et les preuves manquantes. Les champs sont sélectionnés explicitement ; aucun
objet natif brut, numéro de compte, login, solde, secret ou chemin privé n'est
sérialisé. Les refus de qualification conservent des codes statiques.

Les résultats des sondes sont distingués : constats réellement lus, preuves
externes déclarées et confrontations à exécuter en 13.1. Une sonde d'ordre non
exécutée n'est jamais marquée réussie. Sans signal C06 et distance de stop datés,
le risque du volume minimal est NON_EVALUABLE_SANS_SIGNAL ; aucun ATR ni stop
n'est inventé. Ce rapport ne donne aucun verdict C10/A13 ni autorisation native.
Les types de compte DEMO/REEL restent gardés par SessionMT5 à l'attachement.

Catégorie 1 : structure et absence des champs sensibles, preuve expirée et
exports invalides, statuts de sondes honnêtes. Catégorie 2 : vrai assemblage,
specifications/calculs réels, FauxMT5 et CommonFiles temporaires ; aucun
order_send/order_check, aucune modification du portefeuille ou de l'état durable.

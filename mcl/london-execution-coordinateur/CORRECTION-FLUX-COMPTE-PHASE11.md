# Neutralisation des flux de compte connus — phase 11

Le 13/11/2026, le consommateur physique révèle un défaut du contrat C07 déjà
exprimé dans la fiche 1b : une base reconstituée qualifiée en cours de journée
n'est pas appliquée aux bases et au pic de la garde courante. L'API manuelle
neutraliser_flux existe, mais le moteur unique ne l'expose pas à la coquille ;
la coquille ne doit ni lire ses champs privés ni refaire le risque.

L'essai synthétique de preuve est conservé dans le rapport local
`phase11_flux_qualifie_ignore.json` : sur base 100, apport identifié 100,
base reconstituée 200 mais base retenue 100 ; l'équité 196 n'active pas le seuil
quotidien pourtant inclusif. Un retrait connu crée aussi une fausse baisse.

Décision : défigeage formel 1b de nature modification, avant tout changement
actif ; tests propres et de jonction RED, puis correction dans GardesCompte.
Consommer une seule fois les références des flux de la BaseReconstituee
qualifiée du même instant. Préserver le verrou quotidien et l'arrêt global.
Une borne optionnelle de reconstitution transporte aussi les flux antérieurs
à minuit, survenus pendant l'interruption ; la base du nouveau jour ne les
compte pas une deuxième fois, mais le pic antérieur est bien translaté.
Les seuils de C07 et les exports normatifs restent identiques.

La sonde complète vérifie également le pic de solde connu pendant une
interruption : 100→120→108 doit activer la baisse globale de 10 %, dans le même
jour, à minuit et le jour suivant. Le pic historique était aussi ignoré dans
ces chemins. La borne optionnelle couvre donc les mouvements de solde prouvés
pour reconstruire ce pic, sans inventer un flottant non observé. Dix tests
propres/de jonction capturent ces cas, la persistance et la causalité.

Rayon de la carte : consommateurs directs 3, 5a, 5b, 6, transitif 4.
Après gel 1b, revalider 3, 4, 5a, 5b et 6 dans cet ordre, puis gate global et
checkpoint. Les adaptateurs 2a/2b/2c ne seront gelés qu'après stabilisation du
bloc. L'infrastructure est arrêtée entre CP1 et son premier gate de couche 2 ;
le code 90 du garde local est une pause planifiée, pas un test rendu vert.

Le producteur natif doit signaler un solde encore inexpliqué comme flux externe
non neutralisé. Ce point est finalisé dans le contrat 2c avant son premier gel,
en portant le solde réellement lu au callback de rapprochement. Aucun montant
ou historique inconnu n'est assimilé à zéro.

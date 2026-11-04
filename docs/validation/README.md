# Validation et portée des preuves

Le [rapport de réorganisation](verification_projet.json) contient trois passes : conservation et cohérence des ressources ; contrôles des fonctions et contrats ; préparation Git du futur merge. La commande `python tools/verify_project.py --git` régénère un rapport courant dans `.local/reports/verification_projet.json` sans modifier cette copie d'audit.

Les contrôles n'ont besoin d'aucun accès API ou courtier. Les tests d'horaires, d'indicateurs, de causalité des détecteurs et de contrats IA utilisent des données synthétiques. Ils ne démontrent ni la précision sémantique d'un fournisseur jamais appelé ni une hausse de rentabilité.

| Preuve conservée | Portée |
|---|---|
| [Conservation des ressources](conservation_ressources.json) | Empreintes des paramètres, de la source utilisateur, des sections normatives et des fonctions déplacées |
| [Diagnostic technique historique](diagnostic_faisabilite_v3.json) | Comptages et financement du volume minimal ; aucun P&L ou fill réel |
| [Provenance du diagnostic](provenance_diagnostic_v3.json) | Empreintes et chemins historiques des données désormais archivées ; ces chemins décrivent l'ancien workspace |
| [Snapshot public Deriv](snapshot_public_Deriv_2026-11-04.json) | Informations publiques datées ; disponibilité, frais et pas à vérifier sur le vrai compte standard |
| [Provenance de l'étude IA](provenance_IA_v1.json) | Sources et date de revue ; zéro appel d'inférence et aucune validation financière |

Les anciens rapports de 143 contrôles IA et de 155 contrôles techniques restent dans l'archive du nettoyage avec leurs scripts et données d'origine. Les contrôles actuels ont été adaptés au rangement et à des séries synthétiques autonomes ; leurs effectifs sont ceux du nouveau rapport. Les anciens résultats ne sont pas présentés comme de nouveaux tests.

La qualité de classement des API, le comportement du futur robot sur ticks et la validation financière sont encore à réaliser selon les spécifications. La [demande de données](../data/03_Donnees_Historiques_Requises_et_Validation.md) précise ce qui manque.

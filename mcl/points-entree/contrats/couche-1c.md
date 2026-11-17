# Couche 1c — rejeu C10 et archive des résultats (finalisé avant code)

API publique : lancer_rejeu(configuration, document, fichier, *, autorisation=None)
rend un dictionnaire resultat/rapport/archive. Le document xp-demande-rejeu-v1
porte exactement demande (DemandeRejeu sans callback), manifeste (ManifesteTicks),
conditions (ConditionContrat), scenario_fondamental, receptions (paires instant et
ReceptionExterne), table_heure (document S01 ou None), factures, et schema.
Les profils passent par le constructeur C04 public avant l'ouverture des prix.
encoder_rejeu et decoder_rejeu utilisent TYPES_REJEU, liste explicite de classes
figées ; charger_archive(octets, configuration) contrôle le format et les
configurations puis restitue le contenu. fabriquer_controles(configuration,
scenario, receptions=(), table_heure=None) rend la fabrique fraîche attendue par
le moteur C10 et son rejeu, avec sources horodatées liées aux vrais acteurs.

Lancer une demande C10 explicite sur le vrai bloc c2_executeur, avec le lecteur
gzip de l'infrastructure et les configurations figées effectivement chargées.
Le bloc, les conditions contractuelles datées, le manifeste, le scénario de
coût, les factures IA et le régime fondamental sont des entrées vérifiées ;
aucun profil ne se déduit des prix. Les coûts viennent de charger_protocole.
La fabrique London est celle du composant construit, sans stratégie de doublure.

L'ouverture de la source de prix et son itération restent différées derrière
RegistreReserve. Une option expresse et un gel attesté sont requis avant toute
lecture recouvrant le réservé, préchargement compris. Les calendriers,
permissions et snapshots historiques portent leurs réceptions d'origine ; le
contrôle neutre doit être nommé et ne valide jamais C04/C10/A13.

Le résultat réel est archivé par le codec fermé avec une liste explicite de
types C10. Aucune fonction n'est sérialisée ou importée depuis les données.
L'autorisation contenant un callback est remplacée par None dans la copie de
la demande archivée ; l'option, l'empreinte et le journal d'ouverture sont
conservés comme données. Recharger l'archive ne donne jamais l'autorisation de
relancer un test réservé. Les configurations de l'archive doivent égaler la
configuration de confiance, et sa dérivée calculée par appliquer_ecart ; une
simple chaîne d'empreinte identique ne suffit pas à accepter des valeurs changées.

L'archive expose la demande, le résultat, les empreintes physiques/contenu
vérifiées et les entrées originales de contrôle nécessaires au rejeu. Les
commandes de rapports réutilisent ce format. Une seule implémentation C10 et
une seule implémentation des rapports ; les résultats synthétiques restent
NON_VALIDE. La lecture/écriture physique est confinée à l'infrastructure.

Catégorie 1 : lecture réservée interdite avant ouverture, types et configuration
altérés refusés, archive sans callback et sans effet d'autorisation, coûts
REFERENCE/STRESS et erreurs de provenance. Catégorie 2 : vrai Londres, vrais
contrôles, gzip temporaire et rapports réels ; archive/rechargement/rejeu à
résultat identique sans SDK.

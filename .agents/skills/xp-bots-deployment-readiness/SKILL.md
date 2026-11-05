---
name: xp-bots-deployment-readiness
description: "Décision de mise en service des robots XP-Bots : étapes PAPER, PAPER_AB, démonstration prospective et compte réel, critères d'entrée et de sortie de chaque étape (C04, C10, A13), activation d'un veto IA réel seulement après validation financière, arrêts quotidien et global persistants et reprise par décision tracée, alertes opérationnelles déterministes, redémarrage et rapprochement, secrets et .env, registre de déploiement. Utiliser avant tout passage en démo ou en réel, pour une checklist go/no-go, ou après un arrêt. Déclencheurs : déploiement, mise en production, démo, compte réel, live, go/no-go, mise en service, arrêt persistant, kill switch, alerte, redémarrage, surveillance, secrets, clés API."
---

# Préparation au déploiement (go / no-go)

## Ressources

- Autorité : C01 (aucune ouverture de compte ni ordre réel sans décision), C04, C07 (gardes), C08
  (redémarrage), C10 (démonstration prospective), A01, A12 et A13 (activation du veto réel), A11 (alertes).
- Modes : `default_mode` dans `config/parametres_figes_v3.json`, `default_evaluation_mode` et
  `live_veto_requires_financial_validation` dans `config/parametres_IA_integration_v1.json`.
- Secrets : gabarit `.env.example` ; valeurs privées seulement dans `.env`, ignoré par Git.

## Workflow

1. Établir l'étape visée et ses prérequis : PAPER (robot construit, tests C11/A14 verts) ; démo prospective
   (compte qualifié par `xp-bots-broker-account-qualification`, journal C09 complet) ; réel (critères C10 sur le
   test réservé et la démo, décision humaine tracée). Un prérequis non prouvé donne « no-go ».
2. Vérifier les sécurités avant d'activer : gardes quotidienne et globale persistantes, verrou de propriété en
   netting, rapprochement au redémarrage avant toute décision, alertes déterministes affichées localement.
3. Vérifier le complément IA : mode `PAPER_AB` tant que A13 n'est pas établi ; tout veto réel exige la validation
   financière ; changement de modèle ou dérive → suspension des vetos réels.
4. Vérifier l'environnement : clés présentes seulement pour les routes qualifiées, secours payant désactivé
   sauf décision explicite, aucune recharge automatique, budget transactionnel actif.
5. Produire la checklist datée (go / no-go par critère, preuve, responsable) hors des preuves historiques ;
   rejouer `python tools/verify_project.py` pour confirmer que les contrats du dépôt sont intacts.

## Garde-fous

- Aucun agent n'ouvre de compte, ne connecte d'identifiants ni ne passe d'ordre réel : la décision et l'action
  appartiennent à l'humain.
- Un arrêt global à −10 % du pic ne se lève jamais par redémarrage logiciel : nouvelle décision de déploiement
  tracée.
- Des contrôles hors ligne verts ne valent ni validation financière ni autorisation de passage en réel.
- Ne jamais afficher, journaliser ou committer un secret ; les rapports ne contiennent ni solde ni numéro de
  compte.

# Couche 3 — Lecteur du contexte IA

Statut : finalisé avant code le 09/11/2026 après CP2 ; 0, 1 et 2 figées. Consommateur : couture S4.

| Élément | Contrat |
|---|---|
| Unité | lecteur_contexte |
| Responsabilité | Fournir le veto facultatif au port réel du coordinateur, avec politique explicite |
| Signature | LecteurContexte(parametres, politique, etat=None), evaluer(symbole, instant_ms), description(symbole, instant_ms) |
| Entrée | ParametresContexte chargés, PolitiqueVeto, EtatCache éventuel ; octets reçus et temps logique |
| Sortie | DecisionContexteIA canonique BLOCK avec ID ou NEUTRAL ; description JSON de la preuve |
| Effets de bord | Cache mémoire explicite ; aucun appel, fichier, permission ni commande |
| Erreurs | ErreurContexte pour appel/reprise hors contrat ; recevoir rend le rejet de la couche 2 |

Le lecteur implémente le vrai port LecteurContexteIA de c0b_controles. `recevoir`, `avancer`,
`prochaine_echeance_ms` et `etat` délèguent au cache réel 2 ; `politique` est consultable.
Le bras de référence (bras_ia faux) reste NEUTRAL. En exécution réelle, le veto reste NEUTRAL
si la configuration exige une validation financière et que celle-ci manque. En papier, ou après
cette validation, le premier veto actif trié par ID donne BLOCK. Aucun état ALLOW n'existe.
Les champs de politique sont des booléens stricts ; l'appel à evaluer valide temps et symbole,
même lorsque la politique est neutre. Aucun veto ne devient connu avant sa réception effective.

`description` rend une copie indépendante : politique, décision et événement retenu, métadonnées
du dernier snapshot reçu (séquence, hash, génération et réception), vetos pertinents avec ID,
item, fournisseur, bornes, première connaissance et hash de preuve. Une requête antérieure à la
dernière réception masque ces métadonnées futures ; les preuves alors connues restent causales.
Ce n'est pas un historique de tous les heartbeats. Les octets originaux restent dans EtatCache.
La reprise ne réinfère rien et ne renouvelle aucune échéance. Le journal ne reçoit aucun secret.

Tests propres : test_cat1_c3_contexte.py ; jonction réelle 0→3 et oracle : test_cat2_c3_contexte.py.
A14-2/7/16 : cache et reprise ; A14-8 : NEUTRAL n'autorise pas C05 (couture) ; L-15 : couture.
La comparaison à overlay_decision porte sur ses chemins représentatifs valides et rejets ; sa
sortie prématurée sur une liste mixte malformée est une limite documentée au contrat 1, jamais
un motif pour accepter partiellement un snapshot invalide. La référence reste inchangée.

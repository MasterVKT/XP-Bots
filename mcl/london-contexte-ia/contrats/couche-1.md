# Couche 1 — Validation intégrale d'un snapshot

Statut : finalisé avant code, 09/11/2026 ; 0 figée. Consommateur : 2. Sources : A10, A12 et D-13.

| Élément | Contrat |
|---|---|
| Unité | snapshot |
| Responsabilité | Refuser un snapshot invalide avant tout ajout au cache |
| Signature | decoder_snapshot(octets, reception_ms, parametres, derniere_sequence=0) → SnapshotRecu |
| Entrée | Octets exacts ou absence, réception réelle, ParametresContexte réel, dernier entier persisté |
| Sortie | Snapshot intégralement validé avec ses octets originaux et sa réception |
| Effets de bord | Aucun état, fichier, horloge ou inférence |
| Erreurs | ErreurSnapshot(ErreurContexte), attribut raison ; appel mal typé de temps/paramètres : ErreurContexte |

La taille est vérifiée avant décodage, à la borne inclusive max_octets. L'enveloppe ne contient
que payload/sha256 ; payload ne contient que schema/sequence/generated_at_utc/integration_digest/events.
SHA-256 du JSON canonique exact, schéma xp-ai-context-v1 et empreinte IA chargée exigés. La séquence
est un entier positif au moins égal à la dernière persistée ; l'identité d'une relecture appartient à 2.
Génération non future et âge au plus age_max_ms, égalité admise. La réception n'est jamais remplacée
par la génération.

Chaque événement a les sept champs A10 exacts, un ID représentable en C09, la raison autorisée,
un fournisseur chargé et des symboles de l'univers chargé. Heures UTC en ms ; valid_from ≤ génération,
valid_until > valid_from. Un événement déjà expiré peut figurer dans un heartbeat frais sans redevenir
actif. La publication ne figure pas dans l'IPC : sa relation à valid_until appartient au producteur A06.
Deux occurrences identiques du même ID sont tolérées ; des occurrences contradictoires sont refusées.

Toute la liste est validée avant retour : un événement mal formé après un premier actif invalide
le snapshot entier. La référence overlay_decision court-circuite ce cas ; cette limite de l'oracle
est testée explicitement et n'est pas reproduite. Aucun nouveau veto n'est créé sur erreur.

Raisons de rejet : ABSENT, TAILLE, JSON, SCHEMA, EMPREINTE, CONFIGURATION, SEQUENCE, FUTUR, PERIME,
EVENEMENT. Ce sont des diagnostics d'ingestion, pas des motifs d'autorisation ou de refus C09.
Tests : `test_cat1_c1_snapshot.py` et `test_cat2_c1_snapshot.py`, bornes, altérations et jonction réelle.

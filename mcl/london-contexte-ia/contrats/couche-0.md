# Couche 0 — Types de contexte IA

Statut : finalisé avant code le 09/11/2026. Consommateurs : 1, 2 et 3. Dépend de : noyau canonique.

| Élément | Contrat |
|---|---|
| Unité | types_contexte |
| Responsabilité | Valeurs immuables, paramètres chargés, UTC en ms et JSON strict/canonique A10 |
| Signature | charger_parametres(configuration) ; canonique(objet), empreinte(objet), decoder_objet(octets) ; valeurs ci-dessous |
| Entrée | ConfigurationFigee réelle, JSON représentable, octets UTF-8, champs typés |
| Sortie | ParametresContexte, octets canoniques/SHA-256 ou valeurs immuables |
| Effets de bord | Aucun fichier, horloge, réseau, état global mutable ni inférence |
| Erreurs | ErreurContexte(ValueError), booléens jamais entiers, valeurs structurelles incohérentes refusées |

`ParametresContexte(max_octets, age_max_ms, empreinte_integration, fournisseurs, symboles,
validation_financiere_requise)` est créé depuis l'export IA et l'univers technique chargés.
Les seuils ne sont jamais recopiés ; l'empreinte est celle du JSON canonique IA.

`Veto(event_id, symboles, valid_from_ms, valid_until_ms, item_id, provider_id, reason_code)` conserve
la raison OFFICIAL_UNSCHEDULED_POLICY. L'ID doit être représentable dans AI_CONTEXT_VETO/C09 ;
symboles uniques non vides, intervalle strictement positif, textes UTF-8 non vides. La couche 1
vérifie l'univers, le fournisseur et la relation au temps de génération.

`SnapshotIA(sequence, genere_ms, empreinte_integration, vetos, empreinte_payload, octets)` conserve
les octets originaux permettant une revalidation de reprise, les deux SHA-256 et la liste immuable.
Séquence entière positive. Le schéma, la taille, les clés, le hash et l'âge sont vérifiés en 1.
`SnapshotRecu(snapshot, reception_ms)` garde la réception réelle, au plus tôt à la génération.
`VetoConnu(veto, connu_ms, preuve)` relie un veto à son vrai snapshot reçu et à sa réception exacte.

`PolitiqueVeto(bras_ia, execution_reelle=False, validation_financiere=False)` porte trois booléens
stricts. Elle ne crée ni permission fondamentale, ni ordre ; son effet appartient à 3.

`instant`, `entier`, `texte`, `sha256_hex`, `utc` et `en_ms` sont des primitives structurelles.
UTC suit le noyau : décalage nul, précision représentable en millisecondes. `canonique` emploie
UTF-8, clés triées, séparateurs sans espaces et aucun NaN/infini ; `decoder_objet` exige une racine
objet et rejette toutes les clés dupliquées, même imbriquées, les constantes non finies et l'UTF-8
invalide. La taille avant analyse reste la responsabilité de 1.

Spécification exécutable : `tests/robot/london_contexte_ia/test_cat1_c0_types.py`.
Comportements documentés : export de collections immuables, ordre des symboles conservé,
conservation des octets et absence d'interprétation des heures par l'horloge du poste.

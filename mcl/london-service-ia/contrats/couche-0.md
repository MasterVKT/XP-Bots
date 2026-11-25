# Couche 0 — types et ressources

Statut : contrat finalisé le 17/11/2026 avant implémentation.
Consommateurs cartographiés : les onze unités du service.
Dépend de : configuration et primitives publiques du lecteur IA canoniques.

Unité : types.
Responsabilité : représenter les ressources figées, documents, travaux et échanges externes.
Signature : RessourcesIA(configuration, schema_extraction, schema_notes, prompts),
DocumentIA(item_id,url,issuer,titre,texte,publie_ms,premiere_vue_ms,collecte_ms,
couverture='COMPLETE',version_parseur='rss-v1',officiel=True),
RequeteHTTP(url,methode,entetes,corps,timeout_s,max_octets,fournisseur=None),
ReponseHTTP(statut,entetes,corps,recu_ms),
JobIA(job_id,kind,item_id,cree_ms,utile_jusqua_ms,dossier,evidence_ids=(),fournisseur=None),
ResultatIA(job_id,fournisseur,recu_ms,valide=None,erreur=None), et ports DepotIA/HorlogeIA.
Entrée : configuration déjà chargée, ressources JSON strictes en octets UTF-8,
instants UTC en millisecondes et valeurs explicites, sans secret.
Sortie : valeurs immuables, propriétés de ressources décodées en copies, JSON
canonique et empreintes réutilisant les primitives publiques existantes.
Effets de bord : aucun fichier, horloge, base, fil ou réseau.
Erreurs, exceptions : ErreurService, sous-classe de ValueError ; booléens à la
place des entiers, décimaux négatifs/non finis, JSON dupliqué/non fini, dates
incohérentes, URL non HTTPS ou contenant des identifiants et en-têtes secrets refusés.

## Spécification exécutable

test_cat1_c0_types.py vérifie ressources, immutabilité, défauts, bornes et ports.
La feuille n’a aucune catégorie 2. Le gel porte sur cette fiche, son interface
publique et ses tests ; l’implémentation reste révisable sous harnais.

## Comportements documentés

Les valeurs métier viennent exclusivement de ConfigurationFigee. Le service
conserve les schémas et prompts originaux et n’en corrige aucune contrainte.
La date de publication peut être absente ou future : le document est alors
documentaire, sans admissibilité au veto ; sa collecte doit rester causale.
La borne de texte n’est jamais obtenue par découpe d’une négation ou condition.
Les octets du dossier sont archivables ; aucun numéro de compte ni clé n’y est
ajouté par ces types. Les clés d’authentification relèvent seulement du transport.

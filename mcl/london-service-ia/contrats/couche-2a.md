# Couche 2a — veto

Statut : contrat finalisé le 17/11/2026 après CP1, avant code.
Consommateurs cartographiés : planificateur.
Dépend de : types, validation.

Unité : veto.
Responsabilité : Construire le seul veto A06 après validation et appariement causal du calendrier.
Signature : CorrespondanceCalendrier(id_evenement,issuer,genre),
TableAppariement(fournisseur,version,known_at_ms,complete,correspondances),
AppariementCalendrier(valide,correspondance,raison=None,version_calendrier=None,
version_mapping=None,empreinte_calendrier=None,empreinte_mapping=None),
apparier_calendrier(ressources,garde,table,document,recu_ms,*,source_valide),
construire_veto(ressources,sortie,document,provided_text,recu_ms,fournisseur,appariement).
Entrée : ressources, document et sortie d’extraction, garde GardeAnnonces réelle,
table externe connue à l’instant, disponibilité actuelle de la source calendrier.
Sortie : appariement causal avec preuves de versions ; événement A06 égal à
l’oracle sur ses entrées conformes, ou None lorsque le veto n’est pas admissible.
Effets de bord : aucun I/O, ordre, permission, clôture ou modification d’un état.
Erreurs, exceptions : ErreurService pour données et chronologie invalides.
Calendrier indisponible, périmé, non couvert, mapping incomplet ou futur donnent
un appariement invalide ; aucun veto n’est ajouté.

## Spécification exécutable

test_cat1_c2a_veto.py couvre A14-3 à A14-6, origine, citations, instants,
expiration et bornes d’appariement. test_cat2_c2a_veto.py traverse GardeAnnonces,
les vrais types et validateur ; comparaison à build_policy_event sans oracle
dans le code d’exécution. Le lecteur physique D12 est en couche 4.

## Comportements documentés

La table lie les IDs natifs à un issuer configuré ou OTHER, et au genre
POLICY_DECISION exporté ou OTHER. Elle est complète, versionnée, liée au même
fournisseur que le calendrier et connue avant la réception validée. Tous les
IDs HIGH de la version doivent être mappés. Une devise incompatible invalide
le mapping ; une politique d’issuer inconnu dans une devise suivie ne prouve
pas l’absence d’une décision de l’issuer recherché.

Le calendrier est choisi par version_connue, sans accès privé. Fraîcheur et
horizon viennent des communs C05. La recherche est fermée à ± la durée A06 :
la couverture, dont la fin est exclusive, doit contenir les deux bornes. Une
correspondance exige même issuer, HIGH et genre monétaire ; discours, autres
types et autres issuers ne suffisent pas. source_valide=false garde l’extension
neutre même si une ancienne version structurée est encore dans le cache.

Le constructeur revalide A05. Il exige source officielle configurée, classe
et temporalité exactes, acteur identique à l’issuer, stance admissible et
citation assez longue. Publication, première vue, collecte et réception sont
causales ; une date non qualifiée reste documentaire. La fenêtre est
[réception validée, publication + durée exportée), sans rétroactivité ni
prolongation. L’identité utilise item_id et première vue originaux. Les symboles
sont dérivés de la currency de l’issuer et de devises_pour, dans l’ordre de
l’univers figé : cela reproduit exactement A06 sans seconde table concurrente.

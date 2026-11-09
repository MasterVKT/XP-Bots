# Couche 0 — Types fondamentaux

Statut : contrat finalisé avant code, 09/11/2026. Sources : C05, D-11 et D-12.

## Interface

`ErreurFondamental(ValueError)` représente une entrée structurelle refusée.
`DirectionFondamentale` porte ANY, LONG_ONLY, SHORT_ONLY ; `EtatRisque` porte ALLOW, NO_NEW, FLATTEN.
`MessagePermission(symbole, sequence, issued_at_ms, known_at_ms, valid_from_ms, valid_until_ms,
direction, risk_state, model_version, input_snapshot_id)` est une valeur immuable ; la réception
locale est conservée par son consommateur. Les combinaisons temporelles C05 sont validées en 1a.

`TableImportance(fournisseur, version, hautes)` identifie une classification externe versionnée ;
ses valeurs natives hautes sont explicitement fournies, jamais devinées.
`Annonce(id_valeur, id_evenement, code, nom, devise, importance, type, secteur, heure_serveur,
instant_ms, revision, known_at_ms)` conserve les champs natifs et UTC ainsi que sa connaissance.
`VersionCalendrier(version, export_ms, reception_ms, couverture, annonces, table, empreinte)`
conserve une version complète immuable et sa provenance ; `couverture` est l'Intervalle du noyau.

`decoder_json_strict(octets)` rend un objet JSON UTF-8 à clés uniques et sans constante non finie.
Les nombres décimaux sont lus exactement ; l'objet racine doit être un dictionnaire. Aucun fichier
n'est ouvert. Les consommateurs contrôlent ensuite les clés et types propres à leur protocole.
`millisecondes(secondes)` convertit exactement les durées entières de la configuration, sans seuil.
`entier(valeur, minimum=0)`, `instant(valeur)` et `texte(valeur)` vérifient les valeurs structurelles partagées.
`devises_pour(symbole)` rend exactement EUR+USD, GBP+USD ou USD pour les trois symboles C05.

## Garanties et refus

Les booléens ne valent jamais des entiers. Identifiants numériques natifs et séquences sont positifs ;
instants et révisions sont non négatifs. Les textes obligatoires ne sont ni vides ni exclusivement
blancs et sont encodables en UTF-8. Énumérations et collections sont normalisées en valeurs immuables.
Les doublons d'id_valeur d'un calendrier, une annonce connue après réception, une réception avant
export, un mauvais type, une empreinte non SHA-256 ou un symbole hors table sont refusés.

Aucune valeur C05 de durée n'est recopiée. Les objets ne consultent ni horloge, ni source externe.
La table de devises cite la règle C05 et fait l'objet d'un test exact ; elle n'est pas une déduction
à partir d'un nom de symbole. La comparaison de fraîcheur et les décisions métier appartiennent aux
couches consommatrices. Le gel couvre cette fiche, l'interface publique et les tests catégorie 1.

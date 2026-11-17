# Couche 3 — codec durable des valeurs publiques

Statut : finalisé le 10/11/2026 avant code, après le nouveau gel de 2.
Unité : codec ; dépend de 0, 1, 2 et des types publics des amonts gelés.
Consommateurs cartographiés : stockage de session, reprise et rapports de phase 11.
Responsabilité : représenter en JSON canonique les valeurs immuables du moteur,
son checkpoint et ses entrées, sans interpréter une règle de trading.
Signature : `serialiser_valeur(valeur, *, types_supplementaires=()) -> bytes` ;
`deserialiser_valeur(octets, *, types_supplementaires=()) -> valeur`.
Entrée : valeurs publiques, ou octets UTF-8 stricts portant le schéma
`xp-valeur-persistante-v1` ; types supplémentaires explicitement fournis par le
code du consommateur sous forme de couples (nom public, classe de valeur).
Sortie : octets canoniques sans saut de ligne ; ou reconstruction typée exacte.
Effets de bord : aucun fichier, horloge, réseau, SDK, import dynamique ou état
global mutable. Les configurations ne sont pas rechargées par le codec.
Erreurs : `ErreurOrchestration` pour format, version, clés, type, nombre ou valeur
non admis. Les champs et sceaux des états sont vérifiés par leurs API publiques.

## Format et garanties

L’enveloppe contient exactement `schema` et `valeur`. Les conteneurs et types
spéciaux portent une étiquette explicite : les tuples, listes, ensembles et
mappings ne se confondent pas. Les mappings conservent leurs clés typées, sans
collision ni doublon. Les chaînes, booléens, entiers et valeurs nulles restent
distincts. Aucun nombre non fini n’est admis, y compris après reconstruction.

Decimal garde sa représentation décimale, sans changer le contexte global.
Un flottant fini garde ses bits par sa forme hexadécimale. Dates, heures et
datetimes gardent leurs formes ISO ; UTC, décalages fixes, Europe/London et fold
sont conservés, y compris à la répétition d’heure britannique. Les octets gardent
leur contenu exact en hexadécimal. Les collections sans ordre sont classées sur
la forme canonique de leurs valeurs avant encodage.

Les objets portent un nom de classe public appartenant à un registre fermé et
exactement les champs publics de leur dataclass. Le document ne désigne jamais
un module à importer, une fonction à appeler ou un attribut privé. Enums et
dataclasses sont reconstruits par leurs constructeurs réels, sans bypass de leur
validation. Les registres supplémentaires sont des dépendances de code trusted,
pas des données du document : noms uniques, aucun remplacement du registre natif,
classes de valeur seulement. Une fabrique, un moteur ou une fonction n’est pas
sérialisable.

Les doublons JSON sont refusés à tous les niveaux, ainsi que champs inconnus,
étiquettes inconnues, versions étrangères, nombres non finis et objets non
autorisés. Un mauvais sceau d’EtatMoteur ou de CheckpointMoteur est rejeté. Le
stockage et le contrôle des empreintes de configuration restent responsables de
la provenance ; le codec n’ajoute aucune authentification cryptographique.

Tests : `test_cat1_c3_codec.py` et `test_cat2_c3_codec.py`. Catégorie 1 : valeurs,
bornes, fuseaux, corruption et documents hostiles. Catégorie 2 : vrais états et
journaux London A/B, restauration et rejeu sur backend interdit. Les frontières
externes seules sont doublées ; aucun modèle ou terminal n’est appelé.

Extension tracée du 10/11/2026 : jonction des états MARCHE dynamiques de 2,
avec reprise du checkpoint décodé et rejeu des entrées décodées sans backend.
Les types, signatures et format du codec restent identiques ; le champ flux
opaque est validé par le moteur qui le possède. Test test_cat2_c3_marche.py.
## Extension D-09

Le registre fermé inclut CheckpointJournalMoteur, défini par la couche 2. Sa
désérialisation appelle verifier(), comme pour les checkpoints antérieurs. Les
schémas, types supplémentaires, refus d'import dynamique et octets canoniques
restent inchangés. Tests : aller-retour du vrai checkpoint léger, corruption du
sceau et comparaison au checkpoint reconstruit par le rejeu réel.

## Extension P11-15 : engagements des contrôles courants

Finalisée après le nouveau gel de 2 du 14/11/2026 et avant son test : les
champs opaques fondamental et ia du checkpoint de journal contiennent les
engagements courants définis par 2. Le codec les conserve exactement, sans
réinterpréter les permissions ou les veto. Les entrées archivées décodées
doivent reconstruire les mêmes sorties, le même checkpoint court et les mêmes
historiques complets C05 et IA, avec le backend interdit. Le checkpoint court
ne devient pas une autorisation de restaurer directement un moteur.
Test de jonction : test_cat2_c3_checkpoint_journal.py, réceptions répétées et
aller-retour des entrées, des sorties et des deux formes de checkpoint.
